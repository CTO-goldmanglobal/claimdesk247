# Stage 3 Build Request — Voice · Tow & Rental · Admin Dashboard
**Project:** AI Legal Receptionist + Accident Intake System
**Loop:** Fables (Plan) → Cursor + MiniMax M3 (Build) → Fables (Audit)
**Stage:** 3 of 5 (Phase 1 MVP) · **Issued:** 2026-06-13 · Goldman Forge / Fables
**Consumes:** Stage 2 app (`stage-2/app/`), rule-tree v2, Stage 1 design artefacts
**Governed by:** `LOOP-OPERATING-RULES.md` · test-based audit · single gate-ID space (now G-29+)

---

## 0. Read first
This is the largest build stage — three capabilities at once. Two non-negotiables up front:

1. **Reuse, don't rebuild, the engine.** Voice must call the **same** `classify(intake)` from `app/engine.py`. No second fault engine, no LLM deciding band on the voice path. The voice layer is an adapter that fills the same `intakeRecord` and renders band output as speech. Gate **G-29** + test `T-3-001` enforce this.
2. **The 30 Stage 2 tests stay green** (regression, Operating Rules §2/§5). Your runner must execute Stage 2's suite **and** Stage 3's. A red Stage 2 test fails the whole delivery.

Carry-forward fixes CR-3-01..04 are mandatory — see §2.

---

## 1. Scope

### In scope
1. **Voice channel** — telephony intake running the S0→S8 flow over phone: recording consent at call start, conversational slot capture with confirm-back, DTMF fallback, voice short-form disclaimer reuse, warm transfer / after-hours callback on escalation.
2. **Tow flow (S2a)** — execute the sub-flow from `conversation-flow.v1.md`: location, on-road/car-park/private, hazards (000 advisory), vehicle details, callback number → emit `{{TOW_PROVIDER_REF}}`, log to intake record.
3. **Rental flow (S2b)** — eligibility explainer (fixed general framing, not advice), licence/class/location/duration → emit `{{RENTAL_PARTNER_REF}}`, note in intake.
4. **Admin dashboard** — panel-shop view + legal-firm view + audit-log view, with role-based access (Loop Request §9, §10.5).
5. **Acceptance tests** — implement and pass `acceptance-tests.stage3.yaml`, and keep Stage 2's 30 green.

### Out of scope (Stage 4/5 / Phase 2)
- AU-region production deployment, MFA, staging QA → Stage 4
- Legal-firm sign-off revisions → Stage 5
- Direct tow-dispatch API, direct rental-booking API, insurer auto-send, vision → Phase 2 (MVP emits reference numbers only)
- Insurer correspondence draft template is **optional** this stage; if built, framing rules apply

---

## 2. Carry-forward fixes (mandatory)

| CR | Fix |
|---|---|
| CR-3-01 | `accident_type: parking` maps to scenario `s5-reversing` with `location: car_park` set. Apply in both web and voice intake. |
| CR-3-02 | Damage-location values enumerated to `front \| rear \| left \| right \| multiple`. No free text on either channel. |
| CR-3-03 | Keep & document the `inject_band` engine hook (it backs `T-2-027`). Do not remove. |
| CR-3-04 | In `s6.band_logic`, replace the `n/a_esc_routed` annotation with a band-less routing flag (`{ "when": "chain_count >= 3", "route": "esc-multiparty", "pre_band": true }`). Bump to rule-tree v3; engine still fail-closed. |

---

## 3. Implementation constraints (implementation-ready)

### 3.1 Voice architecture
- **Separate the dialog manager from the telephony transport.** Build a `VoiceDialogManager` that consumes text turns (STT output) and emits text turns (for TTS) by driving the **same state machine** used for web. Telephony (Twilio or equivalent) is a thin transport adapter behind an interface, so the dialog logic is testable **without** real audio or a phone line. This is what makes the voice acceptance tests possible and cheap.
- STT/TTS provider: pluggable behind `SpeechAdapter`. Australian English. Provider selection is a config choice, **not** hardcoded.
- **Recording consent** (`recording_consent` FIXED-draft string) is spoken first, before any other content or PII. Decline → no recording, continue with a non-recorded path or callback per firm policy `{{BUSINESS_HOURS}}`/`{{CALLBACK_SLA}}` (token-driven).
- **DTMF fallback**: for enum slots (state, accident_type, damage, controls, police, injuries) accept keypad input mapped to options. Every voice enum prompt must have a DTMF mapping.
- **Confirm-back**: voice confirms each captured slot before advancing (Stage 1 persona rule 6).
- **Disclaimer**: full `master` read once per call; `master_voice_short` (≤40 words) thereafter.
- **Warm transfer**: on any escalation trigger during `{{BUSINESS_HOURS}}` → warm transfer to nominated human; after hours → voicemail + callback booking + brief flagged urgent. Escalation remains terminal for AI assessment.

