# Stage 4 — Traceability Matrix (Gates → Code / Test / Artefact)

This is the single source of truth for what was built, where, and what proves it. All G-50..G-62 are mapped to one of three columns:

- **Code** — the file/line in the repo.
- **Test** — the test ID (T-25-xxx, T-3-xxx, T-2-xxx) that exercises the gate.
- **Artefact** — the deliverable file the audit reads (PDF, MD, JSON).

---

## P0 gates

| Gate | Code | Test | Artefact |
|------|------|------|----------|
| **G-50** Staging URL live; full web intake E2E | `stage-2.5/app/wrap.py` (FastAPI app); deployed via Vercel | T-25-001..T-25-018 (full weblink runner) | `preflight.py:g50_staging_url_live` output |
| **G-51** Supabase adapter passes the full 99-test suite (Stage 2 30 + Stage 3 50 + Stage 2.5 19; pre-T4/T6/T8 was 87, pre-T6 was 79, pre-MFA was 75, pre-Stage-2.5 was 73) | `stage-4/app/supabase_store.py:SupabaseStore` | T-25-016 (regression runner) | `stage-2.5/deliverables/test-report.txt` (99/99 green) |
| **G-52** Data residency: Supabase=Sydney; Vercel PII=`syd1` | `architecture/INFRA-PROVISIONING-CHECKLIST.md` | (deployer-evidence — screenshot) | `sign-off-package/item-7-retention-storage.md` |
| **G-53** RLS enforced in DB: customer/anon cannot read intake or audit | `stage-4/app/supabase_store.py` (RLS-aware; uses supabase-py subject to RLS) | T-25-009 (customer → 403 server-side); `preflight.py:g53_rls_enforced` | `sign-off-package/item-8-audit-log.md` (SQL evidence) |
| **G-54** `audit_log` append-only at DB level | `stage-4/app/supabase_store.py` (SQL for `audit_log_no_update` / `audit_log_no_delete`) + `stage-3/app/audit.py:AuditLog` (language-level) | `preflight.py:g54_audit_append_only` | `sign-off-package/item-8-audit-log.md` |
| **G-55** CORS locked to exact origins (CR-5-02) | `stage-2.5/app/wrap.py:CORS_ALLOWLIST` (env-driven, no regex) | `preflight.py:g55_cors_locked`; T-25-014, T-25-015 (preview CORS check) | `preflight.py` output (allow + reject) |
| **G-56** Rate limiting active on /api/session (CR-5-03) | `stage-2.5/app/wrap.py:_TokenBucket` + `RATE_LIMITER.allow` on `create_session` | `preflight.py:g56_rate_limit` | `preflight.py` output (429 observed) |
| **G-57** MFA enforced on all dashboard roles | `stage-2.5/app/wrap.py:_mfa_satisfied` + check in `get_brief` | T-25-017 (no MFA → 403), T-25-018 (MFA → 200); `preflight.py:g57_mfa_enforced` | `preflight.py` output |
| **G-58** E2E QA on live staging (Part A, 13 journeys) | `stage-4/QA-PLAN-AND-GOLIVE-CHECKLIST.md:Part A` | (deployer-runs manually; tick boxes) | `sign-off-package/qa-evidence/*.png` + session refs |
| **G-61** Sign-off package complete: 8 items | `stage-4/sign-off-package/00-INDEX.md` (all 8 items mapped) + 8 item files | (firm reviews) | `sign-off-package/` |
| **G-62** Regression: 99/99 still green (weblink; pre-T4/T6/T8 was 87, pre-T6 was 79, pre-MFA was 75, pre-Stage-2.5 was 73) | (covered by G-51 runner) | T-25-016 (regression marker) | `stage-2.5/deliverables/test-report.txt` |

## P1 gates

