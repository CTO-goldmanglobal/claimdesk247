"""State machine for the web intake flow.

Implements S0a (consent) -> S1 (triage) -> S3 (intake) -> S4 (classify via engine)
-> S5 (fault-info) -> S6 (evidence) -> S7 (next-steps) -> S8 (close) plus
SX (escalate) and S9 (abandon).

The state machine does NOT own the engine (engine.py is a pure function). It
calls the engine from S4 with the assembled intake record and reports the
result up to the web layer for rendering.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field
from typing import Any, Literal

from app.engine import (
    classify, EngineResult, EngineBandError, _check_global_escalations,
    _resolve_scenario, _scenario_by_id, ACCIDENT_TYPE_TO_SCENARIO,
)

# Session identifier (in-memory for Stage 2; replaceable at Stage 4 with
# Australian-region persistent store).
@dataclass
class Session:
    session_id: str
    consent: bool = False
    privacy_acknowledged: bool = False
    state: str = "S0a"  # current state
    intake: dict[str, Any] = field(default_factory=dict)
    reprompts: dict[str, int] = field(default_factory=dict)
    escalation: str | None = None
    escalation_reason: str | None = None
    engine_result: EngineResult | None = None
    reference: str | None = None
    created_at: str = "2026-06-13T00:00:00Z"  # dev timestamp; Stage 4+ uses real time
    pii_persisted: bool = False  # G-22: only True after consent
    # T6: scenario-question injection (additive — empty until S3.5 begins)
    scenario_questions: list[dict[str, Any]] = field(default_factory=list)
    scenario_questions_answered: list[dict[str, Any]] = field(default_factory=list)


# Slot definitions (from spec/conversation-flow.v1.md §2, order fixed)
#
# Personal-injury extension (spec §1.3): the flat 14-slot motor list is now the
# MOTOR branch of a slot registry keyed by claim_type. Motor ids 1-14 are
# UNCHANGED so every existing acceptance test (which posts motor slot ids)
# keeps passing. PL and med-neg get their own id ranges that do not collide
# with motor.
#
# A `claim_type` slot is collected early (after consent/state). When the
# customer picks motor, the motor branch runs as before. When they pick PL or
# med-neg, the matching branch's slots run instead. The injuries check
# (G-19/G-20) stays reachable from any state.
MOTOR_SLOTS: list[dict[str, Any]] = [
    {"id": 1, "slot": "state_of_accident", "type": "enum", "options": ["NSW", "outside_nsw"], "mandatory": True},
    {"id": 2, "slot": "datetime_location", "type": "text", "mandatory": True},
    {"id": 3, "slot": "accident_type", "type": "enum", "options": ["rear-end", "T-intersection", "roundabout", "merge", "reversing", "car_park", "parked_hit", "intersection_signalised", "turning_right", "sideswipe_same_direction", "multi_vehicle", "not_listed"], "mandatory": True},
    {"id": 4, "slot": "user_vehicle", "type": "text", "mandatory": True},
    {"id": 5, "slot": "other_vehicles", "type": "text", "mandatory": True},
    {"id": 6, "slot": "movement_description", "type": "text", "mandatory": True},
    {"id": 7, "slot": "damage_locations", "type": "multienum", "options": ["front", "rear", "left", "right", "multiple"], "mandatory": True},
    {"id": 8, "slot": "control_devices", "type": "enum", "options": ["lights", "give-way", "stop", "roundabout", "none"], "mandatory": True},
    {"id": 9, "slot": "police_attendance", "type": "enum", "options": ["yes", "no", "unsure"], "mandatory": True},
    {"id": 10, "slot": "witnesses", "type": "text", "mandatory": False},
    {"id": 11, "slot": "dashcam", "type": "enum", "options": ["yours", "theirs", "neither", "unsure"], "mandatory": False},
    {"id": 12, "slot": "photos_taken", "type": "enum", "options": ["yes", "no"], "mandatory": False},
    {"id": 13, "slot": "other_driver_details", "type": "text", "mandatory": False},
    {"id": 14, "slot": "injuries", "type": "enum", "options": ["none", "minor", "serious"], "mandatory": True},
]

# Backward-compat alias: existing callers reference SLOT_DEFINITIONS directly.
# This is the ENGINE-CONTRACT motor list (14 slots, ids 1-14, NO claim_type
# question). Acceptance tests that post slot ids 1-14 use this.
SLOT_DEFINITIONS: list[dict[str, Any]] = MOTOR_SLOTS

# Shared slot collected after state, before the branch. Id 100 keeps it out of
# the motor 1-14 range and the PL/med-neg ranges below.
CLAIM_TYPE_SLOT: dict[str, Any] = {
    "id": 100,
    "slot": "claim_type",
    "type": "enum",
    "options": ["motor", "property_damage", "public_liability", "medical_negligence"],
    "mandatory": True,
}

# Frontend motor list: inserts the claim_type question right after state so a
# new customer is offered the four claim-type branches (spec §1.3 step 3).
# The engine-contract MOTOR_SLOTS above is UNCHANGED so acceptance tests that
# post ids 1-14 keep passing.
FRONTEND_MOTOR_SLOTS: list[dict[str, Any]] = [
    MOTOR_SLOTS[0],          # id 1: state_of_accident
    CLAIM_TYPE_SLOT,         # id 100: claim_type (NEW)
    *MOTOR_SLOTS[1:],        # ids 2-14: the rest of the motor flow
]

# Property-damage (third-party motor, Lane 1 beachhead) branch. Ids 400-414.
# Same collision geometry as motor but recovery-framed: the at-fault driver's
# comprehensive insurer pays, with Arsalan v Rixon hire entitlement. The damage
# map (motor slot 7) IS shown for PD (it's a motor collision). Injuries shared
# (collected at end; any injury → esc-injury → PI pathway, hard firewall).
PD_SLOTS: list[dict[str, Any]] = [
    {"id": 1, "slot": "state_of_accident", "type": "enum", "options": ["NSW", "outside_nsw"], "mandatory": True},
    {"id": 100, "slot": "claim_type", "type": "enum", "options": ["motor", "property_damage", "public_liability", "medical_negligence"], "mandatory": True},
    {"id": 400, "slot": "collision_type", "type": "enum", "options": ["rear-end", "T-intersection", "give_way", "reversing", "parked_hit", "parking", "sideswipe_same_direction", "lane_change", "car_park", "other"], "mandatory": True},
    {"id": 401, "slot": "incident_date", "type": "text", "mandatory": True},
    {"id": 402, "slot": "user_vehicle", "type": "text", "mandatory": True},
    {"id": 403, "slot": "other_vehicles", "type": "text", "mandatory": True},
    {"id": 404, "slot": "movement_description", "type": "text", "mandatory": True},
    {"id": 405, "slot": "damage_locations", "type": "multienum", "options": ["front", "rear", "left", "right", "multiple"], "mandatory": True},
    {"id": 406, "slot": "police_attendance", "type": "enum", "options": ["yes", "no", "unsure"], "mandatory": True},
    {"id": 407, "slot": "police_event_number", "type": "text", "mandatory": False},
    {"id": 408, "slot": "witnesses", "type": "text", "mandatory": False},
    {"id": 409, "slot": "dashcam", "type": "enum", "options": ["yours", "theirs", "neither", "unsure"], "mandatory": False},
    {"id": 410, "slot": "photos_taken", "type": "enum", "options": ["yes", "no"], "mandatory": False},
    {"id": 411, "slot": "other_driver_details", "type": "text", "mandatory": True},
    {"id": 412, "slot": "at_fault_uninsured", "type": "enum", "options": ["yes", "no", "unsure"], "mandatory": True},
    {"id": 413, "slot": "repairer_quote", "type": "text", "mandatory": False},
    {"id": 414, "slot": "vehicle_class", "type": "enum", "options": ["small", "sedan", "suv_4wd", "ute_van", "prestige_luxury", "commercial_heavy", "unsure"], "mandatory": False},
    {"id": 415, "slot": "hire_need", "type": "enum", "options": ["yes_needed", "no_not_needed", "unsure"], "mandatory": False},
    {"id": 416, "slot": "injuries", "type": "enum", "options": ["none", "minor", "serious"], "mandatory": True},
]

# Public Liability branch (spec §2.1). Ids 200-209. The damage map (motor slot
# 7) is NOT shown for PL. Injuries is shared (collected at the end).
PL_SLOTS: list[dict[str, Any]] = [
    {"id": 1, "slot": "state_of_accident", "type": "enum", "options": ["NSW", "outside_nsw"], "mandatory": True},
    {"id": 100, "slot": "claim_type", "type": "enum", "options": ["motor", "public_liability", "medical_negligence"], "mandatory": True},
    {"id": 200, "slot": "incident_date", "type": "text", "mandatory": True},
    {"id": 201, "slot": "pl_location", "type": "enum", "options": ["supermarket", "shopping_centre", "footpath_council", "private_premises", "workplace", "construction_site", "rental_property", "commercial_premises", "stairwell", "car_park", "corridor", "other"], "mandatory": True},
    {"id": 202, "slot": "hazard_type", "type": "enum", "options": ["wet_surface", "spill", "rain_tracked", "cleaning", "uneven_surface", "broken_pavement", "mat", "cabling", "step", "pothole", "falling_object", "stock", "signage", "inadequate_lighting", "defective_premises", "broken_rail", "broken_stair", "fixture", "other_public_place", "other"], "mandatory": True},
    {"id": 203, "slot": "hazard_warned", "type": "enum", "options": ["yes", "no", "unsure"], "mandatory": True},
    {"id": 204, "slot": "hazard_duration", "type": "enum", "options": ["just_happened", "short", "long", "extended", "30min_plus", "unsure"], "mandatory": True},
    {"id": 205, "slot": "claimant_activity", "type": "enum", "options": ["walking_normally", "rushing", "carrying_items", "on_phone", "browsing", "working", "other"], "mandatory": False},
    {"id": 206, "slot": "defendant_type", "type": "enum", "options": ["private_occupier", "council", "public_authority", "government", "business", "unknown"], "mandatory": False},
    {"id": 207, "slot": "at_work", "type": "enum", "options": ["yes", "no", "unsure"], "mandatory": False},
    {"id": 208, "slot": "harm_severity", "type": "enum", "options": ["none", "minor", "serious", "permanent_impairment", "death"], "mandatory": True},
    {"id": 209, "slot": "injuries", "type": "enum", "options": ["none", "minor", "serious"], "mandatory": True},
]

# Medical Negligence branch (spec §3.1). Ids 300-309. Escalation-dominant: the
# slots exist to structure the case file for the lawyer, not to band.
MEDNEG_SLOTS: list[dict[str, Any]] = [
    {"id": 1, "slot": "state_of_accident", "type": "enum", "options": ["NSW", "outside_nsw"], "mandatory": True},
    {"id": 100, "slot": "claim_type", "type": "enum", "options": ["motor", "public_liability", "medical_negligence"], "mandatory": True},
    {"id": 300, "slot": "provider_type", "type": "enum", "options": ["gp", "hospital", "specialist", "surgeon", "dentist", "cosmetic", "pharmacy", "birth_centre", "other"], "mandatory": True},
    {"id": 301, "slot": "provider_public_private", "type": "enum", "options": ["public", "private", "unsure"], "mandatory": False},
    {"id": 302, "slot": "treatment_type", "type": "enum", "options": ["surgical_outcome", "misdiagnosis_delay", "medication_error", "birth_injury", "cosmetic", "dental", "consent_not_informed", "other"], "mandatory": True},
    {"id": 303, "slot": "incident_date", "type": "text", "mandatory": True},
    {"id": 304, "slot": "harm_severity", "type": "enum", "options": ["none", "minor", "serious", "permanent_impairment", "death"], "mandatory": True},
    {"id": 305, "slot": "outcome_nature", "type": "enum", "options": ["unexpected_outcome", "suspected_error", "not_sure", "communication_only"], "mandatory": True},
    {"id": 306, "slot": "second_opinion", "type": "enum", "options": ["yes", "no", "not_yet"], "mandatory": False},
    {"id": 307, "slot": "at_work", "type": "enum", "options": ["yes", "no", "unsure"], "mandatory": False},
    {"id": 308, "slot": "multiple_providers", "type": "enum", "options": ["yes", "no", "unsure"], "mandatory": False},
    {"id": 309, "slot": "injuries", "type": "enum", "options": ["none", "minor", "serious"], "mandatory": True},
]

# Registry of branch slot lists. Motor is the default (backward compat).
BRANCH_SLOTS: dict[str, list[dict[str, Any]]] = {
    "motor": MOTOR_SLOTS,
    "property_damage": PD_SLOTS,
    "public_liability": PL_SLOTS,
    "medical_negligence": MEDNEG_SLOTS,
}

DEFAULT_BRANCH = "motor"


def _active_slots(intake: dict[str, Any], frontend: bool = False) -> list[dict[str, Any]]:
    """Return the slot list for the session's resolved claim_type. Defaults to
    motor when claim_type is absent (preserves the legacy 14-slot motor flow).

    When `frontend=True`, the motor branch uses FRONTEND_MOTOR_SLOTS (which
    inserts the claim_type question after state) so a new web customer is
    offered the three personal-injury branches. The engine-contract path
    (acceptance tests posting ids 1-14) uses the plain MOTOR_SLOTS."""
    ct = intake.get("claim_type", DEFAULT_BRANCH)
    if ct == "motor" and frontend:
        return FRONTEND_MOTOR_SLOTS
    return BRANCH_SLOTS.get(ct, MOTOR_SLOTS)

REPROMPT_CAP = 2  # G-26


def _validate_slot(slot_def: dict[str, Any], value: Any) -> tuple[bool, str | None]:
    """Return (valid, error_message)."""
    if value is None or value == "":
        return False, "This field is required."
    t = slot_def["type"]
    if t == "enum":
        if value not in slot_def["options"]:
            return False, f"Please choose one of: {', '.join(slot_def['options'])}."
    elif t == "multienum":
        if isinstance(value, str):
            value = [v.strip() for v in value.split(",")]
        if not isinstance(value, list) or not all(v in slot_def["options"] for v in value):
            return False, f"Please choose from: {', '.join(slot_def['options'])}."
    elif t == "text":
        if not isinstance(value, str) or len(value.strip()) < 1:
            return False, "Please enter a value."
    elif t == "integer":
        try:
            int(value)
        except (TypeError, ValueError):
            return False, "Please enter a whole number."
    return True, None


def _next_slot_index(intake: dict[str, Any]) -> int:
    """Return the index of the next slot that still needs a value (or is invalid).

    Uses the session's resolved branch slot list (motor by default)."""
    slots = _active_slots(intake)
    for i, slot_def in enumerate(slots):
        if slot_def["mandatory"] and not intake.get(slot_def["slot"]):
            return i
    return len(slots)  # all mandatory done


