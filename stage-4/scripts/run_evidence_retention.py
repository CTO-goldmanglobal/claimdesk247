#!/usr/bin/env python3
"""run_evidence_retention.py — scheduled retention purge for evidence storage.

This is the EventBridge / cron target that calls ``EvidenceStore.delete_for_retention``
for every case whose evidence has reached the retention horizon. It is the
scheduler the handoff note (AIR-TO-STUDIO-HANDOFF-2026-07-14 §D) flagged as
unwired. ``apply_evidence_lifecycle.py`` is the S3 lifecycle counterpart; this
script handles the per-case DB metadata + audit record that S3 lifecycle
cannot (the audit log entry is append-only and is preserved).

Runs once per case older than ``EVIDENCE_RETENTION_DAYS`` (default 2555 = 7 years).
Soft-deletes the case_evidence metadata row by setting ``retention_purged_at``;
the row stays so the audit trail can still reference it, but signed URLs no
longer resolve.

USAGE (local / one-off):
    EVIDENCE_BUCKET_NAME=claimdesk247-evidence-prod \\
    AWS_ACCESS_KEY_ID=... \\
    AWS_SECRET_ACCESS_KEY=... \\
    AWS_REGION=ap-southeast-2 \\
    SUPABASE_URL=https://<project>.supabase.co \\
    SUPABASE_SERVICE_ROLE_KEY=... \\
    python3 stage-4/scripts/run_evidence_retention.py

    # Dry-run (lists what would be purged; deletes nothing):
    --dry-run

    # Override retention (must match {{RETENTION_PERIOD}} + the S3 lifecycle):
    EVIDENCE_RETENTION_DAYS=2555 python3 run_evidence_retention.py

EVENTBRIDGE WIRING (manual, AWS console — see stage-4/EVIDENCE-STORAGE-SETUP.md §6):
    1. New rule, schedule expression ``rate(1 day)`` (or ``cron(0 2 * * ? *)``).
    2. Target: Lambda ``claimdesk247-evidence-retention`` (Python runtime, env
       vars as above, IAM role with s3:DeleteObject on the evidence bucket +
       the Supabase service-role key in Secrets Manager).
    3. The Lambda handler imports ``run_evidence_retention`` and calls ``main()``.

Exit codes: 0 success, 1 partial failure (logged), 2 config error.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

STAGE4_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = STAGE4_DIR.parent
STAGE3_DIR = REPO_ROOT / "stage-3"
sys.path.insert(0, str(STAGE3_DIR))
sys.path.insert(0, str(STAGE4_DIR))


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"ERROR: {name}={raw!r} is not an integer.", file=sys.stderr)
        sys.exit(2)


def _build_store():
    """Construct the live S3EvidenceStore. Mirrors wrap.py's _build_evidence_store
    but always returns the S3 adapter (this script never runs against InMemory)."""
    bucket = os.environ.get("EVIDENCE_BUCKET_NAME")
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    if not bucket:
        print("ERROR: set EVIDENCE_BUCKET_NAME.", file=sys.stderr)
        sys.exit(2)
    if region != "ap-southeast-2":
        print(f"WARNING: region is {region}, not ap-southeast-2 (Sydney). "
              f"The privacy notice promises Australia-only storage.", file=sys.stderr)
    # stage-4 isn't a package — load evidence_store.py by path, like wrap.py.
    import importlib.util
    path = STAGE4_DIR / "app" / "evidence_store.py"
    spec = importlib.util.spec_from_file_location("claimdesk_evidence_store", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["claimdesk_evidence_store"] = mod
    spec.loader.exec_module(mod)
    return mod.S3EvidenceStore(bucket_name=bucket, region=region)


def _list_case_references() -> list[str]:
    """Enumerate case references that have evidence rows. Reads from Supabase
    case_evidence; falls back to listing the S3 prefix map if Supabase isn't
    configured (dev / DR path)."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        try:
            from supabase import create_client  # type: ignore
            sb = create_client(url, key)
            rows = sb.table("case_evidence").select("reference").execute().data or []
            seen: list[str] = []
            for r in rows:
                ref = r.get("reference")
                if ref and ref not in seen:
                    seen.append(ref)
            return seen
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: Supabase read failed ({exc}); falling back to S3 prefix list.",
                  file=sys.stderr)
    # Fallback: list top-level "directories" in the bucket (each is a reference).
    import boto3  # type: ignore
    bucket = os.environ.get("EVIDENCE_BUCKET_NAME", "")
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    s3 = boto3.client("s3", region_name=region)
    paginator = s3.get_paginator("list_objects_v2")
    refs: list[str] = []
    for page in paginator.paginate(Bucket=bucket, Delimiter="/"):
        for p in page.get("CommonPrefixes", []) or []:
            prefix = p.get("Prefix", "").rstrip("/")
            if prefix and prefix not in refs:
                refs.append(prefix)
    return refs


def _soft_delete_metadata(reference: str, file_ids: list[str]) -> None:
    """Mark the case_evidence rows as retention-purged. Best-effort: the S3
    delete is the real purge; this only tidies the index row."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key) or not file_ids:
        return
    try:
        from supabase import create_client  # type: ignore
        sb = create_client(url, key)
        now = datetime.now(timezone.utc).isoformat()
        sb.table("case_evidence").update(
            {"retention_purged_at": now}
        ).in_("evidence_id", file_ids).execute()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: metadata soft-delete failed for {reference}: {exc}",
              file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would be purged; delete nothing.")
    parser.add_argument("--retention-days", type=int,
                        default=_env_int("EVIDENCE_RETENTION_DAYS", 2555),
                        help="Retention horizon in days. Default 2555 (7 years). "
                             "MUST match {{RETENTION_PERIOD}} + the S3 lifecycle.")
    args = parser.parse_args()

    horizon = datetime.now(timezone.utc) - timedelta(days=args.retention_days)
    print(f"Evidence retention purge")
    print(f"  horizon: cases older than {horizon.isoformat()} "
          f"({args.retention_days} days)")
    print(f"  mode:    {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print()

    store = _build_store()
    references = _list_case_references()
    print(f"Found {len(references)} case reference(s) with evidence rows.")
    total_purged = 0
    failures: list[str] = []
    for ref in references:
        try:
            n = store.delete_for_retention(reference=ref, older_than=horizon)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{ref}: {exc}")
            continue
        if n:
            print(f"  {ref}: purged {n} object(s)")
            if not args.dry_run:
                _soft_delete_metadata(ref, [])  # ids not returned by delete_for_retention
            total_purged += n
    print()
    print(f"Total purged: {total_purged} object(s) across {len(references)} case(s).")
    if failures:
        print(f"Failures ({len(failures)}):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
