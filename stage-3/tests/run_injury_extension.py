#!/usr/bin/env python3
"""Personal-Injury Extension acceptance tests.

Spec: claimdesk-injury-extension-INSTRUCTIONS-2026-07-03.md
Extends the 99/99 motor discipline with four test families:

  (a) Per-scenario unsigned → escalation for both new trees (PL pl1-pl6,
      med-neg mn1-mn7). Every new scenario ships with an empty legal_signoff,
      so the engine MUST escalate (unsigned-scenario) until Legal Head signs.
  (b) Med-neg escalation-dominance: NO med-neg substantive scenario emits a
      likely/possible band in v1, even if signed. s5O standard-of-care is
      expert-evidence territory.
  (c) Hash-isolation: mutating the PL tree does NOT stale the motor sign-off,
      and PL scenarios go stale-signoff when their tree changes.
  (d) Per-tree hashing + registry: three independent trees load with distinct
      hashes; /healthz reports the rule_tree_versions map.

This suite is invoked by run_acceptance.py::main() after the Stage-3 motor
suite. Exit 0 iff all green.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Callable

# Make the engine importable when run standalone.
STAGE3_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STAGE3_DIR))

from app import engine as _eng
from app.engine import (
    DEFAULT_CLAIM_TYPE, LIMITATION_BUFFER_YEARS, MEDNEG_TREATMENT_TYPE_TO_SCENARIO,
    PD_COLLISION_TYPE_TO_SCENARIO, PL_HAZARD_TYPE_TO_SCENARIO, RULE_TREE_REGISTRY, classify,
    _claim_type_for_scenario_id, _compute_scenarios_hash, _load_rule_tree,
    _load_rule_tree_for, _resolve_scenario,
)


REPORT_PATH = STAGE3_DIR / "deliverables" / "injury-extension-test-report.txt"


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _base_intake(claim_type: str) -> dict[str, Any]:
    """A minimal NSW intake for the given claim_type with no escalation
    signals (no injury, recent date, no govt defendant, etc.) so the only
    thing left is the sign-off gate."""
    base = {"state": "NSW", "claim_type": claim_type, "injuries": "none",
            "harm_severity": "none", "incident_date": "2026-06-01"}
    return base


def _signed_tree(claim_type: str) -> dict[str, Any]:
    """Return a deep copy of the claim_type's tree with EVERY scenario signed
    against the current content hash. Used to test what the engine would do
    once Legal Head has signed the tree."""
    tree = copy.deepcopy(_load_rule_tree_for(claim_type))
    h = _compute_scenarios_hash(tree)
    for s in tree["scenarios"]:
        s["legal_signoff"] = {"approved": True, "version": h,
                              "by": "Legal Head (test)", "date": "2026-07-04"}
    return tree


def _classify_with_tree(intake: dict[str, Any], fake_tree: dict[str, Any]) -> Any:
    """Run classify() with a specific tree patched in for the resolved
    (state, claim_type). Restores the real loader afterwards.

    Multi-state (per MULTI-STATE-ROLLOUT-PLAN.md): the typed loader is now
    keyed by (state, claim_type); the patch must accept both positional args.
    NSW motor still goes through the zero-arg loader."""
    import app.engine as engmod
    ct = intake.get("claim_type", DEFAULT_CLAIM_TYPE)
    if ct == "motor":
        real = engmod._load_rule_tree
        real.cache_clear()
        engmod._load_rule_tree = lambda: fake_tree  # type: ignore[assignment]
        try:
            return classify(intake)
        finally:
            engmod._load_rule_tree = real  # type: ignore[assignment]
            real.cache_clear()
    real_typed = engmod._load_rule_tree_typed
    real_typed.cache_clear()
    engmod._load_rule_tree_typed = lambda _state, _ct: fake_tree  # type: ignore[assignment]
    try:
        return classify(intake)
    finally:
        engmod._load_rule_tree_typed = real_typed  # type: ignore[assignment]
        real_typed.cache_clear()


def _unsigned_tree(claim_type: str) -> dict[str, Any]:
    """A deep copy of the claim_type's tree with EVERY sign-off stripped
    (approved=False, empty version). Used to exercise the G-PROD-LOCK gate
    mechanism regardless of the live sign-off state — once Legal Head has
    signed the live trees, this patched copy is what proves the gate still
    rejects unsigned content."""
    tree = copy.deepcopy(_load_rule_tree_for(claim_type))
    for s in tree["scenarios"]:
        s["legal_signoff"] = {"approved": False, "version": "", "by": "", "date": ""}
    return tree


# -----------------------------------------------------------------------
# Family (a): per-scenario unsigned → escalation
# -----------------------------------------------------------------------

def _test_pl_all_unsigned_escalate() -> tuple[bool, str]:
    """Every PL scenario pl1-pl6 escalates as unsigned-scenario when the PL
    tree is unsigned. Once the live tree is signed (Legal Head 2026-07-05),
    this is proven by patching in an unsigned copy — the gate mechanism, not
    the live sign-off state, is what's under test."""
    tree = _unsigned_tree("public_liability")
    results = []
    for hazard, sid in PL_HAZARD_TYPE_TO_SCENARIO.items():
        intake = _base_intake("public_liability")
        intake["hazard_type"] = hazard
        er = _classify_with_tree(intake, tree)
        if er.escalation != "unsigned-scenario":
            results.append(f"{sid}: expected unsigned-scenario, got {er.escalation!r}")
    if results:
        return False, "; ".join(results)
    return True, f"all {len(PL_HAZARD_TYPE_TO_SCENARIO)} PL hazard types → unsigned-scenario (via patched unsigned tree)"


