"""FastAPI web app — server-rendered multi-step intake with chat wrapper.

G-23: PII never in URL params. The session_id is a non-PII opaque token in a
cookie. PII travels in POST bodies only.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.config import get_disclaimer, resolve_strict
from app.engine import EngineResult, classify
from app.pdf_gen import render_summary_pdf
from app.state_machine import (
    SLOT_DEFINITIONS, Session, abandon, acknowledge_consent, complete_intake,
    confirm_fault_info, new_session, run_classification, submit_slot,
)
from app.store import InMemoryStore

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="AI Legal Receptionist (Stage 2)")
store = InMemoryStore()

# Cookie name for the session token (non-PII).
SESSION_COOKIE = "gf_session"


def _get_or_create_session(request: Request, response: Response) -> Session:
    sid = request.cookies.get(SESSION_COOKIE)
    session = store.get(sid) if sid else None
    if session is None:
        session = store.create()
        # httpOnly so JS can't read; sameSite=lax for basic CSRF protection
        response.set_cookie(SESSION_COOKIE, session.session_id, httponly=True, samesite="lax")
    return session


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    response = templates.TemplateResponse("index.html", {"request": request})
    return _attach_session_cookie(request, response)


def _attach_session_cookie(request: Request, response: Response) -> Response:
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid or store.get(sid) is None:
        # Need to create and attach
        new = store.create()
        response.set_cookie(SESSION_COOKIE, new.session_id, httponly=True, samesite="lax")
    return response


# ----- S0a: Consent gate -----

@app.get("/consent", response_class=HTMLResponse)
async def consent_get(request: Request) -> Response:
    response = templates.TemplateResponse("consent.html", {
        "request": request,
        "privacy_notice": get_disclaimer("privacy_notice"),
    })
    return _attach_session_cookie(request, response)


@app.post("/consent")
async def consent_post(request: Request, privacy_acknowledged: str = Form(...)) -> Response:
    response = RedirectResponse("/triage", status_code=303)
    session = _get_or_create_session(request, response)
    if privacy_acknowledged != "yes":
        # T-2-029: declined -> S9, no PII
        acknowledge_consent(session, privacy_acknowledged=False)
        abandon(session)
        store.save(session)
        response = RedirectResponse("/abandoned", status_code=303)
        response.set_cookie(SESSION_COOKIE, session.session_id, httponly=True, samesite="lax")
        return response
    acknowledge_consent(session, privacy_acknowledged=True)
    store.save(session)
    return response


# ----- S1: Triage -----

@app.get("/triage", response_class=HTMLResponse)
async def triage_get(request: Request) -> Response:
    response = templates.TemplateResponse("triage.html", {"request": request})
    return _attach_session_cookie(request, response)


# ----- S3: Intake (multi-step form) -----

@app.get("/intake", response_class=HTMLResponse)
async def intake_get(request: Request, slot: int = 1) -> Response:
    response = templates.TemplateResponse("intake.html", {
        "request": request,
        "slot_index": slot,
        "slots": SLOT_DEFINITIONS,
        "current_slot": SLOT_DEFINITIONS[slot - 1] if 1 <= slot <= len(SLOT_DEFINITIONS) else None,
    })
    return _attach_session_cookie(request, response)


@app.post("/intake")
async def intake_post(
    request: Request,
    slot_id: int = Form(...),
    value: str = Form(...),
) -> Response:
    response = RedirectResponse("/intake", status_code=303)
    session = _get_or_create_session(request, response)
    if not session.consent:
        return RedirectResponse("/consent", status_code=303)
    result = submit_slot(session, slot_id, value)
    store.save(session)
    # Branch on result
    if result.get("end_state") == "SX-ESCALATE":
        return RedirectResponse(f"/escalated/{session.reference or 'pending'}", status_code=303)
    if result.get("reprompt"):
        return RedirectResponse(f"/intake?slot={slot_id}", status_code=303)
    if result.get("slot_accepted"):
        next_slot = result.get("next_slot_id")
        if next_slot is None:
            # All slots done -> classify
            return RedirectResponse("/classify", status_code=303)
        return RedirectResponse(f"/intake?slot={next_slot}", status_code=303)
    raise HTTPException(status_code=400, detail="unhandled intake result")


# ----- S4: Classify (call engine) -----

@app.get("/classify", response_class=HTMLResponse)
async def classify_get(request: Request) -> Response:
    response = templates.TemplateResponse("classify.html", {"request": request})
    return _attach_session_cookie(request, response)


@app.post("/classify")
async def classify_post(request: Request) -> Response:
    response = RedirectResponse("/fault-info", status_code=303)
    session = _get_or_create_session(request, response)
    if not session.consent or not session.pii_persisted:
        return RedirectResponse("/consent", status_code=303)
    if session.engine_result is None:
        engine_result = run_classification(session)
    else:
        engine_result = session.engine_result
    store.save(session)
    if engine_result.escalation:
        return RedirectResponse(f"/escalated/{session.reference}", status_code=303)
    return RedirectResponse("/fault-info", status_code=303)


# ----- S5: Fault-info -----

@app.get("/fault-info", response_class=HTMLResponse)
async def fault_info_get(request: Request) -> Response:
    sid = request.cookies.get(SESSION_COOKIE)
    session = store.get(sid) if sid else None
    if not session or session.engine_result is None:
        return RedirectResponse("/consent", status_code=303)

    er = session.engine_result
    text_web = er.text_web or ""
    try:
        text_resolved = resolve_strict(text_web)
    except Exception as exc:
        text_resolved = f"[render error: {exc}]"
    return templates.TemplateResponse("fault_info.html", {
        "request": request,
        "scenario_id": er.scenario_id,
        "band": er.band,
        "text_resolved": text_resolved,
        "master": get_disclaimer("master"),
    })


@app.post("/fault-info/accept")
async def fault_info_accept(request: Request) -> Response:
    response = RedirectResponse("/evidence", status_code=303)
    session = _get_or_create_session(request, response)
    if session and session.state == "S5-FAULT-INFO":
        confirm_fault_info(session)
        store.save(session)
    return response


# ----- S6: Evidence (lightweight placeholder) -----

@app.get("/evidence", response_class=HTMLResponse)
async def evidence_get(request: Request) -> Response:
    response = templates.TemplateResponse("evidence.html", {"request": request})
    return _attach_session_cookie(request, response)


@app.post("/evidence")
async def evidence_post(request: Request) -> Response:
    response = RedirectResponse("/next-steps", status_code=303)
    session = _get_or_create_session(request, response)
    return response


# ----- S7: Next steps + S8: Close -----

@app.get("/next-steps", response_class=HTMLResponse)
async def next_steps_get(request: Request) -> Response:
    response = templates.TemplateResponse("next_steps.html", {"request": request})
    return _attach_session_cookie(request, response)


@app.post("/close")
async def close_post(request: Request) -> Response:
    response = RedirectResponse("/closed", status_code=303)
    session = _get_or_create_session(request, response)
    if session:
        complete_intake(session)
        store.save(session)
    return response


@app.get("/closed", response_class=HTMLResponse)
async def closed_get(request: Request) -> Response:
    sid = request.cookies.get(SESSION_COOKIE)
    session = store.get(sid) if sid else None
    reference = session.reference if session else None
    response = templates.TemplateResponse("closed.html", {
        "request": request,
        "reference": reference,
    })
    return _attach_session_cookie(request, response)


# ----- SX: Escalated -----

@app.get("/escalated/{reference}", response_class=HTMLResponse)
async def escalated_get(reference: str, request: Request) -> Response:
    sid = request.cookies.get(SESSION_COOKIE)
    session = store.get(sid) if sid else None
    trigger = session.escalation if session else None
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
    variant = variant_map.get(trigger or "", "complexity")
    handoff_text = get_disclaimer(f"escalation_handoff.{variant}")
    response = templates.TemplateResponse("escalated.html", {
        "request": request,
        "trigger": trigger,
        "reference": reference,
        "handoff_text": handoff_text,
    })
    return _attach_session_cookie(request, response)


# ----- S9: Abandoned -----

@app.get("/abandoned", response_class=HTMLResponse)
async def abandoned_get(request: Request) -> Response:
    sid = request.cookies.get(SESSION_COOKIE)
    session = store.get(sid) if sid else None
    response = templates.TemplateResponse("abandoned.html", {
        "request": request,
        "reference": session.reference if session else None,
    })
    return _attach_session_cookie(request, response)


# ----- PDF download (G-24, pdf-summary.v1.md) -----

@app.get("/pdf/{reference}")
async def pdf_get(reference: str) -> Response:
    session = store.by_reference(reference)
    if not session or not session.engine_result:
        raise HTTPException(status_code=404, detail="Reference not found")
    pdf_bytes = render_summary_pdf(
        reference=reference,
        intake=session.intake,
        engine_result=session.engine_result,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="accident-summary-{reference}.pdf"'},
    )


# ----- JSON API for testing (used by the test runner) -----

@app.post("/api/classify")
async def api_classify(intake: dict[str, Any]) -> JSONResponse:
    """Direct classification endpoint. Used by tests and the test runner.
    Bypasses the state machine to expose the engine as a pure function.
    """
    try:
        result: EngineResult = classify(intake)
        return JSONResponse(result.to_dict())
    except Exception as exc:
        return JSONResponse({"error": type(exc).__name__, "message": str(exc)}, status_code=400)


@app.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse({"ok": True, "stage": 2})
