# Stage 4 Build Request — Staging Deploy · AU Region · QA · Sign-Off Package
**Project:** AI Legal Receptionist + Accident Intake System
**Loop:** Fables (Plan) → Cursor + MiniMax M3 (Build) → Fables (Audit)
**Stage:** 4 of 5 (Phase 1 MVP) · **Issued:** 2026-06-13 · Goldman Forge / Fables
**Consumes:** stage-2.5 API, stage-3 app, Lovable UX, architecture/ docs
**Governed by:** `LOOP-OPERATING-RULES.md` · go-live gates are P0

---

## 0. What this stage is
The build stops being a set of green test suites and becomes a **running staging environment** the legal firm can review. Stage 4 deploys everything to the real infrastructure (Supabase Sydney, Vercel `syd1`), hardens the go-live items, runs end-to-end QA against the live weblink, and assembles the legal-firm sign-off package. No new product features — deployment, hardening, QA, and packaging.

Two outputs: (1) a working staging URL; (2) the sign-off package (Loop Request §12).

---

## 1. Scope

### In scope
1. **AU-region deployment** — Vercel (`syd1` for PII functions) + Supabase (Sydney) wired to the real `SessionStore` adapter.
2. **Supabase adapter** — implement `SessionStore` Protocol against Supabase; RLS + append-only audit log live.
3. **Security hardening (go-live gates)** — MFA on admin/dashboard, CORS lockdown, rate limiting, the carry-in CRs.
4. **End-to-end QA** — full intake journeys on the live staging URL across web + voice + dashboard; escalation, consent, PDF, brief.
5. **Sign-off package** — the 8 items in Loop Request §12, assembled for a single consolidated firm review.

### Out of scope
- Production deployment + firm-requested revisions → Stage 5
- Phase 2 (vision, live dispatch/booking APIs, multi-state, RAG layer)

---

## 2. Carry-in CRs (must all land this stage)

| CR | Action | Priority |
|---|---|---|
| CR-5-02 | **CORS lockdown — GO-LIVE BLOCKER.** Replace broad `*.lovable.app` with the exact project slug + production domain. No other tenant origin may call the API. | P0 |
| CR-5-03 | Rate limiting on `/api/session` (per-IP cap, Vercel edge or middleware) | P0 |
| CR-5-04 | Remove hardcoded `inject_band` test special-case from `post_classify`; keep the general `VALID_BANDS` guard | P1 |
| CR-5-01 | Explicit `/api/intake/:ref/extras` route for engine-only fields | P1 |
| CR-4-02 | Wire `{{BUSINESS_HOURS}}` / `{{CALLBACK_SLA}}` to runtime config (real values resolve at Stage 5) | P1 |
| CR-4-01 | Free-text follow-up robustness on voice — test against real/transcribed STT samples in QA | P1 |

---

## 3. Implementation constraints

### 3.1 Data layer (Supabase Sydney)
- Implement the Supabase `SessionStore` adapter; the engine/web code must not change (Protocol swap only — proves the Stage 2 design).
- RLS ON every table; `audit_log` blocks UPDATE/DELETE for all roles (append-only); roles `customer / panel_shop_staff / legal_staff / admin`.
- PITR/daily backups enabled. Retention configured to firm value (token until Stage 5).
- Service-role key server-side only; never shipped to Lovable client.