def _test_medneg_all_unsigned_escalate() -> tuple[bool, str]:
    """Every med-neg scenario mn1-mn7 escalates as unsigned-scenario when the
    med-neg tree is unsigned. Once the live tree is signed (Legal Head
    2026-07-05), this is proven by patching in an unsigned copy — the gate
    mechanism, not the live sign-off state, is what's under test."""
    tree = _unsigned_tree("medical_negligence")
    results = []
    for treat, sid in MEDNEG_TREATMENT_TYPE_TO_SCENARIO.items():
        intake = _base_intake("medical_negligence")
        intake["treatment_type"] = treat
        er = _classify_with_tree(intake, tree)
        if er.escalation != "unsigned-scenario":
            results.append(f"{sid}: expected unsigned-scenario, got {er.escalation!r}")
    if results:
        return False, "; ".join(results)
    return True, f"all {len(MEDNEG_TREATMENT_TYPE_TO_SCENARIO)} med-neg treatment types → unsigned-scenario (via patched unsigned tree)"


# -----------------------------------------------------------------------
# Family (b): med-neg escalation-dominance (no likely/possible even if signed)
# -----------------------------------------------------------------------

def _test_medneg_never_bands_likely_or_possible() -> tuple[bool, str]:
    """Even if the med-neg tree were fully signed, NO substantive med-neg
    scenario emits a likely/possible band. s5O standard-of-care is expert
    evidence — the engine must never auto-band it."""
    tree = _signed_tree("medical_negligence")
    violations = []
    for treat, sid in MEDNEG_TREATMENT_TYPE_TO_SCENARIO.items():
        intake = _base_intake("medical_negligence")
        intake["treatment_type"] = treat
        # Give it a plausible harm so it's not the no-harm filter path.
        intake["harm_severity"] = "serious"
        intake["injuries"] = "serious"
        er = _classify_with_tree(intake, tree)
        # esc-injury fires first (serious), which is correct escalation dominance.
        # The assertion is: the engine NEVER returns band in (likely, possible)
        # for a med-neg scenario, regardless of path.
        if er.band in ("likely", "possible"):
            violations.append(f"{sid}: emitted band={er.band} (forbidden for med-neg)")
    if violations:
        return False, "; ".join(violations)
    return True, "no med-neg scenario emits likely/possible (escalation-dominant)"


def _test_medneg_no_harm_filter() -> tuple[bool, str]:
    """Hard filter: no harm at all → unclear band (no compensable damage),
    still human-reviewed. This is the ONE deterministic med-neg resolution."""
    tree = _signed_tree("medical_negligence")
    intake = _base_intake("medical_negligence")
    intake["treatment_type"] = "surgical_outcome"
    intake["harm_severity"] = "none"
    intake["injuries"] = "none"
    er = _classify_with_tree(intake, tree)
    # With no harm and a signed tree, the engine resolves to unclear (the
    # med-neg band helper returns "unclear" for all mn scenarios).
    if er.band == "unclear":
        return True, "no-harm med-neg → unclear (hard filter, human-reviewed)"
    if er.escalation:
        return True, f"no-harm med-neg → escalated ({er.escalation}) — still human-reviewed"
    return False, f"no-harm med-neg produced band={er.band!r} escalation={er.escalation!r}"


# -----------------------------------------------------------------------
# Family (c): hash-isolation between trees
# -----------------------------------------------------------------------

def _test_hash_isolation_pl_change_does_not_stale_motor() -> tuple[bool, str]:
    """Mutating the PL tree must NOT change the motor tree's hash or sign-off
    state. This is the whole point of per-tree hashing (spec §1.2)."""
    motor_tree = _load_rule_tree_for("motor")
    motor_hash_before = _compute_scenarios_hash(motor_tree)

    # Build a mutated PL tree (add a cosmetic field to a scenario).
    pl_tree = copy.deepcopy(_load_rule_tree_for("public_liability"))
    pl_tree["scenarios"][0]["_test_mutation"] = "cosmetic-change"
    pl_hash_mutated = _compute_scenarios_hash(pl_tree)
    pl_hash_original = _compute_scenarios_hash(_load_rule_tree_for("public_liability"))

    # Reload motor (uncached) and re-hash.
    motor_hash_after = _compute_scenarios_hash(_load_rule_tree_for("motor"))

    if motor_hash_before != motor_hash_after:
        return False, "motor hash changed across PL mutation (isolation broken)"
    if pl_hash_mutated == pl_hash_original:
        return False, "PL hash did NOT change after mutation (hash not content-bound)"
    return True, (f"motor hash stable ({motor_hash_before[:8]}) across PL mutation; "
                  f"PL hash changed ({pl_hash_original[:8]} → {pl_hash_mutated[:8]})")


def _test_pl_stale_signoff_after_mutation() -> tuple[bool, str]:
    """A PL scenario signed against the original tree goes stale-signoff when
    the PL tree's content changes. Motor sign-off is untouched."""
    pl_original = _load_rule_tree_for("public_liability")
    h_original = _compute_scenarios_hash(pl_original)

    # Sign pl1 against the original hash.
    pl_signed = copy.deepcopy(pl_original)
    for s in pl_signed["scenarios"]:
        if s["id"] == "pl1-slip-wet-surface":
            s["legal_signoff"] = {"approved": True, "version": h_original,
                                  "by": "Legal Head (test)", "date": "2026-07-04"}

    # Mutate the PL tree (change a scenario's body).
    pl_mutated = copy.deepcopy(pl_signed)
    pl_mutated["scenarios"][0]["name"] = "Slip on a wet surface (MUTATED)"

    intake = _base_intake("public_liability")
    intake["hazard_type"] = "wet_surface"
    er = _classify_with_tree(intake, pl_mutated)
    if er.escalation != "stale-signoff":
        return False, f"expected stale-signoff after PL mutation, got {er.escalation!r}"
    return True, "PL scenario signed-then-mutated → stale-signoff (sign-off bound to content)"


# -----------------------------------------------------------------------
# Family (d): registry + per-tree hashing
# -----------------------------------------------------------------------

def _test_registry_three_distinct_trees() -> tuple[bool, str]:
    """The registry loads three trees with distinct hashes."""
    hashes = {}
    for ct in ("motor", "public_liability", "medical_negligence"):
        tree = _load_rule_tree_for(ct)
        hashes[ct] = _compute_scenarios_hash(tree)
    if len(set(hashes.values())) != 3:
        return False, f"hashes not distinct: {hashes}"
    return True, f"3 trees, 3 distinct hashes: {[h[:8] for h in hashes.values()]}"


