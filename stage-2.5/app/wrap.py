"""Stage 2.5 API — thin HTTP wrapper around stage-3/app/.

Contract endpoints (Stage 2.5 Build Request §2 + Lovable Build Contract):
    GET   /healthz
    POST  /api/session
    POST  /api/consent
    POST  /api/slot
    POST  /api/classify
    GET   /api/pdf/:ref
    GET   /api/brief/:ref

Key constraints:
- No new logic. If you find yourself writing classification, stop.
- /api/classify band MUST equal engine.classify(intake).band (G-41).
- Disclaimer already resolved in /api/classify (G-42, G-18 across HTTP).
- Escalation short-circuits over HTTP (G-43).
- No PII in URLs or query strings (G-44).
- /api/brief is role-gated server-side (G-45).
- x-test-mode is env-gated (G-46).
- /healthz returns engine + rule-tree versions (G-47).
- CORS allow-list (G-49).
"""
from __future__ import annotations

import base64
import importlib
import importlib.util
import json
import os
import re
import secrets
import sys
import types
from pathlib import Path
from typing import Any, Optional

# ----- Bootstrap: temporarily expose stage-3's app package as `app` in
# sys.modules, load all stage-3 modules, then restore. This is the
# minimal-fuss way to satisfy stage-3's internal `from app import X`
# statements while still letting stage-2.5 use its own `app` package. -----
_THIS_DIR = Path(__file__).resolve().parent
_STAGE25_ROOT = _THIS_DIR.parent
_STAGE3_ROOT = _STAGE25_ROOT.parent / "stage-3"

if str(_STAGE3_ROOT) not in sys.path:
    sys.path.insert(0, str(_STAGE3_ROOT))

# Save any pre-existing `app` registration (so the wrapper can put it back
# after stage-3 is loaded).
_preserved_app = sys.modules.get("app")
# Load stage-3's app package
_spec = importlib.util.spec_from_file_location(
    "app", _STAGE3_ROOT / "app" / "__init__.py",
    submodule_search_locations=[str(_STAGE3_ROOT / "app")],
)
_stage3_app_pkg = importlib.util.module_from_spec(_spec)
sys.modules["app"] = _stage3_app_pkg
_spec.loader.exec_module(_stage3_app_pkg)

# Now load the stage-3 submodules
def _load(name: str):
    full = f"app.{name}"
    spec2 = importlib.util.spec_from_file_location(full, _STAGE3_ROOT / "app" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec2)
    sys.modules[full] = mod
    spec2.loader.exec_module(mod)
    return mod

stage3_engine        = _load("engine")
stage3_state_machine = _load("state_machine")
stage3_pdf_gen       = _load("pdf_gen")
stage3_intake_brief  = _load("intake_brief")
stage3_auth          = _load("auth")
stage3_audit         = _load("audit")
stage3_config        = _load("config")
stage3_store         = _load("store")


# CR-4-02: wire {{BUSINESS_HOURS}} / {{CALLBACK_SLA}} (and the rest of the
# STAGE2_TOKENS) to runtime env vars. The default values from
# stage3_config remain as fallbacks. Real firm values resolve at Stage 5.
_RUNTIME_TOKEN_OVERRIDES: dict[str, str] = {}
for _env_key, _token in (
    ("FIRM_NAME",          "{{FIRM_NAME}}"),
    ("FIRM_PHONE",         "{{FIRM_PHONE}}"),
    ("CALLBACK_SLA",       "{{CALLBACK_SLA}}"),
    ("BUSINESS_HOURS",     "{{BUSINESS_HOURS}}"),
    ("RETENTION_PERIOD",   "{{RETENTION_PERIOD}}"),
    ("TOW_PROVIDER_REF",   "{{TOW_PROVIDER_REF}}"),
    ("RENTAL_PARTNER_REF", "{{RENTAL_PARTNER_REF}}"),
    ("PERSONA_NAME",       "{{PERSONA_NAME}}"),
):
    _v = os.environ.get(_env_key)
    if _v:
        _RUNTIME_TOKEN_OVERRIDES[_token] = _v
if _RUNTIME_TOKEN_OVERRIDES:
    stage3_config.STAGE2_TOKENS.update(_RUNTIME_TOKEN_OVERRIDES)

# Restore whichever `app` was registered before we stomped it. If nothing
# was registered before (i.e. stage-2.5/app isn't loaded yet), pop the
# stage-3 alias so the wrapper's `app` package loads fresh.
if _preserved_app is None:
    sys.modules.pop("app", None)
else:
    sys.modules["app"] = _preserved_app

# FastAPI
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__ as STAGE25_VERSION


# ----- Shared singletons -----
# Stage 4 (F-A): wire the real Supabase-backed store when SUPABASE_URL +
# SUPABASE_SERVICE_ROLE_KEY are set. Serverless cannot hold state in-process
# (each invocation is a fresh process), so a persistent store is REQUIRED in
# deployment; without env vars we fall back to the in-memory store for local
# preview. The adapter implements the SessionStore Protocol (`save`); wrap.py
# calls `.put()`, so we alias it. Audit is mirrored into the store's
# append-only table when supported.
# NOTE: wired for deployment but NOT run from the planning seat — verify with
# `stage-4/scripts/preflight.py` against staging (75-test suite must stay green).
def _build_sessions() -> Any:
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        _store_path = _STAGE25_ROOT.parent / "stage-4" / "app" / "supabase_store.py"
        _spec_s = importlib.util.spec_from_file_location("stage4_supabase_store", _store_path)
        _mod_s = importlib.util.module_from_spec(_spec_s)
        _spec_s.loader.exec_module(_mod_s)
        store = _mod_s.build_store()
        if not hasattr(store, "put"):
            store.put = store.save  # Protocol uses save(); wrap.py calls put()
        return store
    return stage3_store.InMemoryStore()


SESSIONS = _build_sessions()


# ----- Evidence store (Feature 2 — photo upload bound to case file) -----
# Same pattern as _build_sessions(): load the stage-4 adapter if a Supabase
# project is configured, else fall back to the in-memory dev store. The store
# is consent-gated in the HTTP layer (see /api/intake/{ref}/evidence) and
# every upload/list/delete writes to AUDIT below.
def _build_evidence_store() -> Any:
    _store_path = _STAGE25_ROOT.parent / "stage-4" / "app" / "evidence_store.py"
    if not _store_path.exists():
        return None
    # Register on sys.modules BEFORE exec so @dataclass inside the module can
    # resolve its own __module__ (Python 3.9 dataclasses needs this; the
    # session-store adapter avoids it because its stage3 modules register
    # themselves via the same pattern). Alias under a unique name to avoid
    # colliding with stage-3's `app` package.
    _alias = "stage4_evidence_store"
    _spec_e = importlib.util.spec_from_file_location(_alias, _store_path)
    _mod_e = importlib.util.module_from_spec(_spec_e)
    sys.modules[_alias] = _mod_e
    _spec_e.loader.exec_module(_mod_e)
    return _mod_e.build_evidence_store()


EVIDENCE_STORE = _build_evidence_store()


def _maybe_persist_evidence_row(rec: Any) -> None:
    """Best-effort write of the case_evidence metadata row.

    Only fires when the active session store exposes its Supabase client (i.e.
    production/staging). The test runner (InMemory) has no DB to write to and
    skips silently — the test suite asserts against the audit_log + the store
    return value, which are both storage-agnostic. Failures here are swallowed
    so a metadata hiccup can never break the upload path (the audit_log +
    S3 object are the source of truth; this row is an index).
    """
    try:
        client = getattr(SESSIONS, "_client", None)
        if client is None:
            return
        client.table("case_evidence").insert({
            "evidence_id": rec.file_id,
            "reference": rec.reference,
            "s3_key": rec.s3_key,
            "s3_bucket": rec.s3_bucket,
            "content_type": rec.content_type,
            "size_bytes": rec.size_bytes,
            "content_hash_sha256": rec.sha256,
            "uploaded_by": rec.uploaded_by,
            "uploaded_at": rec.uploaded_at,
            "storage_class": rec.storage_class,
        }).execute()
    except Exception:
        pass


