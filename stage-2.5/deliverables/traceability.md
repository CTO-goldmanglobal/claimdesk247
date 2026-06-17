# Stage 2.5 Traceability Matrix
**Project:** AI Legal Receptionist + Accident Intake System
**Stage:** 2.5 (bridge — Engine-as-Endpoint for Lovable + weblink tests)
**Date:** 2026-06-13
**Builder:** Cursor + MiniMax M3
**Spec versions:**
  - rule-tree: `rule-tree.nsw.v3.json` (Stage 3, v3.0.0)
  - disclaimers: `disclaimers.v1.complete.json`
  - pdf-summary: `pdf-summary.v1.md` (Stage 2)
  - test suite: `acceptance-tests.stage25.yaml` (16 cases, T-25-001..T-25-016)

## Gate self-check (G-41 .. G-49)

| Gate | Pass | Evidence |
|------|------|----------|
| G-41 (HTTP parity with engine)        | Y | T-25-001 and T-25-002: `classify()` and `/api/classify` return identical bands for the same intake. The wrapper never re-bands; it calls `stage3_engine.classify` via the state machine's `run_classification`. |
| G-42 (disclaimer resolved + enum fail-closed) | Y | T-25-003: `outputText` has zero `{{...}}` tokens (resolved via `stage3_config.resolve_strict`); band is in `VALID_BANDS`. T-25-004: `inject_band=n/a_esc_routed` returns 500 with `band_rendered=False`. |
| G-43 (escalation short-circuits over HTTP) | Y | T-25-005: `injuries=serious` → 200 with `{escalation: esc-injury, next: escalated, terminal: true}`, no `band`. T-25-006: `chain_count=3` → same shape with `esc-multiparty`. |
| G-44 (no PII in URL)                   | Y | T-25-007: full intake (incl. customer name + rego) uses only opaque `reference`; no PII in path/query. T-25-008: PDF is fetched by opaque ref. |
| G-45 (brief role-gated server-side)   | Y | T-25-009: customer → 403. T-25-010: legal_staff → 200 with all 8 brief fields. |
| G-46 (x-test-mode env-gated)          | Y | T-25-011: same intake, same `x-test-mode: 1` header → same deterministic ref. T-25-012: APP_ENV=production short-circuits test-mode activation. |
| G-47 (healthz returns engine + tree versions) | Y | T-25-013: `/healthz` returns `{status: ok, engine_version: 1.0.0, rule_tree_version: 3.0.0, api_version: 0.2.5.0}`. |
| G-48 (Stage 2 + Stage 3 regression)    | Y | T-25-016 spawns both runners via subprocess (PYTHONPATH=stage-3); both report `30/30` and `27/27` green. |
| G-49 (CORS allow-list, no wildcard)    | Y | T-25-014: `Origin: https://evil.example.com` → no `Access-Control-Allow-Origin` echoed. T-25-015: `Origin: https://preview--abc123.lovable.app` → echoed. Regex is `^https://([a-z0-9-]+\.)?lovable\.(app|dev)$` plus the production origin. |

## Deliverable map

| Requirement (from STAGE-2.5-BUILD-REQUEST) | Where built |
|---|---|
| FastAPI app wrapping engine + state machine | `stage-2.5/app/wrap.py` |
| 6 contract endpoints (`/healthz`, `/api/session`, `/api/consent`, `/api/slot`, `/api/classify`, `/api/pdf/:ref`, `/api/brief/:ref`) | `stage-2.5/app/wrap.py:create_app` |
| Engine parity over HTTP (G-41) | wrapper calls `stage3_state_machine.run_classification` → `stage3_engine.classify` |
| Disclaimer already resolved in `/api/classify` (G-42) | `wrap.py:post_classify` calls `stage3_config.resolve_strict` |
| Out-of-enum band → fail-closed, never rendered (G-42) | `wrap.py:post_classify` returns 500 with `band_rendered=False` |
| Escalation short-circuit, no band, terminal (G-43) | `wrap.py:post_slot` and `wrap.py:post_classify` |
| Engine-only intake fields (passthrough) | `wrap.py:post_slot` — unknown slot names stored in `intake` without validation |
| Opaque reference; no PII in URLs (G-44) | `wrap.py:create_session` assigns `reference`; all routes key by it |
| Role-gated `/api/brief` (G-45) | `wrap.py:get_brief` uses `stage3_auth.dashboard_visible_for` server-side |
| `x-test-mode` env-gated (G-46) | `wrap.py:_is_test_mode_active` returns False when `APP_ENV=production` |
| `/healthz` versions (G-47) | `wrap.py:healthz` |
| CORS allow-list, regex-based (G-49) | `wrap.py:create_app` — `allow_origin_regex` and `allow_origins` |
| Test runner (local + weblink) | `stage-2.5/tests/run_acceptance.py` (BASE_URL toggles mode) |
| Combined regression (Stage 2 + Stage 3) | `tests/run_acceptance.py:_drive_regression` (subprocess) |
| Pinned dev deps (CR-4-04) | `requirements-dev.txt` at repo root |

## Test report

See `deliverables/test-report.txt` (combined Stage 2.5 + Stage 2 + Stage 3 regression).

## Compliance scan (legal-domain hard checks)

- [x] No numeric fault % applied to the user (carried forward from Stage 2/3; the wrapper does not author output)
- [x] Master disclaimer attaches to every fault-information output (resolved server-side; Lovable receives `disclaimerText` already populated, never re-resolves)
- [x] All 7 escalation triggers reachable from every intake state; escalation is terminal (G-19/G-43, carried forward)
- [x] Injury asked before any fault output (Stage 3 voice; web intake is the same code path)
- [x] Corrected rule citations only (r72, r73, r296) — engine unchanged
- [x] `[FIRM-TBC]` values are tokens; resolved before response (G-18 across HTTP)
- [x] Privacy/recording consent precedes any PII collection (G-22/G-30, `/api/consent` gate)

## Out-of-scope (Stage 4/5 / Phase 2)

- Real OIDC/SAML auth (currently stub via `as_email` query param)
- Supabase adapter for `SessionStore` (currently in-memory)
- AU-region deployment to Vercel `syd1` (deployment is Stage 4)
- Insurance-correspondence draft template (not in this stage)
- Direct tow-dispatch / rental-booking APIs (Phase 2)