def _test_claim_type_routing() -> tuple[bool, str]:
    """Scenario id prefixes route to the correct (state, claim_type).

    Multi-state (per MULTI-STATE-ROLLOUT-PLAN.md): _claim_type_for_scenario_id
    now returns a (state, claim_type) tuple. NSW scenario ids keep their bare
    prefixes (s/pd/pl/mn) for backward compat; non-NSW scenario ids carry the
    state in the prefix (vic-pdN-...)."""
    checks = {
        "s1-rear-end": ("NSW", "motor"),
        "s11-parked-vehicle": ("NSW", "motor"),
        "pl1-slip-wet-surface": ("NSW", "public_liability"),
        "pl6-other-public-place": ("NSW", "public_liability"),
        "mn1-surgical-outcome": ("NSW", "medical_negligence"),
        "mn4-birth-injury": ("NSW", "medical_negligence"),
        "pd1-rear-end": ("NSW", "property_damage"),
        "vic-pd1-rear-end": ("VIC", "property_damage"),
        "qld-pd1-rear-end": ("QLD", "property_damage"),
        "wa-pd1-rear-end": ("WA", "property_damage"),
        "sa-pd1-rear-end": ("SA", "property_damage"),
        "tas-pd1-rear-end": ("TAS", "property_damage"),
        "act-pd1-rear-end": ("ACT", "property_damage"),
        "nt-pd1-rear-end": ("NT", "property_damage"),
    }
    bad = [(sid, want, _claim_type_for_scenario_id(sid))
           for sid, want in checks.items()
           if _claim_type_for_scenario_id(sid) != want]
    if bad:
        return False, f"routing mismatches: {bad}"
    return True, f"all {len(checks)} scenario-id → (state, claim_type) routes correct"


def _test_new_escalation_triggers() -> tuple[bool, str]:
    """The 4 new injury-extension triggers fire for their gating conditions."""
    results = []
    # esc-serious-injury (all claim types)
    er = classify({**_base_intake("public_liability"), "hazard_type": "wet_surface",
                   "harm_severity": "death"})
    if er.escalation != "esc-serious-injury":
        results.append(f"serious-injury/death: got {er.escalation!r}")
    # esc-workers-comp (PL)
    er = classify({**_base_intake("public_liability"), "hazard_type": "wet_surface",
                   "at_work": "yes"})
    if er.escalation != "esc-workers-comp":
        results.append(f"workers-comp: got {er.escalation!r}")
    # esc-govt-defendant (PL)
    er = classify({**_base_intake("public_liability"), "hazard_type": "wet_surface",
                   "defendant_type": "council"})
    if er.escalation != "esc-govt-defendant":
        results.append(f"govt-defendant: got {er.escalation!r}")
    # esc-limitation (PL, old date)
    er = classify({**_base_intake("public_liability"), "hazard_type": "wet_surface",
                   "incident_date": "2020-01-01"})
    if er.escalation != "esc-limitation":
        results.append(f"limitation: got {er.escalation!r}")
    if results:
        return False, "; ".join(results)
    return True, "all 4 new triggers (serious-injury, workers-comp, govt-defendant, limitation) fire"


def _test_motor_backward_compat_no_claim_type() -> tuple[bool, str]:
    """A motor intake with NO claim_type still resolves to s1-rear-end and
    behaves as before the extension (backward compat with all motor tests).

    Pre-2026-07-05 this asserted unsigned-scenario. Post Legal Head sign-off
    (2026-07-05) the motor tree is live, so the same intake now returns
    band='likely' for a clear rear-end. The backward-compat guarantee under
    test is ROUTING (s1-rear-end) and that the extension didn't change motor
    behavior — the sign-off state is orthogonal to that."""
    er = classify({"state": "NSW", "accident_type": "rear-end", "injuries": "none"})
    if er.scenario_id != "s1-rear-end":
        return False, f"expected s1-rear-end, got {er.scenario_id!r}"
    # With the motor tree now signed, a clear rear-end bands as 'likely'.
    # (If the motor tree were unsigned, er.escalation would be 'unsigned-scenario'
    # — both states confirm routing succeeded; only the gate differs.)
    if er.escalation == "unsigned-scenario":
        return True, "motor intake without claim_type → s1-rear-end, unsigned-scenario (tree not yet signed)"
    if er.band != "likely":
        return False, f"motor rear-end (signed) expected band='likely', got band={er.band!r} escalation={er.escalation!r}"
    return True, "motor intake without claim_type → s1-rear-end, band='likely' (tree signed 2026-07-05)"


# -----------------------------------------------------------------------
# Family (e): Property Damage (Lane 1 beachhead, spec 2026-07-05)
# THIRD-PARTY-MOTOR-CLAIM-FOCUS / HOW-TO-WIN-3P-MOTOR. PD ships unsigned like
# the other trees, but unlike med-neg it IS deterministically bandable once
# signed (rear-end/give-way/reversing have settled liability patterns). The
# injury firewall is the red line: any injury → esc-injury → PI pathway,
# never a PD band, never monetized per-referral.
# -----------------------------------------------------------------------

def _test_pd_all_unsigned_escalate() -> tuple[bool, str]:
    """Every PD scenario pd1-pd7 escalates as unsigned-scenario when the PD
    tree is unsigned. Once the live tree is signed (Legal Head 2026-07-05),
    this is proven by patching in an unsigned copy — the gate mechanism, not
    the live sign-off state, is what's under test."""
    tree = _unsigned_tree("property_damage")
    results = []
    seen_scenarios = set()
    for col, sid in PD_COLLISION_TYPE_TO_SCENARIO.items():
        seen_scenarios.add(sid)
        intake = _base_intake("property_damage")
        intake["collision_type"] = col
        er = _classify_with_tree(intake, tree)
        if er.escalation != "unsigned-scenario":
            results.append(f"{sid} (collision={col}): expected unsigned-scenario, got {er.escalation!r}")
    if results:
        return False, "; ".join(results)
    return True, (f"all {len(seen_scenarios)} PD scenarios → unsigned-scenario "
                 f"(across {len(PD_COLLISION_TYPE_TO_SCENARIO)} collision-type aliases, via patched unsigned tree)")