class _PersistingAudit:
    """Mirror in-memory audit (language-level immutability) into the store's
    append-only audit_log table when the active store supports it (G-34/G-54).
    Maps wrap.py's `user=` to the adapter's `actor=`. Store failures are
    swallowed so an audit-write hiccup never breaks the intake path.

    P0-1 fix (2026-07-14 review): delegates `all()` / `filter()` / `export()`
    to the in-memory base so callers that read the log (e.g. the PD disclosure
    presence check) don't AttributeError against this wrapper in production.
    Note: in serverless, the in-memory copy is per-instance and empty across
    cold starts — callers that need a durable read must query the store's
    audit_log table directly (see `_durable_pd_disclosure_presented`)."""

    def __init__(self, base: Any, store: Any) -> None:
        self._base = base
        self._store = store

    def append(self, *, session_id: str, user: str, action: str,
               inputs: dict, rule_path: list, output: dict) -> Any:
        rv = self._base.append(
            session_id=session_id, user=user, action=action,
            inputs=inputs, rule_path=rule_path, output=output,
        )
        try:
            self._store.append_audit(
                session_id=session_id, actor=user, action=action,
                inputs=inputs, rule_path=rule_path, output=output,
            )
        except Exception:
            pass
        return rv

    # ----- Read-side delegation (so wrapper behaves like the underlying log) -----
    def all(self) -> list[Any]:
        return self._base.all()

    def filter(self, **kwargs: Any) -> list[Any]:
        return self._base.filter(**kwargs)

    def export(self) -> list[dict[str, Any]]:
        return self._base.export()

    def __len__(self) -> int:
        return len(self._base)


def _durable_pd_disclosure_presented(reference: str) -> Optional[dict[str, Any]]:
    """Durable check: did this session already have a pd_disclosure_presented
    event? Queries the persistent audit_log table (not process memory), so the
    check works across serverless cold starts. Returns the audit row's inputs
    (carrying disclosure_hash + version) if found, else None.

    P0-1 fix: the previous in-memory-only check would 500 against this wrapper
    in production, and would silently miss events written by another lambda."""
    durably_query = getattr(SESSIONS, "find_audit_events", None)
    if durably_query is None:
        # In-memory store (tests / local dev): fall back to process log.
        for e in AUDIT.all():
            if e.action != "pd_disclosure_presented":
                continue
            if e.inputs.get("reference") == reference:
                return e.inputs
        return None
    try:
        rows = durably_query(action="pd_disclosure_presented",
                             reference=reference, limit=1)
        if rows:
            return rows[0].get("inputs")
    except Exception:
        # Store read failure → fall back to process log (best-effort).
        for e in AUDIT.all():
            if e.action == "pd_disclosure_presented" and e.inputs.get("reference") == reference:
                return e.inputs
    return None


AUDIT = (
    _PersistingAudit(stage3_audit.DEFAULT_AUDIT_LOG, SESSIONS)
    if hasattr(SESSIONS, "append_audit")
    else stage3_audit.DEFAULT_AUDIT_LOG
)

# CORS allow-list (CR-5-02 / G-55).
# In production we lock to the EXACT Lovable project slug + production domain.
# No more `*.lovable.app` — that allowed ANY tenant to call our API.
# Read from CORS_ALLOWED_ORIGINS env var (comma-separated). The deployer
# must set this; the default below is preview-only.
CORS_ALLOWLIST: list[str] = [
    o.strip() for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        # Preview default: only the staging Lovable project slug.
        "https://preview--smash-repair-engine.lovable.app,http://localhost:3000",
    ).split(",") if o.strip()
]


def _app_env() -> str:
    """Read APP_ENV. 'production' disables test mode (G-46)."""
    return os.environ.get("APP_ENV", "preview").lower()


def _cors_origins() -> list[str]:
    """Return the active CORS allow-list. Never wildcard."""
    return sorted(CORS_ALLOWLIST)


def _is_test_mode_active(headers: dict[str, str]) -> bool:
    """x-test-mode is inert in production (G-46)."""
    if _app_env() == "production":
        return False
    return headers.get("x-test-mode") in ("1", "true", "yes", "True", "TRUE")


def _deterministic_ref(seed: str) -> str:
    """Used only when x-test-mode=1 in preview/staging. Derives a stable
    reference from the seed so weblink runs are reproducible."""
    try:
        import hashlib
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8].upper()
    except Exception:
        digest = secrets.token_hex(4).upper()
    return f"GF-{digest}"


# ----- Slot UI catalog (F-F) -----
# The frontend renders whatever the engine sends — the engine OWNS the
# conversational "chrome" (prompt text + option labels) per the Lovable
# build contract. This catalog gives each spec slot a prompt and an
# inputType; option *values* come from SLOT_DEFINITIONS (the engine's
# authoritative enum), and labels are humanised here. This is distinct
# from the fault `outputText`/`disclaimerText`, which remain verbatim
# from the engine and are NOT touched here.
#   enum     -> single_choice
#   multienum-> multi_choice
#   text     -> text
SLOT_UI: dict[str, dict[str, str]] = {
    "state_of_accident":    {"prompt": "Which state or territory did the accident happen in?", "inputType": "single_choice"},
    "datetime_location":    {"prompt": "When and roughly where did it happen? A date, rough time, and the street or suburb is plenty.", "inputType": "text"},
    "accident_type":        {"prompt": "What kind of accident was it?", "inputType": "single_choice"},
    "user_vehicle":         {"prompt": "What were you driving? Make, model and year if you have them.", "inputType": "text"},
    "other_vehicles":       {"prompt": "What other vehicles were involved?", "inputType": "text"},
    "movement_description": {"prompt": "In your own words, what were you doing the moment it happened?", "inputType": "text"},
    "damage_locations":     {"prompt": "Where is the damage to your vehicle? Select all that apply.", "inputType": "multi_choice"},
    "control_devices":      {"prompt": "Were there any traffic controls at the scene?", "inputType": "single_choice"},
    "police_attendance":    {"prompt": "Did police attend the scene?", "inputType": "single_choice"},
    "witnesses":            {"prompt": "Were there any witnesses? (optional)", "inputType": "text"},
    "dashcam":              {"prompt": "Was there any dashcam footage?", "inputType": "single_choice"},
    "photos_taken":         {"prompt": "Did you take photos at the scene?", "inputType": "single_choice"},
    "other_driver_details": {"prompt": "Did you exchange details with the other driver? (optional)", "inputType": "text"},
    "injuries":             {"prompt": "Was anyone injured?", "inputType": "single_choice"},
    # Personal-injury extension slots (spec §1.3, §2.1, §3.1)
    "claim_type":           {"prompt": "What kind of claim is this?", "inputType": "single_choice"},
    "incident_date":        {"prompt": "When did it happen?", "inputType": "date"},
    # Public Liability
    "pl_location":          {"prompt": "Where did it happen?", "inputType": "single_choice"},
    "hazard_type":          {"prompt": "What kind of hazard caused it?", "inputType": "single_choice"},
    "hazard_warned":        {"prompt": "Was there any warning about the hazard?", "inputType": "single_choice"},
    "hazard_duration":      {"prompt": "How long had the hazard been there, as far as you know?", "inputType": "single_choice"},
    "claimant_activity":    {"prompt": "What were you doing at the time? (optional)", "inputType": "single_choice"},
    "defendant_type":       {"prompt": "Who is responsible for the place? (optional)", "inputType": "single_choice"},
    "at_work":              {"prompt": "Did it happen while you were at work? (optional)", "inputType": "single_choice"},
    "harm_severity":        {"prompt": "How serious was the harm you suffered?", "inputType": "single_choice"},
    # Medical Negligence
    "provider_type":        {"prompt": "Who provided the treatment or care?", "inputType": "single_choice"},
    "provider_public_private": {"prompt": "Was the provider public or private? (optional)", "inputType": "single_choice"},
    "treatment_type":       {"prompt": "What kind of treatment or care was involved?", "inputType": "single_choice"},
    "outcome_nature":       {"prompt": "How would you describe what went wrong?", "inputType": "single_choice"},
    "second_opinion":       {"prompt": "Have you had a second medical opinion? (optional)", "inputType": "single_choice"},
    "multiple_providers":   {"prompt": "Were multiple providers or facilities involved? (optional)", "inputType": "single_choice"},
    # Property Damage (Lane 1 — third-party motor recovery)
    "collision_type":       {"prompt": "What kind of collision was it?", "inputType": "single_choice"},
    "police_event_number":  {"prompt": "Do you have a police event number? (optional)", "inputType": "text"},
    "at_fault_uninsured":   {"prompt": "Does the other driver have insurance cover?", "inputType": "single_choice"},
    "repairer_quote":       {"prompt": "Do you have a repairer's quote or assessment? (optional)", "inputType": "text"},
    "vehicle_class":        {"prompt": "What kind of vehicle were you driving? (optional)", "inputType": "single_choice"},
    "hire_need":            {"prompt": "Do you need a replacement vehicle while yours is off the road? (optional)", "inputType": "single_choice"},
}

