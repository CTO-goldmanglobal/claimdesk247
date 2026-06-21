# Engine Deploy Runbook — ClaimDesk 247 (Stage 4 close-out)
**Goal:** stand up the Stage 2.5 engine as a live AU endpoint, wire the frontend to it, and close the Stage 4 gates that depend on it.
**Australia-only.** Everything runs in `syd1` (Vercel) + Sydney (Supabase). No US/EU.
**Handoff target:** Sunday 2026-06-14 23:55. **Prepared by:** Cowork (Fables seat), 2026-06-13.

---

## What's already DONE (this session)
- **Supabase (Sydney)** schema reconciled to the engine (`stage-4/db/0002_engine_schema_reconcile.sql` applied live): `intake_sessions` + append-only `audit_log` in the exact shape `supabase_store.py` reads/writes, with staff-read RLS (G-53) and append-only audit (G-54). **F-B closed.**
- **Engine code wired (F-A):** `stage-2.5/app/wrap.py` now calls `_build_sessions()` → uses `SupabaseStore` when `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are set, else in-memory; audit mirrored to the store's append-only table. ⚠️ **Untested from the planning seat** — the 75-test suite + preflight (below) is the gate that verifies it.
- **Vercel frontend** live on `claimdesk247.com.au`, functions pinned to `syd1` only (G-52).
- **Deploy artifacts** prepared in `engine-deploy/`: `requirements.txt`, `vercel.json` (syd1), `api/index.py` entrypoint.

## The ONE thing only the CTO can do
**Set `SUPABASE_SERVICE_ROLE_KEY`** on the engine (server-side env var). Cowork cannot enter secret keys. Get it from Supabase → Settings → API Keys → `service_role`. It must NEVER reach the browser/client bundle (G-53).

---

## Deploy steps (CTO / Cursor — needs a Python env to test)

### 1. Assemble the engine deploy repo
Create a new private repo (e.g. `CTO-goldmanglobal/claimdesk247-engine`) — **separate from the frontend** (the frontend is a Nitro/Build-Output project; mixing Python functions in it doesn't work cleanly). Its root must contain:
```
api/index.py            # from engine-deploy/api/index.py
requirements.txt        # from engine-deploy/requirements.txt
vercel.json             # from engine-deploy/vercel.json  (regions: ["syd1"])
stage-2.5/              # copy from this workspace
stage-3/                # copy (engine logic, data/, templates/)
stage-4/                # copy (app/supabase_store.py)
```
(Keep `stage-N/` as siblings — `wrap.py` and the adapter bootstrap stage-3 by relative path.)

### 2. Local verification gate (DO THIS BEFORE DEPLOY — catches the untested F-A wiring)
```bash
pip install -r requirements.txt -r stage-2.5/requirements-dev.txt
(cd stage-2   && PYTHONPATH=. python3 tests/run_acceptance.py)   # 30
(cd stage-3   && PYTHONPATH=. python3 tests/run_acceptance.py)   # 31 (was 27 pre-T1; gained T-1-01..04)
(cd stage-2.5 && python3 tests/run_acceptance.py)                # 19 + regression  → 99/99
uvicorn api.index:app --port 8000          # smoke: GET /healthz returns versions
```
If the F-A wiring has an interface bug, it surfaces here — fix before deploying.

### 3. Create the Vercel project (Goldman team, syd1)
- Import the engine repo into the `cto-goldmanglobals-projects` Vercel team.
- Confirm `vercel.json` pins `regions: ["syd1"]` (Australia).
- **Env vars (Production + Preview):**
  | Var | Value | Notes |
  |---|---|---|
  | `SUPABASE_URL` | `https://mvzzglmegkchlmjartbm.supabase.co` | |
  | `SUPABASE_SERVICE_ROLE_KEY` | *(CTO pastes secret)* | server-side only |
  | `APP_ENV` | `production` | makes `x-test-mode` inert (G-59) |
  | `CORS_ALLOWED_ORIGINS` | `https://claimdesk247.com.au,https://www.claimdesk247.com.au` | exact origins, no `*.lovable.app` (G-55 / CR-5-02) |
  | `RATE_LIMIT_PER_MIN` / `RATE_LIMIT_BURST` | e.g. `10` / `5` | G-56 (in-process; CR-5-06 = Upstash for multi-instance) |
  | `FIRM_NAME`, `FIRM_PHONE`, `BUSINESS_HOURS`, `CALLBACK_SLA`, `RETENTION_PERIOD`, `TOW_PROVIDER_REF`, `RENTAL_PARTNER_REF` | *(Stage 5 firm values)* | optional now; defaults in code |
- Deploy. Note the engine URL, e.g. `https://claimdesk247-engine.vercel.app`.

### 4. Wire the frontend to the engine
On the **frontend** Vercel project (`claimdesk247-76a0b7de`): set `VITE_API_BASE_URL` = the engine URL, and redeploy (via CTO account, as established). This flips the UI out of preview-stub mode onto the real engine.

### 5. Close the gates — run the preflight + suite against staging
```bash
STAGING_URL=https://claimdesk247-engine.vercel.app \
SUPABASE_URL=https://mvzzglmegkchlmjartbm.supabase.co \
SUPABASE_ANON_KEY=sb_publishable_dPhH3_08e-3tuwp1EqZOxQ_LvhuqqQj \
SUPABASE_SERVICE_ROLE_KEY=<service-role> \
CORS_EXPECTED_ORIGIN=https://claimdesk247.com.au \
python3 stage-4/scripts/preflight.py
BASE_URL=https://claimdesk247-engine.vercel.app python3 stage-2.5/tests/run_acceptance.py
```
This closes: **G-50** (staging live), **G-51** (adapter vs real store), **G-55** (CORS), **G-56** (rate limit), **G-59** (test-mode inert), **G-60** (CRs), **G-62** (99/99 regression as of 2026-06-21; was 87/87 pre-T4/T6/T8, 79/79 pre-T6, 75/75 pre-MFA, 73/73 pre-Stage-2.5). Then run QA-PLAN Part A (13 journeys) for **G-58**.

---

## Still needs a decision/build after deploy
- **G-57 MFA** — `wrap.py` enforces an `X-MFA-Verified: 1` header stub; a real OIDC/SAML TOTP provider must set it (CR-5-05). Frontend MFA enrolment per `VERCEL-DEPLOY-FIX.md` spec.
- **Sign-off item 6** (insurer correspondence) — build template or confirm Phase 2 (CR-4-03).
- **Stage 5 tokens** (Loop Request §14): firm name, phone, hours, callback SLA, retention period, tow/rental partner refs.
- **Rotate the GitHub PAT** shared earlier in chat.

## Residency confirmation (for the firm sign-off)
Supabase = `ap-southeast-2` (Sydney) ✅ · Vercel frontend functions = `syd1` ✅ · engine `vercel.json` pins `syd1` ✅ · CORS locked to the AU production domain. No PII leaves Australia.