def _test_pd_injury_firewall() -> tuple[bool, str]:
    """Injury firewall: ANY injury mention in a PD intake routes to esc-injury,
    never to a PD band. This is the red line that keeps Lane 1 (property) clean
    of Lane 2 (CTP injury / claim-farming) exposure. Hard test across all
    collision types AND both injury severities."""
    violations = []
    for col in ("rear-end", "give_way", "reversing", "parked_hit", "car_park"):
        for inj in ("minor", "serious"):
            intake = _base_intake("property_damage")
            intake["collision_type"] = col
            intake["injuries"] = inj
            er = classify(intake)
            if er.escalation != "esc-injury":
                violations.append(f"{col}+injuries={inj}: expected esc-injury, got "
                                  f"escalation={er.escalation!r} band={er.band!r}")
            if er.band is not None:
                violations.append(f"{col}+injuries={inj}: emitted band={er.band!r} (forbidden — injury must firewall)")
    if violations:
        return False, "; ".join(violations)
    return True, "all PD collision types × {minor,serious} → esc-injury, no band (firewall holds)"


def _test_injury_firewall_fail_closed() -> tuple[bool, str]:
    """IX-12 P1-1 fix (2026-07-14 review): the injury firewall MUST fail closed.
    Pre-fix the engine matched literally (serious|minor only), so any non-enum
    truthy value (`yes`, `True`, `whiplash`, `1`) bypassed the firewall and
    got a band. Now: anything that isn't exactly 'none' (case-insensitive) or
    absent escalates as esc-injury. This is the CD-R2 PD §1 'any injury
    mention' invariant."""
    violations = []
    # PD clear rear-end intake that would normally band 'likely'.
    base = _base_intake("property_damage")
    base["collision_type"] = "rear-end"
    base["user_position"] = "front"
    base["user_motion"] = "stopped"
    base["chain_count"] = 2
    # Sanity: with injuries='none' this bands likely (proves the test setup).
    er_none = classify({**base, "injuries": "none"})
    if er_none.escalation == "esc-injury" or er_none.band is None:
        return False, (f"baseline broken: injuries='none' should band, got "
                       f"esc={er_none.escalation!r} band={er_none.band!r}")
    # Each of these MUST escalate — fail-closed.
    for inj in ("yes", True, 1, "whiplash", "hospitalised", "minor ", "SERIOUS",
                "unknown", "maybe", "y", "t"):
        er = classify({**base, "injuries": inj})
        if er.escalation != "esc-injury":
            violations.append(f"injuries={inj!r}: expected esc-injury, "
                              f"got esc={er.escalation!r} band={er.band!r}")
        if er.band is not None:
            violations.append(f"injuries={inj!r}: emitted band={er.band!r} (forbidden)")
    # Absent injuries should NOT trip the firewall (none of the firewall tests
    # in this suite set injuries on the no-injury path).
    # (Note: 'None' value is treated as absent → not injury-positive.)
    if violations:
        return False, "; ".join(violations)
    return True, ("fail-closed: 10 non-enum injury values all → esc-injury; "
                  "'none' still bands normally")


def _test_pd_limitation_per_state() -> tuple[bool, str]:
    """IX-12b P1-2 fix (2026-07-14 review): per-state PD limitation enforcement.
    NT has a 3-year limitation (Limitation Act 1981); all other AU states 6
    years. Pre-fix, PD was exempt from esc-limitation — an NT intake 4 years
    old (statute-barred) would band 'likely'. Now: NT > 2.5 yr → esc-limitation;
    NSW > 5.5 yr → esc-limitation; recent intakes still band normally."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    # 4 years ago — past NT's 3yr bar (with our 6mo buffer = 2.5yr horizon).
    four_yr_ago = (now - timedelta(days=365 * 4)).strftime("%Y-%m-%d")
    # 1 year ago — well within every state's horizon.
    one_yr_ago = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    # 7 years ago — past everyone's 6yr bar.
    seven_yr_ago = (now - timedelta(days=365 * 7)).strftime("%Y-%m-%d")

    base = _base_intake("property_damage")
    base["collision_type"] = "rear-end"
    base["user_position"] = "front"
    base["user_motion"] = "stopped"
    base["chain_count"] = 2

    violations = []
    # NT 4yr → statute-barred → esc-limitation.
    er = classify({**base, "state": "NT", "incident_date": four_yr_ago})
    if er.escalation != "esc-limitation":
        violations.append(f"NT 4yr: expected esc-limitation, got {er.escalation!r} band={er.band!r}")
    if er.band is not None:
        violations.append(f"NT 4yr: emitted band={er.band!r} (forbidden — statute-barred)")
    # NSW 4yr → within 6yr → should band normally.
    er = classify({**base, "state": "NSW", "incident_date": four_yr_ago})
    if er.escalation == "esc-limitation":
        violations.append(f"NSW 4yr: should band, got esc-limitation")
    # NSW 7yr → past 6yr → esc-limitation.
    er = classify({**base, "state": "NSW", "incident_date": seven_yr_ago})
    if er.escalation != "esc-limitation":
        violations.append(f"NSW 7yr: expected esc-limitation, got {er.escalation!r}")
    # NT 1yr → within 3yr → bands normally.
    er = classify({**base, "state": "NT", "incident_date": one_yr_ago})
    if er.escalation == "esc-limitation":
        violations.append(f"NT 1yr: should band, got esc-limitation")
    # All states 7yr → esc-limitation.
    for st in ("VIC", "QLD", "WA", "SA", "TAS", "ACT"):
        er = classify({**base, "state": st, "incident_date": seven_yr_ago})
        if er.escalation != "esc-limitation":
            violations.append(f"{st} 7yr: expected esc-limitation, got {er.escalation!r}")
    if violations:
        return False, "; ".join(violations)
    return True, ("NT 4yr→esc-limitation; NSW 4yr bands; NSW/NT 7yr→esc-limitation; "
                  "all 6yr-states 7yr→esc-limitation")


def _test_pd_uninsured_driver_trigger() -> tuple[bool, str]:
    """The PD-specific esc-uninsured-driver trigger fires when the at-fault
    driver is uninsured or cover is unknown — recovery shifts to the user's
    own insurer, which is a different matter path."""
    for val in ("yes", "unsure"):
        intake = _base_intake("property_damage")
        intake["collision_type"] = "rear-end"
        intake["at_fault_uninsured"] = val
        er = classify(intake)
        if er.escalation != "esc-uninsured-driver":
            return False, f"at_fault_uninsured={val!r}: expected esc-uninsured-driver, got {er.escalation!r}"
    # 'no' must NOT trigger it (driver is insured — normal recovery path)
    intake_ok = _base_intake("property_damage")
    intake_ok["collision_type"] = "rear-end"
    intake_ok["at_fault_uninsured"] = "no"
    er_ok = classify(intake_ok)
    if er_ok.escalation == "esc-uninsured-driver":
        return False, "at_fault_uninsured='no' wrongly triggered esc-uninsured-driver"
    return True, "esc-uninsured-driver fires for yes/unsure, not for 'no'"


def _test_pd_hash_isolation_from_motor_and_others() -> tuple[bool, str]:
    """Mutating the PD tree must NOT change motor, PL, or med-neg hashes.
    Extends IX-05's isolation property to the 4-tree registry."""
    hashes_before = {ct: _compute_scenarios_hash(_load_rule_tree_for(ct))
                     for ct in ("motor", "property_damage", "public_liability", "medical_negligence")}

    pd_mutated = copy.deepcopy(_load_rule_tree_for("property_damage"))
    pd_mutated["scenarios"][0]["_test_mutation"] = "cosmetic-change"
    pd_hash_after = _compute_scenarios_hash(pd_mutated)

    hashes_after = {ct: _compute_scenarios_hash(_load_rule_tree_for(ct))
                    for ct in ("motor", "property_damage", "public_liability", "medical_negligence")}

    if pd_hash_after == hashes_before["property_damage"]:
        return False, "PD hash did NOT change after mutation (hash not content-bound)"
    for ct in ("motor", "public_liability", "medical_negligence"):
        if hashes_before[ct] != hashes_after[ct]:
            return False, f"{ct} hash changed across PD mutation (isolation broken)"
    return True, (f"PD hash changed ({hashes_before['property_damage'][:8]} → {pd_hash_after[:8]}); "
                  f"motor/PL/med-neg hashes stable")