# Calm handoff copy shown when the engine escalates (serious injury,
# re-prompt cap, etc.). This is intake chrome, not legal advice — the
# fault assessment is deliberately NOT produced on an escalated session.
ESCALATION_MESSAGE = (
    "Thank you for telling me. Based on what you've shared, the right next step "
    "is for one of our team to speak with you directly rather than continue here. "
    "Your reference number is {ref} — please keep it handy. We'll be in touch shortly; "
    "you don't need to do anything else right now."
)


# Plain-English labels for option values the auto-humaniser can't make clear.
# Drives the dropdowns the customer actually sees (clarity fixes for state +
# the confusing parking/other choices).
_OPTION_LABELS: dict[str, str] = {
    # state_of_accident
    "NSW": "New South Wales",
    "outside_nsw": "Somewhere else in Australia",
    # accident_type
    "rear-end": "Rear-end (hit from behind, or I hit the car in front)",
    "T-intersection": "Give-way or T-intersection",
    "roundabout": "Roundabout",
    "merge": "Merging or changing lanes",
    "reversing": "I was reversing",
    "car_park": "Car park — I was driving or reversing in a car park",
    "parked_hit": "My parked car was hit (whether or not I was in it)",
    "intersection_signalised": "Traffic-light intersection",
    "turning_right": "Turning right across oncoming traffic",
    "sideswipe_same_direction": "Sideswipe — both going the same way",
    "multi_vehicle": "Multiple vehicles (3 or more)",
    "not_listed": "Something else / I'm not sure",
    # claim_type (spec §1.3)
    "motor": "I was hurt in a car accident",
    "property_damage": "My car was damaged — I wasn't at fault (repairs & replacement vehicle)",
    "public_liability": "I was hurt in a public place / on someone's property",
    "medical_negligence": "I was hurt by medical treatment / care",
    # PL locations
    "supermarket": "Supermarket",
    "shopping_centre": "Shopping centre",
    "footpath_council": "Footpath / council land",
    "private_premises": "Private premises",
    "workplace": "At work",
    "construction_site": "Construction site",
    "rental_property": "Rental property",
    "commercial_premises": "Commercial premises",
    "stairwell": "Stairwell",
    "car_park": "Car park",
    "corridor": "Corridor",
    # hazard types
    "wet_surface": "Wet surface (spill, cleaning, rain)",
    "spill": "Spill",
    "rain_tracked": "Rain-tracked water",
    "cleaning": "Cleaning",
    "uneven_surface": "Uneven surface",
    "broken_pavement": "Broken pavement",
    "mat": "Loose mat",
    "cabling": "Cabling",
    "step": "Step / change of level",
    "pothole": "Pothole",
    "falling_object": "Falling object",
    "stock": "Falling stock",
    "signage": "Falling signage",
    "inadequate_lighting": "Inadequate lighting",
    "defective_premises": "Defective premises",
    "broken_rail": "Broken handrail",
    "broken_stair": "Broken stair",
    "fixture": "Defective fixture",
    "other_public_place": "Another public place",
    # hazard_warned / at_work
    "yes": "Yes",
    "no": "No",
    "unsure": "I'm not sure",
    # hazard_duration
    "just_happened": "Just happened (seconds)",
    "short": "A short time",
    "long": "A long time",
    "extended": "Extended period",
    "30min_plus": "30 minutes or more",
    # claimant_activity
    "walking_normally": "Walking normally",
    "rushing": "Rushing",
    "carrying_items": "Carrying things",
    "on_phone": "On my phone",
    "browsing": "Browsing",
    "working": "Working",
    # defendant_type
    "private_occupier": "A private occupier / owner",
    "council": "Council",
    "public_authority": "A public authority",
    "government": "Government",
    "business": "A business",
    "unknown": "I don't know",
    # harm_severity
    "none": "No physical harm",
    "minor": "Minor",
    "serious": "Serious",
    "permanent_impairment": "Permanent impairment",
    "death": "Death",
    # provider_type
    "gp": "GP",
    "hospital": "Hospital",
    "specialist": "Specialist",
    "surgeon": "Surgeon",
    "dentist": "Dentist",
    "cosmetic": "Cosmetic provider",
    "pharmacy": "Pharmacy",
    "birth_centre": "Birth centre",
    # provider_public_private
    "public": "Public",
    "private": "Private",
    # treatment_type
    "surgical_outcome": "Surgical outcome",
    "misdiagnosis_delay": "Misdiagnosis or delayed diagnosis",
    "medication_error": "Medication error",
    "birth_injury": "Birth injury",
    "dental": "Dental treatment",
    "consent_not_informed": "I wasn't properly informed / didn't consent",
    # outcome_nature
    "unexpected_outcome": "An unexpected outcome",
    "suspected_error": "What I think was an error",
    "not_sure": "I'm not sure",
    "communication_only": "Only a problem with communication / manner",
    # second_opinion / multiple_providers
    "not_yet": "Not yet",
    # injuries (already has none/minor/serious above via harm_severity overlaps)
    # Property Damage — collision_type (PD-specific; mirrors motor geometry but
    # framed for the not-at-fault recovery customer).
    "give_way": "Give-way or stop sign / line",
    "lane_change": "Changing lanes",
    "parking": "Parking manoeuvre",
    # PD — at_fault_uninsured
    "at_fault_uninsured": "Uninsured driver",
    # PD — vehicle_class
    "small": "Small / hatchback",
    "sedan": "Sedan / wagon",
    "suv_4wd": "SUV / 4WD",
    "ute_van": "Ute / van",
    "prestige_luxury": "Prestige / luxury",
    "commercial_heavy": "Commercial / heavy vehicle",
    # PD — hire_need
    "yes_needed": "Yes — I need a replacement vehicle",
    "no_not_needed": "No — I have another option",
}


def _opt_label(value: str) -> str:
    """Humanise an enum value for display. Explicit labels win; state codes stay upper-case."""
    if value in _OPTION_LABELS:
        return _OPTION_LABELS[value]
    if value.isupper():
        return value
    return value.replace("-", " ").replace("_", " ").capitalize()


def _slot_question_for(slot_def: dict[str, Any]) -> dict[str, Any]:
    """Build a frontend SlotQuestion for a given slot def (any branch)."""
    ui = SLOT_UI.get(slot_def["slot"], {"prompt": slot_def["slot"], "inputType": _input_type_for(slot_def["type"])})
    options = None
    if slot_def.get("options"):
        options = [{"value": v, "label": _opt_label(v)} for v in slot_def["options"]]
    return {
        "slot": slot_def["slot"],
        "prompt": ui["prompt"],
        "inputType": ui["inputType"],
        "options": options,
        "done": False,
    }


def _input_type_for(slot_type: str) -> str:
    """Map a state-machine slot type to a frontend input type."""
    return {
        "enum": "single_choice",
        "multienum": "multi_choice",
        "integer": "text",
        "text": "text",
    }.get(slot_type, "text")


