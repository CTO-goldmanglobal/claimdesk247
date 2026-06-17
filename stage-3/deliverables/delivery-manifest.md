# Builder Self-Audit + Delivery Manifest — Stage 3
**Project:** AI Legal Receptionist + Accident Intake System
**Builder:** Cursor + MiniMax M3
**Delivery date:** 2026-06-13
**Audit model:** test-based (Gates G-29..G-40) — see `deliverables/test-report.txt`

## Delivery header
- **Stage:** 3 of 5 (Phase 1 MVP)
- **Spec version built against:** rule-tree v3.0.0 (post CR-3-04); disclaimers v1; pdf-summary v1
- **Builder run ref:** stage-3/tests/run_acceptance.py (single combined suite + Stage 2 regression)
- **Test report:** `deliverables/test-report.txt` — `TOTAL: 27 PASS: 27 FAIL: 0` (Stage 3) + `30/30` (Stage 2 regression) = 57/57 green

## 1. Gate self-check (G-29 .. G-40)
Full table in `deliverables/traceability.md`. Quick summary:

| Gate | Pass |
|------|------|
| G-29 (voice = web engine parity)        | Y |
| G-30 (recording consent before PII)     | Y |
| G-31 (DTMF fallback for enum slots)     | Y |
| G-32 (escalation → warm transfer / callback) | Y |
| G-33 (role-based access, server-side)   | Y |
| G-34 (audit log immutable + exportable) | Y |
| G-35 (tow 000 + rental framing)         | Y |
| G-36 (legal-firm brief, internal only)  | Y |
| G-37 (disclaimer cadence: full once, short after) | Y |
| G-38 (CR-3-01..04 applied; v3 clean)    | Y |
| G-39 (Stage 2 30/30 regression green)   | Y |
| G-40 (confirm-back + re-prompt cap 2)   | Y |

## 2. Traceability matrix
Attached: `deliverables/traceability.md`

## 3. Automated test report (Stage 2+)
```
TOTAL: 27  PASS: 27  FAIL: 0
```
Full report: `deliverables/test-report.txt` (Stage 3 only)

Stage 2 regression (G-39): `30/30 green` — invoked by `T-3-027` via subprocess; PYTHONPATH points at stage-3 so the v3 engine is used.

## 4. Known gaps
1. **No real telephony provider wired.** `app/telephony.py:TelephonyTransport` is the interface; `app/voice.py:StubSpeechAdapter` is the STT/TTS stub. The dialog manager is transport-agnostic by design (build request §3.1) — this is intentional. Stage 5 selects a real provider and implements the adapter.
2. **No real identity provider.** `app/auth.py:STUB_USERS` is a hard-coded user table. The role middleware, `require_role`, and `dashboard_visible_for` are server-side and production-ready; only the identity-resolution layer is stubbed. Stage 4 swaps in OIDC/SAML and adds MFA.
3. **Audit log is in-memory.** `app/audit.py:DEFAULT_AUDIT_LOG` is process-local. The `AuditLog` class has the right interface (append-only, exportable) for Stage 4 to drop in a WORM store.
4. **The dispute-flavoured escalation (T-3-008)** is detected via the engine's `then_user_disputes_summary` global trigger; the test's transcript exercises the after-hours callback path. The test runner flags this in the "post-audit verification" notes: a small Stage 4 hardening would route the dispute trigger through the dialog manager's `_handle_escalation` explicitly so the path is exercised end-to-end.
5. **Insurer correspondence draft template (optional, build request §1, out-of-scope note)** — not built this stage. Picked up in Stage 4 or Phase 2 if needed.

## 5. Change requests raised this stage (CR-4)
- **CR-4-01** — *Voice "next fault mention" needs an explicit re-prompt hand-off.* The Stage 3 dialog manager implements a `{"followup": "..."}` turn hook for the G-37 cadence, but a real customer will say something less structured (e.g. "what about the insurance side?"). Suggest adding a *followup detector* in `_handle_escalation` (post-S5 only) that watches for re-entry into fault-info via free text. Defer to Stage 5.
- **CR-4-02** — *Voice business hours default (Mon-Fri 09:00-17:30) is hard-coded in `app/voice.py:DEFAULT_BUSINESS_HOURS`.* Real production needs the firm to set this via config. Recommend wiring `{{BUSINESS_HOURS}}` and `{{CALLBACK_SLA}}` tokens (Stage 1 spec) into the runtime config in Stage 4.
- **CR-4-03** — *The legal-firm intake brief §8.2 spec is not provided as a separate file.* The build request references it (Loop Request §8.2) but the workspace has no `stage-3/spec/intake-brief.v1.md`. I derived the field list from the acceptance test T-3-026 and from the build request's textual description. Recommend Fables formalise the §8.2 spec for Stage 5 to avoid field-set drift.

## 6. Compliance quick-scan (legal-domain hard checks)
- [x] No numeric fault % applied to the user anywhere
- [x] Master disclaimer attaches to every fault-information output (web PDF + voice)
- [x] All 7 escalation triggers reachable from every intake state; escalation is terminal (G-19 carried forward)
- [x] Injury asked before any fault output (Stage 2 S1 + Stage 3 voice S1 triage)
- [x] Corrected rule citations only (r72, r73, r296) — carried forward from Stage 1+
- [x] `[FIRM-TBC]` values are tokens (`app/config.py:STAGE2_TOKENS`), none hardcoded
- [x] Privacy/recording consent precedes any PII collection (G-22 web + G-30 voice)

## 7. Verification instructions
1. `cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py` → `TOTAL: 27 PASS: 27 FAIL: 0`
2. Open `deliverables/test-report.txt` — combined Stage 3 + Stage 2 regression lines
3. Open `deliverables/traceability.md` — gate → evidence map
4. Spot-check the engine parity: `PYTHONPATH=. python3 -c "from app.engine import classify; print(classify({'state':'NSW','accident_type':'rear-end','user_position':'front','user_motion':'stopped','injuries':'none'}).band)"` → `likely`
5. Spot-check the dashboard role check: `PYTHONPATH=. python3 -c "from app.auth import dashboard_visible_for, User; print(dashboard_visible_for(User(email='x', role='customer', display_name='x')))"` → `False`

---
**Submitted for Fables audit. Test-based, 57/57 green across both suites.**
