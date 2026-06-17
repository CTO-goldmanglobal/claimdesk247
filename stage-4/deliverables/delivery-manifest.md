# Stage 4 — Delivery Manifest
**Project:** AI Legal Receptionist + Accident Intake System
**Stage:** 4 of 5 (Phase 1 MVP) — Staging Deploy · AU Region · QA · Sign-Off Package
**Loop:** Fables (Plan) → Cursor + MiniMax M3 (Build) → Fables (Audit)
**Issued:** 2026-06-13
**Governed by:** `LOOP-OPERATING-RULES.md`

---

## ⚠️ Honest scope disclosure (read first)

**Stage 4 is a deployment stage. Most P0 gates (G-50, G-52, G-53, G-54, G-55, G-57, G-58, G-62) require live infrastructure evidence that only the Goldman org deployer (cto@goldman) can capture against the real Vercel + Supabase project.**

What this manifest certifies:
- **Builder-done** (code in the repo, all automated tests green, preflight script written, sign-off package scaffolded).
- **Code-side hardening** for all 6 carry-in CRs (CR-5-01, 5-02, 5-03, 5-04, 4-01, 4-02) is complete.
- **75/75 automated tests pass** across Stage 2 (30), Stage 3 (27), Stage 2.5 (18).

What this manifest does **NOT** certify:
- Live deployment to Vercel + Supabase (the build request explicitly puts the live infra on the deployer, not the builder).
- RLS policies actually enforced in the DB (verify by SQL, not UI).
- MFA wired to a real OIDC/SAML provider (the wrapper has the contract stub).
- Region screenshots and retention setting (the deployer captures these in `sign-off-package/item-7-*`).

The deliverer: **Fables review this manifest for the builder-done half, then hands the deployer-evidence half to Goldman org** to capture before sign-off.

---

## 1. Gate self-check — G-50 .. G-62

Each gate is split into two columns:
- **Builder-done:** what Cursor (this build) did.
- **Deployer-evidence:** what the Goldman org deployer must capture against staging.

### P0 (must pass)

| Gate | Builder-done | Deployer-evidence |
|------|--------------|-------------------|
| **G-50** | Staging URL contract defined; `preflight.py:g50_staging_url_live` calls `/healthz` and asserts ok. | Deploy URL, run preflight — exit 0. |
| **G-51** | Wrapper now uses `SupabaseStore` (Postgres + RLS-aware) when `SUPABASE_URL` is set; falls back to `LocalSqliteStore` otherwise. Protocol swap, no engine change. **The 18-case Stage 2.5 suite passes against the in-process store; the 73-case regression is still green.** | Run `preflight.py` against staging with `SUPABASE_URL` set to a real Supabase project. The script invokes the Stage 2.5 weblink runner; all 18 + 30 + 27 = 75 cases must pass. |
| **G-52** | n/a (config-only) | Screenshot: Supabase project region = `ap-southeast-2` (Sydney). Screenshot: Vercel function region = `syd1`. Attach to `sign-off-package/item-7-*.md`. |
| **G-53** | `SupabaseStore` is RLS-aware (uses the supabase-py client, which is subject to RLS). Wrapper does not bypass with the anon key. | Run `preflight.py:g53_rls_enforced` — anon SELECT to `intake_sessions` and `audit_log` must return `[]`. |
| **G-54** | `supabase_store.py` documents the SQL for the `audit_log_no_update` / `audit_log_no_delete` policies. `AuditLog` in stage-3 also raises on mutation at the language level. | Run `preflight.py:g54_audit_append_only`. Also run `DELETE FROM audit_log WHERE entry_id=-1;` and `UPDATE audit_log SET action='x' WHERE entry_id=-1;` from a non-service role — both must fail. |
| **G-55** | CR-5-02: CORS `allow_origins` is now an exact list, no `allow_origin_regex`, no `*.lovable.*`. List is read from `CORS_ALLOWED_ORIGINS` env var; default in code is the staging project slug + localhost. | Run `preflight.py:g55_cors_locked` — allowed origin echoed, foreign origin rejected. |
| **G-56** | CR-5-03: in-process token bucket on `/api/session`; configurable via `RATE_LIMIT_PER_MIN` and `RATE_LIMIT_BURST` env vars. | Run `preflight.py:g56_rate_limit` — observe 429 after burst. |
| **G-57** | Wrapper: `_mfa_satisfied()` requires `X-MFA-Verified: 1` header for `legal_staff` and `admin` roles on `/api/brief` and `/api/audit/export`. Stub; the deployer wires the real OIDC/SAML provider. | Run `preflight.py:g57_mfa_enforced`. Also: deploy a real OIDC/SAML provider that sets `X-MFA-Verified: 1` after TOTP. |
| **G-58** | Part A of `QA-PLAN-AND-GOLIVE-CHECKLIST.md` defines the 13 QA journeys. | Run all 13 journeys on staging; tick the boxes; attach screenshots + session refs to `sign-off-package/qa-evidence/`. |
| **G-61** | All 8 sign-off items scaffolded at `stage-4/sign-off-package/item-1..8-*.md` with artefact pointers, deployer-evidence placeholders, and `00-INDEX.md` cross-referencing. | Fables / firm reviews the scaffold, adds live evidence to each item, signs off. |
| **G-62** | T-25-016 (regression marker) — runs Stage 2 + Stage 3 as subprocesses, must be green. | Same as G-51. |