def _test_pd_signed_bands_deterministically() -> tuple[bool, str]:
    """UNLIKE med-neg (IX-03), PD IS deterministically bandable once signed —
    that's the whole point of the Lane 1 beachhead (settled liability patterns).
    With a fully-signed PD tree, a clear rear-end (user in front, stopped) must
    return band='likely', and the catch-all pd7-other must cap at 'unclear'."""
    tree = _signed_tree("property_damage")
    violations = []

    # Clear liability: user in front, stopped, 2-car rear-end → likely
    intake_clear = _base_intake("property_damage")
    intake_clear["collision_type"] = "rear-end"
    intake_clear["user_position"] = "front"
    intake_clear["user_motion"] = "stopped"
    intake_clear["chain_count"] = 2
    er_clear = _classify_with_tree(intake_clear, tree)
    if er_clear.band != "likely":
        violations.append(f"clear rear-end: expected likely, got band={er_clear.band!r}")

    # User was the following driver → possible (not the recovery side)
    intake_behind = _base_intake("property_damage")
    intake_behind["collision_type"] = "rear-end"
    intake_behind["user_position"] = "behind"
    intake_behind["user_motion"] = "moving"
    intake_behind["chain_count"] = 2
    er_behind = _classify_with_tree(intake_behind, tree)
    if er_behind.band != "possible":
        violations.append(f"following driver: expected possible, got band={er_behind.band!r}")

    # Catch-all pd7-other must cap at unclear (never likely/possible)
    intake_other = _base_intake("property_damage")
    intake_other["collision_type"] = "other"
    er_other = _classify_with_tree(intake_other, tree)
    if er_other.band not in ("unclear", None) or er_other.band == "likely":
        violations.append(f"pd7-other: expected unclear, got band={er_other.band!r}")

    if violations:
        return False, "; ".join(violations)
    return True, "signed PD bands deterministically: clear=likely, following=possible, other=unclear"


def _test_pd_routing_and_registry_four_trees() -> tuple[bool, str]:
    """PD scenario ids route to (NSW, property_damage); the NSW registry has 4
    trees with distinct hashes. Updates IX-07/IX-08 for the 4-NSW-tree world.

    Multi-state note (per MULTI-STATE-ROLLOUT-PLAN.md): the registry now also
    contains PD entries for every Australian jurisdiction (11 trees total:
    4 NSW + 7 non-NSW PD), tested by IX-18..27. This case only verifies the
    NSW core."""
    # Routing (state, claim_type)
    route_checks = {
        "pd1-rear-end": ("NSW", "property_damage"),
        "pd7-other": ("NSW", "property_damage"),
        "s1-rear-end": ("NSW", "motor"),
        "pl1-slip-wet-surface": ("NSW", "public_liability"),
        "mn1-surgical-outcome": ("NSW", "medical_negligence"),
    }
    bad_routes = [(sid, want, _claim_type_for_scenario_id(sid))
                  for sid, want in route_checks.items()
                  if _claim_type_for_scenario_id(sid) != want]
    if bad_routes:
        return False, f"routing mismatches: {bad_routes}"

    # NSW core: 4 distinct trees (the VIC PD tree is verified separately)
    nsw_claims = ("motor", "property_damage", "public_liability", "medical_negligence")
    nsw_entries = {ct: fn for (st, ct), fn in RULE_TREE_REGISTRY.items() if st == "NSW"}
    if len(nsw_entries) != 4:
        return False, f"NSW registry has {len(nsw_entries)} trees, expected 4"
    hashes = {ct: _compute_scenarios_hash(_load_rule_tree_for(ct, "NSW"))
              for ct in nsw_claims}
    if len(set(hashes.values())) != 4:
        return False, f"4 NSW trees but hashes not distinct: {[h[:8] for h in hashes.values()]}"
    return True, ("4 NSW trees registered, 4 distinct hashes, PD routing correct "
                  f"(hashes: {[h[:8] for h in hashes.values()]})")


