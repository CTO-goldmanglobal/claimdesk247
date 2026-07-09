# Item 2c — Medical Negligence Rule Tree (rule-tree.nsw.medneg.v1.json)

Personal-injury extension (spec: `claimdesk-injury-extension-INSTRUCTIONS-2026-07-03.md`, Part 3).

## Design posture — ESCALATION-DOMINANT

Medical-negligence liability turns on **breach of the standard of care** judged by *peer professional opinion* (NSW Civil Liability Act **s5O**) plus **causation** (s5D). **You cannot deterministically band a standard-of-care breach from a questionnaire** — it requires expert medical evidence.

So this sub-tree is **structured intake + near-universal escalation**, with only hard filters that rule cases out:
- No injury/harm at all → `unclear` band (no compensable damage) — still human-reviewed.
- Outside limitation window → `esc-limitation`.
- Not a NSW provider → `state-scope`.
- Pure communication/manner complaint → HCCC pathway + escalation.

Everything else → `escalation="medneg-requires-assessment"`. **A substantive med-neg matter is never auto-banded.**

## Builder evidence (CODE)

- `stage-3/app/data/rule-tree.nsw.medneg.v1.json` (v1.0.0, claim_type=medical_negligence)
- Scenarios: mn1-surgical-outcome, mn2-misdiagnosis-delay, mn3-medication-error, mn4-birth-injury (always serious-injury), mn5-cosmetic-dental, mn6-consent-not-informed, mn7-other (catch-all → escalation)
- Engine: `_resolve_scenario(claim_type=medical_negligence)`, band helper returns `"unclear"` for all mn scenarios (never likely/possible)
- State machine: `stage-3/app/state_machine.py` — `MEDNEG_SLOTS` (ids 300-309)
- Per-tree hashing: bound to this tree's own hash; independent of motor and PL.

## Hard test — escalation-dominance (must stay green)

`tests/run_injury_extension.py::IX-03` asserts that NO med-neg substantive scenario emits a `likely`/`possible` band, even if the tree were fully signed. This is the defensible posture. A med-neg product that emits liability bands from a questionnaire is a liability risk to the operator and the firm.

## Ship posture — escalate-everything until signed

Every med-neg scenario ships unsigned. Until Legal Head signs this tree's hash, every med-neg classification returns `escalation="unsigned-scenario"`. Even after signing, the substantive scenarios still escalate (`medneg-requires-assessment`) — signing only removes the unsigned-scenario gate, it does NOT enable auto-banding.

## What Legal Head is signing

- The intake question set (structured capture for the lawyer's case file).
- The hard filters (no-harm, limitation, state-scope, HCCC pathway).
- The escalation-dominant posture itself — i.e. confirmation that banding standard-of-care from a questionnaire is not attempted.
- The draft output text.

## Regulatory flags — REQUIRE SEPARATE SIGN-OFF

- **Different Act.** Med-neg is Civil Liability Act 2002 (esp. s5O peer professional opinion, s5D causation), NOT the Motor Accidents Injuries Act.
- **CD-R2 (touting) MUST be redone for med-neg.** The motor CD-R2 analysis does NOT cover medical-negligence claims. Do not assume the motor CD-R2 sign-off covers med-neg.
- **s5O standard of care is expert-evidence territory.** The escalation-dominant design is what keeps the product defensible.
- **Limitation periods differ** from motor CTP — `esc-limitation` (buffer 2.5 yrs). Confirm exact period.

## Deployer evidence (capture against staging)

- [ ] `/healthz` reports `rule_tree_versions.medical_negligence = {version: "1.0.0", signed: 0, live: false}`.
- [ ] Sample med-neg intake (hospital, surgical-outcome, serious harm) → `unsigned-scenario` (pre-sign).
- [ ] `mn4-birth-injury` intake → always `esc-serious-injury` (regardless of sign state).
- [ ] Med-neg intake with public hospital → `esc-govt-defendant`.
- [ ] Med-neg intake with incident > 2.5 yrs ago → `esc-limitation`.
- [ ] Run `tests/run_injury_extension.py` IX-02, IX-03, IX-04 and attach output.
- [ ] **IX-03 (escalation-dominance) MUST stay green** — it is the core safety property.

Status: [ ] Pending capture    [ ] Captured
