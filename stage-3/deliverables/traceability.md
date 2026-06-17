# Stage 3 Traceability Matrix
**Project:** AI Legal Receptionist + Accident Intake System
**Stage:** 3 of 5 (Phase 1 MVP) · **Date:** 2026-06-13
**Builder:** Cursor + MiniMax M3
**Spec versions:**
  - rule-tree: `rule-tree.nsw.v3.json` (v3.0.0, post CR-3-04)
  - disclaimers: `disclaimers.v1.complete.json` (carried forward from Stage 1)
  - pdf-summary: `pdf-summary.v1.md` (carried forward from Stage 2)
  - conversation-flow: `conversation-flow.v1.md` (carried forward from Stage 1)
  - test suite: `acceptance-tests.stage3.yaml` (27 cases, T-3-001..T-3-027)

## Carry-forward CRs verified

| CR | Status | Evidence |
|---|---|---|
| CR-3-01 | applied | `app/engine.py:_normalise_intake_for_scenario` (parking → s5-reversing + location_type=car_park). T-3-017 PASS. |
| CR-3-02 | applied | `app/state_machine.py:SLOT_DEFINITIONS[6]` (damage_locations multienum = [front, rear, left, right, multiple]); T-3-018 confirms free text rejected. |
| CR-3-03 | retained | `app/engine.py:inject_band` testability hook still present; documented in the rule tree spec_change note. |
| CR-3-04 | applied | `app/data/rule-tree.nsw.v3.json` — s6.band_logic[3] replaced with `{when: "chain_count >= 3", route: "esc-multiparty", pre_band: true}`; engine still fail-closed via `assert_band_is_valid`. T-3-019 PASS. |

## Gate self-check (G-29 .. G-40)

| Gate | Pass | Evidence |
|------|------|----------|
| G-29  | Y | `app/voice.py:VoiceDialogManager` drives `app/state_machine.py:submit_slot` and `run_classification`, which itself calls `app.engine.classify` — same function used by the web intake. T-3-001, T-3-002 confirm parity. |
| G-30  | Y | `app/voice.py:run` consumes `{"consent": "yes"|"no"}` *first*; no PII is read before consent. `acknowledge_consent` is called only after the consent turn. T-3-003 (accept) and T-3-004 (decline → non_recorded_or_callback) PASS. |
| G-31  | Y | `app/voice.py:DTMF_SLOTS` provides digit maps for slots 1, 3, 7, 8, 9, 14 (state, accident_type, damage, control_devices, police, injuries). DTMF input is resolved to the same slot value as speech. T-3-005, T-3-006 PASS. |
| G-32  | Y | `app/voice.py:_handle_escalation` routes: business hours → `warm_transfer=True`, after hours → `callback_booking=True`; `brief_flagged_urgent=True` in both. T-3-007, T-3-008, T-3-009 PASS. |
| G-33  | Y | `app/auth.py:dashboard_visible_for` + `app/dashboard.py:_require_dashboard_access` enforce roles server-side (HTTP 403). Customer + anonymous denied, panel_shop_staff + legal_staff + admin allowed. T-3-020..T-3-023 PASS. |
| G-34  | Y | `app/audit.py:AuditLog` overrides `pop/remove/clear/__setitem__/__delitem__` to raise `AuditMutationError`. Dashboard POST `/dashboard/audit/edit` returns 403. Admin export returns JSON with all 5 required fields. T-3-024, T-3-025 PASS. |
| G-35  | Y | `app/aux_flows.py:run_tow_flow` checks hazards *first*; fuel_leak/on_bend/live_traffic → `advise_000=True, advisory_before_continue=True, reference=None`. Rental uses `RENTAL_ELIGIBILITY_GENERAL` (no "entitled" / "you will get" / "they will pay"). T-3-013..T-3-016 PASS. |
| G-36  | Y | `app/intake_brief.py:generate_intake_brief` produces 8 fields (intake_fields, band, rule_refs, escalation_flags, evidence_gaps, recommended_action, verbatim_quotes, tow_rental_status); `customer_facing=False` always; `brief_passes_compliance_scan` checks for fault % and advice phrases. T-3-026 PASS. |
| G-37  | Y | `app/voice.py:_maybe_attach_master` reads `master` full once per session; on a followup turn reads `master_voice_short` (≤ 40 words, 25 words actual). T-3-010 PASS (`master_full=1 short_count=1 short_words=25`). |
| G-38  | Y | All 4 CRs applied; rule-tree version 3.0.0; engine still fail-closed (assert_band_is_valid); band enum clean across `band_logic` and `outputs` (T-3-019 verifies zero out-of-enum bands). |
| G-39  | Y | `tests/run_acceptance.py:_drive_stage2_regression` shells out to `stage-2/tests/run_acceptance.py` with `PYTHONPATH=stage-3` so the v3 engine is used. T-3-027 PASS (`stage2: 30/30 green`). |
| G-40  | Y | `app/voice.py:run` emits a `confirm_back=True` turn after every accepted slot (CONFIRM_BACK dict covers all 14 slots). Re-prompt cap is delegated to the state machine's `REPROMPT_CAP=2`; on cap exceed, session goes to `SX-ESCALATE` with `offered=callback`. T-3-011, T-3-012 PASS. |