def _slot_question(idx: int) -> dict[str, Any]:
    """Build a frontend SlotQuestion for SLOT_DEFINITIONS[idx] (motor, back-compat).
    Kept for the engine-contract mode that the acceptance tests drive."""
    sd = stage3_state_machine.SLOT_DEFINITIONS[idx]
    ui = SLOT_UI.get(sd["slot"], {"prompt": sd["slot"], "inputType": _input_type_for(sd["type"])})
    options = None
    if sd.get("options"):
        options = [{"value": v, "label": _opt_label(v)} for v in sd["options"]]
    return {
        "slot": sd["slot"],
        "prompt": ui["prompt"],
        "inputType": ui["inputType"],
        "options": options,
        "done": False,
    }


_DONE_QUESTION: dict[str, Any] = {
    "slot": "", "prompt": "", "inputType": "text", "options": None, "done": True,
}


def _progress(intake: dict[str, Any]) -> dict[str, int]:
    """Progress over the mandatory slots of the ACTIVE branch (the only ones
    the engine asks). Branches by claim_type so PL/med-neg get their own totals."""
    active = stage3_state_machine._active_slots(intake, frontend=True)  # type: ignore[attr-defined]
    mandatory = [sd for sd in active if sd["mandatory"]]
    answered = sum(1 for sd in mandatory if intake.get(sd["slot"]))
    return {"answered": answered, "total": len(mandatory)}


def _next_question(intake: dict[str, Any]) -> dict[str, Any]:
    """The next SlotQuestion to ask, or the done sentinel. Uses the active
    branch (motor by default; PL/med-neg when claim_type is set)."""
    active = stage3_state_machine._active_slots(intake, frontend=True)  # type: ignore[attr-defined]
    idx = stage3_state_machine._next_slot_index(intake)  # type: ignore[attr-defined]
    if idx >= len(active):
        return dict(_DONE_QUESTION)
    return _slot_question_for(active[idx])


_SCENARIO_INPUT_TYPE = {
    "enum": "single_choice",
    "multienum": "multi_choice",
    "integer": "text",
    "text": "text",
}


def _scenario_slot_question(q: dict[str, Any]) -> dict[str, Any]:
    """Render a scenario classification_question as a SlotQuestion (T6).
    Uses the question's `question_web` as the prompt and `options` as buttons,
    so the frontend renders it through the existing SlotQuestion path."""
    options = None
    if q.get("options"):
        options = [{"value": v, "label": _opt_label(v)} for v in q["options"]]
    return {
        "slot": q["slot"],
        "prompt": q.get("question_web") or q.get("slot"),
        "inputType": _SCENARIO_INPUT_TYPE.get(q.get("answer_type", "text"), "text"),
        "options": options,
        "done": False,
    }


# ----- Request / response models -----
# Models accept BOTH dialects so the same endpoints serve the Lovable
# frontend (camelCase `ref`) and the engine-contract acceptance tests
# (`reference`). Handlers branch on which key is present.

class SessionRequest(BaseModel):
    channel: str = Field(default="web")
    ref: Optional[str] = None           # frontend consent step: {ref, consentGranted}
    reference: Optional[str] = None     # tolerated alias
    consentGranted: Optional[bool] = None


class ConsentRequest(BaseModel):
    reference: str
    accept: bool


class SlotRequest(BaseModel):
    reference: Optional[str] = None     # engine-contract (tests)
    ref: Optional[str] = None           # frontend
    slot: Optional[str] = None
    value: Any = None


class ClassifyRequest(BaseModel):
    reference: Optional[str] = None
    ref: Optional[str] = None


class ExtrasRequest(BaseModel):
    """Stage 4 (CR-5-01): engine-only intake fields, set via /api/intake/:ref/extras."""
    fields: dict[str, Any]


class ScenarioQuestionRequest(BaseModel):
    """T6: scenario-question injection. No question_id => start (returns the
    first scenario question). With question_id+value => submit an answer."""
    reference: Optional[str] = None
    ref: Optional[str] = None
    question_id: Optional[str] = None
    value: Any = None


# ----- App factory -----

