# Stage 2 Delivery Manifest
**Project:** AI Legal Receptionist + Accident Intake System
**Stage:** 2 of 5 (Phase 1 MVP) · **Delivery date:** 2026-06-13
**Builder:** Cursor + MiniMax M3 · **Issuer:** Goldman Forge / Fables (per build request)
**Spec versions built against:**
- rule-tree.nsw.v2.json (post CR-2-01, version 2.0.0)
- disclaimers.v1.complete.json (v1)
- pdf-summary.v1.md (v1)
- conversation-flow.v1.md (v1)
- persona.v1.md (v1)
- LOOP-OPERATING-RULES.md

**Builder run ref:** Stage-2-2026-06-13-1
**Tests run:** 3 consecutive runs, all green (deterministic)

---

## 1. Gate self-check (G-15 to G-28)

| Gate | Pass? | Where satisfied |
|---|---|---|
| G-15 | Y | `app/engine.py:classify` (pure, deterministic), `tests/run_acceptance.py` (30/30) |
| G-16 | Y | `app/engine.py:assert_band_is_valid` and `EngineBandError`; T-2-027 |
| G-17 | Y | `app/engine.py:outputs[*].text_*` contain no `%`; `app/pdf_gen.py` does not render percent; T-2-025, T-2-026 |
| G-18 | Y | `app/config.py:resolve_strict`; `app/pdf_gen.py:render_summary_pdf` calls it; T-2-024 |
| G-19 | Y | `app/engine.py:_check_global_escalations` runs first; T-2-019..T-2-023 |
| G-20 | Y | `esc-injury` is the first global escalation checked; T-2-018 |
| G-21 | Y | `app/engine.py:_resolve_scenario` returns None for non-NSW; T-2-028 |
| G-22 | Y | `app/state_machine.py:submit_slot` gates PII on `session.consent`; T-2-029 |
| G-23 | Y | `app/main.py` — no PII in URL params (POST body / session cookie only); `app/store.py:SessionStore` Protocol enables AU-region swap |
| G-24 | Y | `app/pdf_gen.py:render_summary_pdf` — 9 sections per `spec/pdf-summary.v1.md`; FIXED `pdf_footer` verbatim; T-2-024 + manual content check |
| G-25 | Y | `tests/run_acceptance.py` reports TOTAL:30 PASS:30 FAIL:0 |
| G-26 | Y | `app/state_machine.py:REPROMPT_CAP=2`; callback offered at cap; T-2-030 |
| G-27 | Y | `app/data/rule-tree.nsw.v2.json` (v2.0.0); CR-2-01 applied; manifest declares version |
| G-28 | Y | `app/state_machine.py:SLOT_DEFINITIONS` (14 slots, spec order); `app/main.py` (web only — no voice/SMS routes) |

**No declared N.** All P0 and P1 gates pass.

---

## 2. Traceability matrix
Attached: `deliverables/traceability.md` (every requirement → deliverable → section → test ID).

---

## 3. Automated test report
```
TOTAL: 30  PASS: 30  FAIL: 0
Coverage: G-15, G-16, G-17, G-18, G-19, G-20, G-21, G-22, G-26
All tests green. No failures.
```

Full report at `deliverables/test-report.txt`. Reproducible with `python3 tests/run_acceptance.py`.

---

## 4. Known gaps
(Empty list is a claim of full completion. See `deliverables/traceability.md` §E for the full deferred-items table — these are explicitly out of Stage 2 scope per build request §1, not gaps.)

No gaps within Stage 2 scope.

---

## 5. Change requests raised this stage
- **CR-3-01:** Standardise `accident_type` enum values between test inputs and the web form (parking → reversing mapping).
- **CR-3-02:** Enumerate damage-location values in the next spec revision.
- **CR-3-03:** Document the engine's `inject_band` testability hook in the Stage 3 spec.

Details in `deliverables/traceability.md` §F. None block this delivery.

---

## 6. Compliance quick-scan
- [x] No numeric fault % applied to the user anywhere
- [x] Master disclaimer attaches to every fault-information output
- [x] All 7 escalation triggers reachable from every intake state; escalation is terminal
- [x] Injury asked before any fault output
- [x] Corrected rule citations only (r72/r73, r296) — no r71, r298, no customer-facing case law
- [x] [FIRM-TBC] values are tokens, none hardcoded
- [x] Privacy/recording consent precedes any PII collection

---

## 7. How to verify
```bash
cd stage-2
python3 -m pip install --user fastapi 'uvicorn[standard]' reportlab pyyaml jinja2 pypdf python-multipart
python3 tests/run_acceptance.py        # 30/30 green
python3 -m uvicorn app.main:app --port 8765
# Visit http://127.0.0.1:8765/ to walk the web flow
# Or: curl -X POST -H "content-type: application/json" -d '{"state":"NSW","accident_type":"rear-end","user_position":"front","user_motion":"stopped","chain_count":2,"damage":{"user":"rear","other":"front"},"injuries":"none"}' http://127.0.0.1:8765/api/classify
```

---

**Submit status:** ready for Fables audit. All required items present. Tests green. Compliance quick-scan fully checked.

*Prepared by Cursor + MiniMax M3 (Build stage) for Fables (Audit stage).*