def _test_pd_backward_compat_motor_unchanged() -> tuple[bool, str]:
    """Adding the PD tree did not change motor behavior. The motor suite is
    unaffected — same scenario resolution. Post Legal Head sign-off
    (2026-07-05) motor now bands (was unsigned); the backward-compat guarantee
    under test is ROUTING (s1/s5), not the sign-off state."""
    er = classify({"state": "NSW", "claim_type": "motor",
                   "accident_type": "rear-end", "injuries": "none"})
    if er.scenario_id != "s1-rear-end":
        return False, f"motor rear-end now routes to {er.scenario_id!r} (should be s1-rear-end)"
    # Motor is now signed: clear rear-end bands as 'likely'.
    if er.escalation == "unsigned-scenario":
        pass  # tree not yet signed — still valid backward compat
    elif er.band != "likely":
        return False, f"motor rear-end (signed) expected band='likely', got band={er.band!r} escalation={er.escalation!r}"
    # And the legacy no-claim_type path still works
    er2 = classify({"state": "NSW", "accident_type": "reversing", "injuries": "none"})
    if er2.scenario_id != "s5-reversing":
        return False, f"legacy motor reversing now routes to {er2.scenario_id!r}"
    state = "band='likely' (signed)" if er.band == "likely" else "unsigned-scenario"
    return True, f"motor behavior unchanged by PD addition (s1→{state}, s5 resolves as before)"


# -----------------------------------------------------------------------
# Multi-state (per MULTI-STATE-ROLLOUT-PLAN.md) — VIC PD as proof state.
# These tests prove the multi-state scaffold works end-to-end without
# enabling a single band in the new state until Legal Head signs.
# -----------------------------------------------------------------------

def _test_vic_pd_routing() -> tuple[bool, str]:
    """VIC PD intakes route to the VIC tree's scenario ids (prefixed vic-pdN).
    Confirms _resolve_scenario dispatches by (state, claim_type) and that the
    state prefix is applied to keep scenario ids globally unique."""
    # Resolve a rear-end PD intake in VIC.
    sid = _resolve_scenario({
        "state": "VIC", "claim_type": "property_damage",
        "collision_type": "rear-end", "injuries": "none",
    })
    if sid != "vic-pd1-rear-end":
        return False, f"VIC rear-end routed to {sid!r}, expected 'vic-pd1-rear-end'"
    # And a couple more collision types.
    for col, expected_suffix in [
        ("reversing", "vic-pd3-reversing"),
        ("parked_hit", "vic-pd4-parked-vehicle-struck"),
        ("lane_change", "vic-pd5-changing-lanes-sideswipe"),
        ("car_park", "vic-pd6-car-park"),
        ("other", "vic-pd7-other"),
    ]:
        sid = _resolve_scenario({
            "state": "VIC", "claim_type": "property_damage",
            "collision_type": col, "injuries": "none",
        })
        if sid != expected_suffix:
            return False, f"VIC {col!r} routed to {sid!r}, expected {expected_suffix!r}"
    return True, "VIC PD collision types route to vic-pdN scenario ids (state-prefixed)"


def _test_vic_pd_unsigned_stage1() -> tuple[bool, str]:
    """Stage 1 = NSW-only live (P1-6 un-sign, 2026-07-14 review). VIC PD
    tree is back to staging-unsigned: classify MUST escalate as
    'unsigned-scenario' with no band. Routing still state-prefixed (vic-pdN).
    Stage 2 (later) re-signs VIC after the verify item + citation audit close."""
    er = classify({
        "state": "VIC", "claim_type": "property_damage",
        "collision_type": "rear-end", "injuries": "none",
        "user_position": "front", "user_motion": "stopped", "chain_count": 2,
    })
    if er.scenario_id != "vic-pd1-rear-end":
        return False, f"routing: got {er.scenario_id!r}, expected vic-pd1-rear-end"
    if er.escalation != "unsigned-scenario":
        return False, (f"stage 1 VIC must escalate as unsigned-scenario, "
                       f"got esc={er.escalation!r} band={er.band!r}")
    if er.band is not None:
        return False, f"VIC emitted band={er.band!r} (forbidden — unsigned in stage 1)"
    return True, "VIC PD stage 1: routes vic-pd1-rear-end → unsigned-scenario, no band"


def _test_vic_pd_injury_firewall() -> tuple[bool, str]:
    """The injury firewall applies in VIC too. Any injury mention escalates as
    esc-injury, before scenario resolution, with no band. This is the red line
    that keeps Lane 1 (PD) clean of Lane 2 (CTP/TAC injury) exposure in any state."""
    violations = []
    for col in ("rear-end", "give_way", "reversing"):
        for inj in ("minor", "serious"):
            intake = {"state": "VIC", "claim_type": "property_damage",
                      "collision_type": col, "injuries": inj}
            er = classify(intake)
            if er.escalation != "esc-injury":
                violations.append(
                    f"VIC {col}+injuries={inj}: expected esc-injury, got {er.escalation!r}")
            if er.band is not None:
                violations.append(
                    f"VIC {col}+injuries={inj}: emitted band={er.band!r} (forbidden — injury firewall)")
    if violations:
        return False, "; ".join(violations)
    return True, "VIC PD collision types × {minor,serious} → esc-injury, no band (firewall holds across states)"


