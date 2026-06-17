# Fables Audit — Stage 3
**Date:** 2026-06-13 · **Auditor:** Fables · **Spec versions:** rule-tree v3, disclaimers v1
**Delivery:** stage-3/app (voice, aux_flows, dashboard, auth, audit, intake_brief) + tests + deliverables/

## Decision: **LOOP CLOSED (PASS)** — after dependency correction; 3 forward CRs ruled; 1 Stage 4 finding

## Independent verification (Fables re-ran)

| Check | Result | Evidence |
|---|---|---|
| Stage 3 suite | **27/27 PASS** | Re-ran myself (after installing `httpx` — see F-3) |
| Determinism | PASS | 2 consecutive runs, identical 27/27 |
| G-39 regression | PASS | Stage 2 suite 30/30 green inside the run |
| G-29 engine parity | PASS | `app/voice.py` imports `from app.engine import classify`; **no rival `classify()` in voice layer** — engine not forked |
| G-30 recording consent | PASS | consent before PII; decline → non-recorded/callback, no PII persisted |
| G-32 escalation routing | PASS | warm transfer (business hrs) / callback+urgent brief (after hrs); terminal |
| G-33 role access (server-side) | PASS | customer & anonymous → 403; staff/legal → 200. Enforced server-side, not UI hiding |
| G-34 audit immutable + export | PASS | mutation rejected, append-only; admin export returns full records |
| G-35 tow/rental framing | PASS | hazard → 000 advisory before continue; rental general-info framing |
| G-36 intake brief | PASS | 8 field groups present, customer_facing=False, no fault % |
| G-37 voice disclaimer cadence | PASS | master full ×1, short-form 25 words, 4 elements |
| G-38 CR-3-01..04 / v3 | PASS | parking→s5, damage enum rejection, inject_band retained, v3 band-less routing flag |

**Spot-check:** G-29 parity by code inspection (single engine), G-33 by direct 403/200 results, audit-log immutability by mutation-rejection. Clean.

## Finding F-3 (process / Stage 4) — test dependency not pinned
Six dashboard tests (T-3-020..025) initially errored in a clean environment: `fastapi.testclient` needs `httpx`, which the runner doesn't declare. They are **not** logic failures — all 6 pass once `httpx` is installed. But a delivery whose tests can't run in a clean environment violates the "green before audit" contract in spirit.

**Required for Stage 4:** pin test dependencies (`requirements-dev.txt` or equivalent: fastapi, httpx, reportlab, pyyaml) and have the runner fail with a clear message if a dep is missing. This matters more next stage: the weblink black-box tests (Lovable build contract §5) depend on a reproducible runner environment. Logged as `CR-4-04`.

## Carry-forward CRs (builder-applied) — verified
CR-3-01 parking→reversing (T-3-017), CR-3-02 damage enum (T-3-018), CR-3-03 inject_band retained, CR-3-04 v3 band-less routing flag (T-3-019). All confirmed.

## Forward CRs raised by builder — Fables rulings

| CR | Request | Ruling |
|---|---|---|
| CR-4-01 | Free-text follow-up detection (real speech messier than the `{followup}` test hook) | **ACCEPT → Stage 4.** Logic is correct under the test harness; robustness against real STT output is a voice-QA hardening item, not a Stage 3 correctness gap. Address in Stage 4 QA with real/transcribed samples. |
| CR-4-02 | Wire `{{BUSINESS_HOURS}}` / `{{CALLBACK_SLA}}` to runtime config (currently hard-coded defaults) | **ACCEPT → Stage 4/5.** These are firm-confirmed tokens that resolve at sign-off (Loop Request §14). Hard-coded dev defaults are fine for Stage 3; wire to config at Stage 4 deployment, real values at Stage 5. |
| CR-4-03 | Formalise §8.2 intake-brief spec | **DONE.** Written now: `stage-3/spec/intake-brief.v1.md` (8 field groups, internal-only, no %). T-3-026 already asserts against it. |

## Loop status
Stage 3 closed. Engine integrity held across the voice boundary (the stage's biggest risk), regression intact, access control enforced server-side. The only gap was an unpinned test dependency (F-3 → CR-4-04), not a defect. Carry into Stage 4: CR-4-01, CR-4-02, CR-4-04, plus the AU-region deployment, MFA, and staging QA already scoped.