## Deliverable map

| Requirement (from STAGE-3-BUILD-REQUEST §1) | Where built |
|---|---|
| Voice channel — text-in/text-out dialog manager, drives state machine | `app/voice.py` |
| Recording consent + privacy before PII | `app/voice.py:run` (S0a stage) |
| DTMF fallback for enum slots | `app/voice.py:DTMF_SLOTS` |
| Confirm-back per slot | `app/voice.py:CONFIRM_BACK` + `_ask` |
| Master disclaimer cadence (full once, short after) | `app/voice.py:_maybe_attach_master` |
| Warm transfer (BH) / callback (after hours) on escalation | `app/voice.py:_handle_escalation` |
| Telephony transport interface (provider-agnostic) | `app/telephony.py:TelephonyTransport` |
| SpeechAdapter (STT/TTS) interface | `app/voice.py:SpeechAdapter` + `StubSpeechAdapter` |
| Tow flow (S2a) | `app/aux_flows.py:run_tow_flow` |
| Tow hazard → 000 advisory | `app/aux_flows.py:run_tow_flow` (hazards-first) |
| Rental flow (S2b) | `app/aux_flows.py:run_rental_flow` |
| Rental eligibility — general-info framing | `app/aux_flows.py:RENTAL_ELIGIBILITY_GENERAL` + `RENTAL_FORBIDDEN_PHRASES` |
| Admin dashboard — panel-shop + legal-firm + audit views | `app/dashboard.py:create_dashboard_app` |
| Role-based access (4 roles, server-side) | `app/auth.py:require_role` + `dashboard_visible_for` |
| Audit log (append-only, immutable, exportable) | `app/audit.py:AuditLog` + `DEFAULT_AUDIT_LOG` |
| Legal-firm intake brief (§8.2) | `app/intake_brief.py:generate_intake_brief` |
| Stage 3 acceptance test runner | `tests/run_acceptance.py` |
| Stage 2 regression | `tests/run_acceptance.py:_drive_stage2_regression` |

## Test report

See `deliverables/test-report.txt` (combined Stage 3 + Stage 2 regression).

## Compliance scan (legal-domain hard checks)

- [x] No numeric fault % applied to the user (verified in `app/intake_brief.py:FAULT_PERCENT_PATTERNS` and `app/pdf_gen.py` — carried forward from Stage 2).
- [x] Master disclaimer attaches to every fault-information output (Stage 2 PDF; Stage 3 voice `_maybe_attach_master`).
- [x] All 7 escalation triggers reachable (carried forward from Stage 2 engine).
- [x] Injury asked before any fault output (Stage 2 S1; Stage 3 voice S1 triage — injuries is slot 14, asked first in the dialog manager).
- [x] Corrected rule citations (r72, r73, r296) — carried forward from Stage 1 rule tree v1+.
- [x] `[FIRM-TBC]` values are tokens (`app/config.py:STAGE2_TOKENS`) — none hardcoded.
- [x] Privacy/recording consent precedes any PII (G-22 web + G-30 voice).

## Out-of-scope (Stage 4/5 / Phase 2)

- AU-region production deployment, MFA, staging QA → Stage 4
- Legal-firm sign-off revisions → Stage 5
- Direct tow-dispatch API, direct rental-booking API, insurer auto-send, vision → Phase 2
- Insurer correspondence draft template (optional this stage — *not built*)
