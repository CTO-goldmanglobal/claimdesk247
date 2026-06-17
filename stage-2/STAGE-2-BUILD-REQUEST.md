# Stage 2 Build Request — Web Intake · Fault Engine · PDF Summary
**Project:** AI Legal Receptionist + Accident Intake System
**Loop:** Fables (Plan) → Cursor + MiniMax M3 (Build) → Fables (Audit)
**Stage:** 2 of 5 (Phase 1 MVP) · **Issued:** 2026-06-13 · Goldman Forge / Fables
**Consumes:** Stage 1 artefacts in `stage-1/deliverables/` (spec version v1) + `CR-2-01`
**Governed by:** `LOOP-OPERATING-RULES.md` and the test-based audit model (§4 below)

---

## 0. Read first
This is the first **code** stage. The audit is **test-based, not document-based** (Operating Rules §2): you build the fault engine against the acceptance tests in `stage-2/acceptance-tests.stage2.yaml`, ship a **green** report in the delivery manifest, and Fables audits the report + a 10% manual spot-check. A delivery with any red test, or missing the manifest/traceability/test-report, is returned unopened (Operating Rules §3).

Carry-forward fix `CR-2-01` is mandatory in this stage — see §2.

---

## 1. Scope

### In scope
1. **Web intake** — multi-step form with chat wrapper, implementing the S0a→S8 flow and all 14 slots from `stage-1/deliverables/flows.md` + `spec/conversation-flow.v1.md`. Web channel only (voice is Stage 3).
2. **Fault engine** — deterministic classifier consuming `rule-tree.nsw.v1.complete.json`: scenario match → exception probes → damage-consistency → band assignment → band-keyed output string with disclaimer attached.
3. **PDF summary generator** — customer PDF per Loop Request §8.1, including the `pdf_footer` FIXED string.
4. **Acceptance test suite** — implement and pass every case in `acceptance-tests.stage2.yaml`.

### Out of scope (later stages)
- Voice / telephony, tow & rental conversation execution, admin dashboard → Stage 3
- Legal firm intake brief delivery integration, audit-log export UI → Stage 3/4
- Insurer correspondence draft → Stage 3 (optional) / Phase 2
- Anything in Loop Request §3.2

---

## 2. CR-2-01 (mandatory carry-forward from Stage 1 audit)
`s6-multi-chain` in the Stage 1 rule tree carries an out-of-enum output band `n/a_esc_routed`. **Before wiring the engine:** remove that 5th entry from `s6.outputs`; handle `chain_count >= 3` purely through `s6.escalation_overrides` → route to SX using the `escalation_handoff` (complexity variant) string. The band enum the engine accepts is strictly `likely | possible | unclear | insufficient`. Bump the consumed copy to `rule-tree.nsw.v2.json` and record the change in the manifest. Engine must **reject/parse-error** any band outside the enum (fail-closed), which `T-2-027` tests.

---

## 3. Implementation constraints (implementation-ready)

### 3.1 Architecture
- The fault engine is a **pure, deterministic function**: `classify(intakeRecord) → { scenarioId, band, exceptionsFired[], damageConsistent, outputKey }`. No LLM call inside classification — the rule tree is executed as data/logic so outcomes are reproducible and testable. (An LLM may be used only for the conversational *wrapper* phrasing, never to decide band.)
- Disclaimer attachment is a post-processor: any output whose `outputKey` is a fault-information band must resolve `{{ATTACH:master}}` → the FIXED master string before render. Unresolved `{{ATTACH:*}}` at render time is a hard error (`T-2-024`).
- State machine drives slot order; engine is called only at S4 after mandatory slots are filled.

### 3.2 Stack
- Web: any modern SPA/SSR stack the builder prefers (React/Next or equiv). Mobile-responsive. Embeddable widget output (iframe or JS snippet) is a Stage 3 concern but **do not** hardcode anything that blocks it.
- Persistence: store intake records server-side; **no PII in URL params** (Loop Request §10.3). Australian-region storage is a Stage 4 deployment concern — for Stage 2 use a local/dev store but keep the data layer swappable.
- PDF: server-side generation (e.g. a headless renderer or PDF lib). Deterministic content for testing.
- All tokens `{{...}}` resolve from a single config map (stubbed values for dev, real at Stage 5).