def create_app() -> FastAPI:
    app = FastAPI(title="Stage 2.5 — Engine-as-Endpoint", version=STAGE25_VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWLIST,  # CR-5-02 / G-55: exact origins only
        allow_origin_regex=None,        # no wildcards
        # If a wildcard is present (test mode), credentials MUST be off —
        # Starlette enforces this. Production should never have *.
        allow_credentials=("*",) != tuple(CORS_ALLOWLIST),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ---- /healthz (G-47 + G-VER) ----
    @app.get("/healthz")
    def healthz() -> Any:
        tree = stage3_engine._load_rule_tree()  # type: ignore[attr-defined]  # NSW motor tree
        # Multi-state (per MULTI-STATE-ROLLOUT-PLAN.md): the registry is now
        # keyed by (state, claim_type). healthz reports a per-(state, claim_type)
        # map so the deployer can see which sub-trees are signed and live in
        # each state. The fallback preserves backward compat with older engine
        # builds that still use a flat claim_type-keyed registry.
        registry = getattr(stage3_engine, "RULE_TREE_REGISTRY",
                           {("NSW", "motor"): "rule-tree.nsw.v3.json"})
        # Normalise to a list of (state, claim_type) keys.
        registry_keys: list[tuple[str, str]] = []
        for k in registry.keys():
            if isinstance(k, tuple):
                registry_keys.append(k)
            else:
                # Legacy flat registry (claim_type only) → NSW default.
                registry_keys.append(("NSW", k))
        registry_keys.sort()
        rule_tree_versions: dict[str, Any] = {}
        for (state, claim_type) in registry_keys:
            label = f"{state}.{claim_type}"
            try:
                ct_tree = stage3_engine._load_rule_tree_for(claim_type, state)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001 — healthz must never crash
                rule_tree_versions[label] = {"error": str(exc)}
                continue
            scenarios = ct_tree.get("scenarios", [])
            signed = sum(
                1 for s in scenarios
                if isinstance(s.get("legal_signoff"), dict)
                and s["legal_signoff"].get("approved") is True
            )
            current_hash = stage3_engine._compute_scenarios_hash(ct_tree)  # type: ignore[attr-defined]
            # P2 fix (2026-07-14 review): live means every scenario is BOTH
            # approved AND its sign-off version equals the current content
            # hash. The previous definition (signed == total) overstated
            # "live" for stale-but-approved trees. Runtime escalates stale
            # as stale-signoff, so healthz must reflect the same.
            signed_current = sum(
                1 for s in scenarios
                if isinstance(s.get("legal_signoff"), dict)
                and s["legal_signoff"].get("approved") is True
                and s["legal_signoff"].get("version") == current_hash
            )
            signed_approved = sum(
                1 for s in scenarios
                if isinstance(s.get("legal_signoff"), dict)
                and s["legal_signoff"].get("approved") is True
            )
            stale = sum(
                1 for s in scenarios
                if isinstance(s.get("legal_signoff"), dict)
                and s["legal_signoff"].get("approved") is True
                and s["legal_signoff"].get("version") != current_hash
            )
            unsigned = len(scenarios) - signed_approved
            rule_tree_versions[label] = {
                "version": ct_tree.get("version", "unknown"),
                "hash": current_hash,
                "scenarios": len(scenarios),
                "signed_current": signed_current,
                "signed_approved": signed_approved,
                "stale": stale,
                "unsigned": unsigned,
                "live": signed_current == len(scenarios),
            }
        return {
            "status": "ok",
            "engine_version": "1.0.0",
            "rule_tree_version": tree.get("version", "unknown"),  # NSW motor (back-compat)
            "rule_tree_hash": stage3_engine._compute_scenarios_hash(tree),  # G-VER, NSW motor
            "rule_tree_versions": rule_tree_versions,  # per (state, claim_type)
            "api_version": STAGE25_VERSION,
        }

    # ---- /api/session (S0/S0a) ----
    # Serves two frontend calls on one path:
    #   start   POST {}                       -> {ref, consentRequired, consentGranted:false, ...}
    #   consent POST {ref, consentGranted:true}-> {ref, consentRequired, consentGranted:true}
    # plus the engine-contract `reference`/`consent_required`/`next` fields
    # for the acceptance tests (no field collisions, so both ship together).
    @app.post("/api/session")
    def create_session(req: SessionRequest, request: Request) -> Any:
        # --- Consent branch (frontend grantConsent posts here) ---
        ref = req.ref or req.reference
        if req.consentGranted is not None and ref:
            s = SESSIONS.by_reference(ref)
            if s is None:
                raise HTTPException(status_code=404, detail="session not found")
            if not req.consentGranted:
                stage3_state_machine.abandon(s)
                SESSIONS.put(s)
                return {"ref": ref, "reference": ref, "consentRequired": True,
                        "consentGranted": False, "next": "abandoned"}
            stage3_state_machine.acknowledge_consent(s, privacy_acknowledged=True)
            SESSIONS.put(s)  # F-E: persist consent so the next request sees it
            AUDIT.append(
                session_id=s.session_id, user=_client_ip(request), action="consent_granted",
                inputs={"reference": ref}, rule_path=[], output={"state": s.state},
            )
            # PD-COUNSEL-MEMO §3.3: the consent-grant doubles as the
            # pd_disclosure_acknowledged sibling event for any session whose
            # pd_disclosure_presented event already fired. Carry the disclosure
            # hash forward so the acknowledgement is bound to the exact text
            # version the user saw (P1-3 fix). Uses the durable check (P0-1 fix)
            # so this works across serverless cold starts and doesn't 500
            # against _PersistingAudit.
            presented_inputs = _durable_pd_disclosure_presented(ref)
            if presented_inputs is not None:
                AUDIT.append(
                    session_id=s.session_id, user=_client_ip(request),
                    action="pd_disclosure_acknowledged",
                    inputs={
                        "reference": ref, "claim_type": "property_damage",
                        "disclosure_hash": presented_inputs.get("disclosure_hash"),
                        "disclosure_version": presented_inputs.get("disclosure_version"),
                    },
                    rule_path=[], output={"state": s.state},
                )
            return {"ref": s.reference, "reference": s.reference,
                    "consentRequired": True, "consentGranted": True, "next": "slot"}

        # --- Start branch (frontend startSession + engine-contract start) ---
        # CR-5-03 / G-56: per-IP rate limit on session creation.
        ip = _client_ip(request)
        if not RATE_LIMITER.allow(ip):
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded; retry after a minute",
                headers={"Retry-After": "60"},
            )
        s = stage3_state_machine.new_session()
        s.reference = stage3_state_machine._new_reference()  # type: ignore[attr-defined]
        if _is_test_mode_active(dict(request.headers)):
            seed = json.dumps(req.model_dump(), sort_keys=True)
            s.reference = _deterministic_ref(seed)
            # Test-mode determinism: the same seed maps to the same reference.
            # Re-creating it must be idempotent — reuse the existing session
            # rather than inserting a duplicate (the store's `reference` column
            # is UNIQUE, so a second insert would 500). Production refs are
            # random, so this branch never runs there.
            existing = SESSIONS.by_reference(s.reference)
            if existing is not None:
                return {
                    "ref": existing.reference,
                    "consentRequired": True,
                    "consentGranted": bool(getattr(existing, "consent", False)),
                    "reference": existing.reference,
                    "consent_required": True,
                    "next": "consent",
                }
        SESSIONS.put(s)
        # Audit (G-34 / G-52: every session logs timestamp + session id)
        AUDIT.append(
            session_id=s.session_id, user=ip, action="session_created",
            inputs={"channel": req.channel, "reference": s.reference},
            rule_path=[], output={"state": s.state},
        )
        return {
            "ref": s.reference,            # frontend
            "consentRequired": True,       # frontend
            "consentGranted": False,       # frontend
            "reference": s.reference,      # engine-contract (tests)
            "consent_required": True,
            "next": "consent",
        }

    # ---- /api/consent (S0a) ----
    @app.post("/api/consent")
    def post_consent(req: ConsentRequest, request: Request) -> Any:
        s = SESSIONS.by_reference(req.reference)
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        if not req.accept:
            stage3_state_machine.abandon(s)
            SESSIONS.put(s)
            return {"next": "abandoned"}
        stage3_state_machine.acknowledge_consent(s, privacy_acknowledged=True)
        SESSIONS.put(s)  # F-E: persist consent so the next request sees it (real store)
        # PD-COUNSEL-MEMO §3.3: the consent-grant doubles as the
        # pd_disclosure_acknowledged sibling event if the presented-event fired.
        # Carry the disclosure hash forward (P1-3 fix). Uses the durable check
        # (P0-1 fix) — works across serverless cold starts.
        presented_inputs = _durable_pd_disclosure_presented(req.reference)
        if presented_inputs is not None:
            ip = _client_ip(request)
            AUDIT.append(
                session_id=s.session_id, user=ip,
                action="pd_disclosure_acknowledged",
                inputs={
                    "reference": req.reference, "claim_type": "property_damage",
                    "disclosure_hash": presented_inputs.get("disclosure_hash"),
                    "disclosure_version": presented_inputs.get("disclosure_version"),
                },
                rule_path=[], output={"state": s.state},
            )
        slot_def = stage3_state_machine.SLOT_DEFINITIONS[0]
        return {"next": "slot", "slot": {"id": 1, "name": slot_def["slot"], "type": slot_def["type"]}}

    # ---- /api/disclosure/{claim_type} (PD-COUNSEL-MEMO-2026-07-14 §3.3) ----
    # Returns the pre-consent disclosure text for the given claim_type and fires
    # the pd_disclosure_presented audit event when claim_type=property_damage.
    # The consent_granted audit (fired in /api/session + /api/consent above)
    # doubles as the pd_disclosure_acknowledged sibling event for PD intakes.
    # Together these two events satisfy the memo's evidentiary requirement
    # that the consumer was told before any PII was collected.
    #
    # P1-3 fix (2026-07-14 review): the disclosure text hash is recorded in
    # the audit event so a later text change is detectable, and `ref` is
    # REQUIRED — no anonymous presented-events. This makes the audit pair
    # strong enough to defeat an ACL "I wasn't told" complaint.
    @app.get("/api/disclosure/{claim_type}")
    def get_disclosure(claim_type: str, request: Request) -> Any:
        ref = request.query_params.get("ref")
        ct = claim_type.lower()
        if ct != "property_damage":
            # Motor/PL/med-neg don't carry the PD recovery disclosure today;
            # the privacy notice in /api/session is their consent-gate text.
            return {"claim_type": ct, "disclosure_text": None, "disclosure_hash": None}
        if not ref:
            # The disclosure MUST bind to a session so the presented-event is
            # evidentiary. An anonymous render would prove nothing.
            raise HTTPException(
                status_code=400,
                detail="ref query parameter is required for the PD disclosure"
            )
        try:
            raw = stage3_config.get_disclaimer("pd_recovery_disclosure")
            text = stage3_config.resolve_tokens(raw)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"disclosure render failed: {exc}")
        import hashlib as _hashlib
        disclosure_hash = "sha256:" + _hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        # Fire the presented-event for this session. The session must exist.
        s = SESSIONS.by_reference(ref)
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        ip = _client_ip(request)
        AUDIT.append(
            session_id=s.session_id, user=ip,
            action="pd_disclosure_presented",
            inputs={
                "claim_type": "property_damage", "reference": ref,
                "disclosure_hash": disclosure_hash,
                "disclosure_version": "2026-07-14-v1",
            },
            rule_path=[], output={"state": s.state},
        )
        SESSIONS.put(s)
        return {
            "claim_type": "property_damage",
            "disclosure_text": text,
            "disclosure_hash": disclosure_hash,
            "disclosure_version": "2026-07-14-v1",
        }

    # ---- /api/slot (S3 + validation) ----
    # Two dialects on one path:
    #   frontend: {ref}              -> first question {ref, next: SlotQuestion, progress}
    #             {ref, slot, value} -> {ref, next: SlotQuestion|null, progress}  (next.done -> classify)
    #   engine  : {reference, slot, value} -> {accepted, next, next_slot|slot, ...}  (acceptance tests)
    @app.post("/api/slot")
    def post_slot(req: SlotRequest) -> Any:
        frontend_mode = req.ref is not None
        ref = req.ref or req.reference
        s = SESSIONS.by_reference(ref) if ref else None
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        if not s.consent:
            raise HTTPException(status_code=400, detail="consent required")

        # --- Frontend mode: engine drives the conversation ---
        if frontend_mode:
            # No slot/value => the UI is asking for the FIRST/next question.
            if not req.slot:
                return {"ref": s.reference, "next": _next_question(s.intake),
                        "progress": _progress(s.intake)}
            # Look up the slot id within the active branch (motor by default;
            # PL/med-neg once claim_type is set). The claim_type slot itself
            # (id 100) is resolvable before a branch is chosen.
            active = stage3_state_machine._active_slots(s.intake, frontend=True)  # type: ignore[attr-defined]
            slot_id = None
            for sd in active:
                if sd["slot"] == req.slot:
                    slot_id = sd["id"]
                    break
            if slot_id is None and req.slot == stage3_state_machine.CLAIM_TYPE_SLOT["slot"]:
                slot_id = stage3_state_machine.CLAIM_TYPE_SLOT["id"]
            if slot_id is None:
                # Backward-compat: motor slot submitted before claim_type is set.
                for sd in stage3_state_machine.MOTOR_SLOTS:
                    if sd["slot"] == req.slot:
                        slot_id = sd["id"]
                        break
            if slot_id is None:
                raise HTTPException(status_code=400, detail=f"unknown slot: {req.slot}")
            stage3_state_machine.submit_slot(s, slot_id, req.value)
            SESSIONS.put(s)  # F-E: persist mutation
            # Escalation (serious injury / re-prompt cap) -> end the Q&A; the
            # UI calls classify, which returns the calm handoff message.
            if s.escalation:
                return {"ref": s.reference, "next": dict(_DONE_QUESTION),
                        "progress": _progress(s.intake), "escalated": True}
            # Valid -> advance; invalid -> _next_question returns the SAME slot
            # (not yet stored), so the UI simply re-asks it.
            return {"ref": s.reference, "next": _next_question(s.intake),
                    "progress": _progress(s.intake)}

        # --- Engine-contract mode (acceptance tests) ---
        # Spec slots go through the state machine (with validation).
        # Engine-only fields (e.g. simultaneous_entry, sight_lines) are
        # accepted but stored in the intake dict directly without
        # validation. This matches the test contract for scenario-specific
        # data and keeps the spec slot list authoritative.
        slot_id = None
        for sid, sd in enumerate(stage3_state_machine.SLOT_DEFINITIONS, 1):
            if sd["slot"] == req.slot:
                slot_id = sid
                break

        if slot_id is None:
            # Engine intake field (not a spec slot) — store directly.
            s.intake[req.slot] = req.value
            s.pii_persisted = True
            SESSIONS.put(s)
            return {"accepted": True, "next": "slot"}

        result = stage3_state_machine.submit_slot(s, slot_id, req.value)
        SESSIONS.put(s)  # F-E: persist slot mutation (real store needs explicit save)

        # G-43: escalation short-circuits
        if result.get("end_state") == "SX-ESCALATE" or s.escalation:
            return {
                "accepted": False,
                "escalation": s.escalation,
                "next": "escalated",
                "terminal": True,
            }

        if not result.get("slot_accepted"):
            return {
                "accepted": False,
                "reprompt": result.get("error", "invalid value"),
                "next": "slot",
                "slot": {"id": slot_id, "name": req.slot, "type": stage3_state_machine.SLOT_DEFINITIONS[slot_id - 1]["type"]},
            }

        # Slot accepted. Either more slots remain, or we move to classify.
        next_id = stage3_state_machine._next_slot_index(s.intake) + 1
        if next_id > len(stage3_state_machine.SLOT_DEFINITIONS):
            return {"accepted": True, "next": "classify"}
        next_def = stage3_state_machine.SLOT_DEFINITIONS[next_id - 1]
        return {
            "accepted": True,
            "next": "slot",
            "next_slot": {"id": next_id, "name": next_def["slot"], "type": next_def["type"]},
        }

    # ---- /api/intake/:ref/extras (CR-5-01) ----
    @app.post("/api/intake/{ref}/extras")
    def post_extras(ref: str, payload: ExtrasRequest, request: Request) -> Any:
        """Store engine-only fields (e.g. simultaneous_entry, sight_lines,
        chain_count) in the intake. NOT user-facing; reserved for
        operator scripts and tests. Validated lightly: keys must be
        alphanumeric/underscore, values must be JSON-serialisable scalars
        or short lists.
        """
        s = SESSIONS.by_reference(ref)
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        if not s.consent:
            raise HTTPException(status_code=403, detail="consent required")
        # Light validation
        for k, v in payload.fields.items():
            if not isinstance(k, str) or not k.replace("_", "").isalnum():
                raise HTTPException(status_code=400, detail=f"bad key: {k!r}")
        s.intake.update(payload.fields)
        SESSIONS.put(s)
        return {"stored": list(payload.fields.keys())}

    # ---- /api/classify (G-41, G-42, G-43) ----
    def _render_pdf_for_session(s: Any) -> bytes:
        """Render the customer-facing summary PDF for a session.

        Extracted from /api/pdf/:ref so the classify response can include
        the same bytes inline (base64-encoded) and bypass the Vercel
        serverless session-persistence problem. See the note on get_pdf
        below for the full history.
        """
        intake_record = {
            "session_id": s.session_id,
            "reference": s.reference,
            **s.intake,
        }
        if s.engine_result:
            intake_record["band"] = s.engine_result.band
            intake_record["scenario_id"] = s.engine_result.scenario_id
            intake_record["output_text"] = s.engine_result.text_web
        return stage3_pdf_gen.render_summary_pdf(
            reference=s.reference,
            intake=intake_record,
            engine_result=s.engine_result,
        )

    @app.post("/api/classify")
    def post_classify(req: ClassifyRequest) -> Any:
        frontend_mode = req.ref is not None
        ref = req.ref or req.reference
        s = SESSIONS.by_reference(ref) if ref else None
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")

        # If the session already escalated during slot collection (e.g.
        # serious injury), don't classify — surface the calm handoff. The
        # frontend has no separate escalation screen, so we return a
        # ClassifyResponse with NO fault band and the handoff as outputText.
        if frontend_mode and s.escalation:
            return {
                "band": None,
                "outputText": ESCALATION_MESSAGE.format(ref=s.reference),
                "disclaimerText": stage3_config.get_disclaimer("master"),
                "escalated": True,
                "pdf_base64": base64.b64encode(_render_pdf_for_session(s)).decode("ascii"),
            }

        # CR-5-04: out-of-enum band is fail-closed via the engine's
        # VALID_BANDS guard. No `inject_band` test special-case in the
        # API layer. The general fail-closed behaviour is exercised by
        # T-25-004 via /api/intake/:ref/extras (engine out-of-enum
        # bands are produced by an alternate scenario injection).
        er = stage3_state_machine.run_classification(s)
        SESSIONS.put(s)  # F-E: persist engine_result for later PDF/brief reads

        if er.escalation:
            if frontend_mode:
                return {
                    "band": None,
                    "outputText": ESCALATION_MESSAGE.format(ref=s.reference),
                    "disclaimerText": stage3_config.get_disclaimer("master"),
                    "escalated": True,
                    "pdf_base64": base64.b64encode(_render_pdf_for_session(s)).decode("ascii"),
                }
            return {
                "escalation": er.escalation,
                "next": "escalated",
                "terminal": True,
            }

        if er.band not in stage3_engine.VALID_BANDS:
            return Response(
                content=json.dumps({"error": "fail-closed: out-of-enum band", "band_rendered": False}),
                status_code=500, media_type="application/json",
            )

        # G-18 across HTTP: disclaimer already resolved
        try:
            resolved_output = stage3_config.resolve_strict(er.text_web or "")
        except stage3_config.UnresolvedTokenError:
            return Response(
                content=json.dumps({"error": "unresolved token in engine output"}),
                status_code=500, media_type="application/json",
            )
        disclaimer = stage3_config.get_disclaimer("master")

        return {
            "band": er.band,
            "scenario_id": er.scenario_id,
            "outputText": resolved_output,
            "disclaimerText": disclaimer,
            "pdf_base64": base64.b64encode(_render_pdf_for_session(s)).decode("ascii"),
        }

    # ---- /api/scenario-question (T6: scenario-question injection) ----
    @app.post("/api/scenario-question")
    def post_scenario_question(req: ScenarioQuestionRequest) -> Any:
        ref = req.ref or req.reference
        s = SESSIONS.by_reference(ref) if ref else None
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        if not s.consent:
            raise HTTPException(status_code=400, detail="consent required")

        # Branch on session state: at S4-CLASSIFY this call STARTS the phase; at
        # S3.5 it SUBMITS the current answer. (The frontend doesn't track ids.)
        if s.state == "S4-CLASSIFY":
            result = stage3_state_machine.start_scenario_questions(s)
            SESSIONS.put(s)
            q = result.get("question")
            return {
                "ref": s.reference,
                "next": _scenario_slot_question(q) if q else dict(_DONE_QUESTION),
                "answered": result.get("answered", 0),
                "total_questions": result.get("total_questions", 0),
                "ready_to_classify": result.get("ready_to_classify", q is None),
            }

        if s.state != "S3.5-INJECT-QUESTIONS":
            raise HTTPException(status_code=409,
                                detail=f"no scenario question pending (state {s.state})")
        # question_id is optional — when omitted the answer applies to the current question.
        result = stage3_state_machine.submit_scenario_question(s, req.question_id, req.value)
        SESSIONS.put(s)

        if result.get("end_state") == "SX-ESCALATE" or s.escalation:
            return {"ref": s.reference, "next": dict(_DONE_QUESTION),
                    "escalation": s.escalation, "escalated": True, "ready_to_classify": False}
        if result.get("reprompt"):
            return {"ref": s.reference, "reprompt": True, "error": result.get("error"),
                    "reprompt_count": result.get("reprompt_count"), "ready_to_classify": False}

        nxt = result.get("next_question")
        return {
            "ref": s.reference,
            "next": _scenario_slot_question(nxt) if nxt else dict(_DONE_QUESTION),
            "answered": result.get("answered", 0),
            "total_questions": result.get("total_questions", 0),
            "ready_to_classify": result.get("ready_to_classify", nxt is None),
        }

    # ---- /api/pdf/:ref (G-44) ----
    # NOTE 2026-06-19: this endpoint was the only P0 in the customer-flow UX
    # audit. On Vercel's serverless runtime, the in-memory SESSIONS dict is
    # not shared across lambda invocations, so the GET that downloads the
    # PDF almost always lands in a different instance from the one that
    # created the session. The endpoint therefore returns 404 'session not
    # found' for every real browser customer, even though server-to-server
    # curl tests pass.
    #
    # Two changes fix this without touching the session store:
    #   1. /api/classify now also returns the rendered PDF as `pdf_base64`,
    #      so the customer's browser already has the bytes and never needs
    #      to call this endpoint.
    #   2. /api/pdf/:ref is kept for back-compat (e.g. server-side tooling)
    #      but is no longer the customer-facing download path.
    # See handoff/UX-AUDIT-CUSTOMER-FLOW-2026-06-19-v2.md for the audit
    # trail and handoff/CTO-ACTION-CORS-FIX.md for the related CORS work.
    @app.get("/api/pdf/{ref}")
    def get_pdf(ref: str) -> Response:
        s = SESSIONS.by_reference(ref)
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        pdf_bytes = _render_pdf_for_session(s)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={s.reference}.pdf"},
        )

    # ---- /api/brief/:ref (G-45) ----
    @app.get("/api/brief/{ref}")
    def get_brief(ref: str, request: Request) -> Any:
        s = SESSIONS.by_reference(ref)
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")

        # ---- Authn/authz (G-45 + G-57) ----
        if _brief_auth_mode() == "jwt":
            # Real path: verify a Supabase access token (ES256/JWKS) and
            # require AAL2. Identity comes from the signed `email` claim;
            # role from the existing auth mapping. No PII in the URL.
            authz = request.headers.get("authorization", "")
            token = authz[7:].strip() if authz[:7].lower() == "bearer " else ""
            claims = _verify_supabase_jwt(token)
            if not claims:
                raise HTTPException(status_code=403, detail="invalid or missing bearer token")
            if claims.get("aal") != "aal2":
                raise HTTPException(status_code=403, detail="MFA (AAL2) required")
            email = claims.get("email")
            if not email:
                raise HTTPException(status_code=403, detail="token missing email claim")
            try:
                user = stage3_auth.authenticate(email)
            except stage3_auth.AuthError as exc:
                raise HTTPException(status_code=403, detail=str(exc))
        else:
            # Stub path (default): as_email + X-MFA-Verified header.
            email = request.query_params.get("as_email")
            if not email:
                raise HTTPException(status_code=403, detail="auth required (as_email stub)")
            try:
                user = stage3_auth.authenticate(email)
            except stage3_auth.AuthError as exc:
                raise HTTPException(status_code=403, detail=str(exc))
            if not _mfa_satisfied(request):
                raise HTTPException(
                    status_code=403, detail="MFA required (X-MFA-Verified: 1 header missing)",
                )
        if not stage3_auth.dashboard_visible_for(user):
            raise HTTPException(status_code=403, detail="brief access denied for role")
        if user.role not in ("legal_staff", "admin"):
            raise HTTPException(status_code=403, detail="brief is legal-staff/admin only")
        # (MFA is enforced per-mode above: AAL2 claim in jwt mode, X-MFA-Verified in stub mode.)

        brief = stage3_intake_brief.generate_intake_brief(s, s.engine_result)
        # G-34: audit the read
        AUDIT.append(
            session_id=s.session_id, user=user.email, action="brief_viewed",
            inputs={"reference": ref},
            rule_path=[], output={"fields_count": len(brief.to_dict())},
        )
        return brief.to_dict()

    # ============================================================
    # Feature 2 — Evidence upload bound to the case file
    # (POST/GET /api/intake/{ref}/evidence, GET /api/case/{ref})
    # ============================================================
    #
    # Compliance: every path below is consent-gated server-side (403 if the
    # session hasn't passed /api/consent — same gate as /api/slot). Every
    # upload, list-read, and signed-URL issuance writes to the immutable
    # audit_log. Files live in Supabase Storage (Sydney region), private
    # bucket; reads only via short-TTL signed URLs minted here. Object paths
    # are {reference}/{uuid}.{ext} — no PII in URLs.

    def _require_session_with_consent(ref: str, request: Request) -> Any:
        """Shared gate for evidence endpoints. Returns the live Session or raises."""
        s = SESSIONS.by_reference(ref)
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        # Consent check is SERVER-SIDE — the UI cannot bypass it. Same gate
        # as /api/slot returns 400 for, but the evidence contract uses 403
        # (forbidden) because the resource exists but the caller may not touch it.
        if not s.consent:
            raise HTTPException(status_code=403, detail="consent required")
        return s

    @app.post("/api/intake/{ref}/evidence")
    async def post_evidence(ref: str, request: Request,
                            file: UploadFile = File(...)) -> Any:
        """Upload ONE image file and bind it to the case reference.

        Multipart/form-data; field name `file`. Validates:
          * session exists AND consent granted (403 otherwise),
          * file content sniffs as an allowed image MIME,
          * size <= EVIDENCE_MAX_FILE_MB (default 10 MB),
          * per-case count <= EVIDENCE_MAX_FILES_PER_CASE (default 20).

        Audit: writes one entry per upload with the SHA-256 hash, filename,
        size, and content_type. Returns the new EvidenceRecord with a
        short-TTL signed URL for the customer to preview.
        """
        if EVIDENCE_STORE is None:
            raise HTTPException(status_code=503, detail="evidence storage not configured")
        s = _require_session_with_consent(ref, request)
        ip = _client_ip(request)
        content = await file.read()
        try:
            rec = EVIDENCE_STORE.upload(
                reference=ref, content=content,
                content_type=file.content_type or "application/octet-stream",
                filename=file.filename or "upload", actor=ip,
            )
        except Exception as exc:
            # Validation errors carry a customer-facing reason; everything
            # else gets a generic 400 so we never leak internals. We match by
            # class name (not isinstance) because the store module is loaded
            # dynamically and never registered on sys.modules.
            if type(exc).__name__ == "EvidenceValidationError":
                raise HTTPException(status_code=400, detail=str(exc))
            detail = (exc.args[0] if exc.args else "upload rejected")
            raise HTTPException(status_code=400, detail=detail)
        AUDIT.append(
            session_id=s.session_id, user=ip, action="evidence_uploaded",
            inputs={"reference": ref, "file_id": rec.file_id,
                    "filename": rec.filename, "content_type": rec.content_type,
                    "size_bytes": rec.size_bytes, "sha256": rec.sha256},
            rule_path=[], output={"s3_key": rec.s3_key, "s3_bucket": rec.s3_bucket},
        )
        _maybe_persist_evidence_row(rec)  # index row; S3 + audit are source of truth
        return rec.to_dict()

    @app.get("/api/intake/{ref}/evidence")
    def get_evidence(ref: str, request: Request) -> Any:
        """List evidence files bound to the case (consent-gated).

        Each item includes a freshly-minted signed URL (short TTL). The list
        itself is audited so a leak of the customer's reference is detectable
        from the trail even if no file is read.
        """
        if EVIDENCE_STORE is None:
            raise HTTPException(status_code=503, detail="evidence storage not configured")
        s = _require_session_with_consent(ref, request)
        ip = _client_ip(request)
        items = EVIDENCE_STORE.list(reference=ref)
        AUDIT.append(
            session_id=s.session_id, user=ip, action="evidence_listed",
            inputs={"reference": ref}, rule_path=[],
            output={"count": len(items), "file_ids": [i.file_id for i in items]},
        )
        return {"reference": ref, "count": len(items),
                "items": [i.to_dict() for i in items]}

    @app.get("/api/case/{ref}")
    def get_case(ref: str, request: Request) -> Any:
        """Return the bound case file: intake session + evidence list + pdf ref.

        Same consent gate as the evidence endpoints — the customer reaches
        this view from their `?ref=<ref>` link after granting consent. Staff
        views go through the dashboard (separate, role-gated). The PDF is
        referenced as a link (not embedded) so the customer can re-download
        without re-running /api/classify.
        """
        s = _require_session_with_consent(ref, request)
        items = []
        if EVIDENCE_STORE is not None:
            try:
                items = EVIDENCE_STORE.list(reference=ref)
            except Exception:
                items = []
        band = None
        if s.engine_result:
            band = s.engine_result.band
        # Light audit — same surface as brief_viewed but customer-readable.
        AUDIT.append(
            session_id=s.session_id, user=_client_ip(request),
            action="case_viewed",
            inputs={"reference": ref}, rule_path=[],
            output={"evidence_count": len(items), "band": band},
        )
        return {
            "reference": ref,
            "state": s.state,
            "band": band,
            "evidence": [i.to_dict() for i in items],
            "evidence_count": len(items),
            "pdf_url": f"/api/pdf/{ref}",
            "intake_completed": s.state in ("S5", "S6", "S7", "S8")
                                or bool(s.engine_result),
        }

    return app


