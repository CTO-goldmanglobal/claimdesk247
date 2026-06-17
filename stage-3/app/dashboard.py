"""FastAPI dashboard for panel-shop and legal-firm views (Stage 3).

Routes:
    GET  /dashboard              — list (panel-shop / legal-staff / admin)
    GET  /dashboard/session/{id} — session summary + brief
    GET  /dashboard/audit        — read-only audit log view (legal_staff, admin)
    GET  /dashboard/audit/export — JSON export (admin only)
    POST /dashboard/audit/edit   — rejected (G-34, append-only)

Auth is via `?as=email@…` query param in Stage 3 (test stub). Stage 4
swaps for a real OIDC/SAML middleware. Role enforcement is server-side.

The dashboard reads from an in-memory session registry (Stage 2 store).
The web intake (Stage 2) and voice dialog (Stage 3) both write into
this same store so the dashboard sees them. The session registry is
populated by the test runner (and by the live web app).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from app.audit import DEFAULT_AUDIT_LOG, AuditLog, AuditMutationError
from app.auth import AuthError, authenticate, dashboard_visible_for, require_role
from app.intake_brief import (
    ADVICE_PHRASES, FAULT_PERCENT_PATTERNS, IntakeBrief, brief_passes_compliance_scan,
    generate_intake_brief,
)
from app.store import InMemoryStore


# Session registry — a single in-memory store shared across web, voice, and the dashboard.
# Stage 4 swaps this for a persistent store. The Protocol interface doesn't change.
SESSIONS = InMemoryStore()
AUDIT = DEFAULT_AUDIT_LOG


def _user_from_query(as_email: str | None):
    if not as_email:
        return None
    return authenticate(as_email)


def _require_dashboard_access(user) -> None:
    if user is None or not dashboard_visible_for(user):
        # G-33: server-side enforcement, not just UI hiding.
        raise HTTPException(status_code=403, detail="dashboard access denied")


def _session_summary(s: Any) -> dict[str, Any]:
    """Build a list-row dict for a session."""
    intake = getattr(s, "intake", {}) or {}
    return {
        "session_id": s.session_id,
        "state": s.state,
        "reference": getattr(s, "reference", None),
        "created_at": getattr(s, "created_at", ""),
        "scenario": intake.get("accident_type", ""),
        "band": intake.get("_band") or (s.engine_result.band if getattr(s, "engine_result", None) else None),
        "escalation": s.escalation or "",
        "status": _status_tag(s),
        "customer_label": intake.get("first_name", "") or intake.get("name", "") or "—",
    }


def _status_tag(s: Any) -> str:
    if s.escalation:
        return "referred-legal"
    band = None
    if getattr(s, "engine_result", None):
        band = s.engine_result.band
    if band in ("likely", "possible"):
        return "referred-insurer"
    if band in ("unclear", "insufficient"):
        return "on-hold"
    return "open"


def create_dashboard_app(templates_dir: str | None = None) -> FastAPI:
    """Build the dashboard FastAPI app. `templates_dir` is optional; if
    None, returns a JSON-only app (used by the test runner)."""
    app = FastAPI(title="Stage 3 Dashboard", version="0.3.0")

    @app.get("/dashboard")
    def list_sessions(as_email: Optional[str] = Query(default=None)) -> Any:
        user = _user_from_query(as_email)
        _require_dashboard_access(user)
        sessions = SESSIONS.list()
        # Panel-shop and legal-staff see the same list per the build request
        # §3.3. Admin sees the same list plus the audit-log link.
        return {
            "user": {"email": user.email, "role": user.role, "display_name": user.display_name},
            "sessions": [_session_summary(s) for s in sessions],
            "view": user.role,
        }

    @app.get("/dashboard/session/{session_id}")
    def session_detail(session_id: str, as_email: Optional[str] = Query(default=None)) -> Any:
        user = _user_from_query(as_email)
        _require_dashboard_access(user)
        s = SESSIONS.get(session_id)
        if s is None:
            raise HTTPException(status_code=404, detail="session not found")
        intake = getattr(s, "intake", {}) or {}
        er = getattr(s, "engine_result", None)
        # Build the brief only if the user is legal_staff or admin
        brief = None
        if user.role in ("legal_staff", "admin"):
            brief = generate_intake_brief(s, er).to_dict() if er else None
        return {
            "user": {"email": user.email, "role": user.role, "display_name": user.display_name},
            "session": _session_summary(s),
            "intake": intake,
            "engine_result": er.to_dict() if er else None,
            "brief": brief,
            "brief_visible": user.role in ("legal_staff", "admin"),
        }

    @app.get("/dashboard/audit")
    def audit_view(as_email: Optional[str] = Query(default=None)) -> Any:
        user = _user_from_query(as_email)
        if user is None or user.role not in ("legal_staff", "admin"):
            raise HTTPException(status_code=403, detail="audit log view denied")
        return {
            "user": {"email": user.email, "role": user.role, "display_name": user.display_name},
            "entries": [e.to_dict() for e in AUDIT.all()],
            "can_export": user.role == "admin",
        }

    @app.get("/dashboard/audit/export")
    def audit_export(as_email: Optional[str] = Query(default=None)) -> Response:
        user = _user_from_query(as_email)
        if user is None or user.role != "admin":
            raise HTTPException(status_code=403, detail="audit log export is admin-only")
        body = json.dumps({
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "entries": AUDIT.export(),
        }, indent=2)
        return Response(content=body, media_type="application/json",
                        headers={"Content-Disposition": "attachment; filename=audit-log.json"})

    @app.post("/dashboard/audit/edit")
    def audit_edit_attempt(as_email: Optional[str] = Query(default=None)) -> Any:
        """G-34: any attempt to mutate the audit log is rejected."""
        # Even admins are blocked.
        try:
            AUDIT.clear()  # raises AuditMutationError
        except AuditMutationError as exc:
            return JSONResponse(status_code=403,
                                content={"mutation": "rejected", "log_append_only": True,
                                         "reason": str(exc)})
        # If it didn't raise, something is wrong
        return JSONResponse(status_code=500, content={"error": "log not append-only"})

    return app


# ---- convenience for tests ----

def populate_session(session: Any) -> None:
    """Add a session to the in-memory store. Used by the test runner
    and by the web intake."""
    SESSIONS.put(session)
