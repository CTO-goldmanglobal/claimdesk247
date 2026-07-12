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
    DEFAULT_CLAIM_TYPE, DEFAULT_STATE, RULE_TREE_REGISTRY,
    _compute_scenarios_hash, _load_rule_tree_for,
)

DATA_DIR = STAGE3_DIR / "app" / "data"


def _registry_keys() -> list[tuple[str, str]]:
    """All (state, claim_type) keys in the registry, sorted by (state, claim_type)."""
    return sorted(RULE_TREE_REGISTRY.keys(), key=lambda k: (k[0], k[1]))


def _format_key(state: str, claim_type: str) -> str:
    """Human-readable key for CLI output: 'NSW.motor', 'VIC.property_damage'."""
    return f"{state}.{claim_type}"


def _parse_key(s: str) -> tuple[str, str]:
    """Parse a CLI selector like 'NSW.motor' or 'VIC.property_damage' into a
    (state, claim_type) tuple. Backward-compat: a bare claim_type ('motor')
    is interpreted as NSW.<claim_type>."""
    if "." in s:
        state, ct = s.split(".", 1)
        return (state.upper(), ct)
    # Backward-compat: bare claim_type → NSW claim_type
    return (DEFAULT_STATE, s)


def _load_tree_from_disk(state: str, claim_type: str) -> dict:
    """Load the tree fresh from disk (bypassing the lru_cache)."""
    filename = RULE_TREE_REGISTRY[(state, claim_type)]
    with (DATA_DIR / filename).open() as f:
        return json.load(f)


def _sign_tree(state: str, claim_type: str, by: str, date: str) -> tuple[int, str]:
    """Sign every scenario in one tree. Returns (n_scenarios_signed, hash).

    Idempotent: re-running with the same content produces the same sign-off
    block (the hash doesn't depend on the sign-off metadata). Re-running after
    a content change re-stamps with the new hash (a re-sign)."""
    tree = _load_tree_from_disk(state, claim_type)
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
    filename = RULE_TREE_REGISTRY[(state, claim_type)]
    out_path = DATA_DIR / filename
    with out_path.open("w") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return n, h


def _verify_tree(state: str, claim_type: str) -> tuple[bool, str]:
    """Read-only check: does every signed scenario's version match the current
    content hash? Returns (all_ok, detail)."""
    tree = _load_tree_from_disk(state, claim_type)
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
    label = _format_key(state, claim_type)
    detail = (f"{label}: {signed_ok}/{total} signed-ok, "
              f"{unsigned} unsigned, {stale} stale, hash={current_hash[:12]}, "
              f"live={'true' if live else 'false'}")
    return live, detail


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    # --tree accepts a selector. Forms: 'NSW.motor', 'VIC.property_damage', or
    # bare 'motor' (interpreted as NSW.motor for backward compat with the
    # original single-state CLI).
    key_choices = [_format_key(st, ct) for (st, ct) in _registry_keys()]
    legacy_choices = [ct for (st, ct) in _registry_keys() if st == DEFAULT_STATE]
    all_choices = sorted(set(key_choices) | set(legacy_choices))
    g.add_argument("--tree", choices=all_choices,
                   help="Sign a single tree. Selector forms: '<STATE>.<claim_type>' "
                        "(e.g. 'VIC.property_damage') or bare '<claim_type>' "
                        "(interpreted as NSW.<claim_type> for backward compat).")
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
        for (st, ct) in _registry_keys():
            ok, detail = _verify_tree(st, ct)
            print(f"  [{'OK' if ok else 'STALE/MISSING'}] {detail}")
            if not ok:
                all_ok = False
        if all_ok:
            print("\nAll trees live (every scenario carries a current sign-off).")
            return 0
        print("\nOne or more trees are NOT live — unsigned or stale scenarios present.")
        print("Unsigned trees are EXPECTED for new states staged before Legal Head sign-off "
              "(per MULTI-STATE-ROLLOUT-PLAN.md).")
        return 1

    if not args.by:
        p.error("--by is required when signing (use --verify for a read-only check)")
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.all:
        trees = _registry_keys()
    else:
        trees = [_parse_key(args.tree)]
    print(f"Signing rule trees: {', '.join(_format_key(st, ct) for (st, ct) in trees)}")
    print(f"  by: {args.by}")
    print(f"  date: {date}")
    print()
    for (st, ct) in trees:
        n, h = _sign_tree(st, ct, args.by, date)
        print(f"  [SIGNED] {_format_key(st, ct)}: {n} scenarios stamped, hash={h[:16]}…, "
              f"file={RULE_TREE_REGISTRY[(st, ct)]}")
    print("\nDone. Re-run with --verify to confirm all trees are live.")
    print("Commit the signed JSON files to record the sign-off event.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