| Gate | Code | Test | Artefact |
|------|------|------|----------|
| **G-59** x-test-mode confirmed inert in production | `stage-2.5/app/wrap.py:_is_test_mode_active` (env-gated) | T-25-012 (preview enabled, production gated) | `preflight.py:g59_test_mode_inert` |
| **G-60** All carry-in CRs (5-01, 5-04, 4-01, 4-02) landed | `preflight.py:g60_carry_in_crs` (source-grep audit) | (covered by 99/99 green as of 2026-06-21; was 79/79 pre-T4/T6/T8, 75/75 pre-MFA, 73/73 pre-Stage-2.5) | `preflight.py` output |

## Carry-in CRs (G-60 detail)

| CR | Code | Test | Artefact |
|----|------|------|----------|
| **CR-5-01** | `stage-2.5/app/wrap.py:ExtrasRequest` + `post_extras` (line 305-330) | T-25-004 (uses extras route for fail-closed) | `stage-2.5/app/wrap.py` |
| **CR-5-02** | `stage-2.5/app/wrap.py:CORS_ALLOWLIST` (line 102-108) + `CORSMiddleware(allow_origins=CORS_ALLOWLIST, allow_origin_regex=None)` | T-25-014, T-25-015, `preflight.py:g55` | `stage-2.5/app/wrap.py` |
| **CR-5-03** | `stage-2.5/app/wrap.py:_TokenBucket` + `RATE_LIMITER.allow` on `create_session` (line 411-419) | `preflight.py:g56` | `stage-2.5/app/wrap.py` |
| **CR-5-04** | `stage-2.5/app/wrap.py:post_classify` (no `inject_band` branch) | T-25-004 (engine's `VALID_BANDS` guard is the only fail-closed path) | `stage-2.5/app/wrap.py` |
| **CR-4-01** | `stage-3/app/voice.py:followup_signals` (line 380-403) | T-3-010 (voice followup test) | `stage-3/app/voice.py` |
| **CR-4-02** | `stage-2.5/app/wrap.py:_RUNTIME_TOKEN_OVERRIDES` (line 80-97) | T-25-003 (disclaimer tokens resolve) | `stage-2.5/app/wrap.py` |

## Sign-off package items (G-61 detail)

| Item | Code | Live evidence |
|------|------|---------------|
| 1. Disclaimers | `stage-3/app/data/disclaimers.v1.complete.json` | `sign-off-package/item-1-disclaimers.md` |
| 2. Rule tree | `stage-3/app/data/rule-tree.nsw.v3.json` + `stage-1/deliverables/rule-tree-review.md` | `sign-off-package/item-2-rule-tree.md` |
| 3. Escalation triggers | `stage-3/app/engine.py:ENGINE_TRIGGERS` | `sign-off-package/item-3-escalation-triggers.md` |
| 4. Privacy + consent | `stage-3/app/data/disclaimers.v1.complete.json` | `sign-off-package/item-4-privacy-consent.md` |
| 5. PDF template | `stage-3/app/pdf_gen.py` + `stage-2/spec/pdf-summary.v1.md` | `sign-off-package/item-5-pdf-template.md` |
| 6. Insurer correspondence | (PENDING — see CR-4-03) | `sign-off-package/item-6-PHASE-2-NOTE.md` |
| 7. Retention + storage | `architecture/INFRA-PROVISIONING-CHECKLIST.md` | `sign-off-package/item-7-retention-storage.md` |
| 8. Audit log | `stage-3/app/audit.py` + `stage-4/app/supabase_store.py` | `sign-off-package/item-8-audit-log.md` |

## CR-5 list (raised for Stage 5)

| CR | Where raised | Code-side action |
|----|---------------|------------------|
| **CR-4-03** | §7 of build request | Insurer-correspondence template scaffold (item 6) |
| **CR-5-05** | G-57 stub | Wire real OIDC/SAML provider for MFA |
| **CR-5-06** | G-56 production | Replace in-process token bucket with Vercel Edge Config / Upstash Redis |
| **CR-5-07** | §14 tokens | Wire production `{{FIRM_*}}` token values |

---

*Generated 2026-06-13 by Stage 4 build (Cursor + MiniMax M3).*
