# Fables Audit — Stage 2.5 (Engine-as-Endpoint)
**Date:** 2026-06-13 · **Auditor:** Fables · **Delivery:** stage-2.5/app/wrap.py + tests + requirements-dev.txt

## Decision: **LOOP CLOSED (PASS)** — 3 forward CRs ruled; 1 security item elevated for Stage 4

73/73 reproduced independently. Parity (the reason this stage exists) holds. One CORS finding I'm elevating above the builder's own framing — read CR-5-02 below.

## Independent verification (Fables re-ran)

| Check | Result | Evidence |
|---|---|---|
| Stage 2.5 suite | **16/16 PASS** | re-ran with pinned deps |
| Determinism | PASS | 2 runs identical |
| Regression G-48 | PASS | Stage 2 **30/30** + Stage 3 **27/27** re-run separately |
| G-41 parity | PASS | `/api/classify` → `run_classification` → real engine; **no rival classifier in wrap.py** |
| G-42 fail-closed + disclaimer | PASS | general `er.band not in VALID_BANDS` guard → 500; `resolve_strict` → `UnresolvedTokenError` → 500; no unresolved `{{...}}` to client |
| G-43 escalation short-circuit | PASS | escalation returns `{escalation, next: escalated, terminal}` with no `band` field |
| G-44 no PII in URL | PASS | `/api/pdf/{ref}`, `/api/brief/{ref}` keyed by opaque `GF-` reference; PII in POST bodies |
| G-45 brief role-gated | PASS | server-side 403 without auth |
| G-46/G-47 | PASS | test-mode env-gated; healthz returns versions |
| G-49 CORS no wildcard | PASS (preview) | `allow_origin_regex` anchored, no literal `*` — but see F-4 |
| CR-4-04 deps pinned | **CLOSED** | `requirements-dev.txt` present; my clean run used it, no missing-dep errors (fixes the Stage 3 F-3 issue) |

**Spot-check:** read the classify handler end-to-end — delegates to engine, double fail-closed, escalation pre-empts band, disclaimer resolved server-side. Clean.

## Finding F-4 (minor) — test scaffolding in the production path
`post_classify` has a hardcoded `if s.intake.get("inject_band") == "n/a_esc_routed"` early-return. The **general** `VALID_BANDS` guard below it already covers this case, so the hardcoded check is redundant test-scaffolding living in the production route. Not a risk (it only triggers on an injected test value), but it should come out. **Stage 4: remove the special-case; keep the general guard.** Logged as `CR-5-04`.

## Forward CRs — Fables rulings

| CR | Request | Ruling |
|---|---|---|
| CR-5-01 | Explicit `/api/intake/:ref/extras` route for engine-only fields (slot passthrough muddies contract) | **ACCEPT → Stage 4.** Contract cleanliness; current passthrough works but the explicit route is the right seam for Lovable. Non-blocking. |
| CR-5-02 | Tighten CORS regex to explicit labels | **ACCEPT — ELEVATED to production-blocking.** The current regex `^https://([a-z0-9-]+\.)?lovable\.app$` allows **any** lovable.app subdomain — i.e. any other tenant's Lovable project can call your API. Fine for preview/dev; **must** tighten to the specific project subdomain(s) + the production domain before go-live. Restrict to known labels (`preview--`, `staging--`, the exact project slug) and drop the broad `*.lovable.app` in production config. Tracked into Stage 4 as a go-live gate. |
| CR-5-03 | Rate limiting on session creation | **ACCEPT → Stage 4.** `/api/session` is public and unauthenticated; needs a per-IP cap (Vercel edge or middleware) before production to prevent abuse/cost. |

## Loop status
Stage 2.5 closed. The engine now lives behind the exact contract Lovable calls, parity proven, governance carried across HTTP (resolved disclaimers, fail-closed bands, opaque refs, role gating), and the full 73-test suite is the regression baseline. CR-4-04 (pinned deps) closed — the weblink runner is now reproducible.

**Carry into Stage 4:** CR-4-01, CR-4-02, CR-5-01, CR-5-02 (go-live blocker), CR-5-03, CR-5-04 — plus AU-region deploy, Supabase adapter, MFA, staging QA, sign-off package.
