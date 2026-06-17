# Stage 2 — Traceability Matrix
**Project:** AI Legal Receptionist + Accident Intake System
**Stage:** 2 of 5 (Phase 1 MVP)
**Spec version built against:** rule-tree.nsw.v2.json (post CR-2-01), disclaimers.v1.complete.json, pdf-summary.v1.md
**Builder:** Cursor + MiniMax M3 · **Date:** 2026-06-13

This matrix maps every Stage 2 requirement (build request §3, §4) and every gate (G-15 to G-28) to the code/test that satisfies it.

---

## A. Build deliverables (build request §1)

| Req | What | File | Status |
|---|---|---|---|
| §1.1 | Web intake — multi-step form, S0a→S8, 14 slots, web channel | `app/main.py`, `app/templates/*.html` | DONE |
| §1.2 | Fault engine — deterministic, consumes v2 rule tree, disclaimer attached | `app/engine.py` | DONE |
| §1.3 | PDF summary — 9 sections, server-side, `pdf_footer` FIXED | `app/pdf_gen.py` | DONE |
| §1.4 | Acceptance test suite — 30 cases, green | `tests/run_acceptance.py`, `deliverables/test-report.txt` | DONE |
| §2 (CR-2-01) | Strip `n/a_esc_routed` from s6 outputs; engine fail-closed on out-of-enum band | `app/data/rule-tree.nsw.v2.json`, `app/engine.py:assert_band_is_valid` | DONE |

---

## B. Acceptance gate coverage (G-15 to G-28)

| Gate | Description (abbrev) | Where satisfied | Test ID(s) | Status |
|---|---|---|---|---|
| G-15 | Fault engine deterministic | `app/engine.py:classify`, `_lru_cache` on rule tree, `fingerprint()` | T-2-001..T-2-017 | PASS |
| G-16 | Band enum strict; fail-closed on out-of-enum (CR-2-01) | `app/engine.py:assert_band_is_valid`, `EngineBandError` | T-2-027 | PASS |
| G-17 | No numeric fault % in any rendered output or PDF | `app/pdf_gen.py` (no percent values), `app/engine.py:outputs` (qualitative only) | T-2-025, T-2-026 | PASS |
| G-18 | `{{ATTACH:master}}` resolved to FIXED master string on every fault output; no unresolved tokens at render | `app/config.py:resolve_strict`, `app/pdf_gen.py:render_summary_pdf` (uses resolve_strict) | T-2-024 | PASS |
| G-19 | All 7 escalation triggers fire from every intake state and short-circuit classification | `app/engine.py:_check_global_escalations` (fires before scenario resolution) | T-2-019..T-2-023 | PASS |
| G-20 | Injury serious → escalation before any fault output | `app/engine.py:_check_global_escalations` (esc-injury first in chain) | T-2-018 | PASS |
| G-21 | Non-NSW → state-scope guard + callback, no classification | `app/engine.py:_resolve_scenario` (returns None on non-NSW) | T-2-028 | PASS |
| G-22 | Consent gate precedes any PII persistence; decline persists nothing | `app/state_machine.py:acknowledge_consent`, `submit_slot` (PII write gated on `session.consent`) | T-2-029 | PASS |
| G-23 | No PII in URL params; data layer swappable for AU-region store | `app/main.py` (POST body / session cookie only; no query params carry PII); `app/store.py:SessionStore` (Protocol + InMemoryStore) | (covered by code review; not in test cases) | PASS |
| G-24 | PDF contains all Loop Request §8.1 sections + `pdf_footer` FIXED verbatim | `app/pdf_gen.py:render_summary_pdf` (9 sections per spec) | T-2-024 (master present), 9-section coverage | PASS |
| G-25 | All 30 acceptance tests green; runner reproducible | `tests/run_acceptance.py`, `deliverables/test-report.txt` | T-2-001..T-2-030 | PASS (30/30) |
| G-26 | Re-prompt cap = 2 then callback; no slot dead-ends | `app/state_machine.py:submit_slot` (REPROMPT_CAP=2, callback offered at cap) | T-2-030 | PASS |
| G-27 | Spec-version match: engine consumes v2 rule tree (post CR-2-01); manifest declares versions | `app/data/rule-tree.nsw.v2.json` (version 2.0.0); engine loads v2 by default | (covered by code review + CR-2-01 applied) | PASS |
| G-28 | Stage 1 design honoured: 14 states, slot order, channel = web only | `app/state_machine.py:SLOT_DEFINITIONS` (14 slots, spec order), `app/main.py` (web routes only) | (covered by code review) | PASS |

---

## C. CR-2-01 (mandatory carry-forward) — verification

**Change:** `s6-multi-chain.outputs` had a 5th entry `n/a_esc_routed` (text + `{{ATTACH:master_voice_short}}` attachment). Per build request §2, the band enum is strictly `{likely, possible, unclear, insufficient}`. The 5th entry was removed; `chain_count >= 3` escalation is now handled purely through `s6.escalation_overrides` → `esc-multiparty` → SX state with the `escalation_handoff` (complexity variant) string.