def _test_vic_pd_hash_isolation() -> tuple[bool, str]:
    """Mutating the VIC PD tree must NOT change any NSW hash (motor, PD, PL,
    med-neg). Extends IX-14's isolation property to the multi-state registry.
    Also confirms the VIC tree has its own distinct hash."""
    nsw_claims = ("motor", "property_damage", "public_liability", "medical_negligence")
    nsw_hashes_before = {ct: _compute_scenarios_hash(_load_rule_tree_for(ct, "NSW"))
                         for ct in nsw_claims}
    vic_hash_before = _compute_scenarios_hash(_load_rule_tree_for("property_damage", "VIC"))

    # Mutate a copy of the VIC tree.
    import copy
    vic_mutated = copy.deepcopy(_load_rule_tree_for("property_damage", "VIC"))
    vic_mutated["scenarios"][0]["_test_mutation"] = "cosmetic-vic-change"
    vic_hash_after_mutation = _compute_scenarios_hash(vic_mutated)

    # NSW hashes are recomputed fresh (cache cleared).
    nsw_hashes_after = {ct: _compute_scenarios_hash(_load_rule_tree_for(ct, "NSW"))
                        for ct in nsw_claims}

    if vic_hash_after_mutation == vic_hash_before:
        return False, "VIC hash did NOT change after mutation (hash not content-bound)"
    for ct in nsw_claims:
        if nsw_hashes_before[ct] != nsw_hashes_after[ct]:
            return False, f"NSW {ct} hash changed across VIC mutation (isolation broken)"
    # VIC's hash must also differ from NSW PD's hash (different content, by design).
    if vic_hash_before == nsw_hashes_before["property_damage"]:
        return False, "VIC PD hash equals NSW PD hash (trees not actually distinct)"
    return True, (f"VIC PD hash changed ({vic_hash_before[:8]} → {vic_hash_after_mutation[:8]}); "
                  f"all 4 NSW hashes stable ({[nsw_hashes_after[c][:8] for c in nsw_claims]})")


def _test_unregistered_state_escalates() -> tuple[bool, str]:
    """Non-AU / unknown states escalate as state-scope. Motor outside NSW has
    no motor tree and must also escalate. All AU PD states are registered
    and signed (Legal Head go-ahead 2026-07-13)."""
    for st in ("outside_nsw", "NZ", "OTHER"):
        er = classify({"state": st, "claim_type": "property_damage",
                       "collision_type": "rear-end", "injuries": "none"})
        if er.escalation != "state-scope":
            return False, (f"{st} PD intake: expected state-scope, "
                           f"got escalation={er.escalation!r} band={er.band!r}")
        if er.band is not None:
            return False, f"{st} PD intake emitted band={er.band!r} (forbidden)"
    # Motor in non-NSW AU states still has no motor tree → state-scope.
    for st in ("VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"):
        er2 = classify({"state": st, "claim_type": "motor",
                        "accident_type": "rear-end", "injuries": "none"})
        if er2.escalation != "state-scope":
            return False, (f"{st} motor intake: expected state-scope "
                           f"(no {st} motor tree), got {er2.escalation!r}")
    return True, ("non-AU PD → state-scope; "
                  "non-NSW motor → state-scope (national PD-only multi-state)")


def _test_qld_wa_pd_routing() -> tuple[bool, str]:
    """QLD and WA PD intakes route to state-prefixed scenario ids (qld-pdN / wa-pdN)."""
    checks = [
        ("QLD", "rear-end", "qld-pd1-rear-end"),
        ("QLD", "reversing", "qld-pd3-reversing"),
        ("QLD", "other", "qld-pd7-other"),
        ("WA", "rear-end", "wa-pd1-rear-end"),
        ("WA", "parked_hit", "wa-pd4-parked-vehicle-struck"),
        ("WA", "car_park", "wa-pd6-car-park"),
    ]
    for st, col, expected in checks:
        sid = _resolve_scenario({
            "state": st, "claim_type": "property_damage",
            "collision_type": col, "injuries": "none",
        })
        if sid != expected:
            return False, f"{st} {col!r} routed to {sid!r}, expected {expected!r}"
    return True, "QLD/WA PD collision types route to state-prefixed scenario ids"


def _test_qld_wa_pd_unsigned_stage1() -> tuple[bool, str]:
    """Stage 1 = NSW-only live (P1-6 un-sign). QLD and WA escalate as
    unsigned-scenario; no band emitted."""
    violations = []
    for st, prefix in (("QLD", "qld"), ("WA", "wa")):
        er = classify({
            "state": st, "claim_type": "property_damage",
            "collision_type": "rear-end", "injuries": "none",
            "user_position": "front", "user_motion": "stopped", "chain_count": 2,
        })
        if er.scenario_id != f"{prefix}-pd1-rear-end":
            violations.append(f"{st} routing: {er.scenario_id!r}")
        if er.escalation != "unsigned-scenario":
            violations.append(f"{st}: expected unsigned-scenario, got esc={er.escalation!r}")
        if er.band is not None:
            violations.append(f"{st}: emitted band={er.band!r} (forbidden in stage 1)")
    if violations:
        return False, "; ".join(violations)
    return True, "QLD + WA PD stage 1: unsigned-scenario, no band"


def _test_qld_wa_pd_hash_isolation() -> tuple[bool, str]:
    """Mutating QLD or WA PD must not change NSW or VIC hashes. Each state's
    PD tree has its own distinct content-bound hash."""
    keys = [
        ("NSW", "motor"), ("NSW", "property_damage"),
        ("NSW", "public_liability"), ("NSW", "medical_negligence"),
        ("VIC", "property_damage"), ("QLD", "property_damage"), ("WA", "property_damage"),
    ]
    before = {k: _compute_scenarios_hash(_load_rule_tree_for(k[1], k[0])) for k in keys}

    import copy
    qld_mut = copy.deepcopy(_load_rule_tree_for("property_damage", "QLD"))
    qld_mut["scenarios"][0]["_test_mutation"] = "cosmetic-qld-change"
    qld_mut_hash = _compute_scenarios_hash(qld_mut)
    if qld_mut_hash == before[("QLD", "property_damage")]:
        return False, "QLD hash did NOT change after mutation"

    after = {k: _compute_scenarios_hash(_load_rule_tree_for(k[1], k[0])) for k in keys}
    for k in keys:
        if before[k] != after[k]:
            return False, f"{k[0]}.{k[1]} hash changed across QLD mutation (isolation broken)"

    # All PD state hashes must be pairwise distinct (different citations/ids).
    pd_hashes = [before[("NSW", "property_damage")], before[("VIC", "property_damage")],
                 before[("QLD", "property_damage")], before[("WA", "property_damage")]]
    if len(set(pd_hashes)) != 4:
        return False, f"PD state hashes not distinct: {[h[:8] for h in pd_hashes]}"
    return True, (f"QLD mutation isolated; 4 PD state hashes distinct "
                  f"({[h[:8] for h in pd_hashes]})")