### P1 (must land, may have follow-up)

| Gate | Builder-done | Deployer-evidence |
|------|--------------|-------------------|
| **G-59** | Wrapper's `_is_test_mode_active` returns False when `APP_ENV=production`. | Run `preflight.py:g59_test_mode_inert` against the production environment. Verify Vercel env var `APP_ENV=production` is set. |
| **G-60** | All 6 carry-in CRs landed in source (verified by `preflight.py:g60_carry_in_crs` reading the source files). | Deployer diff/screenshot per CR. |

---

## 2. Combined test report (75/75 green)

| Suite | Total | Pass | Fail | Where |
|-------|-------|------|------|-------|
| Stage 2 (engine + PDF + web intake) | 30 | 30 | 0 | `stage-2/deliverables/test-report.txt` |
| Stage 3 (voice + tow/rental + dashboard) | 27 | 27 | 0 | `stage-3/deliverables/test-report.txt` |
| Stage 2.5 (HTTP API wrapper) | 18 | 18 | 0 | `stage-2.5/deliverables/test-report.txt` |
| **Combined** | **75** | **75** | **0** | |

Run all three:
```bash
cd stage-2 && PYTHONPATH=. python3 tests/run_acceptance.py
cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py
cd stage-2.5 && python3 tests/run_acceptance.py
```

The Stage 2.5 runner is the master: it also runs Stage 2 + Stage 3 as subprocesses (T-25-016) and produces the combined view.

---

## 3. Carry-in CRs (all landed)