### 3.2 Hosting (Vercel)
- PII-touching functions in `syd1`. No US/EU edge for anything touching personal data.
- Production branch protected; preview deploys remain the test target.
- `x-test-mode` inert in production (verify, don't assume).
- Secrets in env vars per environment.

### 3.3 Security
- MFA required for dashboard (panel_shop_staff / legal_staff / admin) — Loop Request §10.5.
- Role-based access enforced server-side via RLS (re-verify G-33 against the real DB, not the in-memory store).
- HTTPS everywhere; no PII in URLs (re-verify against live).

### 3.4 Audit & privacy (re-verify live)
- Every session logs timestamp, session ID, inputs, rule path, output — now persisted in Supabase, still immutable.
- Consent (privacy + voice recording) precedes any PII write — against the real store.
- Exportable audit log for legal-firm admin.

---

## 4. Acceptance gates (Fables audit) — P0 must pass

| ID | Gate | Pri |
|---|---|---|
| G-50 | Staging URL live; full web intake completes end-to-end against it | P0 |
| G-51 | Supabase adapter passes the **full 73-test suite** against the real store (parity with in-memory) | P0 |
| G-52 | Data residency verified: Supabase region = Sydney; PII functions = `syd1`; evidence captured | P0 |
| G-53 | RLS enforced in DB: customer/anon cannot read intake or audit; roles scoped; verified by query, not UI | P0 |
| G-54 | `audit_log` append-only at DB level: UPDATE/DELETE rejected by policy | P0 |
| G-55 | CORS locked to exact origins (CR-5-02); foreign lovable subdomain → blocked | P0 |
| G-56 | Rate limiting active on `/api/session` (CR-5-03) | P0 |
| G-57 | MFA enforced on all dashboard roles | P0 |
| G-58 | End-to-end QA pass: web + voice + tow/rental + dashboard + PDF + brief on live staging; escalation + consent paths | P0 |
| G-59 | `x-test-mode` confirmed inert in production config | P1 |
| G-60 | All carry-in CRs (5-01, 5-04, 4-01, 4-02) landed and evidenced | P1 |
| G-61 | Sign-off package complete: all 8 Loop Request §12 items assembled | P0 |
| G-62 | Regression: 99/99 still green against the deployed API (weblink runner; pre-T4/T6/T8 was 87, pre-T6 was 79, pre-MFA was 75, pre-Stage-2.5 was 73) | P0 |

---

## 5. Sign-off package (Loop Request §12) — assemble for single firm review
1. All disclaimer text (screen + voice) — from disclaimers v1
2. Fault rule tree + output framing — rule-tree v3 + rule-tree-review.md
3. Escalation trigger list — 7 triggers, with evidence they route to human
4. Privacy notice + consent wording
5. Customer PDF summary template — live sample
6. Insurer correspondence draft template — **decision needed (see §7)**
7. Data retention + storage policy — region evidence + retention setting
8. Audit log specification — schema + immutability evidence + export sample

Deliver as `stage-4/sign-off-package/` with an index mapping each item to its artefact + live evidence.

---

## 6. Delivery manifest (Operating Rules §3)
Gate self-check (G-50…G-62) · traceability · combined green report **against the deployed URL** · known gaps · CRs (`CR-5-xx` for Stage 5) · compliance quick-scan · **residency evidence** (region screenshots/config) · staging URL + test credentials per role.

---

## 7. Open decision for finn / firm (before or during this stage)
**Insurer correspondence draft (§8.3 / sign-off item 6)** — never formally scheduled. Options: (a) build the without-prejudice template now so item 6 is complete for sign-off; (b) mark it Phase 2 and have the firm sign off the other 7 items. Recommend (a) if the panel-shop partner needs it at launch, else (b). Flag to Fables so the sign-off package is honest either way.

Also pending from Loop Request §14 and now due for Stage 5 token resolution: firm name, phone number, business hours, callback SLA, retention period, approved tow/rental partners.

---

## 8. Budget note
Deployment stages fail on environment/config, not logic — the 73 tests already prove the logic. So the spend here is in *verification against reality*: region actually Sydney, RLS actually enforced in the DB, CORS actually locked, MFA actually required. Re-run the existing suite against the live store (G-51/G-62) rather than writing much new — cheapest path to a trustworthy staging environment. Revision budget: 1 audit + 1 revision (config fixes are usually fast).

---

*Prepared by Fables · finn@goldmanglobal.com.au · 2026-06-13*