# Convenience: the default app instance used by uvicorn / Vercel
app = create_app()


# ===== Stage 4 hardening: rate limit (CR-5-03), MFA (G-57), runtime
# tokens (CR-4-02), explicit extras route (CR-5-01) =====

class _TokenBucket:
    """Tiny in-process token bucket. Per-IP cap on /api/session.

    In Vercel's edge runtime this won't span instances — for the staging
    preview it caps a single container. Production with multiple
    containers should use Vercel Edge Config or Upstash Redis. This
    satisfies CR-5-03 *for the preview*; the deployer swaps in a
    distributed limiter for production.
    """

    def __init__(self, *, rate_per_minute: int = 10, burst: int = 5) -> None:
        self._rate = rate_per_minute
        self._burst = burst
        self._buckets: dict[str, tuple[float, float]] = {}
        # tokens, last_refill_ts

    def allow(self, key: str) -> bool:
        import time as _t
        now = _t.time()
        if key in self._buckets:
            tokens, last = self._buckets[key]
            elapsed_min = (now - last) / 60.0
            tokens = min(self._burst, tokens + elapsed_min * self._rate)
            if tokens < 1:
                self._buckets[key] = (tokens, now)
                return False
            tokens -= 1
            self._buckets[key] = (tokens, now)
            return True
        self._buckets[key] = (self._burst - 1, now)
        return True