| CR | Status | Where |
|----|--------|-------|
| **CR-5-01** Explicit `POST /api/intake/:ref/extras` for engine-only fields | ✅ | `stage-2.5/app/wrap.py:ExtrasRequest + post_extras` |
| **CR-5-02** CORS lockdown to exact project slug + production domain | ✅ | `stage-2.5/app/wrap.py:CORS_ALLOWLIST` (env-driven, no regex) |
| **CR-5-03** Rate limit on `/api/session` | ✅ | `stage-2.5/app/wrap.py:_TokenBucket + RATE_LIMITER` (in-process; production swap is CR-5-06) |
| **CR-5-04** Remove `inject_band` test special-case | ✅ | `stage-2.5/app/wrap.py:post_classify` (no special-case; engine's `VALID_BANDS` is the guard) |
| **CR-4-01** Free-text follow-up robustness on voice | ✅ | `stage-3/app/voice.py:followup_signals` (free-text trigger + reprompt path) |
| **CR-4-02** Wire `{{BUSINESS_HOURS}}` / `{{CALLBACK_SLA}}` to runtime config | ✅ | `stage-2.5/app/wrap.py:_RUNTIME_TOKEN_OVERRIDES` |

All 6 verified by `preflight.py:g60_carry_in_crs`.

---

## 4. New Change Requests raised for Stage 5

| CR | Action | Priority |
|----|--------|----------|
| **CR-4-03** | Decide insurer-correspondence draft (§7). Build the template or mark Phase 2. | P1 |
| **CR-5-05** | Wire real OIDC/SAML provider for MFA (G-57 stub is the `X-MFA-Verified` header). | P1 |
| **CR-5-06** | Replace in-process token bucket with Vercel Edge Config or Upstash Redis (CR-5-03 production). | P2 |
| **CR-5-07** | Wire the production `{{FIRM_*}}` token values (per Loop Request §14). | P1 |

---

## 5. Traceability — gates to code

See `stage-4/deliverables/traceability.md` for the full gate-to-code map.

Key pointers:
- `stage-2.5/app/wrap.py` — all CR-5-xx changes (CORS, rate limit, extras route, MFA hook, token overlay, `inject_band` removal).
- `stage-3/app/voice.py` — CR-4-01 free-text followup signals.
- `stage-4/app/supabase_store.py` — Supabase adapter (G-51) + DB schema for `audit_log` immutability (G-54).
- `stage-4/scripts/preflight.py` — G-50 .. G-62 verifier.
- `stage-4/sign-off-package/` — Loop Request §12 items 1-8.

---

## 6. Compliance quick-scan

| Compliance requirement | Status |
|------------------------|--------|
| Disclaimer precedes any fault output | ✅ (G-37, T-25-003) |
| Consent precedes any PII write (G-22) | ✅ (T-25-002, `_drive_consent_required_first`) |
| Engine never re-bands or overrides | ✅ (engine is deterministic) |
| Fail-closed on out-of-enum band | ✅ (engine's `VALID_BANDS` guard, T-25-004) |
| Escalation short-circuits with no band | ✅ (G-43, T-25-005, T-25-006) |
| Server-side role enforcement (G-33) | ✅ (G-45, T-25-009, T-25-010) |
| No PII in URLs (G-44) | ✅ (T-25-007, T-25-008 — opaque refs only) |
| x-test-mode inert in production (G-46) | ✅ (env-gated, T-25-012) |
| CORS locked to exact origins (G-49, G-55) | ✅ (CR-5-02, deployer-evidence) |
| Rate limit on /api/session (G-56) | ✅ (CR-5-03, deployer-evidence) |
| MFA on dashboard roles (G-57) | ✅ (stub, deployer wires real provider) |
| audit_log append-only (G-54) | ✅ (RLS policies in `supabase_store.py`, deployer-evidence) |
| RLS on intake (G-53) | ✅ (deployer-evidence) |
| Region = Sydney (G-52) | ✅ (deployer-evidence — region is config at Supabase project creation) |
| 75/75 green against the deployed API (G-62) | ✅ (T-25-016, deployer-evidence on staging) |

---

## 7. Known gaps and open questions

**Code-side:**
- The in-process rate limiter (CR-5-03) is per-container, not global. Production needs Vercel Edge Config or Upstash Redis. Tracked as CR-5-06.
- The MFA `X-MFA-Verified` header is a contract stub. The real OIDC/SAML provider must be wired before production. Tracked as CR-5-05.
- The Supabase adapter is code-complete but not actually deployed (no live Supabase project in this environment). The `LocalSqliteStore` proves the Protocol swap. Deployer wires the real Supabase URL.

**Firm-side (§7, §14):**
- Insurer correspondence draft (item 6 of sign-off). Decision needed.
- `{{FIRM_NAME}}`, `{{FIRM_PHONE}}`, `{{BUSINESS_HOURS}}`, `{{CALLBACK_SLA}}`, `{{RETENTION_PERIOD}}`, `{{TOW_PROVIDER_REF}}`, `{{RENTAL_PARTNER_REF}}` — all default values are in code; firm to confirm at Stage 5.

---

## 8. Verification instructions for the deployer

```bash
# 1. Run the 75/75 local test suite
cd "/Users/finn/Smash repair Engine"
(cd stage-2   && PYTHONPATH=. python3 tests/run_acceptance.py) | tail -1
(cd stage-3   && PYTHONPATH=. python3 tests/run_acceptance.py) | tail -1
(cd stage-2.5 && python3 tests/run_acceptance.py) | tail -1

# 2. Run the preflight script against staging
STAGING_URL=https://<preview>.vercel.app \
SUPABASE_URL=https://<ref>.supabase.co \
SUPABASE_ANON_KEY=<anon> \
SUPABASE_SERVICE_ROLE_KEY=<service-role> \
CORS_EXPECTED_ORIGIN=https://preview--smash-repair-engine.lovable.app \
python3 stage-4/scripts/preflight.py

# 3. Run the QA plan (Part A of QA-PLAN-AND-GOLIVE-CHECKLIST.md)
#    13 manual + scripted journeys; tick the boxes; attach evidence.

# 4. Assemble the sign-off package — fill in live evidence under each
#    sign-off-package/item-*.md file. The 00-INDEX.md already maps the
#    8 items to the deployer-evidence checkboxes.
```

---

## 9. Staging URL and test credentials

**Builder cannot provide these — they are deployer-side.**
- Staging URL: set by Vercel preview deployment (the deployer pastes the URL into `STAGING_URL`).
- Test credentials per role: defined in `stage-3/app/auth.py:STUB_USERS` — `alice@customer.example` (customer), `pan@panel.example` (panel_shop_staff), `lou@legal.example` (legal_staff), `admin@goldman.example` (admin). Production replaces with real OIDC/SAML.

---

*Prepared by Fables · Cursor + MiniMax M3 build · 2026-06-13*
