"""Tow (S2a) and Rental (S2b) sub-flows.

These are deterministic slot-collection flows per
`stage-1/deliverables/flows.md` (the tow and rental sub-flows). They do
NOT call the engine. They emit reference-number tokens that the intake
record stores for later use:

    {{TOW_PROVIDER_REF}}    e.g. "TOW-A1B2C3"
    {{RENTAL_PARTNER_REF}}  e.g. "REN-X9Y8Z7"

Outputs are reference numbers only this stage (Stage 3). Real dispatch
and booking APIs are Phase 2 per the build request §1.

The hazard check on tow (G-35): if the user reports a fuel leak or
similar, the system advises calling 000 FIRST, before continuing. This
mirrors the serious-injury safety precedence in the main flow.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any


# Forbidden phrases in rental eligibility output. These would constitute
# advice and must be replaced with general-info framing (G-35).
RENTAL_FORBIDDEN_PHRASES = [
    "you are entitled",
    "you will get",
    "they will pay",
    "you can claim",
    "you're entitled",
    "you can definitely",
]

# Rental eligibility — general-information framing. Never "you are entitled".
RENTAL_ELIGIBILITY_GENERAL = (
    "Whether rental costs can be recovered from the at-fault driver depends "
    "on the circumstances of the accident, the level of cover on your policy, "
    "and the evidence available. A lawyer can review your situation and "
    "advise on your options. {{ATTACH:master_voice_short}}"
)


@dataclass
class TowFlowResult:
    captured: dict[str, Any] = field(default_factory=dict)
    """Captured slots: location, on_surface, vehicle, callback, hazards."""
    reference: str | None = None
    """The {{TOW_PROVIDER_REF}} if completed. None if redirected to 000."""
    advise_000: bool = False
    """True if hazards were reported and 000 was advised first."""
    redirect_000_reason: str | None = None
    """Why 000 was advised (e.g. 'fuel leak')."""
    advisory_before_continue: bool = False
    """G-35: True if the 000 advisory was issued before any further slots."""
    logged_to_intake: bool = False
    """Whether the result was logged to the parent intake record."""


@dataclass
class RentalFlowResult:
    captured: dict[str, Any] = field(default_factory=dict)
    """Captured slots: licence, class, pickup, duration, comprehensive, other_at_fault."""
    reference: str | None = None
    """The {{RENTAL_PARTNER_REF}} if completed."""
    framing_general: bool = True
    """Always True (we never output advice-style claims)."""
    forbidden_phrases_absent: bool = True
    """Always True; verified by the test runner against RENTAL_FORBIDDEN_PHRASES."""
    noted_in_intake: bool = False
    """Whether the result was noted in the parent intake."""


def _new_ref(prefix: str) -> str:
    """Generate a 6-char alphanumeric reference. e.g. TOW-A1B2C3."""
    return f"{prefix}-{secrets.token_hex(3).upper()}"


# ----- Tow flow (S2a) -----

# Slot order for tow. Each entry is (key, prompt, validator-or-options).
TOW_SLOTS: list[dict[str, Any]] = [
    {"key": "location", "prompt": "Where is the car? Address, intersection, or suburb.",
     "type": "text"},
    {"key": "on_surface", "prompt": "Is it on the road, in a car park, or on private property?",
     "type": "enum", "options": ["road", "car_park", "private"]},
    {"key": "hazards", "prompt": "Are there any hazards — fuel leak, fire, on a bend, or the car in live traffic?",
     "type": "enum", "options": ["none", "fuel_leak", "on_bend", "live_traffic", "other"]},
    {"key": "vehicle", "prompt": "Vehicle details — make, model, colour, rego?",
     "type": "text"},
    {"key": "callback", "prompt": "What number should the tow provider call you on?",
     "type": "text"},
]


def run_tow_flow(intake_record: dict[str, Any], inputs: dict[str, Any]) -> TowFlowResult:
    """Execute the tow sub-flow.

    `inputs` is the user's responses keyed by slot key. Required keys:
    location, on_surface, vehicle, callback, plus 'hazards' (always).
    """
    result = TowFlowResult()

    # ----- Hazard check FIRST (G-35) -----
    hazard = inputs.get("hazards", "none")
    if hazard in ("fuel_leak", "fire") or hazard != "none":
        # 000 advisory before continuing
        result.advise_000 = True
        result.advisory_before_continue = True
        result.redirect_000_reason = hazard
        # We still log the advisory; we don't emit a tow ref until hazards clear.
        result.captured["location"] = inputs.get("location")
        result.captured["on_surface"] = inputs.get("on_surface")
        result.captured["hazards"] = hazard
        result.captured["vehicle"] = inputs.get("vehicle")
        result.captured["callback"] = inputs.get("callback")
        # Log the advisory into the intake record but no provider ref.
        intake_record.setdefault("tow_advisory", []).append({
            "reason": hazard,
            "advised_000": True,
        })
        result.logged_to_intake = True
        return result

    # Normal happy path
    for key in ("location", "on_surface", "vehicle", "callback", "hazards"):
        if key in inputs:
            result.captured[key] = inputs[key]
    result.reference = _new_ref("TOW")
    intake_record.setdefault("tow_refs", []).append(result.reference)
    intake_record.setdefault("tow", []).append(result.captured)
    result.logged_to_intake = True
    return result


# ----- Rental flow (S2b) -----

RENTAL_SLOTS: list[dict[str, Any]] = [
    {"key": "licence", "prompt": "Driving licence number, state, and expiry?",
     "type": "object"},
    {"key": "class", "prompt": "What class of vehicle do you need — sedan, SUV, ute, van?",
     "type": "enum", "options": ["sedan", "suv", "ute", "van", "other"]},
    {"key": "pickup", "prompt": "Where do you need to pick up — suburb or city?",
     "type": "text"},
    {"key": "duration", "prompt": "For how long — number of days?",
     "type": "text"},
    {"key": "comprehensive", "prompt": "Do you have comprehensive insurance on the car? yes / no / unknown",
     "type": "enum", "options": ["yes", "no", "unknown"]},
    {"key": "other_at_fault", "prompt": "Is the other driver likely to be at fault? yes / no / unknown",
     "type": "enum", "options": ["yes", "no", "unknown"]},
]


def run_rental_flow(intake_record: dict[str, Any], inputs: dict[str, Any]) -> RentalFlowResult:
    """Execute the rental sub-flow.

    Captured slots: licence, class, pickup, duration (always required),
    plus comprehensive / other_at_fault (optional eligibility context).
    """
    result = RentalFlowResult()
    for key in ("licence", "class", "pickup", "duration", "comprehensive", "other_at_fault"):
        if key in inputs:
            result.captured[key] = inputs[key]
    result.reference = _new_ref("REN")

    # Build the eligibility text using the general-info framing.
    eligibility = RENTAL_ELIGIBILITY_GENERAL
    # Verify no forbidden phrases slipped in.
    low = eligibility.lower()
    for bad in RENTAL_FORBIDDEN_PHRASES:
        if bad in low:
            result.forbidden_phrases_absent = False
    result.captured["eligibility_explainer"] = eligibility
    intake_record.setdefault("rental_refs", []).append(result.reference)
    intake_record.setdefault("rental", []).append(result.captured)
    result.noted_in_intake = True
    return result
