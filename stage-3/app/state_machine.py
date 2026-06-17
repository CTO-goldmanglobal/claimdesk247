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

from app.engine import classify, EngineResult, EngineBandError, _check_global_escalations

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


# Slot definitions (from spec/conversation-flow.v1.md §2, order fixed)
SLOT_DEFINITIONS: list[dict[str, Any]] = [
    {"id": 1, "slot": "state_of_accident", "type": "enum", "options": ["NSW", "QLD", "VIC", "TAS", "SA", "WA", "ACT", "NT"], "mandatory": True},
    {"id": 2, "slot": "datetime_location", "type": "text", "mandatory": True},
    {"id": 3, "slot": "accident_type", "type": "enum", "options": ["rear-end", "T-intersection", "roundabout", "merge", "reversing", "parking", "other"], "mandatory": True},
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
    return True, None


def _next_slot_index(intake: dict[str, Any]) -> int:
    """Return the index of the next slot that still needs a value (or is invalid)."""
    for i, slot_def in enumerate(SLOT_DEFINITIONS):
        if slot_def["mandatory"] and not intake.get(slot_def["slot"]):
            return i
    return len(SLOT_DEFINITIONS)  # all mandatory done


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

    slot_def = SLOT_DEFINITIONS[slot_id - 1]  # slot_id is 1-based, list is 0-indexed
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

    # State-scope guard after slot 1 (G-21)
    if slot_def["slot"] == "state_of_accident" and value != "NSW":
        session.state = "SX-ESCALATE"
        session.escalation = "state-scope"
        session.escalation_reason = f"non-NSW accident: {value}"
        session.reference = _new_reference()
        return {"state_scope_guard_shown": True, "escalation": "callback",
                "end_state": "SX-ESCALATE", "reference": session.reference}

    # Move to next slot
    next_idx = _next_slot_index(session.intake)
    if next_idx >= len(SLOT_DEFINITIONS):
        session.state = "S4-CLASSIFY"
    else:
        session.state = f"S3-SLOT{next_idx+1}"
    return {"slot_accepted": True, "next_state": session.state, "next_slot_id": next_idx + 1 if next_idx < len(SLOT_DEFINITIONS) else None}


def run_classification(session: Session) -> EngineResult:
    """Invoke the engine. Called when state reaches S4-CLASSIFY."""
    if not session.consent:
        raise RuntimeError("classification attempted without consent")
    if not session.pii_persisted:
        raise RuntimeError("classification attempted with no PII persisted")

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