### 3.2 Tow & rental
- Both are deterministic slot-collection flows; no fault logic. Reuse slot-validation + re-prompt-cap-2 pattern.
- Tow hazard answer `yes` (fuel leak / on a bend) → advise calling 000 first **before** continuing (safety precedence; same priority as serious injury).
- Rental eligibility explainer is **general information**, not advice — it must pass the same `framing_rules` as fault output (no "you are entitled", use "you may be entitled / a lawyer can help pursue this").
- Outputs are reference numbers/tokens only this stage (no live dispatch/booking).

### 3.3 Admin dashboard
- Two role views (panel-shop, legal-firm) + audit-log view, per Loop Request §9.
- **Role-based access (G-33):** `customer` (no dashboard), `panel_shop_staff`, `legal_staff`, `admin`. No intake data reachable without authentication. Enforce server-side, not just UI hiding.
- **Audit log (G-34):** every intake session already logs timestamp, session ID, inputs, rule-tree path, output (Stage 2 store). Dashboard exposes a **read-only** view; log remains append-only/immutable. Exportable by legal-firm admin.
- Panel-shop view: list (date, customer, scenario, band), open summary, status tags (referred-insurer / referred-legal / resolved / on-hold), PDF download, notes.
- Legal-firm view: same list + intake brief (Loop Request §8.2 — build the brief generator here), assign-to-lawyer, callback notes, follow-up flag, audit-log view.
- **Legal-firm intake brief (§8.2)** is new this stage: structured fields + band + rule refs + escalation flags + evidence gaps + recommended action + verbatim key quotes + tow/rental status. Internal only, never customer-facing; framing rules still apply to any narrative text.

### 3.4 Data / privacy
- Voice recording consent + privacy notice precede PII (same gate family as Stage 2 G-22, now also voice).
- No PII in URLs (dashboard included).
- Store stays behind the `SessionStore` Protocol (AU-region swap is Stage 4).

---

## 4. Acceptance gates (Fables audit) — P0 must pass

| ID | Gate | Pri |
|---|---|---|
| G-29 | Voice path calls the same `classify()`; identical intake → identical band on voice and web (no divergent engine) | P0 |
| G-30 | Recording consent spoken before any PII on voice; decline → no recording, no PII persisted | P0 |
| G-31 | Every voice enum slot has a DTMF mapping; DTMF input produces same slot value as speech | P1 |
| G-32 | Escalation on voice → warm transfer (business hrs) or callback+urgent brief (after hrs); terminal for AI assessment | P0 |
| G-33 | Role-based access enforced server-side; no intake data without auth; customer role cannot reach dashboard | P0 |
| G-34 | Audit log read-only in dashboard, remains append-only/immutable; legal-firm export works | P0 |
| G-35 | Tow hazard `yes` → 000 advisory before continuing; rental eligibility uses general-info framing (no "entitled") | P0 |
| G-36 | Legal-firm intake brief (§8.2) contains all required fields; never customer-facing; no fault % | P1 |
| G-37 | Voice disclaimer: full master once per call, short-form (≤40 words, 4 elements) thereafter | P0 |
| G-38 | CR-3-01..04 applied; rule-tree v3; engine still fail-closed; band enum clean in outputs AND band_logic | P1 |
| G-39 | **Regression: all 30 Stage 2 tests green** | P0 |
| G-40 | Confirm-back on every voice slot; re-prompt cap 2 → callback (no voice dead-ends) | P1 |

---

## 5. Acceptance tests
- File: `stage-3/acceptance-tests.stage3.yaml`, IDs `T-3-001`…, plus the runner must invoke Stage 2's suite for G-39.
- Voice cases run through `VoiceDialogManager` as **text transcripts** (STT/TTS stubbed) — deterministic, no audio.
- Green (0 failures across both suites) required before submit.

---

## 6. Delivery manifest (Operating Rules §3) — required or returned unopened
Gate self-check (G-29…G-40) · traceability · **combined** test-report (Stage 2 + Stage 3 green) · known-gaps · CRs (`CR-4-xx`) · compliance quick-scan.

---

## 7. Budget note
Biggest stage = biggest revision risk. Two specific cost controls: (a) the dialog-manager/transport split means voice is tested as text — you never burn cycles debugging audio to prove logic; (b) reusing `classify()` means zero new fault-logic to get wrong, so the voice fault path is correct by construction (G-29 just proves you didn't fork it). Revision budget: 1 audit + up to 2 revisions; green-both-suites-before-submit targets first-audit closure.

---

*Prepared by Fables · finn@goldmanglobal.com.au · 2026-06-13*