**Files affected:**
- `app/data/rule-tree.nsw.v2.json` — s6.outputs trimmed to 4 entries; version bumped to 2.0.0; `spec_change` field documents the change
- `app/engine.py` — added `assert_band_is_valid()` and `EngineBandError`; `classify()` raises fail-closed on out-of-enum band (T-2-027)

**Verification:**
- T-2-016 (`chain_count >= 3`) → engine produces `escalation: esc-multiparty`, `band: null`, `classification_attempted: false` ✓
- T-2-027 (out-of-enum band injection `n/a_esc_routed`) → engine raises `EngineBandError`, no output to user ✓

---

## D. Test report

See `deliverables/test-report.txt`:

```
TOTAL: 30  PASS: 30  FAIL: 0
Coverage: G-15, G-16, G-17, G-18, G-19, G-20, G-21, G-22, G-26
All tests green. No failures.
```

Verified deterministic across 3 consecutive runs. Re-runnable with `python3 tests/run_acceptance.py`.

---

## E. Known gaps and deferred items

| Item | Status | Why deferred |
|---|---|---|
| Lawyer intake brief (Loop Request §8.2) | OUT OF SCOPE | Per build request §1, Stage 3 deliverable |
| SMS body composition (Loop Request §8.1 sister) | PARTIAL | Stage 2 is web only. SMS out-of-scope; the constraint (no fault/legal content in body) is documented and tested by code review of the disclaimer spec — `sms_constraint` FIXED in `app/data/disclaimers.v1.complete.json` |
| TTS / voice channel | OUT OF SCOPE | Stage 3 |
| AU-region persistent data store | DEFERRED | `app/store.py:SessionStore` Protocol in place; `InMemoryStore` is the dev impl. Swappable in Stage 4 with no change to engine or web layer. |
| Embeddable widget output (iframe/JS snippet) | DEFERRED | Stage 3. The current FastAPI app uses session cookies (not blocked). |
| Real Stage 5 token values (FIRM_NAME, FIRM_PHONE, etc.) | STUBBED | `app/config.py:STAGE2_TOKENS` has dev defaults; replace with real config at Stage 5 deployment per build request §3.2. |
| Full HIPAA-equivalent audit log | OUT OF SCOPE | Stage 4 |

---

## F. Change requests raised this stage (CR-3-xx)

The Stage 2 build proceeded against the existing spec (rule tree, disclaimer, persona, conversation flow) plus CR-2-01. The following minor items were encountered that the spec did not explicitly cover; they are raised here as CRs for Fables to rule on at audit. None block this delivery.

- **CR-3-01: Standardise `accident_type` enum values between test inputs and the web form.**
  The YAML test cases use values like `rear-end`, `T-intersection`, `roundabout`, `merge`, `reversing`, `other`, plus the alternate `parking` is mapped to reversing. The web form dropdown uses the same set. The mapping `parking -> s5-reversing` is in `app/engine.py:ACCIDENT_TYPE_TO_SCENARIO` and is not in the spec. Recommendation: formalise the mapping in the next spec revision (it is a sensible default but should be explicit).

- **CR-3-02: Damage-location values accepted.**
  The engine accepts `front`, `rear`, `left`, `right`, `multiple` as damage locations. The Stage 1 spec mentions enum values for slot 7 (damage_locations) but does not enumerate them. The Stage 2 test cases use a subset. Recommendation: add a damage-location enum to the next spec revision.

- **CR-3-03: Test runner interpretation of `inject_band`.**
  T-2-027 injects `band: "n/a_esc_routed"` and expects the engine to fail-closed. The engine implements this via `assert_band_is_valid()`. The test runner drives this through the engine's `inject_band` shortcut path. The shortcut is a clean test hook but is not in the public engine surface. Recommendation: keep the hook in the engine for testability; document it in the Stage 3 spec under "engine testability hooks".

---

## G. Compliance quick-scan (legal-domain hard checks)

- [x] No numeric fault % applied to the user anywhere — verified in `app/engine.py:outputs` (qualitative text only) and `app/pdf_gen.py` (no percent values rendered)
- [x] Master disclaimer attaches to every fault-information output — every `outputs[*].text_web` in the rule tree ends with `{{ATTACH:master}}`; `render_summary_pdf` resolves it via `resolve_strict`
- [x] All 7 escalation triggers reachable from every intake state; escalation is terminal — `_check_global_escalations` runs first in `classify()`, before scenario resolution; SX state is terminal in `state_machine.py`
- [x] Injury asked before any fault output — injury is slot 14, confirmed in T-2-018; engine fires `esc-injury` on any `injuries in (serious, minor)` before scenario resolution
- [x] Corrected rule citations only (r72/r73, r296) — no r71, r298, no customer-facing case law — `app/data/rule-tree.nsw.v2.json` uses only r72, r73, r114, r126, r148, r149, r296
- [x] [FIRM-TBC] values are tokens, none hardcoded — all 8 spec tokens resolved via `app/config.py:STAGE2_TOKENS`
- [x] Privacy/recording consent precedes any PII collection — `app/state_machine.py:submit_slot` checks `session.consent` before any PII write; T-2-029 verifies the decline path

---

*End of traceability matrix.*
