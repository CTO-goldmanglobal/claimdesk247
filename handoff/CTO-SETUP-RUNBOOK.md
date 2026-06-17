# Setup Runbook — Supabase + Vercel + GitHub (execute as cto@goldmanglobal.com.au)
**Why you're doing this, not Fables:** provisioning requires signing in as the CTO. Credential entry and account auth can't be delegated to the assistant — and the currently-connected connectors are personal accounts (`finn-tang` on Supabase, `nswcoachcharter-au` on Vercel), **not** Goldman. Everything below must be done signed into the Goldman accounts so the resources are Goldman-owned.

**Repo:** `https://github.com/CTO-goldmanglobal/claimdesk247-76a0b7de.git`

---

## 1. Supabase — new project (one-way doors first)
1. Sign in as **cto@goldmanglobal.com.au**. Create/confirm a **Goldman organisation** (not personal).
2. New project → **Region: Sydney (ap-southeast-2)**. ← permanent, cannot change later. Verify before clicking create.
3. Paid plan → enable **Point-in-Time Recovery / daily backups** (needed for retention + audit defensibility).
4. Save the project ref, `anon` key, and `service_role` key somewhere safe. The `service_role` key is **server-side only** — it must never reach the browser/Lovable client.
5. Schema + policies (apply the Stage 4 Supabase adapter migration when ready):
   - Tables: `intake_sessions`, `audit_log` (+ supporting).
   - **RLS ON** every table.
   - `audit_log`: policy blocks **UPDATE and DELETE** for all roles (append-only).
   - Roles: `customer` (no dashboard), `panel_shop_staff`, `legal_staff`, `admin`.
   - Retention: set to firm-confirmed period (placeholder until Stage 5).

## 2. GitHub — confirm access
- The repo is private under `CTO-goldmanglobal`. Ensure the Vercel + Supabase integrations are authorised against **this** org, and that Cursor (next chat) has read access.

## 3. Vercel — link repo + deploy
1. Sign in as **cto@goldmanglobal.com.au**; use a **Goldman Team** (not `nswcoachcharter-au`).
2. New Project → Import Git Repository → `claimdesk247-76a0b7de`.
3. **Function region: Sydney (`syd1`)** for anything touching personal data — not a US/EU default.
4. Environment variables (per environment — preview vs production):
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY` (client-safe)
   - `SUPABASE_SERVICE_ROLE_KEY` (server functions only — never exposed to client)
   - `ENGINE_BASE_URL` → the Stage 2.5 engine endpoint once deployed
   - `X_TEST_MODE` → enabled on **preview only**, off in production
5. Protect the **production** branch (require a reviewer). Preview deploys are the weblink test target.
6. Deploy. Confirm the preview URL loads and `/healthz` responds once the engine is wired.

## 4. Wire the engine (the missing link)
The live site currently runs a **placeholder engine** ("Preview mode" banner). To make it real:
- Deploy the Stage 2.5 API (`stage-2.5/app/wrap.py`) as the engine service.
- Point the UI's `ENGINE_BASE_URL` at it.
- Run the weblink tests: `BASE_URL=https://<preview-url> python3 stage-2.5/tests/run_acceptance.py` → expect parity (real bands, resolved disclaimers, no percentages).

## 5. CORS lockdown before go-live (CR-5-02 — blocker)
- In the engine config, restrict CORS to the **exact** project origin(s) + production domain. Drop the broad `*.lovable.app` — today it lets any Lovable tenant call the API.

## 6. Verify residency (capture evidence for firm sign-off)
- Screenshot Supabase region = Sydney and Vercel function region = `syd1`. These become items 7 of the legal sign-off package.

---
**Done = ** Goldman-owned Supabase (Sydney) + Vercel (`syd1`) linked to the GitHub repo, env vars set, engine wired, CORS locked, residency evidence captured. Then the live site stops being a stub.