def _test_remaining_states_pd_unsigned_stage1() -> tuple[bool, str]:
    """Stage 1 = NSW-only live. SA/TAS/ACT/NT route correctly, escalate as
    unsigned-scenario with no band, and keep distinct hashes. NT limitation
    wording must still reflect 3 years (carried for stage-2 sign-off prep)."""
    states = ("SA", "TAS", "ACT", "NT")
    route_checks = [
        ("SA", "rear-end", "sa-pd1-rear-end"),
        ("TAS", "reversing", "tas-pd3-reversing"),
        ("ACT", "car_park", "act-pd6-car-park"),
        ("NT", "other", "nt-pd7-other"),
    ]
    for st, col, expected in route_checks:
        sid = _resolve_scenario({
            "state": st, "claim_type": "property_damage",
            "collision_type": col, "injuries": "none",
        })
        if sid != expected:
            return False, f"{st} {col!r} routed to {sid!r}, expected {expected!r}"

    violations = []
    for st in states:
        er = classify({
            "state": st, "claim_type": "property_damage",
            "collision_type": "rear-end", "injuries": "none",
            "user_position": "front", "user_motion": "stopped", "chain_count": 2,
        })
        if er.escalation != "unsigned-scenario":
            violations.append(f"{st}: expected unsigned-scenario, got esc={er.escalation!r}")
        if er.band is not None:
            violations.append(f"{st}: emitted band={er.band!r} (forbidden in stage 1)")
    if violations:
        return False, "; ".join(violations)

    # NT limitation wording must reflect 3 years (not 6) — for stage-2 prep.
    nt_tree = _load_rule_tree_for("property_damage", "NT")
    gov = nt_tree.get("governing_law", "")
    if "3 years" not in gov and "3-year" not in gov:
        return False, f"NT governing_law missing 3-year limitation note: {gov!r}"

    # All 8 PD jurisdictions registered with distinct hashes.
    pd_states = ("NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT")
    hashes = [_compute_scenarios_hash(_load_rule_tree_for("property_damage", st))
              for st in pd_states]
    if len(set(hashes)) != 8:
        return False, f"PD jurisdiction hashes not all distinct: {[h[:8] for h in hashes]}"
    return True, ("SA/TAS/ACT/NT route + stage-1 unsigned-escalate; NT 3yr flagged; "
                  f"8 PD hashes distinct ({[h[:8] for h in hashes]})")


# -----------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------

CASES: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
    ("IX-01", _test_pl_all_unsigned_escalate),
    ("IX-02", _test_medneg_all_unsigned_escalate),
    ("IX-03", _test_medneg_never_bands_likely_or_possible),
    ("IX-04", _test_medneg_no_harm_filter),
    ("IX-05", _test_hash_isolation_pl_change_does_not_stale_motor),
    ("IX-06", _test_pl_stale_signoff_after_mutation),
    ("IX-07", _test_registry_three_distinct_trees),
    ("IX-08", _test_claim_type_routing),
    ("IX-09", _test_new_escalation_triggers),
    ("IX-10", _test_motor_backward_compat_no_claim_type),
    # Property Damage (Lane 1 beachhead) — spec 2026-07-05
    ("IX-11", _test_pd_all_unsigned_escalate),
    ("IX-12", _test_pd_injury_firewall),
    ("IX-12a", _test_injury_firewall_fail_closed),  # P1-1 fix
    ("IX-12b", _test_pd_limitation_per_state),       # P1-2 fix
    ("IX-13", _test_pd_uninsured_driver_trigger),
    ("IX-14", _test_pd_hash_isolation_from_motor_and_others),
    ("IX-15", _test_pd_signed_bands_deterministically),
    ("IX-16", _test_pd_routing_and_registry_four_trees),
    ("IX-17", _test_pd_backward_compat_motor_unchanged),
    # Multi-state national PD — Legal Head go-ahead 2026-07-13 (all live).
    ("IX-18", _test_vic_pd_routing),
    ("IX-19", _test_vic_pd_unsigned_stage1),  # P1-6 stage 1 NSW-only
    ("IX-20", _test_vic_pd_injury_firewall),
    ("IX-21", _test_vic_pd_hash_isolation),
    ("IX-22", _test_unregistered_state_escalates),
    ("IX-23", _test_qld_wa_pd_routing),
    ("IX-24", _test_qld_wa_pd_unsigned_stage1),  # P1-6 stage 1
    ("IX-25", _test_qld_wa_pd_hash_isolation),
    ("IX-26", _test_remaining_states_pd_unsigned_stage1),  # P1-6 stage 1
]


def run_all() -> tuple[int, int, int, list[dict]]:
    results: list[dict] = []
    passes = 0
    fails = 0
    for cid, fn in CASES:
        try:
            ok, detail = fn()
        except Exception as exc:  # pragma: no cover
            ok = False
            detail = f"EXC: {type(exc).__name__}: {exc}"
        results.append({"id": cid, "pass": ok, "detail": detail})
        if ok:
            passes += 1
        else:
            fails += 1
    return len(CASES), passes, fails, results


def write_report(total: int, passes: int, fails: int, results: list[dict]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["PERSONAL-INJURY EXTENSION TEST REPORT",
             f"Generated: {__import__('datetime').datetime.utcnow().isoformat()}Z",
             "Spec: claimdesk-injury-extension-INSTRUCTIONS-2026-07-03.md", ""]
    lines.append("=" * 80)
    for r in results:
        flag = "PASS" if r["pass"] else "FAIL"
        lines.append(f"[{flag}] {r['id']:6s}  {r['detail']}")
    lines.append("=" * 80)
    lines.append(f"TOTAL: {total}  PASS: {passes}  FAIL: {fails}")
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def main() -> int:
    total, passes, fails, results = run_all()
    write_report(total, passes, fails, results)
    print(f"[injury-extension] TOTAL: {total}  PASS: {passes}  FAIL: {fails}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
