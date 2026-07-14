#!/usr/bin/env python3
"""apply_evidence_lifecycle.py — opt-in S3 lifecycle rule for the evidence bucket.

Applies the two-tier lifecycle agreed 2026-07-14 (user-confirmed):
  * Standard → Glacier Deep Archive after 90 days
  * Glacier Deep Archive → Expire (delete) after RETENTION_PERIOD days
    (default 7 years = 2555 days; MUST match the engine's {{RETENTION_PERIOD}})

WHY: this is the cost + retention mechanism for evidence storage. At 500GB
blended, the lifecycle makes the bucket ~$3-5 AUD/mo instead of ~$13 AUD/mo,
and enforces automatic deletion at the legal retention horizon.

USAGE (opt-in — run once after creating the bucket; re-runnable):
    EVIDENCE_BUCKET_NAME=claimdesk247-evidence-prod \\
    AWS_ACCESS_KEY_ID=... \\
    AWS_SECRET_ACCESS_KEY=... \\
    AWS_REGION=ap-southeast-2 \\
    python3 stage-4/scripts/apply_evidence_lifecycle.py

    # Override retention (must match {{RETENTION_PERIOD}}):
    EVIDENCE_RETENTION_DAYS=2555 python3 apply_evidence_lifecycle.py

    # Dry-run (prints the rule, does not apply):
    --dry-run

This script is idempotent: re-running it replaces the bucket's lifecycle
configuration with the version computed here. It will NOT delete existing
objects; it only sets the rule that governs future transitions.

Required IAM permission: s3:PutLifecycleConfiguration on the bucket.
"""
from __future__ import annotations

import argparse
import os
import sys


def build_lifecycle_rule(retention_days: int) -> dict:
    """The two-tier lifecycle rule.

    The `id` is stable so re-applying the rule replaces (not appends to) the
    existing config — AWS matches by rule id.
    """
    return {
        "Rules": [
            {
                "ID": "claimdesk247-evidence-two-tier",
                "Status": "Enabled",
                "Filter": {"Prefix": ""},  # all objects in the bucket
                "Transitions": [
                    {
                        "Days": 90,
                        "StorageClass": "GLACIER_DEEP_ARCHIVE",
                    },
                ],
                "Expiration": {"Days": retention_days},
                "NoncurrentVersionExpiration": {"NoncurrentDays": retention_days},
            }
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the rule, do not apply.")
    parser.add_argument("--retention-days", type=int,
                        default=int(os.environ.get("EVIDENCE_RETENTION_DAYS", "2555")),
                        help="Retention horizon in days. Default 2555 (7 years). "
                             "MUST match {{RETENTION_PERIOD}}.")
    args = parser.parse_args()

    bucket = os.environ.get("EVIDENCE_BUCKET_NAME")
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    if not bucket:
        print("ERROR: set EVIDENCE_BUCKET_NAME (see .env.example).", file=sys.stderr)
        return 2
    if region != "ap-southeast-2":
        print(f"WARNING: region is {region}, not ap-southeast-2 (Sydney). "
              f"The privacy notice promises Australia-only storage.", file=sys.stderr)

    rule = build_lifecycle_rule(args.retention_days)
    print(f"Bucket: {bucket}")
    print(f"Region: {region}")
    print(f"Retention: {args.retention_days} days ({args.retention_days / 365:.1f} years)")
    print(f"Lifecycle rule:")
    import json
    print(json.dumps(rule, indent=2))

    if args.dry_run:
        print("\n--dry-run: not applying.")
        return 0

    try:
        import boto3
    except ImportError:
        print("ERROR: boto3 is not installed. Run: pip install boto3>=1.34",
              file=sys.stderr)
        return 2

    client = boto3.client("s3", region_name=region)
    client.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration=rule,
    )
    print(f"\nApplied. Verify in the AWS console → S3 → {bucket} → Management → "
          f"Lifecycle configuration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