### 3.3 Slot validation (from conversation-flow spec)
- Each slot: validate, max 2 re-prompts → offer human callback (route to SX callback booking, not a dead end).
- Slot 1 `state_of_accident`: non-NSW → `state_scope_guard` string → SX callback, **no scenario match attempted**.
- Slot 14 `injuries`: `serious` → SX immediately, before S4. `minor` → flag `esc-injury`, finish safety items, then SX.

### 3.4 Consent gate
- S0a must complete (privacy notice acknowledged; recording consent N/A for web but privacy notice required) before any slot writes PII. No record persisted on decline → S9 ABANDON.

---

## 4. Acceptance tests (the audit backbone)
- File: `stage-2/acceptance-tests.stage2.yaml` — 30 scripted cases, IDs `T-2-001`…`T-2-030`, each tied to a gate.
- Builder implements a runner that feeds `inputs` through the real state machine + engine and asserts `expect`.
- **Green = 0 failures.** Submit the report in the manifest. IDs are permanent; Stage 3 must keep all 30 green (regression).
- Fables re-runs the suite and hand-checks 3 cases (~10%).

---

## 5. Acceptance gates (Fables audit)

Continues the single gate-ID space (Operating Rules §5). P0 must all pass.

| ID | Gate | Pri |
|---|---|---|
| G-15 | Fault engine is deterministic: same intake → same band, 100% reproducible across runs | P0 |
| G-16 | Band output ∈ {likely, possible, unclear, insufficient}; engine fail-closed on any other value (CR-2-01) | P0 |
| G-17 | No numeric fault % in any rendered output or PDF | P0 |
| G-18 | `{{ATTACH:master}}` resolved to FIXED master string on every fault output and in PDF; no unresolved tokens at render | P0 |
| G-19 | All 7 escalation triggers fire from every intake state and short-circuit classification (no band shown) | P0 |
| G-20 | Injury serious → escalation before any fault output; verified by test | P0 |
| G-21 | Non-NSW → state-scope guard + callback, no classification | P0 |
| G-22 | Consent gate precedes any PII persistence; decline persists nothing | P0 |
| G-23 | No PII in URL params; data layer swappable for AU-region store | P1 |
| G-24 | PDF contains all Loop Request §8.1 sections + `pdf_footer` FIXED string verbatim | P1 |
| G-25 | All 30 acceptance tests green; runner reproducible | P0 |
| G-26 | Re-prompt cap = 2 then callback; no slot dead-ends | P1 |
| G-27 | Spec-version match: engine consumes v2 rule tree (post CR-2-01); manifest declares versions | P1 |
| G-28 | Stage 1 design honoured: 14 states, slot order, channel = web only | P1 |

---

## 6. Delivery manifest (required — Operating Rules §3)
1. Gate self-check table (G-15…G-28) with evidence pointers.
2. `deliverables/traceability.md` — requirements + gates → code/tests.
3. `deliverables/test-report.txt` — full green run (TOTAL/PASS/FAIL + coverage).
4. Known-gaps list.
5. Change requests raised (`CR-3-xx`) for anything the spec didn't cover.
6. Compliance quick-scan (template §6) fully checked.

Missing any item → returned unopened.

---

## 7. Budget note
The acceptance tests are the cheap insurance: build the engine against them from day one rather than building then testing. Most Stage 2 revision cost comes from the fault engine guessing band logic — the tests pin it down, so there should be little to guess. Revision budget: 1 audit + up to 2 revisions (Operating Rules §1), but green-tests-before-submit is designed to make the first audit close it.

---

*Prepared by Fables · finn@goldmanglobal.com.au · 2026-06-13*
