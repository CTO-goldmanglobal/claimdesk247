#!/usr/bin/env python3
"""Sign the rule trees — close the G-PROD-LOCK / G-VER sign-off gate.

This is the legal-sign-off tool. Legal Head reviews each rule tree's content
and, on approval, the operator runs this script to stamp every scenario in a
tree with `legal_signoff: {approved: true, version: <hash>, by, date}`.

The hash is the SAME one the engine enforces at runtime
(`app.engine._compute_scenarios_hash` — SHA-256 of the scenarios[] array with
each scenario's `legal_signoff` field stripped). So a signed tree's sign-off
is bound to its logical content: any later edit to a scenario invalidates the
sign-off and the engine re-escalates (G-VER / stale-signoff).

Why a script (not hand-edited hashes):
- The hash is invariant under sign-off mutation (legal_signoff is stripped),
  so the script is IDEMPOTENT — running it twice produces the same result.
- Per-tree hashing (spec §1.2) means trees are signed independently as Legal
  Head approves each one.
- The output is auditable: git diff on the JSON shows exactly which scenarios
  gained a sign-off block, by whom, and when.
- Sits next to `preflight.py` as the deploy-time governance pair.

Usage:
    # Sign one tree
    python3 stage-4/scripts/sign_rule_trees.py --tree motor \\
        --by "Jane Citizen, Practising Certificate NSW 1234" \\
        --date 2026-07-05

    # Sign all trees at once (after Legal Head approves all)
    python3 stage-4/scripts/sign_rule_trees.py --all \\
        --by "Jane Citizen, Practising Certificate NSW 1234" \\
        --date 2026-07-05

    # Verify (read-only) that every signed scenario's hash matches current content
    python3 stage-4/scripts/sign_rule_trees.py --verify

Exit code: 0 on success, 1 if any tree fails to load or (in --verify mode) any
sign-off is stale/missing.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the engine importable so we use the EXACT hash the runtime enforces.
STAGE3_DIR = Path(__file__).resolve().parent.parent.parent / "stage-3"
sys.path.insert(0, str(STAGE3_DIR))

from app.engine import (  # noqa: E402  (path setup above)
    RULE_TREE_REGISTRY, _compute_scenarios_hash, _load_rule_tree_for,
)

DATA_DIR = STAGE3_DIR / "app" / "data"


def _load_tree_from_disk(claim_type: str) -> dict:
    """Load the tree fresh from disk (bypassing the lru_cache)."""
    filename = RULE_TREE_REGISTRY[claim_type]
    with (DATA_DIR / filename).open() as f:
        return json.load(f)


def _sign_tree(claim_type: str, by: str, date: str) -> tuple[int, str]:
    """Sign every scenario in one tree. Returns (n_scenarios_signed, hash).

    Idempotent: re-running with the same content produces the same sign-off
    block (the hash doesn't depend on the sign-off metadata). Re-running after
    a content change re-stamps with the new hash (a re-sign)."""
    tree = _load_tree_from_disk(claim_type)
    h = _compute_scenarios_hash(tree)
    n = 0
    for s in tree["scenarios"]:
        s["legal_signoff"] = {
            "approved": True,
            "version": h,
            "by": by,
            "date": date,
        }
        n += 1
    # Write back, preserving the registry filename.
    filename = RULE_TREE_REGISTRY[claim_type]
    out_path = DATA_DIR / filename
    with out_path.open("w") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return n, h


def _verify_tree(claim_type: str) -> tuple[bool, str]:
    """Read-only check: does every signed scenario's version match the current
    content hash? Returns (all_ok, detail)."""
    tree = _load_tree_from_disk(claim_type)
    current_hash = _compute_scenarios_hash(tree)
    scenarios = tree.get("scenarios", [])
    signed_ok = 0
    stale = 0
    unsigned = 0
    for s in scenarios:
        so = s.get("legal_signoff")
        if not isinstance(so, dict) or so.get("approved") is not True:
            unsigned += 1
            continue
        if so.get("version") == current_hash:
            signed_ok += 1
        else:
            stale += 1
    total = len(scenarios)
    live = (signed_ok == total)
    detail = (f"{claim_type}: {signed_ok}/{total} signed-ok, "
              f"{unsigned} unsigned, {stale} stale, hash={current_hash[:12]}, "
              f"live={'true' if live else 'false'}")
    return live, detail


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--tree", choices=sorted(RULE_TREE_REGISTRY),
                   help="Sign a single tree")
    g.add_argument("--all", action="store_true",
                   help="Sign all trees in the registry")
    g.add_argument("--verify", action="store_true",
                   help="Read-only: check every signed scenario's hash matches current content")
    p.add_argument("--by", help='Sign-off identity (e.g. "Jane Citizen, PC NSW 1234"). Required for --tree/--all.')
    p.add_argument("--date", help="Sign-off date (YYYY-MM-DD). Defaults to today (UTC).")
    args = p.parse_args()

    if args.verify:
        print("Verifying rule-tree sign-off state (read-only)...")
        all_ok = True
        for ct in sorted(RULE_TREE_REGISTRY):
            ok, detail = _verify_tree(ct)
            print(f"  [{'OK' if ok else 'STALE/MISSING'}] {detail}")
            if not ok:
                all_ok = False
        if all_ok:
            print("\nAll trees live (every scenario carries a current sign-off).")
            return 0
        print("\nOne or more trees are NOT live — unsigned or stale scenarios present.")
        return 1

    if not args.by:
        p.error("--by is required when signing (use --verify for a read-only check)")
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    trees = sorted(RULE_TREE_REGISTRY) if args.all else [args.tree]
    print(f"Signing rule trees: {', '.join(trees)}")
    print(f"  by: {args.by}")
    print(f"  date: {date}")
    print()
    for ct in trees:
        n, h = _sign_tree(ct, args.by, date)
        print(f"  [SIGNED] {ct}: {n} scenarios stamped, hash={h[:16]}…, "
              f"file={RULE_TREE_REGISTRY[ct]}")
    print("\nDone. Re-run with --verify to confirm all trees are live.")
    print("Commit the signed JSON files to record the sign-off event.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