def _find_slot_def(slot_id: int, intake: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Find a slot def by id within the active branch. Returns (slot_def, branch).
    The claim_type slot (id 100) is always resolvable since it's in every branch
    except the legacy motor list — so we also check CLAIM_TYPE_SLOT and the
    motor list explicitly for backward compat."""
    # Claim-type slot is special: it can be submitted before a branch is chosen.
    if slot_id == CLAIM_TYPE_SLOT["id"]:
        return CLAIM_TYPE_SLOT, _active_slots(intake)
    # Look in the active branch first.
    branch = _active_slots(intake)
    for sd in branch:
        if sd["id"] == slot_id:
            return sd, branch
    # Backward-compat fallback: motor slot ids 1-14 submitted before claim_type
    # is set resolve against the motor list.
    for sd in MOTOR_SLOTS:
        if sd["id"] == slot_id:
            return sd, MOTOR_SLOTS
    return None, branch


def new_session() -> Session:
    return Session(session_id=secrets.token_urlsafe(16))


def acknowledge_consent(session: Session, privacy_acknowledged: bool) -> None:
    """G-22: consent must precede any PII persistence. Recording consent is
    N/A for web (per build request §3.4); privacy notice is the gate."""
    session.consent = True
    session.privacy_acknowledged = privacy_acknowledged
    if not privacy_acknowledged:
        # T-2-029: declined consent -> S9 ABANDON, no PII persisted.
        session.state = "S9-ABANDON"
        return
    session.state = "S1-TRIAGE"


def submit_slot(session: Session, slot_id: int, value: Any) -> dict[str, Any]:
    """Submit a slot value. Returns a dict describing the result and any
    escalation. Implements the re-prompt cap and consent gate."""
    if session.state == "S9-ABANDON":
        return {"error": "session abandoned", "end_state": "S9-ABANDON"}
    if not session.consent:
        return {"error": "consent required before PII", "end_state": "S0a-CONSENT"}

    slot_def, branch = _find_slot_def(slot_id, session.intake)
    if slot_def is None:
        return {"error": f"unknown slot id: {slot_id} for claim_type "
                         f"{session.intake.get('claim_type', DEFAULT_BRANCH)}"}
    valid, err = _validate_slot(slot_def, value)
    if not valid:
        # Increment re-prompt count; if at cap, offer callback (T-2-030)
        session.reprompts[slot_def["slot"]] = session.reprompts.get(slot_def["slot"], 0) + 1
        if session.reprompts[slot_def["slot"]] > REPROMPT_CAP:
            # Offer human callback
            session.state = "SX-ESCALATE"
            session.escalation = "repompt-cap"
            session.escalation_reason = f"max re-prompts on slot {slot_def['slot']}"
            session.reference = _new_reference()
            return {
                "error": "max re-prompts exceeded",
                "reprompts": session.reprompts[slot_def["slot"]],
                "offered": "callback",
                "end_state": "SX-ESCALATE",
                "reference": session.reference,
            }
        return {"error": err, "reprompt": True, "reprompt_count": session.reprompts[slot_def["slot"]]}

    # Valid: persist (now that consent is given, PII write is allowed)
    session.intake[slot_def["slot"]] = value
    session.pii_persisted = True

    # Injury check after every slot — escalation can fire from any state (G-19).
    if slot_def["slot"] == "injuries" and value == "serious":
        session.state = "SX-ESCALATE"
        session.escalation = "esc-injury"
        session.escalation_reason = "serious injury reported"
        session.reference = _new_reference()
        return {"escalation": "esc-injury", "end_state": "SX-ESCALATE", "reference": session.reference}

    # State-scope guard after slot 1 (G-21). NSW-only product: anything other
    # than NSW (the dropdown offers "outside_nsw") routes to a human callback —
    # the lead is captured, not dead-ended.
    if slot_def["slot"] == "state_of_accident" and value != "NSW":
        session.state = "SX-ESCALATE"
        session.escalation = "state-scope"
        session.escalation_reason = f"non-NSW accident: {value}"
        session.reference = _new_reference()
        return {"state_scope_guard_shown": True, "escalation": "callback",
                "end_state": "SX-ESCALATE", "reference": session.reference}

    # Accident-type fast-fail (T6 §6.7): if the chosen type has no auto-band
    # scenario (e.g. "not_listed" / anything unmapped), route to a human
    # callback immediately rather than asking 11 more slots and then dead-ending.
    # Captures the lead with a reference instead of letting the customer leave.
    if slot_def["slot"] == "accident_type" and value not in ACCIDENT_TYPE_TO_SCENARIO:
        session.state = "SX-ESCALATE"
        session.escalation = "unmapped-accident-type"
        session.escalation_reason = f"accident_type has no auto-band scenario: {value}"
        session.reference = _new_reference()
        return {"escalation": "callback", "unmapped_accident_type": True,
                "end_state": "SX-ESCALATE", "reference": session.reference}

    # Move to next slot (within the active branch)
    branch = _active_slots(session.intake)
    next_idx = _next_slot_index(session.intake)
    if next_idx >= len(branch):
        session.state = "S4-CLASSIFY"
        next_slot_id = None
    else:
        session.state = f"S3-SLOT{branch[next_idx]['id']}"
        next_slot_id = branch[next_idx]["id"]
    return {"slot_accepted": True, "next_state": session.state, "next_slot_id": next_slot_id}


def run_classification(session: Session) -> EngineResult:
    """Invoke the engine. Called when state reaches S4-CLASSIFY."""
    if not session.consent:
        raise RuntimeError("classification attempted without consent")
    if not session.pii_persisted:
        raise RuntimeError("classification attempted with no PII persisted")

    # T6: mirror the web-intake slot name onto the engine's canonical key so the
    # state-machine path is engine-callable. The fixed intake stores
    # `state_of_accident`; the engine resolves the scenario from `state`.
    # Additive only — never overwrites an explicitly-set `state`.
    if not session.intake.get("state") and session.intake.get("state_of_accident"):
        session.intake["state"] = session.intake["state_of_accident"]

    # If any of the global escalations are positive, we still call classify()
    # so the engine produces a deterministic result; the test runner asserts
    # against the engine output. The state machine also marks the session.

    result = classify(session.intake)
    session.engine_result = result

    if result.escalation:
        session.escalation = result.escalation
        session.escalation_reason = result.escalation_reason
        session.state = "SX-ESCALATE"
        session.reference = _new_reference()
    elif result.band is not None:
        session.state = "S5-FAULT-INFO"
    else:
        session.state = "S5-FAULT-INFO"  # insufficient or unclear still get S5 with disclaimer

    return result


def confirm_fault_info(session: Session) -> None:
    """User accepts the S5 fault-information output -> move to S6."""
    if session.state != "S5-FAULT-INFO":
        raise RuntimeError(f"cannot confirm fault info from state {session.state}")
    session.state = "S6-EVIDENCE"


def complete_intake(session: Session) -> str:
    """Move from S7 to S8 and issue a reference. Returns the reference."""
    session.state = "S8-CLOSE"
    if not session.reference:
        session.reference = _new_reference()
    return session.reference


def abandon(session: Session) -> str | None:
    """User drops mid-intake. S9 ABANDON. Reference issued if consent was given."""
    session.state = "S9-ABANDON"
    if session.consent and not session.reference:
        session.reference = _new_reference()
    return session.reference


def _new_reference() -> str:
    return "GF-" + secrets.token_hex(4).upper()


# ----------------------------------------------------------------------
# T6 — Scenario-question injection (L1 dependency)
#
# After the fixed 14 slots are filled (state S4-CLASSIFY), the resolved
# scenario's `classification_questions` are asked one at a time. Each answer
# is persisted into `session.intake` under the question's `slot` name so the
# engine's band functions have their inputs. Purely additive: the fixed-slot
# flow (`submit_slot`) and existing endpoints are unchanged. The orchestrator
# (web layer) calls `start_scenario_questions` once after slot 14, then
# `submit_scenario_question` per answer, then `/api/classify` as before.
# ----------------------------------------------------------------------

SCENARIO_REPROMPT_CAP = 2  # G-26 (mirrors the fixed-slot cap)


def _get_scenario_questions(intake: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return the resolved scenario's classification_questions, or None if no
    scenario resolves (e.g. accident_type missing/unmapped). Never raises."""
    scenario_id = _resolve_scenario(intake)
    if not scenario_id:
        return None
    try:
        scenario = _scenario_by_id(scenario_id)
    except Exception:
        return None
    return scenario.get("classification_questions", [])


def _validate_scenario_question(q: dict[str, Any], value: Any) -> tuple[bool, str | None]:
    """Validate a value against a scenario question's answer_type/options.
    Shape validation only — business-rule ranges (e.g. chain_count >= 3) are
    enforced by the engine's band logic, not here."""
    answer_type = q.get("answer_type", "text")
    if value is None or value == "":
        return False, "This field is required."
    if answer_type == "enum":
        if value not in q.get("options", []):
            return False, f"Please choose one of: {', '.join(q.get('options', []))}."
    elif answer_type == "multienum":
        vals = [v.strip() for v in value.split(",")] if isinstance(value, str) else value
        if not isinstance(vals, list) or not all(v in q.get("options", []) for v in vals):
            return False, f"Please choose from: {', '.join(q.get('options', []))}."
    elif answer_type == "text":
        if not isinstance(value, str) or len(value.strip()) < 1:
            return False, "Please enter a value."
    elif answer_type == "integer":
        try:
            int(value)
        except (TypeError, ValueError):
            return False, "Please enter a whole number."
    return True, None


def start_scenario_questions(session: Session) -> dict[str, Any]:
    """Begin the scenario-question phase. Call once after the 14 fixed slots
    are filled (state S4-CLASSIFY). If the resolved scenario has questions,
    transition to S3.5-INJECT-QUESTIONS and return the first one; otherwise
    pass straight through to classify."""
    if session.state != "S4-CLASSIFY":
        raise RuntimeError(f"cannot start scenario questions from state {session.state}")
    questions = _get_scenario_questions(session.intake)
    if not questions:
        return {"state": "S4-CLASSIFY", "question": None,
                "total_questions": 0, "answered": 0, "ready_to_classify": True}
    session.state = "S3.5-INJECT-QUESTIONS"
    session.scenario_questions = list(questions)
    session.scenario_questions_answered = []
    return {"state": "S3.5-INJECT-QUESTIONS", "question": questions[0],
            "total_questions": len(questions), "answered": 0}


def _current_scenario_question(session: Session) -> dict[str, Any] | None:
    answered_ids = {a["id"] for a in session.scenario_questions_answered}
    return next((q for q in session.scenario_questions if q["id"] not in answered_ids), None)


def submit_scenario_question(session: Session, question_id: str, value: Any) -> dict[str, Any]:
    """Submit an answer to the current scenario question. Validates, persists
    into session.intake under the question's slot, and advances. After the last
    question, transitions back to S4-CLASSIFY (ready_to_classify=True)."""
    if session.state != "S3.5-INJECT-QUESTIONS":
        raise RuntimeError(f"cannot submit scenario question from state {session.state}")
    current = _current_scenario_question(session)
    if current is None:
        raise RuntimeError("no scenario question pending")
    # question_id is optional: when omitted (None) the answer applies to the
    # current question (the frontend doesn't need to track question ids).
    if question_id is None:
        question_id = current["id"]
    if current["id"] != question_id:
        raise RuntimeError(f"question_id mismatch: expected {current['id']}, got {question_id}")

    valid, err = _validate_scenario_question(current, value)
    if not valid:
        key = current["slot"]
        session.reprompts[key] = session.reprompts.get(key, 0) + 1
        if session.reprompts[key] > SCENARIO_REPROMPT_CAP:
            session.state = "SX-ESCALATE"
            session.escalation = "reprompt-cap"
            session.escalation_reason = f"max re-prompts on scenario slot {key}"
            session.reference = session.reference or _new_reference()
            return {"escalation": "reprompt-cap", "end_state": "SX-ESCALATE",
                    "reference": session.reference}
        return {"reprompt": True, "error": err, "reprompt_count": session.reprompts[key]}

    session.intake[current["slot"]] = value
    session.pii_persisted = True  # G-22: scenario answers may be PII
    session.scenario_questions_answered.append({"id": current["id"], "value": value})

    next_q = _current_scenario_question(session)
    if next_q is None:
        session.state = "S4-CLASSIFY"
        return {"accepted": True, "next_question": None, "ready_to_classify": True,
                "answered": len(session.scenario_questions_answered),
                "total_questions": len(session.scenario_questions)}
    return {"accepted": True, "next_question": next_q, "ready_to_classify": False,
            "answered": len(session.scenario_questions_answered),
            "total_questions": len(session.scenario_questions)}