RATE_LIMITER = _TokenBucket(
    rate_per_minute=int(os.environ.get("RATE_LIMIT_PER_MIN", "10")),
    burst=int(os.environ.get("RATE_LIMIT_BURST", "5")),
)


def _client_ip(request: Request) -> str:
    """Resolve the client IP, preferring X-Forwarded-For (Vercel sets it)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _mfa_satisfied(request: Request) -> bool:
    """G-57: MFA required for dashboard roles.

    Stub: reads `X-MFA-Verified: 1` header (the OIDC/SAML provider at
    Stage 4 will set this after a successful TOTP challenge). The
    stub makes the contract testable today; the deployer wires the
    real provider.
    """
    return request.headers.get("x-mfa-verified") == "1"


# ----- Real server-side AAL2 auth for /api/brief (CR-5-05 / D-3) -----
# Default mode = "stub" (the X-MFA-Verified header path above) so existing
# tests + the current frontend keep working unchanged. Set BRIEF_AUTH_MODE=jwt
# to require a verified Supabase access token with aal2. The frontend must then
# send `Authorization: Bearer <access_token>` (drop the as_email query param).
_JWKS_URL = (
    os.environ.get("SUPABASE_URL", "").rstrip("/") + "/auth/v1/.well-known/jwks.json"
    if os.environ.get("SUPABASE_URL") else ""
)
_jwks_client = None  # lazily constructed PyJWKClient (caches keys)


def _brief_auth_mode() -> str:
    """Auth mode for /api/brief.

    P0-3 fix (2026-07-14 review): in production, BRIEF_AUTH_MODE must be 'jwt'
    — the stub path (as_email + X-MFA-Verified) is spoofable and ships PII via
    query string. Hard-fail at request time if APP_ENV=production and the
    operator hasn't explicitly set BRIEF_AUTH_MODE=jwt.

    Allow stub override via BRIEF_ALLOW_STUB_IN_PRODUCTION=1 only for known
    emergency-rollback scenarios (sets a loud header on responses)."""
    mode = os.environ.get("BRIEF_AUTH_MODE", "stub").lower()
    app_env = _app_env()
    allow_stub = os.environ.get("BRIEF_ALLOW_STUB_IN_PRODUCTION") == "1"
    if app_env == "production" and mode != "jwt" and not allow_stub:
        # Fail loud — never silently serve briefs under spoofable auth in prod.
        raise HTTPException(
            status_code=500,
            detail=("BRIEF_AUTH_MODE must be 'jwt' in production (currently "
                    f"'{mode}'). Set BRIEF_AUTH_MODE=jwt or, for emergency "
                    "rollback only, BRIEF_ALLOW_STUB_IN_PRODUCTION=1.")
        )
    return mode


def _verify_supabase_jwt(token: str) -> Optional[dict]:
    """Verify a Supabase access token via the project JWKS (ES256).
    Returns the claims dict (incl. `email`, `aal`, `sub`) or None if invalid.
    No shared secret needed — the project uses asymmetric keys."""
    global _jwks_client
    if not token or not _JWKS_URL:
        return None
    try:
        import jwt  # PyJWT
        from jwt import PyJWKClient
        if _jwks_client is None:
            _jwks_client = PyJWKClient(_JWKS_URL)
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token, signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except Exception:
        return None
