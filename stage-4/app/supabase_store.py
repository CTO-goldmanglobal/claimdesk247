"""Supabase SessionStore adapter (Stage 4).

Implements the SessionStore Protocol from stage-3/app/store.py against
Supabase Postgres. RLS-aware: queries go through the Supabase REST client
which is itself subject to the row-level security policies defined at
DB-provision time (see INFRA-PROVISIONING-CHECKLIST.md).

The adapter is intentionally split:
    - SupabaseStore   — production path (uses the supabase-py client)
    - LocalSqliteStore — dev/CI path (implements the same Protocol)

The wrapper picks one at import time based on SUPABASE_URL presence.
Both implement the same Protocol, so the engine / web code does not
need to change (Stage 2 design proven).

Required DB schema (created in Supabase at deploy time — see
INFRA-PROVISIONING-CHECKLIST.md for the SQL):

    CREATE TABLE intake_sessions (
        session_id TEXT PRIMARY KEY,
        reference   TEXT UNIQUE,
        state       TEXT,
        intake      JSONB,
        escalation  TEXT,
        escalation_reason TEXT,
        engine_result JSONB,
        created_at  TIMESTAMPTZ DEFAULT now()
    );
    ALTER TABLE intake_sessions ENABLE ROW LEVEL SECURITY;

    CREATE TABLE audit_log (
        entry_id    BIGSERIAL PRIMARY KEY,
        ts          TIMESTAMPTZ DEFAULT now(),
        session_id  TEXT,
        actor       TEXT,
        action      TEXT,
        inputs      JSONB,
        rule_path   JSONB,
        output      JSONB
    );
    ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
    -- Append-only policy (CR-5-04 / G-54):
    CREATE POLICY audit_log_no_update ON audit_log FOR UPDATE USING (false);
    CREATE POLICY audit_log_no_delete ON audit_log FOR DELETE USING (false);

    CREATE ROLE panel_shop_staff NOLOGIN;
    CREATE ROLE legal_staff NOLOGIN;
    CREATE ROLE admin NOLOGIN;
    -- Policies per role (customer has none, G-53).

Service-role key (server-side only, never in client bundle — G-53) is
read from SUPABASE_SERVICE_ROLE_KEY env var. Anonymous reads/writes
should be blocked by RLS.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Re-use the stage-3 path-shim pattern so the wrapper can live in stage-4
# without colliding with stage-3's `app` package.
_THIS_DIR = Path(__file__).resolve().parent
_STAGE4_ROOT = _THIS_DIR.parent
_STAGE3_ROOT = _STAGE4_ROOT.parent / "stage-3"

if str(_STAGE3_ROOT) not in sys.path:
    sys.path.insert(0, str(_STAGE3_ROOT))

# Load stage-3's app modules under a virtual stage3_app package.
_STAGE3_APP = "stage3_app"
if _STAGE3_APP not in sys.modules:
    import types
    pkg = types.ModuleType(_STAGE3_APP)
    pkg.__path__ = [str(_STAGE3_ROOT / "app")]
    sys.modules[_STAGE3_APP] = pkg


def _load(name: str):
    spec2 = importlib.util.spec_from_file_location(
        f"stage3_app.{name}", _STAGE3_ROOT / "app" / f"{name}.py",
    )
    mod = importlib.util.module_from_spec(spec2)
    sys.modules[f"stage3_app.{name}"] = mod
    spec2.loader.exec_module(mod)
    return mod


stage3_state_machine = _load("state_machine")
stage3_config = _load("config")


# ----- Supabase adapter (production path) -----

class SupabaseStore:
    """SessionStore implementation backed by Supabase Postgres.

    All operations go through the supabase-py client, which is itself
    subject to the RLS policies defined in the DB. The client uses the
    service-role key for server-side writes (G-53: never shipped to the
    client); the anon key for client-side reads is not used here.
    """

    def __init__(self, *, supabase_url: str, service_role_key: str) -> None:
        # Lazy import so the adapter is usable only when the supabase
        # package is installed (it is, in requirements-dev.txt).
        from supabase import create_client
        self._client = create_client(supabase_url, service_role_key)
        self._table = "intake_sessions"
        self._audit_table = "audit_log"

    def create(self) -> Any:
        s = stage3_state_machine.new_session()
        s.reference = stage3_state_machine._new_reference()  # type: ignore[attr-defined]
        self.save(s)
        return s

    def get(self, session_id: str) -> Any | None:
        r = self._client.table(self._table).select("*").eq("session_id", session_id).limit(1).execute()
        if not r.data:
            return None
        return self._row_to_session(r.data[0])

    def by_reference(self, reference: str) -> Any | None:
        r = self._client.table(self._table).select("*").eq("reference", reference).limit(1).execute()
        if not r.data:
            return None
        return self._row_to_session(r.data[0])

    def save(self, session: Any) -> None:
        row = {
            "session_id": session.session_id,
            "reference": session.reference,
            "state": session.state,
            "intake": session.intake,
            "escalation": session.escalation,
            "escalation_reason": session.escalation_reason,
            "engine_result": (session.engine_result.to_dict() if getattr(session, "engine_result", None) else None),
            # F-E: full session state must round-trip — in-memory shared refs
            # hid these; a real store loses them unless persisted explicitly.
            "consent": getattr(session, "consent", False),
            "privacy_acknowledged": getattr(session, "privacy_acknowledged", False),
            "pii_persisted": getattr(session, "pii_persisted", False),
            "reprompts": getattr(session, "reprompts", {}) or {},
        }
        # Upsert; relies on RLS to block UPDATE/DELETE for non-service roles.
        self._client.table(self._table).upsert(row).execute()

    # ----- Audit log (append-only at the DB; the client just calls append) -----

    def append_audit(self, *, session_id: str, actor: str, action: str,
                     inputs: dict, rule_path: list, output: dict) -> int:
        """Append to audit_log. UPDATE/DELETE are blocked by RLS (G-54)."""
        r = self._client.table(self._audit_table).insert({
            "session_id": session_id, "actor": actor, "action": action,
            "inputs": inputs, "rule_path": rule_path, "output": output,
        }).execute()
        if r.data:
            return r.data[0].get("entry_id", 0)
        return 0

    def audit_export(self) -> list[dict]:
        r = self._client.table(self._audit_table).select("*").order("entry_id").execute()
        return r.data or []

    @staticmethod
    def _row_to_session(row: dict) -> Any:
        s = stage3_state_machine.Session(session_id=row["session_id"])
        s.reference = row.get("reference")
        s.state = row.get("state", "S0a")
        s.intake = row.get("intake") or {}
        s.escalation = row.get("escalation")
        s.escalation_reason = row.get("escalation_reason")
        s.consent = bool(row.get("consent"))
        s.privacy_acknowledged = bool(row.get("privacy_acknowledged"))
        s.pii_persisted = bool(row.get("pii_persisted"))
        s.reprompts = row.get("reprompts") or {}
        er_dict = row.get("engine_result")
        if er_dict:
            # Re-hydrate as an EngineResult if available
            try:
                from stage3_app import engine as _engine
                s.engine_result = _engine.EngineResult(
                    scenario_id=er_dict.get("scenario_id", ""),
                    band=er_dict.get("band"),
                    classification_attempted=er_dict.get("classification_attempted", True),
                    escalation=er_dict.get("escalation"),
                    escalation_reason=er_dict.get("escalation_reason"),
                    text_web=er_dict.get("text_web"),
                    text_voice=er_dict.get("text_voice"),
                )
            except Exception:
                s.engine_result = None
        return s


# ----- Dev / CI fallback (SQLite-backed) -----

class LocalSqliteStore:
    """Dev/CI SessionStore using a local SQLite file. Same Protocol.

    Use this when SUPABASE_URL is not set (e.g. local dev, the weblink
    runner). In production / staging, deploy SupabaseStore.
    """

    def __init__(self, db_path: str | os.PathLike | None = None) -> None:
        import sqlite3
        if db_path is None:
            db_path = os.environ.get("STAGE4_SQLITE_PATH", "/tmp/stage4-sessions.db")
        self._path = str(db_path)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS intake_sessions (
                session_id TEXT PRIMARY KEY,
                reference TEXT UNIQUE,
                state TEXT,
                intake TEXT,
                escalation TEXT,
                escalation_reason TEXT,
                engine_result TEXT,
                consent INTEGER DEFAULT 0,
                privacy_acknowledged INTEGER DEFAULT 0,
                pii_persisted INTEGER DEFAULT 0,
                reprompts TEXT DEFAULT '{}'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT, actor TEXT, action TEXT,
                inputs TEXT, rule_path TEXT, output TEXT
            )
        """)
        self._conn.commit()

    def create(self) -> Any:
        s = stage3_state_machine.new_session()
        s.reference = stage3_state_machine._new_reference()  # type: ignore[attr-defined]
        self.save(s)
        return s

    def get(self, session_id: str) -> Any | None:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM intake_sessions WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def by_reference(self, reference: str) -> Any | None:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM intake_sessions WHERE reference=?", (reference,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def save(self, session: Any) -> None:
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO intake_sessions
                (session_id, reference, state, intake, escalation, escalation_reason, engine_result,
                 consent, privacy_acknowledged, pii_persisted, reprompts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                reference=excluded.reference,
                state=excluded.state,
                intake=excluded.intake,
                escalation=excluded.escalation,
                escalation_reason=excluded.escalation_reason,
                engine_result=excluded.engine_result,
                consent=excluded.consent,
                privacy_acknowledged=excluded.privacy_acknowledged,
                pii_persisted=excluded.pii_persisted,
                reprompts=excluded.reprompts
        """, (
            session.session_id,
            session.reference,
            session.state,
            json.dumps(session.intake),
            session.escalation,
            session.escalation_reason,
            json.dumps(session.engine_result.to_dict() if getattr(session, "engine_result", None) else None),
            1 if getattr(session, "consent", False) else 0,
            1 if getattr(session, "privacy_acknowledged", False) else 0,
            1 if getattr(session, "pii_persisted", False) else 0,
            json.dumps(getattr(session, "reprompts", {}) or {}),
        ))
        self._conn.commit()

    def append_audit(self, *, session_id: str, actor: str, action: str,
                     inputs: dict, rule_path: list, output: dict) -> int:
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO audit_log (session_id, actor, action, inputs, rule_path, output)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, actor, action,
              json.dumps(inputs), json.dumps(rule_path), json.dumps(output)))
        self._conn.commit()
        return cur.lastrowid or 0

    def audit_export(self) -> list[dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM audit_log ORDER BY entry_id")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]

    def _row_to_session(self, row: tuple) -> Any:
        s = stage3_state_machine.Session(session_id=row[0])
        s.reference = row[1]
        s.state = row[2] or "S0a"
        s.intake = json.loads(row[3] or "{}")
        s.escalation = row[4]
        s.escalation_reason = row[5]
        s.consent = bool(row[7]) if len(row) > 7 else False
        s.privacy_acknowledged = bool(row[8]) if len(row) > 8 else False
        s.pii_persisted = bool(row[9]) if len(row) > 9 else False
        s.reprompts = json.loads(row[10]) if len(row) > 10 and row[10] else {}
        er_dict = json.loads(row[6] or "null")
        if er_dict:
            try:
                from stage3_app import engine as _engine
                s.engine_result = _engine.EngineResult(
                    scenario_id=er_dict.get("scenario_id", ""),
                    band=er_dict.get("band"),
                    classification_attempted=er_dict.get("classification_attempted", True),
                    escalation=er_dict.get("escalation"),
                    escalation_reason=er_dict.get("escalation_reason"),
                    text_web=er_dict.get("text_web"),
                    text_voice=er_dict.get("text_voice"),
                )
            except Exception:
                s.engine_result = None
        return s


def build_store() -> Any:
    """Pick the right store at import time.

    Production / staging: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
    Local dev / CI: neither is set; fall back to SQLite.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return SupabaseStore(supabase_url=url, service_role_key=key)
    return LocalSqliteStore()
