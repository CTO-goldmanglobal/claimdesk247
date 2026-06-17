"""Voice dialog manager.

Text-in / text-out adapter that drives the same state machine used for web
(per build request §3.1). The voice layer is the *only* thing that decides
how to render prompts as speech and how to interpret the user's spoken
input. The engine (classify) is unchanged — G-29 is satisfied by construction.

Test hooks:
- VoiceDialogManager.run(transcript) consumes a list of "user turn" dicts
  and returns a list of "assistant turn" dicts plus the session.
- A transcript entry is one of:
    {"input": "<spoken text>"}                    # speech
    {"dtmf": "<keypad digits>"}                   # keypad
    {"consent": "yes"|"no"}                       # for the consent step
- The session is updated in-place; the same Session dataclass used by web.

This module is deliberately transport-agnostic. The TelephonyAdapter below
defines the interface; the dialog logic does not import any telephony SDK.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Iterator, Protocol

from app.config import get_disclaimer
from app.engine import classify
from app.state_machine import (
    SLOT_DEFINITIONS, Session, abandon, acknowledge_consent, complete_intake,
    new_session, run_classification, submit_slot,
)


# Voice-only slot labels (more conversational than the form field names).
VOICE_LABELS: dict[str, str] = {
    "state_of_accident": "Which state did the accident happen in?",
    "datetime_location": "About what date and time, and where — suburb or intersection?",
    "accident_type": "How would you describe what happened?",
    "user_vehicle": "Tell me about your car — make, model, colour, and rego?",
    "other_vehicles": "And the other car — same details if you have them, or 'unknown'.",
    "movement_description": "In the moments before the impact, was your car stopped, moving, or slowing? And which direction were you both heading?",
    "damage_locations": "Where is the damage on your car — front, rear, left side, right side, or multiple?",
    "control_devices": "Were there any traffic controls — lights, a give way sign, a stop sign, a roundabout, or none?",
    "police_attendance": "Did the police attend?",
    "witnesses": "Were there any witnesses?",
    "dashcam": "Did either car have a dashcam running — yours, theirs, or neither?",
    "photos_taken": "Have you taken any photos yet?",
    "other_driver_details": "Do you have the other driver's name, rego, or insurer? 'Refused' or 'unknown' is fine.",
    "injuries": "Is anyone hurt, even a little?",
}

# Enum slots that should expose a DTMF mapping (G-31).
DTMF_SLOTS: dict[int, dict[str, str]] = {
    1: {"1": "NSW", "2": "QLD", "3": "VIC", "4": "TAS", "5": "SA", "6": "WA", "7": "ACT", "8": "NT"},
    3: {"1": "rear-end", "2": "T-intersection", "3": "roundabout", "4": "merge", "5": "reversing", "6": "parking", "7": "other"},
    7: {"1": "front", "2": "rear", "3": "left", "4": "right", "5": "multiple"},
    8: {"1": "lights", "2": "give-way", "3": "stop", "4": "roundabout", "5": "none"},
    9: {"1": "yes", "2": "no", "3": "unsure"},
    14: {"1": "none", "2": "minor", "3": "serious"},
}

# Confirm-back templates for each slot (Stage 1 persona rule 6: confirm before advancing).
CONFIRM_BACK: dict[str, str] = {
    "state_of_accident": "So that's {value} — is that right?",
    "datetime_location": "So that's {value} — is that right?",
    "accident_type": "So you described it as {value} — is that right?",
    "user_vehicle": "So your car is a {value} — is that right?",
    "other_vehicles": "So the other car is {value} — is that right?",
    "movement_description": "So the situation was: {value} — is that right?",
    "damage_locations": "So the damage is on the {value} — is that right?",
    "control_devices": "So the controls were {value} — is that right?",
    "police_attendance": "So police {value} — is that right?",
    "witnesses": "So witnesses: {value} — is that right?",
    "dashcam": "So dashcam: {value} — is that right?",
    "photos_taken": "So photos: {value} — is that right?",
    "other_driver_details": "So the other driver: {value} — is that right?",
    "injuries": "So {value} injuries — is that right?",
}

# Token-driven business hours (default 9-5:30 Mon-Fri AEST). Stage 5 may override.
DEFAULT_BUSINESS_HOURS = {
    "start": time(9, 0),
    "end": time(17, 30),
    "weekdays": {0, 1, 2, 3, 4},  # Mon..Fri
}


def is_business_hours(now: datetime | None = None) -> bool:
    """Return True if `now` falls within the firm's business hours.
    Default behaviour: Mon-Fri 09:00-17:30."""
    now = now or datetime.now()
    if now.weekday() not in DEFAULT_BUSINESS_HOURS["weekdays"]:
        return False
    return DEFAULT_BUSINESS_HOURS["start"] <= now.time() < DEFAULT_BUSINESS_HOURS["end"]


@dataclass
class VoiceTurn:
    """One turn of the voice dialog. Either assistant output (to be TTS'd) or
    captured state (for test inspection)."""
    role: str  # "assistant" or "system"
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceDialogResult:
    """The full transcript of a voice session plus session state.
    Used by the test runner to assert expected behaviour."""
    session: Session
    turns: list[VoiceTurn] = field(default_factory=list)
    classification: Any = None  # EngineResult if classification ran
    disclaimer_full_read: bool = False
    disclaimer_short_count: int = 0
    recording_active: bool = False
    warm_transfer: bool = False
    callback_booking: bool = False
    brief_flagged_urgent: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session.session_id,
            "final_state": self.session.state,
            "classification": self.classification.to_dict() if self.classification else None,
            "turns": [{"role": t.role, "text": t.text, "meta": t.meta} for t in self.turns],
            "disclaimer_full_read": self.disclaimer_full_read,
            "disclaimer_short_count": self.disclaimer_short_count,
            "recording_active": self.recording_active,
            "warm_transfer": self.warm_transfer,
            "callback_booking": self.callback_booking,
            "brief_flagged_urgent": self.brief_flagged_urgent,
        }


class SpeechAdapter(Protocol):
    """Interface for STT/TTS. Stubbed in tests; real provider is a config choice."""
    def transcribe(self, audio: bytes) -> str: ...
    def synthesise(self, text: str) -> bytes: ...


class StubSpeechAdapter:
    """Deterministic stub for tests. transcribe() assumes caller pre-converted
    audio to text (or accepts text directly)."""
    def transcribe(self, audio: bytes) -> str:
        if isinstance(audio, bytes):
            try:
                return audio.decode("utf-8")
            except UnicodeDecodeError:
                return ""
        return str(audio)
    def synthesise(self, text: str) -> bytes:
        return text.encode("utf-8")


def _normalise_user_input(value: str) -> str:
    """Normalise spoken input for slot submission. Maps common synonyms to
    the enum value the state machine expects."""
    v = value.strip().lower()
    # Synonyms
    syn = {
        "rear end": "rear-end", "rear-ended": "rear-end",
        "t intersection": "T-intersection", "t-intersection": "T-intersection",
        "round about": "roundabout",
        "lane change": "merge", "merging": "merge", "lane-merge": "merge",
        "reversing": "reversing", "reverse": "reversing",
        "parking": "parking", "parked": "parking", "car park": "parking",
        "yes": "yes", "yep": "yes", "yeah": "yes",
        "no": "no", "nope": "no", "nah": "no",
        "i don't know": "unsure", "i dont know": "unsure", "not sure": "unsure", "unsure": "unsure",
        "front": "front", "rear": "rear", "left": "left", "right": "right", "multiple": "multiple",
        "lights": "lights", "give way": "give-way", "give-way": "give-way", "stop": "stop",
        "none": "none", "no one": "none", "no-one": "none",
        "minor": "minor", "serious": "serious",
        # Australian state abbrevs
        "nsw": "NSW", "new south wales": "NSW",
        "qld": "QLD", "queensland": "QLD",
        "vic": "VIC", "victoria": "VIC",
        "tas": "TAS", "tasmania": "TAS",
        "sa": "SA", "south australia": "SA",
        "wa": "WA", "western australia": "WA",
        "act": "ACT", "nt": "NT",
    }
    if v in syn:
        return syn[v]
    # Multi-word match: split on whitespace
    parts = v.split()
    for p in parts:
        if p in syn:
            return syn[p]
    return value.strip()  # pass through


def _slot_id_to_name(slot_id: int) -> str:
    return SLOT_DEFINITIONS[slot_id - 1]["slot"]


def _slot_options_for_voice(slot_id: int) -> list[str]:
    return SLOT_DEFINITIONS[slot_id - 1].get("options", [])


def _next_mandatory_slot(session: Session) -> int | None:
    """Return the 1-based slot id of the next mandatory slot that still
    needs a value, or None if all mandatory slots are filled."""
    for i, slot_def in enumerate(SLOT_DEFINITIONS, 1):
        if slot_def["mandatory"] and not session.intake.get(slot_def["slot"]):
            return i
    return None


def _dtmf_map_for_slot(slot_id: int) -> dict[str, str] | None:
    return DTMF_SLOTS.get(slot_id)


class VoiceDialogManager:
    """Drives the dialog for a voice call. Pure logic: pass in a transcript
    of user turns (text or DTMF or consent) and get back a transcript of
    assistant turns plus the final session state.

    The dialog manager does NOT call classify() directly. It drives the
    state machine (submit_slot, run_classification) which itself calls
    classify() at S4. This is the single-engine path G-29 requires.
    """

    def __init__(self, *, business_hours: bool | None = None,
                 speech: SpeechAdapter | None = None) -> None:
        self.speech = speech or StubSpeechAdapter()
        # If business_hours is None, use the time-based default.
        self._business_hours = business_hours

    @property
    def business_hours(self) -> bool:
        if self._business_hours is None:
            return is_business_hours()
        return self._business_hours

    def _ask(self, result: VoiceDialogResult, text: str, **meta: Any) -> None:
        result.turns.append(VoiceTurn("assistant", text, meta))

    def _capture(self, result: VoiceDialogResult, text: str, **meta: Any) -> None:
        result.turns.append(VoiceTurn("system", text, meta))

    def _maybe_attach_master(self, result: VoiceDialogResult, full: bool) -> None:
        if full:
            result.disclaimer_full_read = True
            self._ask(result, get_disclaimer("master"), attach="master")
        else:
            result.disclaimer_short_count += 1
            self._ask(result, get_disclaimer("master_voice_short"), attach="master_voice_short")

    def run(self, transcript: list[dict[str, Any]]) -> VoiceDialogResult:
        """Drive a complete voice session from a scripted transcript.

        Each transcript entry is one of:
            {"input": "..."}      # user spoke
            {"dtmf": "1"}         # user pressed a key
            {"consent": "yes"|"no"}  # consent response
            {"confirm": "yes"|"no"}  # confirm-back response
        """
        session = new_session()
        result = VoiceDialogResult(session=session)
        iterator = iter(transcript)

        # ----- S0a: Recording consent FIRST (before any PII) -----
        self._ask(result, get_disclaimer("recording_consent"), state="S0a")
        # Pull the consent response from the transcript
        consent_turn = next(iterator, None)
        if not consent_turn or "consent" not in consent_turn:
            result.turns.append(VoiceTurn("system", "no consent response", meta={"error": "no_consent"}))
            return result
        consent_value = consent_turn["consent"]
        # Accept "yes", "accepted", "y", etc. (test cases may use "accepted")
        if str(consent_value).lower() in ("yes", "accepted", "y", "ok", "okay", "true", "1"):
            result.recording_active = True
            acknowledge_consent(session, privacy_acknowledged=True)
            self._ask(result, "Thanks. Let's get started.", state="S1")
        else:
            # Decline: no recording, no PII, route to non-recorded path / callback
            acknowledge_consent(session, privacy_acknowledged=False)
            abandon(session)
            result.turns.append(VoiceTurn("assistant",
                "No problem. We can take your details without recording. A lawyer will call you back to continue.",
                {"state": "S9", "path": "non_recorded_or_callback"}))
            return result

        # ----- S1: Triage — ask about injuries FIRST (G-20) -----
        # We pull slot 14 (injuries) as a special early check.
        self._ask(result, "First, is anyone hurt — no-one, minor injuries, or serious injuries?", state="S1", slot=14)
        # Get the response
        inj_turn = next(iterator, None)
        if not inj_turn:
            return result
        inj_value = self._extract_value(inj_turn)
        inj_value = _normalise_user_input(inj_value)
        if inj_value == "serious":
            # G-20: serious injury -> immediate escalation, no further slots.
            session.intake["injuries"] = "serious"
            session.escalation = "esc-injury"
            session.escalation_reason = "serious injury reported"
            session.pii_persisted = True
            self._handle_escalation(result)
            return result
        # For non-serious: continue and let the regular S3 intake handle it.
        # We record the injuries answer for later.

        # ----- S3: Intake loop -----
        # Process remaining transcript entries as slot inputs. The order is
        # spec-fixed; missing slots are filled from the transcript in order.
        # We collect all user inputs into a buffer and feed them in slot order.
        user_inputs_buffer: list[Any] = []
        for turn in iterator:
            if "input" in turn:
                user_inputs_buffer.append(_normalise_user_input(turn["input"]))
            elif "dtmf" in turn:
                user_inputs_buffer.append(turn["dtmf"])
            elif "confirm" in turn:
                user_inputs_buffer.append({"confirm": turn["confirm"]})
            else:
                user_inputs_buffer.append(turn)

        # Feed slots in order. For each slot that needs a value, keep trying
        # buffer values until one is accepted (or buffer / re-prompt cap runs
        # out, in which case the state machine itself fires the repompt-cap
        # escalation).
        for slot_id in range(1, len(SLOT_DEFINITIONS) + 1):
            slot_def = SLOT_DEFINITIONS[slot_id - 1]
            if not slot_def["mandatory"]:
                continue
            if session.intake.get(slot_def["slot"]):
                continue  # already filled (e.g. injuries from S1 triage)
            # Try buffer values until one is accepted (max 3 attempts per slot
            # — the state machine's REPROMPT_CAP=2 plus the first try).
            for attempt in range(3):
                while user_inputs_buffer and isinstance(user_inputs_buffer[0], dict) and "confirm" in user_inputs_buffer[0]:
                    user_inputs_buffer.pop(0)
                if not user_inputs_buffer:
                    break
                value = user_inputs_buffer.pop(0)
                # Resolve DTMF -> slot value
                if isinstance(value, str) and _dtmf_map_for_slot(slot_id) and value in _dtmf_map_for_slot(slot_id):
                    value = _dtmf_map_for_slot(slot_id)[value]
                r = submit_slot(session, slot_id, value)
                if r.get("end_state") == "SX-ESCALATE":
                    self._capture(result, f"slot {slot_id} -> {r}", meta=r)
                    if session.escalation:
                        self._handle_escalation(result)
                    return result
                if r.get("slot_accepted"):
                    slot_name = slot_def["slot"]
                    confirm_text = CONFIRM_BACK.get(slot_name, "So that's {value} — is that right?").format(value=value)
                    self._ask(result, confirm_text, state=session.state, slot_id=slot_id, confirm_back=True)
                    break
                # Re-prompt: log it and try the next buffer value
                self._ask(result, f"Sorry, {r.get('error', 'please try again')}",
                          state=session.state, slot_id=slot_id, reprompt=True)
            else:
                # Buffer exhausted for this slot; break and let classification
                # run with whatever we have (insufficient band if needed)
                break

        # ----- S4: Classify -----
        if session.state == "S4-CLASSIFY":
            er = run_classification(session)
            result.classification = er
            if er.escalation:
                self._handle_escalation(result)
                return result
            # ----- S5: Fault-info — attach master (full first, short after) -----
            self._maybe_attach_master(result, full=True)
            text = er.text_web or ""
            try:
                from app.config import resolve_strict
                resolved = resolve_strict(text)
            except Exception:
                resolved = text
            self._ask(result, resolved, state="S5", band=er.band, scenario=er.scenario_id)
            # CR-4-01: real-world STT follow-up robustness. We support two
            # trigger paths:
            #   1. Explicit {"followup": "..."} turn (test hook).
            #   2. Free-text re-entry via the S5/S6 buffer that contains
            #      a followup signal phrase ("what about", "and what if",
            #      "what does that mean for", "ok but", "what about my").
            # On a trigger we emit a second fault output with the short-form
            # disclaimer (G-37) and audit the followup.
            followup_signals = (
                "what about", "and what if", "what does that mean for",
                "ok but", "what about my", "what about the",
                "how does that affect", "and for", "what about my insurer",
            )
            trigger_followup = False
            for entry in user_inputs_buffer:
                if isinstance(entry, dict) and "followup" in entry:
                    trigger_followup = True
                    break
                if isinstance(entry, str):
                    low = entry.lower()
                    if any(sig in low for sig in followup_signals):
                        trigger_followup = True
                        break
            if trigger_followup:
                self._maybe_attach_master(result, full=False)
                self._ask(result, resolved, state="S5",
                          band=er.band, scenario=er.scenario_id, followup=True)
        # ----- S7/S8: close -----
        if session.state in ("S5-FAULT-INFO", "S6-EVIDENCE", "S7-NEXT-STEPS"):
            complete_intake(session)
        self._ask(result, f"All done. Your reference is {session.reference}. A lawyer will call you back within {get_disclaimer('master') and 'during the next business day'}.", state="S8")
        return result

    def _extract_value(self, turn: dict[str, Any]) -> str:
        if "input" in turn:
            return str(turn["input"])
        if "dtmf" in turn:
            return str(turn["dtmf"])
        if "consent" in turn:
            return str(turn["consent"])
        if "confirm" in turn:
            return str(turn["confirm"])
        return ""

    def _handle_escalation(self, result: VoiceDialogResult) -> None:
        """Escalation is terminal for AI assessment. Route via warm transfer
        (business hours) or callback booking (after hours). Brief flagged
        urgent in either case (G-32)."""
        trigger = result.session.escalation
        if not trigger:
            return
        # Map escalation trigger -> handoff variant
        variant_map = {
            "esc-injury": "injury",
            "esc-hitrun": "complexity",
            "esc-vulnerable": "vulnerability",
            "esc-fraud": "dispute_fraud",
            "esc-dispute": "dispute_fraud",
            "esc-multiparty": "complexity",
            "esc-advice": "advice",
            "repompt-cap": "complexity",
            "state-scope": "complexity",
        }
        variant = variant_map.get(trigger, "complexity")
        handoff_text = get_disclaimer(f"escalation_handoff.{variant}")
        if self.business_hours:
            result.warm_transfer = True
            result.brief_flagged_urgent = True
            self._ask(result, f"Important — {trigger} detected. I'm transferring you now. {handoff_text}",
                     state="SX", action="warm_transfer", escalation=trigger)
        else:
            result.callback_booking = True
            result.brief_flagged_urgent = True
            self._ask(result, f"After hours — {trigger} detected. {handoff_text}",
                     state="SX", action="callback_booking", escalation=trigger)
