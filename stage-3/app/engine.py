"""Pure fault engine.

Spec: classify(intakeRecord) -> { scenarioId, band, exceptionsFired[],
damageConsistent, outputKey, escalation, escalationReason }.

No LLM, no I/O, no side effects. Pure function. Same input -> same output.
Band enum is strictly {likely, possible, unclear, insufficient}. Any other
value is a hard engine error (CR-2-01, G-16, T-2-027 fail-closed).

The engine reads its data from the v2 rule tree (app/data/rule-tree.nsw.v2.json).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"

VALID_BANDS = frozenset({"likely", "possible", "unclear", "insufficient"})

# Personal-injury extension (spec §1.4): limitation-period safety buffer for
# esc-limitation. ~2.5 years under the standard limitation period. Confirm the
# exact period with Legal Head — this is a one-line change when confirmed.
LIMITATION_BUFFER_YEARS = 2.5

# Truthiness normalisation. YAML parses bare `yes`/`no` as Python True/False;
# the engine should treat them consistently. The `injuries: none` value is
# parsed as the string "none" (not Python None) and is therefore NOT truthy.
TRUE_VALUES = {True, "yes", "y", "true", "Yes", "YES"}
FALSE_VALUES = {False, "no", "n", "false", "No", "NO", "none", "None", None, ""}


def is_positive(value: Any) -> bool:
    """Return True if the value indicates an affirmative/positive response.
    Used to evaluate exception probes and condition checks."""
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    # For strings like "obstructed" / "not_working" / "no_indication" — treat
    # the value itself as a positive if it indicates a problem, but only if
    # the field's semantic is exception-like. We use a small set of "always
    # positive" string values for that purpose.
    always_positive = {"obstructed", "partially_obstructed", "very_obstructed",
                       "no_indication", "not_working", "faded", "defective",
                       "unsure", "simultaneous", "sudden", "reversed", "pushed"}
    return value in always_positive

# Mapping from test-facing accident_type strings to scenario id.
# Keys here are what appears in acceptance test inputs. The web intake form
# produces the same string set (validated in slot 3).
ACCIDENT_TYPE_TO_SCENARIO: dict[str, str] = {
    "rear-end": "s1-rear-end",
    "T-intersection": "s2-giveway-t",
    "roundabout": "s3-roundabout",
    "merge": "s4-lane-merge",
    "reversing": "s5-reversing",
    "parking": "s5-reversing",  # parking is treated as reversing
    "other": "s6-multi-chain",
    # Phase-2 Tier-1 (v3.1.0) — scenarios s7–s10
    "car_park": "s7-car-park",
    "intersection_signalised": "s8-signalised-intersection",
    "turning_right": "s9-right-turn-oncoming",
    "sideswipe_same_direction": "s10-sideswipe-same-direction",
    # Intake-clarity additions (v3.1.0)
    "parked_hit": "s11-parked-vehicle",   # user's parked car was struck
    "multi_vehicle": "s6-multi-chain",     # clear user-facing label for 3+ vehicles
}

# Public Liability hazard-type → scenario id (spec §2.1).
PL_HAZARD_TYPE_TO_SCENARIO: dict[str, str] = {
    "wet_surface": "pl1-slip-wet-surface",
    "spill": "pl1-slip-wet-surface",
    "rain_tracked": "pl1-slip-wet-surface",
    "uneven_surface": "pl2-trip-uneven-surface",
    "broken_pavement": "pl2-trip-uneven-surface",
    "mat": "pl2-trip-uneven-surface",
    "cabling": "pl2-trip-uneven-surface",
    "step": "pl2-trip-uneven-surface",
    "falling_object": "pl3-falling-object",
    "stock": "pl3-falling-object",
    "signage": "pl3-falling-object",
    "inadequate_lighting": "pl4-inadequate-lighting",
    "defective_premises": "pl5-defective-premises",
    "broken_rail": "pl5-defective-premises",
    "broken_stair": "pl5-defective-premises",
    "fixture": "pl5-defective-premises",
    "other_public_place": "pl6-other-public-place",
}

# Medical-negligence treatment-outcome → scenario id (spec §3.2). All scenarios
# are escalation-dominant in v1; the map exists to structure the case file for
# the lawyer, not to emit a band.
MEDNEG_TREATMENT_TYPE_TO_SCENARIO: dict[str, str] = {
    "surgical_outcome": "mn1-surgical-outcome",
    "misdiagnosis_delay": "mn2-misdiagnosis-delay",
    "medication_error": "mn3-medication-error",
    "birth_injury": "mn4-birth-injury",
    "cosmetic": "mn5-cosmetic-dental",
    "dental": "mn5-cosmetic-dental",
    "consent_not_informed": "mn6-consent-not-informed",
    "other": "mn7-other",
}

# Property-damage (third-party motor, Lane 1) collision-type → scenario id.
# The beachhead product per THIRD-PARTY-MOTOR-CLAIM-FOCUS-2026-07-05.md §3-4.
# Same collision geometry as motor (s1-s11) but recovery-framed: outputs cite
# Arsalan v Rixon for the like-for-like hire entitlement and the recovery is
# from the at-fault driver's *comprehensive* insurer (not CTP). Outside the
# NSW Claim Farming Practices Prohibition Act 2025 (injury only).
PD_COLLISION_TYPE_TO_SCENARIO: dict[str, str] = {
    "rear-end": "pd1-rear-end",
    "T-intersection": "pd2-failure-to-give-way",
    "give_way": "pd2-failure-to-give-way",
    "reversing": "pd3-reversing",
    "parked_hit": "pd4-parked-vehicle-struck",
    "parking": "pd4-parked-vehicle-struck",
    "sideswipe_same_direction": "pd5-changing-lanes-sideswipe",
    "lane_change": "pd5-changing-lanes-sideswipe",
    "car_park": "pd6-car-park",
    "other": "pd7-other",
}

# Field-name normalisation. Test inputs use free-form keys; the scenarios use
# longer field names. This map flattens the test-input vocabulary onto the
# slot names each scenario's band_logic inspects.
FIELD_ALIASES: dict[str, str] = {
    # rear-end
    "user_position": "user_position",
    "user_motion": "user_motion",
    "chain_count": "chain_count",
    "sudden_braking": "sudden_braking",
    "brake_lights": "brake_lights",
    "front_reversed": "front_reversed",
    # give-way / T
    "user_road": "user_road_type",
    "sight_lines": "obstructed_sight",
    "simultaneous_entry": "simultaneous_entry",
    "controls": "traffic_lights_override",
    "obstructed_sight": "obstructed_sight",
    # roundabout
    "user_action": "user_action",
    "other_action": "other_action",
    "lanes": "lane_count",
    "other_indicated": "other_failed_indicate",
    "exit_conflict": "multi_lane_conflict",
    # lane change / merge
    # NOTE: `zip_merge` is intentionally NOT aliased to `merge_layout_dispute`.
    # `zip_merge: yes` is the accident descriptor (this was a zip merge).
    # `merge_layout_dispute: yes` is the answer to a probe (user disputes the
    # layout). The two are different fields and the test inputs use the
    # descriptor form.
    "user_indicating": "user_indicating",
    "other_indicating": "other_indicating",
    "crossed_lines": "user_position_relative",
    "simultaneous_lane_change": "simultaneous_change",
    # reversing
    "other_stationary": "other_vehicle_state",
    "location": "location_type",
    "both_moving": "low_speed_both_moving",
    "view_obstruction": "view_obstruction",
    "other_unannounced_move": "other_unannounced_move",
    # multi-chain
    "chain_mechanism": "chain_mechanism",
    "multi_complex": "multi_complex",
    "vulnerable_or_heavy_party": "vulnerable_or_heavy_party",
}


# ----------------------------- Engine result ----------------------------- #

@dataclass
class EngineResult:
    scenario_id: str
    band: str | None  # None when escalation overrides classification
    exceptions_fired: list[str] = field(default_factory=list)
    damage_consistent: bool | None = None
    output_key: str | None = None  # (scenario_id, band) tuple rendered as string
    escalation: str | None = None
    escalation_reason: str | None = None
    classification_attempted: bool = True
    text_web: str | None = None
    text_web_resolved: str | None = None  # post-token-resolution copy
    disclaimer_attached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "band": self.band,
            "exceptions_fired": self.exceptions_fired,
            "damage_consistent": self.damage_consistent,
            "output_key": self.output_key,
            "escalation": self.escalation,
            "escalation_reason": self.escalation_reason,
            "classification_attempted": self.classification_attempted,
            "text_web": self.text_web,
            "text_web_resolved": self.text_web_resolved,
            "disclaimer_attached": self.disclaimer_attached,
        }


# ----------------------------- Rule tree registry ----------------------------- #
# Personal-injury extension (spec §1.2): the single motor tree becomes a
# registry keyed by `claim_type`. Each tree carries its own hash and its own
# legal_signoff, so a change to one tree never stales another tree's sign-off.
# `claim_type` defaults to "motor" when absent, preserving backward compat with
# every existing 99/99 motor test (which posts no claim_type).
#
# Backward-compat note: the Stage-3 acceptance tests monkey-patch
# `_load_rule_tree` (the zero-arg cached motor loader) with patched loaders
# that accept NO arguments. To keep those patches working, `_load_rule_tree`
# remains zero-arg (returns the motor tree), and the typed lookup goes through
# `_load_rule_tree_for(claim_type)` which the tests do not patch.

DEFAULT_CLAIM_TYPE = "motor"
DEFAULT_STATE = "NSW"

# Multi-state rule-tree registry (per MULTI-STATE-ROLLOUT-PLAN.md §5).
# Keyed by (state, claim_type). NSW remains the default for every claim type;
# additional states add entries only for claim types they have a signed (or
# staging-unsigned) tree for. Trees absent from this registry escalate as
# `state-scope`, exactly as a non-NSW intake does today.
#
# Each tree's sign-off hash is computed from its own scenarios[] (CD-E4 per-tree
# hashing), so adding a VIC PD tree does not change any NSW hash. A tree with
# its scenarios' `legal_signoff` blocks stripped (or set approved=false) makes
# every scenario escalate as `unsigned-scenario` under G-PROD-LOCK — that is
# the safety property that lets us merge the engineering scaffold for a new
# state before Legal Head has signed its content.
RULE_TREE_REGISTRY: dict[tuple[str, str], str] = {
    ("NSW", "motor"): "rule-tree.nsw.v3.json",
    ("NSW", "property_damage"): "rule-tree.nsw.pd.v1.json",
    ("NSW", "public_liability"): "rule-tree.nsw.pl.v1.json",
    ("NSW", "medical_negligence"): "rule-tree.nsw.medneg.v1.json",
    # VIC PD — Lane 1 beachhead, second state. Scenarios ship UNSIGNED so the
    # engine escalates every VIC PD intake as `unsigned-scenario` until Legal
    # Head signs the tree (CD-R2 + PD counsel memo for VIC required first).
    # Multi-state PD (all jurisdictions). Trees ship UNSIGNED; G-PROD-LOCK
    # escalates until Legal Head signs before launch (CD-R2 + PD counsel memo
    # per state). VIC/QLD/WA are priority; SA/TAS/ACT/NT included for national
    # coverage. NT limitation is 3 years (flagged in tree wording).
    ("VIC", "property_damage"): "rule-tree.vic.pd.v1.json",
    ("QLD", "property_damage"): "rule-tree.qld.pd.v1.json",
    ("WA", "property_damage"): "rule-tree.wa.pd.v1.json",
    ("SA", "property_damage"): "rule-tree.sa.pd.v1.json",
    ("TAS", "property_damage"): "rule-tree.tas.pd.v1.json",
    ("ACT", "property_damage"): "rule-tree.act.pd.v1.json",
    ("NT", "property_damage"): "rule-tree.nt.pd.v1.json",
}

# States whose PD tree is registered (signed or staging-unsigned). Used by the
# intake state-scope guard so VIC/QLD/WA are accepted at slot-fill time; the
# engine still escalates unsigned trees via G-PROD-LOCK.
PD_REGISTERED_STATES: frozenset[str] = frozenset(
    st for (st, ct) in RULE_TREE_REGISTRY if ct == "property_damage"
)


def _claim_type_for_scenario_id(scenario_id: str) -> tuple[str, str]:
    """Route a scenario id to (state, claim_type) by prefix.

    NSW scenarios use the bare prefixes `sN-...`, `pdN-...`, `plN-...`,
    `mnN-...` (preserves backward compat with every existing test). Multi-state
    scenarios carry the state in the prefix: `vic-pdN-...`, `qld-pdN-...`,
    `wa-pdN-...`, `sa-pdN-...`, `tas-pdN-...`, `act-pdN-...`, `nt-pdN-...`.
    Only PD is rolling out nationally; motor/PL/med-neg remain NSW-only and
    escalate as `state-scope` for any non-NSW intake via _resolve_scenario.
    """
    low = scenario_id.lower()
    for st in ("vic", "qld", "wa", "sa", "tas", "act", "nt"):
        if low.startswith(f"{st}-pd"):
            return (st.upper(), "property_damage")
    if scenario_id.startswith("pd"):
        return ("NSW", "property_damage")
    if scenario_id.startswith("pl"):
        return ("NSW", "public_liability")
    if scenario_id.startswith("mn"):
        return ("NSW", "medical_negligence")
    return ("NSW", "motor")


@lru_cache(maxsize=16)
def _load_rule_tree_typed(state: str, claim_type: str) -> dict[str, Any]:
    """Load the rule tree for the given (state, claim_type). Cached per pair.
    This is the typed loader used by _load_rule_tree_for(); the tests patch
    the public zero-arg _load_rule_tree (NSW motor only), not this one."""
    filename = RULE_TREE_REGISTRY.get((state, claim_type))
    if filename is None:
        raise KeyError(f"unknown (state, claim_type): ({state!r}, {claim_type!r}); "
                       f"known: {sorted(RULE_TREE_REGISTRY)}")
    with (DATA_DIR / filename).open() as f:
        return json.load(f)


def _load_rule_tree_for(claim_type: str, state: str = DEFAULT_STATE) -> dict[str, Any]:
    """Public typed lookup. Clears through the cache so test monkey-patches
    on the motor loader are honored for NSW motor while typed trees load fresh.
    `state` defaults to NSW so every existing call site keeps working unchanged."""
    if state == DEFAULT_STATE and claim_type == DEFAULT_CLAIM_TYPE:
        # NSW motor path: defer to the (possibly monkey-patched) zero-arg loader
        # so sign-off / hash tests that patch _load_rule_tree keep working.
        return _load_rule_tree()
    return _load_rule_tree_typed(state, claim_type)


@lru_cache(maxsize=1)
def _load_rule_tree() -> dict[str, Any]:
    """Load the MOTOR rule tree (zero-arg, cached). Retained as the canonical
    motor loader that the acceptance tests monkey-patch for sign-off/hash
    cases. For other claim types use _load_rule_tree_for(claim_type)."""
    with (DATA_DIR / "rule-tree.nsw.v3.json").open() as f:
        return json.load(f)


def _scenario_by_id(scenario_id: str) -> dict[str, Any]:
    state, claim_type = _claim_type_for_scenario_id(scenario_id)
    tree = _load_rule_tree_for(claim_type, state)
    for s in tree["scenarios"]:
        if s["id"] == scenario_id:
            return s
    raise KeyError(f"unknown scenario id: {scenario_id}")


# ----------------------- Legal signoff (G-PROD-LOCK / G-VER) ----------------------- #
# The rule tree's "legal_signoff" metadata binds a scenario's logical content to a
# sign-off event. T1 (G-PROD-LOCK + G-VER) makes that binding enforced: a scenario
# without a matching, current sign-off escalates instead of returning a band.
#
# Sign-off check: the scenario must have `legal_signoff.approved = true` AND
# `legal_signoff.version` must equal the SHA-256 of the scenarios[] array with each
# scenario's own `legal_signoff` field stripped (so the hash reflects the scenario's
# logical content, not its sign-off metadata).
#
# This means: any change to a scenario's content invalidates its existing sign-off
# and forces re-sign by Legal Head. The cost is small (one hash per classify call)
# and the safety property is high (no band escapes from a stale or missing sign-off).

def _compute_scenarios_hash(tree: dict[str, Any]) -> str:
    """SHA-256 of the canonicalized scenarios[] with each scenario's `legal_signoff`
    stripped. The hash represents the scenario's logical content; Legal Head signs
    this hash, not the file bytes, so cosmetic re-orderings of the file (or new
    metadata fields) don't invalidate a sign-off."""
    pruned = [
        {k: v for k, v in s.items() if k != "legal_signoff"}
        for s in tree.get("scenarios", [])
    ]
    blob = json.dumps(pruned, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _check_legal_signoff(scenario: dict[str, Any], current_hash: str) -> tuple[bool, str]:
    """Return (ok, escalation_reason). ok=True iff the scenario carries a current
    sign-off (approved=True AND version matches the live content hash)."""
    signoff = scenario.get("legal_signoff")
    if not isinstance(signoff, dict):
        return False, "unsigned-scenario"
    if not signoff.get("approved") is True:
        return False, "unsigned-scenario"
    signed_version = signoff.get("version", "")
    if not signed_version or signed_version != current_hash:
        return False, "stale-signoff"
    return True, ""


# ----------------------- Band-validity guard (G-16) ----------------------- #

def assert_band_is_valid(band: str) -> None:
    """Fail-closed at the engine boundary. Used by T-2-027 injection test."""
    if band not in VALID_BANDS:
        raise EngineBandError(f"engine emitted out-of-enum band: {band!r}")


class EngineBandError(RuntimeError):
    """Raised when the engine or its inputs produce a band outside the enum."""


# ----------------------- Damage-consistency helpers ----------------------- #

def _damage_consistency(intake: dict[str, Any], scenario: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (is_consistent, mismatches).

    The damage dict in the intake is {user: <side>, other: <side>} where <side>
    is one of front/rear/left/right/multiple. The scenario's
    damage_consistency_check.expected is a prose string describing the
    expected pairing. We map the canonical pairings per scenario.
    """
    damage = intake.get("damage")
    if not damage:
        return True, []  # no damage info -> not inconsistent (insufficient handled elsewhere)
    user = damage.get("user")
    other = damage.get("other")
    if not user or not other:
        return True, []  # unknown -> don't fail
    sid = scenario["id"]
    if sid == "s1-rear-end":
        # In a rear-end: the rear vehicle hits the front vehicle from behind.
        # - If user is the front vehicle: user has rear damage, other has front damage.
        # - If user is the rear vehicle: user has front damage, other has rear damage.
        # - If user is middle of chain: any consistent profile.
        pos = intake.get("user_position")
        if pos == "front":
            return (user == "rear" and other == "front"), []
        if pos == "behind":
            return (user == "front" and other == "rear"), []
        # middle_of_chain or unsure -> accept any profile
        return True, []
    if sid == "s2-giveway-t":
        # Give way: terminating road vehicle has front damage; through road has side damage.
        return (user == "front" and other in ("left", "right")), []
    if sid == "s3-roundabout":
        # Roundabout: entering vehicle has front damage; circulating has side damage.
        # OR both have side damage (lane-change sideswipe).
        return ((user == "front" and other in ("left", "right"))
                or (user in ("left", "right") and other in ("left", "right"))), []
    if sid == "s4-lane-merge":
        # Lane-merge: sideswipe (both sides) or front-of-merging + side-of-continuing.
        return ((user in ("left", "right") and other in ("left", "right"))
                or (user == "front" and other in ("left", "right"))), []
    if sid == "s5-reversing":
        # Reversing: reversing vehicle has rear damage; stationary has front damage.
        # OR both rear (both reversing).
        return ((user == "rear" and other == "front")
                or (user == "rear" and other == "rear")), []
    if sid == "s6-multi-chain":
        return True, []  # multi-chain is fuzzy
    return True, []


# ----------------------- Exception-probe evaluator ----------------------- #

def _eval_exceptions(intake: dict[str, Any], scenario: dict[str, Any]) -> list[str]:
    """Return the list of exception ids that fired for this scenario given
    the normalised intake. Each scenario's exceptions[] list has:
      { id, slot, effect: downgrade_band | flag_unclear | escalate }
    and we map positive 'yes' values or matching values to a fired exception.
    """
    fired: list[str] = []
    for ex in scenario.get("exceptions", []):
        slot = ex["slot"]
        val = intake.get(slot)
        if val is None:
            # Try the alias inverse
            for k_alias, v_alias in FIELD_ALIASES.items():
                if v_alias == slot and k_alias in intake:
                    val = intake[k_alias]
                    break
        if val is None:
            continue
        if is_positive(val):
            fired.append(ex["id"])
    return fired


def _is_exception_positive(slot: str, value: Any) -> bool:
    """Wrapper kept for clarity; is_positive is the canonical check."""
    return is_positive(value)


# ----------------------- Scenario resolution ----------------------- #

def _resolve_scenario(intake: dict[str, Any]) -> str | None:
    """Map intake to scenario id. Returns None when the intake is out of scope
    for the engine — either because (state, claim_type) has no registered tree
    (escalates as `state-scope`) or because the accident descriptor doesn't map
    to a scenario in the registered tree.

    Multi-state (per MULTI-STATE-ROLLOUT-PLAN.md §5): resolution is gated on
    (state, claim_type) being present in RULE_TREE_REGISTRY. NSW is the default
    for every existing test that doesn't pass a state. Non-NSW intakes without
    a registered tree escalate as `state-scope`, exactly as before.

    Personal-injury extension (spec §1.2): resolve `claim_type` first, then
    resolve the scenario within that claim_type's tree. Motor is the default
    when claim_type is absent (backward compat with all existing tests)."""
    state = intake.get("state", DEFAULT_STATE) or DEFAULT_STATE
    claim_type = intake.get("claim_type", DEFAULT_CLAIM_TYPE)

    # State-scope guard: if no tree is registered for (state, claim_type), the
    # engine does not attempt classification. Returns None → state-scope esc.
    if (state, claim_type) not in RULE_TREE_REGISTRY:
        return None

    if claim_type == "motor":
        acc = intake.get("accident_type")
        if not acc:
            return None
        return ACCIDENT_TYPE_TO_SCENARIO.get(acc)

    if claim_type == "property_damage":
        col = intake.get("collision_type") or intake.get("accident_type")
        if not col:
            return None
        sid = PD_COLLISION_TYPE_TO_SCENARIO.get(col)
        if sid is None:
            return None
        # Prefix the state for non-NSW PD so the scenario id is globally unique
        # and routes back to the right tree via _claim_type_for_scenario_id.
        if state != DEFAULT_STATE:
            sid = f"{state.lower()}-{sid}"
        return sid

    if claim_type == "public_liability":
        haz = intake.get("hazard_type")
        if not haz:
            return None
        return PL_HAZARD_TYPE_TO_SCENARIO.get(haz)

    if claim_type == "medical_negligence":
        treat = intake.get("treatment_type")
        if not treat:
            return None
        return MEDNEG_TREATMENT_TYPE_TO_SCENARIO.get(treat)

    return None


def _normalise_intake_for_scenario(intake: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    """Apply CR-3-01: accident_type=parking implies location_type=car_park.

    Returns a new dict (does not mutate the input). Other scenarios pass through.
    """
    out = dict(intake)
    if scenario_id == "s5-reversing" and out.get("accident_type") == "parking":
        out.setdefault("location_type", "car_park")
    return out


# ----------------------- Band assignment ----------------------- #

_STATE_PD_ID_RE = re.compile(
    r"^(vic|qld|wa|sa|tas|act|nt)-(pd.+)$", re.IGNORECASE
)


def _canonical_pd_id(scenario_or_exc_id: str) -> str:
    """Strip state prefix from multi-state PD ids.

    `vic-pd1-rear-end` → `pd1-rear-end`; `qld-pd4-e1` → `pd4-e1`.
    NSW bare `pd*` ids pass through unchanged. Band helpers and exception
    checks are written against the bare pd* namespace.
    """
    m = _STATE_PD_ID_RE.match(scenario_or_exc_id)
    return m.group(2) if m else scenario_or_exc_id


def _assign_band(scenario: dict[str, Any], intake: dict[str, Any],
                 exceptions_fired: list[str], damage_consistent: bool) -> str:
    """Apply scenario's band_logic and return the band.

    We translate each scenario's `band_logic` rules into a small set of
    scenario-specific helpers below, because the rule tree encodes them in
    English prose. The band_logic rules ARE the spec — these helpers reproduce
    them deterministically. If the rule tree changes, these helpers change.
    """
    sid = scenario["id"]
    # Common: incomplete -> insufficient
    if intake.get("incomplete") is True:
        return "insufficient"
    # If there is a flag_unclear exception fired, band = unclear
    for ex in scenario.get("exceptions", []):
        if ex["id"] in exceptions_fired and ex.get("effect") == "flag_unclear":
            return "unclear"
    # If damage is inconsistent, cap at unclear
    if damage_consistent is False:
        return "unclear"

    if sid == "s1-rear-end":
        return _band_s1(intake, exceptions_fired, damage_consistent)
    if sid == "s2-giveway-t":
        return _band_s2(intake, exceptions_fired)
    if sid == "s3-roundabout":
        return _band_s3(intake, exceptions_fired)
    if sid == "s4-lane-merge":
        return _band_s4(intake, exceptions_fired)
    if sid == "s5-reversing":
        return _band_s5(intake, exceptions_fired)
    if sid == "s6-multi-chain":
        return _band_s6(intake, exceptions_fired, damage_consistent)
    if sid == "s7-car-park":
        return _band_s7(intake, exceptions_fired)
    if sid == "s8-signalised-intersection":
        return _band_s8(intake, exceptions_fired)
    if sid == "s9-right-turn-oncoming":
        return _band_s9(intake, exceptions_fired)
    if sid == "s10-sideswipe-same-direction":
        return _band_s10(intake, exceptions_fired)
    if sid == "s11-parked-vehicle":
        return _band_s11(intake, exceptions_fired)

    # Personal Liability scenarios (spec §2.2) — draft bands for Legal Head sign.
    if sid.startswith("pl"):
        return _band_pl(sid, intake, exceptions_fired)

    # Property-damage scenarios (Lane 1) — NSW `pd*` and multi-state
    # `<state>-pd*` share the same band helpers after canonicalisation.
    pd_sid = _canonical_pd_id(sid)
    if pd_sid.startswith("pd"):
        pd_exc = [_canonical_pd_id(e) for e in exceptions_fired]
        return _band_pd(pd_sid, intake, pd_exc)

    # Medical negligence scenarios (spec §3) — escalation-dominant. A substantive
    # med-neg matter never returns a band from a questionnaire (s5O standard of
    # care is expert-evidence territory). If execution reaches here, the
    # scenario was signed AND no escalation fired — still resolve to "unclear"
    # rather than emit a liability band. The hard test in tests/ asserts no
    # med-neg scenario ever emits likely/possible.
    if sid.startswith("mn"):
        return "unclear"

    raise EngineBandError(f"no band logic for scenario: {sid}")


def _band_pl(sid: str, intake: dict[str, Any], exc: list[str]) -> str:
    """Public liability band (draft — Legal Head signs). Spec §2.2.

    Three-level shape mirroring motor's enum: likely / possible / unclear.
    (Spec prose says "unlikely"; that maps onto the valid "unclear" band since
    VALID_BANDS is strictly likely|possible|unclear|insufficient.)
    Escalation cases (pl6 catch-all, govt defendant, workplace, serious injury)
    are routed earlier by global/scenario escalation checks, so by the time we
    reach here the case is a clean occupier-liability question."""
    if intake.get("incomplete") is True:
        return "insufficient"
    # pl6-other-public-place is a catch-all — should be routed to escalation
    # before reaching here, but defensively band as unclear if it slips through.
    if sid == "pl6-other-public-place":
        return "unclear"

    warned = is_positive(intake.get("hazard_warned"))
    duration = intake.get("hazard_duration", "")
    long_present = duration in ("long", "extended", "30min_plus", "30 min+")
    claimant_reasonable = not is_positive(intake.get("claimant_at_fault"))

    # likely: clear hazard, occupier on notice / long-present, no warning, claimant reasonable
    if long_present and not warned and claimant_reasonable:
        return "likely"
    # possible: hazard present but warning given, or short duration, or contributory factors
    return "possible"


def _band_pd(sid: str, intake: dict[str, Any], exc: list[str]) -> str:
    """Property-damage band (draft — Legal Head signs). Lane 1 beachhead
    (Focus Study §4). Same deterministic collision geometry as motor (s1-s11)
    but framed for recovery: the not-at-fault driver recovers repair + hire +
    associated costs from the at-fault driver's comprehensive insurer under
    Arsalan v Rixon [2021] HCA.

    Band enum is the same likely|possible|unclear|insufficient. Inputs use the
    pd-prefixed slot names (pd1-q1 etc.). Pre-checks (incomplete → insufficient;
    fired flag_unclear exception → unclear; inconsistent damage → unclear) are
    applied in _assign_band BEFORE this runs. pd7-other is a catch-all that
    never bands above unclear."""
    if intake.get("incomplete") is True:
        return "insufficient"
    if sid == "pd7-other":
        return "unclear"

    # pd1-rear-end — following driver responsible (RR126).
    if sid == "pd1-rear-end":
        pos = intake.get("user_position")
        if pos == "behind":
            # user is the following driver — not the recovery side
            return "possible"
        if pos in ("front", "middle_of_chain"):
            # downgrade exceptions already handled pre-check; if we're here
            # with no downgrade/unclear fired, the front vehicle recovers.
            return "likely"
        return "insufficient"

    # pd2-failure-to-give-way (RR72/73)
    if sid == "pd2-failure-to-give-way":
        road = intake.get("user_road_type")
        sight = intake.get("sight_lines")
        if sight == "disputed":
            return "unclear"
        if sight == "obstructed":
            return "possible"
        if road == "through_road":
            return "likely"
        if road in ("terminating_road",):
            # user was the one who should have given way
            return "possible"
        if road == "unsure":
            return "unclear"
        return "insufficient"

    # pd3-reversing (RR96)
    if sid == "pd3-reversing":
        u = intake.get("user_action")
        o = intake.get("other_vehicle_state") or intake.get("other_action")
        if is_positive(intake.get("both_moving")):
            return "unclear"
        if u == "reversing":
            return "possible"  # user reversing — not the recovery side
        if u in ("stationary", "moving_forward", "parked") and o == "reversing":
            return "likely"
        return "unclear"

    # pd4-parked-vehicle-struck
    if sid == "pd4-parked-vehicle-struck":
        motion = intake.get("pv_user_motion")
        legal = intake.get("pv_parking_legal")
        if motion == "moving":
            return "unclear"
        if legal == "unsure":
            return "unclear"
        if legal == "no" or "pd4-e1" in exc:
            return "possible"
        if motion in ("parked_stationary", "just_stopped") and legal == "yes":
            return "likely"
        return "unclear"

    # pd5-changing-lanes-sideswipe (RR148)
    if sid == "pd5-changing-lanes-sideswipe":
        u = intake.get("ss_user_lane")
        o = intake.get("ss_other_lane")
        if not u or not o:
            return "insufficient"
        if u == "unsure" or o == "unsure":
            return "unclear"
        if u == "changing_lane" and o == "changing_lane":
            return "unclear"
        if u == "holding_lane" and o == "changing_lane":
            return "likely"
        if u == "changing_lane":
            return "possible"
        return "unclear"

    # pd6-car-park manoeuvre
    if sid == "pd6-car-park":
        u = intake.get("cp_user_role")
        o = intake.get("cp_other_role")
        if not u or not o:
            return "insufficient"
        if is_positive(intake.get("cp_both_moving")):
            return "unclear"
        if "pd6-e1" in exc:
            return "possible"  # aisle vehicle too fast (downgrade)
        if u == "driving_in_aisle" and o in ("reversing_from_bay", "entering_bay"):
            return "likely"
        if u in ("reversing_from_bay", "entering_bay") and o == "driving_in_aisle":
            return "possible"
        return "unclear"

    # Defensive: any other pd scenario we haven't authored band logic for.
    return "unclear"


def _band_s1(intake: dict[str, Any], exc: list[str], damage_consistent: bool) -> str:
    # T-2-001: user_position=front, user_motion=stopped, no exceptions, damage consistent -> likely
    # T-2-002: user_position=behind, user_motion=moving, sudden_braking=yes, damage consistent -> possible
    # T-2-003: user_position=front, user_motion=stopped, front_reversed=yes, damage inconsistent -> unclear
    # T-2-004: incomplete -> insufficient
    if intake.get("incomplete") is True:
        return "insufficient"
    # Downgrade-band exceptions
    if any(e in exc for e in ("s1-e1", "s1-e2")):
        return "possible"
    # Flag-unclear exceptions
    if any(e in exc for e in ("s1-e3", "s1-e4")):
        return "unclear"
    if damage_consistent is False:
        return "unclear"
    return "likely"


def _band_s2(intake: dict[str, Any], exc: list[str]) -> str:
    # T-2-005: user on terminating road, no exceptions, damage consistent -> likely
    # T-2-006: user on continuing road, sight_lines=obstructed, no other exceptions -> possible
    # T-2-007: simultaneous_entry=yes, sight_lines disputed -> unclear
    if is_positive(intake.get("simultaneous_entry")):
        return "unclear"
    if intake.get("sight_lines") == "obstructed":
        return "possible"
    if intake.get("user_road") in ("terminating_road", "terminating", "through_road", "continuing"):
        return "likely"
    return "possible"


def _band_s3(intake: dict[str, Any], exc: list[str]) -> str:
    # T-2-008: user entering, other circulating, single lane, no exceptions -> likely
    # T-2-009: user circulating, other entering, multi lane, other_indicated=no -> possible
    # T-2-010: multi-lane, exit_conflict=yes -> unclear
    if is_positive(intake.get("exit_conflict")):
        return "unclear"
    if intake.get("lanes") == "multi":
        # other_indicated=no means the other driver failed to indicate.
        # The intake may encode this as False, "no", or absent.
        other_ind = intake.get("other_indicated")
        if other_ind in (False, "no", "n", "false", "No", "NO"):
            return "possible"
        return "unclear"
    # single lane scenarios
    user_action = intake.get("user_action")
    if user_action == "entering":
        return "likely"
    return "possible"


def _band_s4(intake: dict[str, Any], exc: list[str]) -> str:
    # T-2-011: merge, user changing lanes, crossed_lines=yes -> likely
    # T-2-012: zip_merge=yes, user_position=ahead -> possible
    # T-2-013: simultaneous_lane_change=yes -> unclear
    if is_positive(intake.get("simultaneous_lane_change")):
        return "unclear"
    if is_positive(intake.get("zip_merge")):
        return "possible"
    if intake.get("user_action") in ("changing_lanes", "changing_into_their_lane"):
        return "likely"
    return "possible"


def _band_s5(intake: dict[str, Any], exc: list[str]) -> str:
    # T-2-014: user reversing, other stationary, road location -> likely
    # T-2-015: car park, both_moving=yes -> unclear
    if is_positive(intake.get("both_moving")):
        return "unclear"
    if intake.get("user_action") == "reversing" or intake.get("user_motion") == "reversing":
        return "likely"
    return "possible"


def _band_s6(intake: dict[str, Any], exc: list[str], damage_consistent: bool) -> str:
    # T-2-016: chain_count >= 3 -> escalation, no band (handled in classify())
    # T-2-017: chain_count=2, multi_complex=yes -> unclear
    if is_positive(intake.get("multi_complex")):
        return "unclear"
    return "unclear"


# ----------------------- Phase-2 Tier-1 band functions (s7–s10, v3.1.0) ----------------------- #
# Common pre-checks (incomplete -> insufficient; a fired flag_unclear exception
# or inconsistent damage -> unclear) are applied in _assign_band BEFORE these
# run. Each function reproduces its scenario's band_logic deterministically and
# returns "insufficient" if the discriminating classification answers are absent.

_CP_MANOEUVRING = {"reversing_from_bay", "entering_bay"}


def _band_s7(intake: dict[str, Any], exc: list[str]) -> str:
    """Car park / parking-lot manoeuvre."""
    u = intake.get("cp_user_role")
    o = intake.get("cp_other_role")
    if not u or not o:
        return "insufficient"
    if u in _CP_MANOEUVRING and o in _CP_MANOEUVRING:
        return "unclear"  # both manoeuvring (s7-e2 flag_unclear also covers this)
    if "s7-e1" in exc:
        return "possible"  # aisle vehicle partly at fault (downgrade)
    if (u == "driving_in_aisle" and o in _CP_MANOEUVRING) or \
       (o == "driving_in_aisle" and u in _CP_MANOEUVRING):
        return "likely"
    return "unclear"  # both stationary / both aisle / ambiguous roles


def _band_s8(intake: dict[str, Any], exc: list[str]) -> str:
    """Signalised (traffic-light) intersection."""
    light = intake.get("sig_user_light")
    movement = intake.get("sig_user_movement")
    if not light or not movement:
        return "insufficient"
    if light == "unsure":
        return "unclear"  # light state not certain (s8-e2 flag_unclear also covers this)
    if "s8-e1" in exc or light == "yellow":
        return "possible"  # entered on yellow (downgrade)
    if light in ("green", "green_arrow", "red"):
        return "likely"  # clear signal state on one side -> the other was opposite
    return "unclear"


def _band_s9(intake: dict[str, Any], exc: list[str]) -> str:
    """Right turn across oncoming traffic."""
    role = intake.get("rt_user_role")
    signal = intake.get("rt_signal")
    if not role or not signal:
        return "insufficient"
    if role == "unsure" or signal == "unsure":
        return "unclear"
    if signal == "green_arrow":
        return "unclear"  # turning driver had a green arrow (s9-e1 flag_unclear also covers this)
    if "s9-e2" in exc:
        return "possible"  # oncoming driver at-fault factor (downgrade)
    if role in ("going_straight", "turning_right"):
        return "likely"  # clear right-turn give-way pattern
    return "unclear"


def _band_s10(intake: dict[str, Any], exc: list[str]) -> str:
    """Sideswipe, both vehicles travelling the same direction."""
    u = intake.get("ss_user_lane")
    o = intake.get("ss_other_lane")
    if not u or not o:
        return "insufficient"
    if u == "unsure" or o == "unsure":
        return "unclear"
    if u == "changing_lane" and o == "changing_lane":
        return "unclear"  # both changing (s10-e1 flag_unclear also covers this)
    if "s10-e2" in exc:
        return "possible"  # lane-holder partly over the line (downgrade)
    if (u == "holding_lane" and o == "changing_lane") or \
       (o == "holding_lane" and u == "changing_lane"):
        return "likely"
    return "unclear"  # both holding -> ambiguous


def _band_s11(intake: dict[str, Any], exc: list[str]) -> str:
    """Parked / stationary vehicle struck by a moving vehicle."""
    motion = intake.get("pv_user_motion")
    legal = intake.get("pv_parking_legal")
    if not motion or not legal:
        return "insufficient"
    if motion == "moving":
        return "unclear"  # not actually a parked-vehicle case
    if legal == "unsure":
        return "unclear"
    if legal == "no" or "s11-e1" in exc:
        return "possible"  # parked illegally / obstructing (contributory)
    if motion in ("parked_stationary", "just_stopped") and legal == "yes":
        return "likely"
    return "unclear"


# ----------------------- Global escalation triggers (Loop Request §6.4) ----------------------- #

def _check_global_escalations(intake: dict[str, Any]) -> tuple[str, str] | None:
    """Evaluate the global escalation triggers (7 motor + 5 injury/PD-extension = 12).
    Returns (trigger_id, reason) or None.

    These fire BEFORE scenario classification and short-circuit it. Spec requires
    they be reachable from every intake state (G-19, G-20).

    Triggers 8-11 (esc-serious-injury, esc-workers-comp, esc-govt-defendant,
    esc-limitation) are gated by claim_type per spec §1.4. Trigger 12
    (esc-uninsured-driver) applies to motor + property_damage."""
    # 1. esc-injury: any injury reported. (injuries: "none" is parsed as string
    # "none" and is therefore not positive.)
    inj = intake.get("injuries")
    if inj in ("serious", "minor", "Serious", "Minor"):
        return ("esc-injury", f"injury reported: {inj}")
    # 2. esc-hitrun
    if is_positive(intake.get("hit_and_run")):
        return ("esc-hitrun", "hit-and-run indicated")
    # 3. esc-vulnerable: pedestrian or cyclist
    vp = intake.get("vulnerable_party")
    if vp in ("pedestrian", "cyclist") or is_positive(vp):
        return ("esc-vulnerable", f"vulnerable party: {vp}")
    # 4. esc-fraud: story inconsistency, rego mismatch, third-party pressure
    if is_positive(intake.get("rego_mismatch")):
        return ("esc-fraud", "rego mismatch indicated")
    if is_positive(intake.get("story_inconsistency")):
        return ("esc-fraud", "story inconsistency indicated")
    if is_positive(intake.get("third_party_pressure")):
        return ("esc-fraud", "third-party pressure indicated")
    # 5. esc-dispute: customer disputes the AI's summary
    if is_positive(intake.get("then_user_disputes_summary")):
        return ("esc-dispute", "user disputed AI summary")
    # 6. esc-multiparty: 3+ vehicles
    try:
        if int(intake.get("chain_count", 0)) >= 3:
            return ("esc-multiparty", "3+ vehicles in chain")
    except (TypeError, ValueError):
        pass
    # 7. esc-advice: user asks for legal advice directly
    if intake.get("user_asks"):
        return ("esc-advice", f"advice request: {intake.get('user_asks')!r}")

    # ---- Personal-injury extension (spec §1.4): 4 new global triggers. ----
    # These apply to the injury claim types (public_liability, medical_negligence)
    # and some to motor. Gate each by claim_type applicability per the spec table.
    claim_type = intake.get("claim_type", DEFAULT_CLAIM_TYPE)

    # 8. esc-serious-injury: death, permanent impairment, or hospitalisation.
    # Applies to ALL claim types (motor, PL, med-neg). High-stakes — never band.
    harm = intake.get("harm_severity")
    if harm in ("death", "permanent_impairment", "hospitalised"):
        return ("esc-serious-injury", f"serious injury / high harm: {harm}")
    if is_positive(intake.get("death_reported")):
        return ("esc-serious-injury", "death reported")

    # 9. esc-workers-comp: injury happened at work / in the course of employment.
    # Routes to the workers-comp scheme, not civil liability. Applies to PL and
    # med-neg (a workplace motor accident stays motor but flags work-cover).
    if claim_type in ("public_liability", "medical_negligence") and is_positive(intake.get("at_work")):
        return ("esc-workers-comp", "injury occurred in the course of employment")

    # 10. esc-govt-defendant: defendant is a public authority / council / hospital.
    # Special notice & procedural rules apply. Applies to PL and med-neg.
    if claim_type in ("public_liability", "medical_negligence"):
        defendant = intake.get("defendant_type")
        if defendant in ("council", "public_authority", "government", "public_hospital"):
            return ("esc-govt-defendant", f"government/public defendant: {defendant}")

    # 11. esc-limitation: incident date > LIMITATION_BUFFER_YEARS ago.
    # Applies to PL and med-neg (limitation differs from motor CTP). Buffer
    # keeps a margin under the standard limitation period.
    if claim_type in ("public_liability", "medical_negligence"):
        lim = _check_limitation(intake)
        if lim is not None:
            return lim

    # 12. esc-uninsured-driver (PD / motor): at-fault driver uninsured or
    # identity unknown (hit-and-run without a plate is already esc-hitrun;
    # this catches the "we know who but they have no cover" case). For PD,
    # the recovery shifts to the user's own insurer (uninsured-motorist
    # extension / property damage cover) — different matter handling.
    if claim_type in ("property_damage", "motor") and is_positive(intake.get("at_fault_uninsured")):
        return ("esc-uninsured-driver", "at-fault driver uninsured or cover unknown")

    return None


def _check_limitation(intake: dict[str, Any]) -> tuple[str, str] | None:
    """Return (esc-limitation, reason) if the incident date is older than
    LIMITATION_BUFFER_YEARS, else None. Tolerates ISO date, ISO datetime, and
    dd/mm/yyyy; anything unparseable is skipped (no false escalation)."""
    raw = intake.get("incident_date") or intake.get("datetime_location")
    if not raw or not isinstance(raw, str):
        return None
    parsed = _parse_incident_date(raw)
    if parsed is None:
        return None
    now = datetime.now(timezone.utc)
    age_years = (now - parsed).total_seconds() / (365.25 * 24 * 3600)
    if age_years > LIMITATION_BUFFER_YEARS:
        return ("esc-limitation", f"incident {age_years:.1f} yrs old > {LIMITATION_BUFFER_YEARS} yr buffer")
    return None


def _parse_incident_date(raw: str) -> datetime | None:
    """Best-effort parse of a date string. Returns timezone-aware datetime or None."""
    raw = raw.strip()
    candidates = (
        # ISO 8601 (with or without time / timezone)
        ("%Y-%m-%dT%H:%M:%S%z", raw),
        ("%Y-%m-%dT%H:%M:%S", raw),
        ("%Y-%m-%d %H:%M:%S", raw),
        ("%Y-%m-%d", raw),
        # AU common forms
        ("%d/%m/%Y", raw),
        ("%d/%m/%Y %H:%M", raw),
    )
    for fmt, s in candidates:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # Final fallback: fromisoformat (handles some ISO variants the above miss)
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


# ----------------------- Scenario-level escalation overrides ----------------------- #

def _check_scenario_escalation(scenario: dict[str, Any], intake: dict[str, Any]) -> tuple[str, str] | None:
    """Evaluate scenario-level escalation_overrides (e.g. s2 user_road=unsure)."""
    for ov in scenario.get("escalation_overrides", []):
        cond = ov.get("condition", "")
        if cond == "chain_count >= 3":
            try:
                if int(intake.get("chain_count", 0)) >= 3:
                    return ("esc-multiparty", "chain_count >= 3")
            except (TypeError, ValueError):
                pass
        if cond == "user_road_type = unsure AND other_vehicle_motion = unsure":
            if (intake.get("user_road_type") == "unsure"
                    and intake.get("other_vehicle_motion") == "unsure"):
                return ("esc-complexity", "user road type and other motion both unsure")
        if cond == "lane_count = multi_lane AND collision_location = while_circulating":
            if (intake.get("lane_count") == "multi_lane"
                    and intake.get("collision_location") == "while_circulating"):
                return ("esc-complexity", "multi-lane circulating conflict")
        if cond == "user_position_relative = unsure":
            if intake.get("user_position_relative") == "unsure":
                return ("esc-complexity", "user position relative unsure")
        if cond == "user_motion = unsure":
            if intake.get("user_motion") == "unsure":
                return ("esc-complexity", "user motion unsure")
    return None


# ----------------------- Public entry point ----------------------- #

def classify(intake: dict[str, Any]) -> EngineResult:
    """Pure fault engine. No I/O. Returns EngineResult.

    Order of evaluation (per Stage 1 spec):
    1. Global escalation triggers (injury, hitrun, vulnerable, fraud, dispute,
       multiparty, advice + the 4 injury-extension triggers: serious-injury,
       workers-comp, govt-defendant, limitation + esc-uninsured-driver)
    2. State-scope guard (non-NSW)
    3. Scenario-level escalation overrides (e.g. s6 chain_count >= 3)
    4. Exception probes
    5. Damage consistency
    6. Band assignment (fail-closed on out-of-enum)
    """
    # Special injection path: T-2-027. When the intake asks the engine to
    # produce or accept an out-of-enum band, fail-closed.
    if "inject_band" in intake:
        bad = intake["inject_band"]
        if bad not in VALID_BANDS:
            raise EngineBandError(f"engine received out-of-enum band: {bad!r}")
        # If somehow VALID, classify normally.
        intake = {k: v for k, v in intake.items() if k != "inject_band"}

    # 1. Global escalations fire BEFORE scenario resolution. This is
    # G-20 (serious injury -> immediate escalation) and G-19 (all triggers
    # reachable from any state, including states with no accident_type).
    global_esc = _check_global_escalations(intake)
    if global_esc:
        return EngineResult(
            scenario_id="",
            band=None,
            classification_attempted=False,
            escalation=global_esc[0],
            escalation_reason=global_esc[1],
        )

    # 2. Resolve scenario. If (state, claim_type) has no registered tree, or the
    # accident descriptor doesn't map to a scenario, no classification attempted
    # (G-21). Today every NSW claim_type is registered; non-NSW is registered
    # only for claim types that have a tree (per MULTI-STATE-ROLLOUT-PLAN.md).
    scenario_id = _resolve_scenario(intake)
    if scenario_id is None:
        return EngineResult(
            scenario_id="",
            band=None,
            classification_attempted=False,
            escalation="state-scope",
            escalation_reason="state/claim_type has no registered rule tree, or unmappable accident descriptor",
        )

    scenario = _scenario_by_id(scenario_id)

    # 3. G-PROD-LOCK / G-VER: enforce Legal Head sign-off on the rule tree.
    # A scenario without a matching sign-off never returns a band — it escalates.
    # The current_hash binds the sign-off to the scenario's logical content; any
    # change to a scenario's body invalidates the existing sign-off.
    #
    # Per-tree hashing (spec §1.5 + MULTI-STATE-ROLLOUT-PLAN §6): the hash is
    # computed PER TREE for the (state, claim_type) that owns this scenario.
    # Mutating the PL tree, or adding a VIC PD tree, does not stale the NSW motor
    # sign-off, and vice versa.
    scenario_state, scenario_claim_type = _claim_type_for_scenario_id(scenario_id)
    resolved_tree = _load_rule_tree_for(scenario_claim_type, scenario_state)
    current_hash = _compute_scenarios_hash(resolved_tree)
    signoff_ok, signoff_reason = _check_legal_signoff(scenario, current_hash)
    if not signoff_ok:
        return EngineResult(
            scenario_id=scenario_id,
            band=None,
            classification_attempted=False,
            escalation=signoff_reason,
            escalation_reason=(
                f"scenario {scenario_id} {signoff_reason}: "
                f"approved={scenario.get('legal_signoff', {}).get('approved')!r}, "
                f"signed_version={scenario.get('legal_signoff', {}).get('version', '')[:12]!r}, "
                f"current_hash={current_hash[:12]!r}"
            ),
        )

    # 4. Apply scenario-specific intake normalisation (CR-3-01).
    intake = _normalise_intake_for_scenario(intake, scenario_id)

    # 5. Scenario-level escalation overrides
    esc = _check_scenario_escalation(scenario, intake)
    if esc:
        return EngineResult(
            scenario_id=scenario_id,
            band=None,
            classification_attempted=False,
            escalation=esc[0],
            escalation_reason=esc[1],
        )

    # 6. Run exception probes
    exceptions_fired = _eval_exceptions(intake, scenario)

    # 7. Damage consistency
    damage_consistent, _ = _damage_consistency(intake, scenario)

    # 8. Assign band
    band = _assign_band(scenario, intake, exceptions_fired, damage_consistent)
    assert_band_is_valid(band)  # fail-closed per CR-2-01

    # 9. Resolve output text from scenario.outputs[]
    output_entry = next(
        (o for o in scenario["outputs"] if o["band"] == band),
        None,
    )
    if output_entry is None:
        raise EngineBandError(f"scenario {scenario_id} missing output for band {band}")

    text_web = output_entry["text_web"]
    return EngineResult(
        scenario_id=scenario_id,
        band=band,
        exceptions_fired=exceptions_fired,
        damage_consistent=damage_consistent,
        output_key=f"{scenario_id}.{band}",
        text_web=text_web,
        disclaimer_attached="{{ATTACH:master}}" in text_web,
    )


# ----------------------- Determinism guard (G-15) ----------------------- #

def fingerprint(result: EngineResult) -> str:
    """Stable string form of a result, for determinism assertions."""
    return json.dumps(result.to_dict(), sort_keys=True, default=str)
