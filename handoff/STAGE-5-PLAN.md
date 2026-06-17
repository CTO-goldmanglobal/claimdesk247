# Stage 5 Plan — L0 closure + L1 transition · ClaimDesk 247
**Prepared by:** Cursor / MiniMax (build seat) · **Date:** 2026-06-15
**Scope:** audit T1 (L0 T1), record L0 state, plan L0 closure and L1 build queue, propose next autonomous moves.
**Inputs read:** `CURSOR-HANDOFF-MASTER.md`, `CLAIMDESK247-LOOP-ROADMAP.md`, `LOOP-OPERATING-RULES.md`, `LOOP-GATE-COMPLETENESS-REVIEW.md`, `stage-4/GATE-REGISTER-ADDENDUM.md`, `stage-4/FABLES-AUDIT-STAGE-4.md`, `handoff/LOOP-CLOSE-DECISIONS.md`, `stage-4/sign-off-package/LEGAL-HEAD-SIGNOFF.md`, `stage-4/PHASE-2-RULE-COVERAGE-GAPLIST.md`.

---

## 1. Audit of T1 (L0 T1 — G-PROD-LOCK + G-VER)

**Status: ✅ closed. Live in syd1.**

### 1.1 What landed

| Item | Where | Evidence |
|---|---|---|
| Per-scenario `legal_signoff` metadata (6 scenarios, all unsigned) | `stage-3/app/data/rule-tree.nsw.v3.json` | Each scenario now has `"legal_signoff": { "approved": false, "version": "", "by": "", "date": "" }` |
| Hash + signoff gate in `classify()` | `stage-3/app/engine.py` | `_compute_scenarios_hash` (SHA-256 of `scenarios[]` with each scenario's own `legal_signoff` stripped) + `_check_legal_signoff` (returns escalation envelope if unsigned or stale) + `classify()` call to the check after scenario resolution |
| `rule_tree_hash` exposed in `/healthz` | `stage-2.5/app/wrap.py` | New field in the `/healthz` JSON, computed at request time |
| 4 new acceptance tests (T-1-01..T-1-04) | `stage-3/acceptance-tests.stage3.yaml` + `stage-3/tests/run_acceptance.py` + `stage-2.5/tests/run_acceptance.py` | signed→band, unsigned→escalation, stale→escalation, hash deterministic |
| 2 existing dispatchers updated | `stage-2.5/tests/run_acceptance.py` | `_drive_unresolved_and_enum` accepts escalation as pass; `_drive_healthz` asserts `rule_tree_hash` field |

### 1.2 Test evidence

| Suite | Working folder | Engine repo clone |
|---|---|---|
| stage-2 | 30/30 | not in repo (intentional — predecessor state) |
| stage-2.5 | 18/18 (incl. 1 stage-2 regression marker, marked PASS as cross-suite) | 17/18 — the 1 fail (T-25-016) is the cross-stage regression whose target `stage-2/` is intentionally absent from the engine repo |
| stage-3 | 31/31 (27 baseline + 4 new T-1-01..T-1-04) | 30/31 — the 1 fail (T-3-027) is the same cross-stage regression |
| **Total** | **79/79** | **47/48** |

The clone's 1 fail is **pre-existing and by design** — the engine repo doesn't carry `stage-2/`, which is the predecessor stage. Verified separately in the working folder. **No regression introduced by T1.**

### 1.3 Live deployment evidence

- **Commit:** `7a8d3d8` on `CTO-goldmanglobal/claimdesk247-engine` `main`
- **Author:** `CTO Goldman <cto@goldmanglobal.com.au>` (matches prior 5 Fables commits)
- **Vercel auto-deploy:** live at `https://claimdesk247-engine.vercel.app/healthz`
- **Live response:**
  ```json
  {
    "status": "ok",
    "engine_version": "1.0.0",
    "rule_tree_version": "3.0.0",
    "rule_tree_hash": "1ddabeb5c441fa8790e56e00a8bfe3ef75a2680ae6077817f53a0191ee4f7c72",
    "api_version": "0.2.5.0"
  }
  ```
- **Region:** `syd1` (Vercel ID header confirms)

### 1.4 The `rule_tree_hash` for Legal Head

```
1ddabeb5c441fa8790e56e00a8bfe3ef75a2680ae6077817f53a0191ee4f7c72
```

This is what B1–B6 (and later B7–B15) must be signed against. Per scenario in `rule-tree.nsw.v3.json`, replace `legal_signoff` with:
```json
"legal_signoff": {
  "approved": true,
  "version": "1ddabeb5c441fa8790e56e00a8bfe3ef75a2680ae6077817f53a0191ee4f7c72",
  "by": "<Legal Head name / role>",
  "date": "<ISO 8601>"
}
```

### 1.5 What T1 deliberately did NOT do

- **No bypass code in the T1 commit.** The Vercel Protection Bypass header injection in `stage-2.5/tests/run_acceptance.py` is preserved at `/tmp/t1_bypass_full.py` for a future commit #2 (per the user's "two commits" decision). Currently inert (only activates if `VERCEL_BYPASS` env var is set; that secret was deleted per the handoff).
- **No `requirements.txt` comment drift.** The 2-line explanatory comment about `PyJWT[crypto]` that's in the working folder's `engine-deploy/requirements.txt` but missing from the engine repo's `main` `requirements.txt` is left for a future commit. Not load-bearing; the actual package pin is already in `main`.
- **No scenario sign-offs.** T1 enforces the gate; it does not sign anything. The 6 scenarios are unsigned by design until Legal Head says YES.

### 1.6 Drift and risks I want to surface

- **The 6 scenarios are unsigned.** Live engine currently escalates *every* scenario in the rule tree (because none have `legal_signoff.approved = true`). That means the live site, in its current state, will return escalations for *all* intake→classify flows — not a regression, but a *change* from pre-T1 behavior (which returned bands). **This is by design** (G-PROD-LOCK fail-closed), but it's worth flagging: the live site is in a "lawyer will contact you" state until Legal Head signs. Sign the scenarios and the bands return automatically.
- **The "stage-2 regression target" is missing from the engine repo's tests.** This is by design (stage-2 is a predecessor, lives in the working folder), but the cross-stage regression marker (T-25-016 / T-3-027) will always fail in the engine repo. Worth a code comment in the test files noting this. Not a T1 problem, but a maintenance note for future loops.
- **No autosign workflow.** Today, signing is a manual edit to the rule-tree JSON. For 6 scenarios that's fine; for 15 (post-Phase-2) it's a small but real ops tax. The long-term solution is a tool/Legal-Head UI that records sign-off (G-LH per the gate register addendum). **Not blocking L0 close, but a L1+ consideration.**

---

## 2. L0 state (post-T1)

### 2.1 L0 build queue (per `CURSOR-HANDOFF-MASTER.md` §7)

| Task | Description | Status | Where it lives |
|---|---|---|---|
| **T1** | G-PROD-LOCK + G-VER (engine enforcement) | ✅ **DONE** (commit `7a8d3d8`, live, this session) | Engine repo `main` |
| **T2** | Activate server-side AAL2 on `/api/brief` | 🟡 **BUILT, FLAGGED OFF** (per handoff: `BRIEF_AUTH_MODE=stub` default, `jwt` available; needs real staff token to test roll-out) | Engine repo `main` (commit `0e7dda7`) |
| **T3** | Monitoring + rollback (alerting on error/5xx, escalation rate, band-distribution drift; tested one-step rollback) | 🔴 **NOT STARTED** | All new work; engine repo + Vercel + Supabase |

### 2.2 L0 governance gates (per `GATE-REGISTER-ADDENDUM.md`)

| Gate | Status | Evidence |
|---|---|---|
| **G-PROD-LOCK** | 🟢 **PASS** (T1) | Engine refuses unsigned scenarios; verified by 4 T-1-* tests + live `/healthz` |
| **G-VER** | 🟢 **PASS** (T1) | `rule_tree_hash` computed + exposed; tested stale-signoff detection in T-1-03 |
| **G-LH** | 🔴 **OPEN** | Per-scenario YES/NO from Legal Head not yet recorded (waiting on B1–B6 sign-off) |
| **G-AMEND** | 🟡 **STANDS READY** | Loop-closure gate; will pass once G-LH is recorded and no open audit findings |

### 2.3 L0 product/compliance/security gates (per `FABLES-AUDIT-STAGE-4.md` and `LOOP-CLOSE-DECISIONS.md`)

| Gate | Status | Notes |
|---|---|---|
| G-50 staging live; web e2e | 🟢 PASS (per audit 2026-06-14) | `claimdesk247.com.au` live against real engine |
| G-51 / G-62 scored regression | 🟢 PASS (per audit 2026-06-14) | 75/75 vs deployed preview; bypass secret deleted (so any future remote run needs a fresh secret) |
| G-52 AU residency | 🟢 PASS | Supabase `ap-southeast-2`; Vercel `syd1` only |
| G-53 RLS enforced | 🟢 PASS | Anon reads 0 rows; staff-read RLS policies |
| G-54 audit_log append-only | 🟡 **CLIENT-ENFORCED** (per audit) | Append-only trigger `0003` written; needs CTO to apply to Supabase (D-7) |
| G-55 CORS exact-origin | 🟢 PASS | CR-5-02 lockdown; verified live |
| G-56 rate-limit | 🟢 PASS | Per-IP cap enforced (Durable/Upstash = CR-5-06 Phase-2) |
| G-57 MFA | 🟡 **ENFORCED** (per audit) | TOTP live; `VITE_MFA_REQUIRED=true` set; remaining = one staff enrol (CTO action) + server-side AAL2 (T2) |
| G-58 E2E QA | 🟢 PASS (web scope) | Voice descoped to Phase 2 (D-5) |
| G-59 test-mode inert in prod | 🟢 PASS | `VITE_TEST_MODE` unset; client-side only |
| G-60 carry-in CRs | 🟡 PARTIAL | CR-5-01 / CR-5-04 done; CR-4-02 (firm-hours/SLA) needs D-8 firm tokens; CR-4-01 (voice STT) Phase 2 |
| G-61 sign-off package | 🟢 COMPLETE (pending firm) | 8 items; item 6 deferred to Phase 2 (D-6) |
| G-50–62 tally | PASS 11 · PARTIAL 1 (G-60) · OPEN 0 (per `FABLES-AUDIT-STAGE-4.md` line 22) | |

### 2.4 CTO/Firm-gated items (cannot be closed from build seat)

| Item | What | Who |
|---|---|---|
| **D-2** MFA activation | TOTP already on in Supabase; one staff enrol needed | CTO |
| **D-7 apply** | Run `0003_audit_log_append_only_trigger.sql` in Supabase SQL editor | CTO |
| **D-8** firm tokens | `FIRM_NAME`, `FIRM_PHONE`, `BUSINESS_HOURS`, `CALLBACK_SLA`, `RETENTION_PERIOD`, `TOW_PROVIDER_REF`, `RENTAL_PARTNER_REF` | Firm |
| **D-9** rotate credentials | Service role key + 2 GitHub PATs | CTO (secrets; build seat must not handle) |
| **T8** Legal Head sign-off B1–B6 | 6 live scenarios → sign against `rule_tree_hash 1ddabeb5c441...` | Legal Head |
| **T2 test roll-out** | Set `BRIEF_AUTH_MODE=jwt` on engine + test with real staff token (D-2 first) | CTO + Legal Head test with a real signed-in session |

### 2.5 L0 exit / L1 entry milestone (per `CLAIMDESK247-LOOP-ROADMAP.md`)

> Legal YES on the 6 live scenarios **and** 4 P0 gates closed **and** live-site/consumer-law fixes shipped **and** NSW advertising cleared.

Current status against that:
- 4 P0 gates: **G-PROD-LOCK ✅, G-VER ✅**; G-LH pending T8; G-AMEND stands ready.
- Live-site/consumer-law: shipped (commit `144516e`).
- NSW advertising cleared: pending Legal Head review (D-2 / D-3 / D-6 / D-8 in the decision register).

**Therefore L0 closes when Legal Head signs B1–B6 + NSW advertising is cleared + the firm provides the D-8 tokens.** That's a governance/human gate, not a build gate. The build work that can be done from this seat is T3 (monitoring/rollback) and T2 (AAL2 test roll-out), both partially gated on CTO actions.

---

## 3. L1 build queue (Phase-2 scenarios, evidence, flywheel, analytics)

### 3.1 The headline L1 sub-loop (per `CLAIMDESK247-LOOP-ROADMAP.md` §L1)

> Phase-2 scenarios 6 → 15 — car-park, signalised, right-turn, sideswipe, driveway, U-turn, head-on, dooring, unmarked.

Per the handoff §7 (L1):

1. **T4** — Add 9 scenarios → rule tree (v3.1.0). Specs in `stage-4/PHASE-2-TIER1-RULE-BRANCHES.md` + `…TIER2…`. 9 scenarios: car-park, signalised, right-turn, sideswipe, driveway, U-turn, head-on, dooring, unmarked.
2. **T5** — Band functions + routing. Add `_band_s7…_band_s15` in `engine.py`; add `ACCIDENT_TYPE_TO_SCENARIO` entries + damage-consistency maps.
3. **T6** — **Conversational question-injection (the dependency — mandatory).** Today the live flow asks only the fixed 14 `SLOT_DEFINITIONS`; the per-scenario `classification_questions` (e.g. `user_position`, `sight_lines`, light colour) are not asked. Build dynamic injection: after `accident_type` is known and the scenario resolved, the state machine asks that scenario's `classification_questions`. **Touches `state_machine.py` + `wrap.py`; regression-guard all 6 existing scenarios.**
4. **T7** — Tests. ≥2 acceptance cases per new scenario; keep the suite green (75 → ~93).
5. **T8** — Legal Head (final gate). Per-scenario yes/no via `LEGAL-HEAD-SIGNOFF.md` (B7–B15). G-PROD-LOCK keeps unsigned scenarios escalating until YES, bound to v3.1.0 (G-VER).
6. **T9** — Coverage backtest, flywheel, evidence intake.

### 3.2 L1 other items (per `CLAIMDESK247-LOOP-ROADMAP.md`)

| Task | Description | Closes gap |
|---|---|---|
| Coverage backtest | Backtest rule tree vs historical claims; measured accuracy per scenario | "Coverage estimated not measured" |
| Flywheel | Capture every human determination as structured data | "Flywheel not built" |
| Evidence intake v1 | Photo/document upload + OCR; partner for damage AI | "Evidence as questions" |
| Firm analytics dashboard | Volumes, band mix, escalation reasons, seed status | "No analytics dashboard" |
| Pen-test + DR/BCP + durable shared rate limiter | Security/ops hardening | "No pen-test/DR/BCP" |
| ISO 42001 docs | AI impact assessment + risk register + supplier register | "Certification groundwork" |

### 3.3 The key dependency I want to flag

**T6 (question-injection) is the dependency.** T4 + T5 + T7 without T6 = band functions with no inputs, defaulting to `unclear` or `insufficient`. The handoff is explicit: "Without this, the band logic has no inputs and would default — so this sub-step is mandatory, not optional."

**T6 touches the shared flow.** The fixed 14 `SLOT_DEFINITIONS` ask things like state, date, location, etc. The 9 new scenarios need additional questions (front/rear position, sight lines, light colour, etc.) *injected after the scenario is resolved*. The injection has to be additive — the 6 existing scenarios must continue to work without their question list expanding (they're signed; changing them invalidates the G-VER hash).

**This is the load-bearing build for L1.** Get this right and the 9 scenarios get bands; get it wrong and we ship band defaults and the 9 scenarios all escalate.

### 3.4 L1 entry conditions (per loop discipline)

- L0 closed (4 P0 gates + Legal Head sign-off on B1–B6 + firm tokens)
- T8 of L1 (Legal Head sign-off on B7–B15) before any L1 scenario serves in prod
- Test suite green throughout (T4–T8 with regression-guard)
- T6 (question-injection) done and audited before T4–T7 land

---

## 4. Proposed autonomous next steps (per the "long term automatic" / "loop-after-loop" council standing instruction in `LOOP-CLOSE-DECISIONS.md`)

Given the user's repeated "long term automatic solution" guidance and the council standing instruction, the next moves I can take from the build seat are:

### 4.1 Immediate (this session, if approved)

| # | Action | Why | Risk |
|---|---|---|---|
| 1 | Push T1's bypass code as commit #2 to engine repo `main` | Already split and tested; matches user's "two commits" decision; the code is inert until `VERCEL_BYPASS` env is set (per handoff, that secret was deleted) | Low — code is small, tested, gated by env var |
| 2 | Update `handoff/CURSOR-HANDOFF-MASTER.md` L0 status (T1 ✅, T2/T3 next) | Keeps the handoff in sync with reality; the next "build seat" picking up cold sees correct state | None — doc only |
| 3 | Add a code comment in `stage-2.5/tests/run_acceptance.py` and `stage-3/tests/run_acceptance.py` noting that the cross-stage regression markers (T-25-016, T-3-027) target `stage-2/` which is intentionally absent from the engine repo | Maintenance note for future loops; prevents a future builder from "fixing" it incorrectly | None — comment only |

### 4.2 Next-session (T2 prep, L0 → L1)

| # | Action | Pre-condition | Gated by |
|---|---|---|---|
| 4 | T2 — activate server-side AAL2 on `/api/brief` (turn `BRIEF_AUTH_MODE=jwt`, frontend forwards token) | CTO enables TOTP + enrols one staff (D-2); firm provides test credentials | CTO (D-2); firm (test user) |
| 5 | T3 — monitoring + rollback | Stand up a minimal monitoring layer (Vercel observability + Supabase log-based alert on error/5xx + band-distribution drift) + write a rollback runbook + test rollback once | CTO (Vercel/Supabase dashboards); firm tokens for SLA thresholds |
| 6 | T4 prep — start drafting the 9 Phase-2 scenario JSON objects (no engine code yet) | None — design work, doesn't break anything | None |
| 7 | T6 (question-injection) design — write the design doc for how classification_questions get injected after scenario resolution | None — design work | None |

### 4.3 Blocked (cannot do from this seat)

| # | Action | Why blocked |
|---|---|---|
| 8 | Apply `0003_audit_log_append_only_trigger.sql` to Supabase | Build seat doesn't have prod-DB write access (MCP apply is read-only) |
| 9 | Rotate service_role key + 2 GitHub PATs | Secrets — build seat must not handle |
| 10 | Sign B1–B6 scenarios (T8) | Legal Head is a human gate; the build seat writes the code, Legal Head approves |
| 11 | Set `BRIEF_AUTH_MODE=jwt` in production | Needs a real staff token test path (D-2 + firm test user) |
| 12 | Test rollback (G-ROLLBACK) | Needs CTO to perform a controlled rollback exercise (deployment authority) |

---

## 5. Decision log (proposed, pending user approval)

| # | Decision | Recommendation | Why |
|---|---|---|---|
| **D-11** | Push the T1 bypass code as commit #2 now, or defer? | **Push now** (item 1 in §4.1) | Inert code; matches user's "two commits" choice; unblocks future remote regression runs |
| **D-12** | Update the master handoff doc with T1 closure? | **Yes** (item 2 in §4.1) | Keep handoff in sync; small but real maintenance win |
| **D-13** | Add the cross-stage regression comment? | **Yes** (item 3 in §4.1) | Prevents future "fix" mistakes; tiny comment, zero risk |
| **D-14** | What's the order of T2 vs T3 in the L0 remaining work? | **T2 first** (AAL2 is the higher-risk governance gap; T3 monitoring is observable, not load-bearing) | T2 closes a P0-adjacent auth risk; T3 is P1 monitoring; AAL2 has been built and is just waiting for token-test |
| **D-15** | When to start L1 (Phase-2) prep work? | **Now, in design only** (item 6 + 7 in §4.2) | T4 scenario JSON drafting + T6 question-injection design are doc-only work, don't touch live code, and front-load the expensive Fables model time before the cheap Cursor stack picks it up |

---

## 6. Risks + things to watch

- **Live site is in a "lawyer will contact you" state until T8 (Legal Head signs B1–B6).** G-PROD-LOCK is working as designed, but worth knowing. Any user testing the live site will see escalation envelopes, not bands.
- **`stage-2` is not in the engine repo.** The cross-stage regression test (T-25-016, T-3-027) will always fail in the engine repo. Maintenance note in the test files will help future loops.
- **Stage-2.5 dispatchers depend on `app.wrap` import paths.** With the T1 changes, `_drive_healthz` and `_drive_unresolved_and_enum` are correct. But a future change to `wrap.py` shape (e.g. renaming the `healthz` function) would break these tests. Worth a brief future "smoke test" CI step.
- **T6 (question-injection) is the load-bearing L1 dependency.** If it's not done well, T4–T7 produce scenarios that don't band. This is the one place to invest the most spec quality.
- **The 75-test regression now requires a fresh Vercel Protection Bypass secret** to run against the preview deploy (the old one was deleted per the handoff). The bypass code is staged (item 1 in §4.1); the secret is a CTO/setting action.

---

## 7. Definition of "L0 closed" — what to look for

Per `LOOP-OPERATING-RULES.md` §7, "no incomplete loop":

1. All P0 gates pass — **including G-PROD-LOCK, G-VER, G-LH, G-AMEND** (per `GATE-REGISTER-ADDENDUM.md`).
2. Automated test report green + spot-check.
3. Traceability complete and version-matched (G-VER).
4. Open CRs resolved or named to a later stage.
5. Known-gaps list empty or explicitly accepted to Phase 2.
6. **No open audit finding or Legal-Head NO (G-AMEND).**

**Current L0 state against that:** 1, 2, 3, 4, 5 = pass-ready. 6 = waiting on T8 (Legal Head signs B1–B6). L0 closes the moment Legal Head's YES is recorded in the rule tree.

**L0 does NOT close when T3 (monitoring/rollback) is done.** T3 is P1, not P0. L0 closes on the P0 governance gates + Legal Head. T3 can be a L1 carry-in or a L0 follow-up — your call.

---

*Prepared by Cursor / MiniMax (build seat) · next action pending user direction. See §5 for proposed decisions.*
