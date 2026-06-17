# Conversation Flow Spec v1 — State Machine
**Binding spec for D1.** Builders produce full Mermaid diagrams (`deliverables/flows.md`) covering every state, transition, and interrupt below, per channel.

## 1. States

| State | Purpose | Entry condition | Exits |
|---|---|---|---|
| S0 GREETING | Identify channel + time of day; offer services | Session start | → S0a |
| S0a CONSENT | Recording consent (voice) + privacy notice, **before any PII** | From S0 | accept → S1 · decline → S9-ABANDON (no PII stored) |
| S1 TRIAGE | Safety: injured? safe location? driveable? tow needed now? | Consent given | serious injury → SX-ESCALATE(emergency-first) · minor injury → continue, flag esc-injury · else → S2 or S3 |
| S2 SERVICES | Tow sub-flow (S2a), rental sub-flow (S2b) | Tow/rental needed | → S3 (or S8 if services-only call) |
| S3 INTAKE | Slot collection per §2 below | Triage clear | all mandatory slots OR max-reprompts → S4; any interrupt → SX |
| S4 CLASSIFY | Match to rule-tree scenario; run exception probes | Intake complete | scenario matched → S5 · no match/insufficient → S5 (band=insufficient) |
| S5 FAULT-INFO | Read/show master disclaimer, then band output | Classification done | user disputes → SX-ESCALATE(esc-dispute) · else → S6 |
| S6 EVIDENCE | Checklist, gaps, scene guidance, next-24h guidance | After S5 | → S7 |
| S7 NEXT-STEPS | Callback booking, PDF dispatch, internal brief creation | After S6 | → S8 |
| S8 CLOSE | Reference number, what-happens-next, disclaimer confirm | After S7 (or S2 services-only) | end |
| S9 ABANDON | User drops/declines | Any state | save partial (if consented), issue ref, queue follow-up SMS |
| SX ESCALATE | Human handoff | Any global trigger, any state | business hours → warm transfer · after hours → callback booking + brief flagged urgent |

**Interrupt rule:** the 7 global escalation triggers (rule-tree spec) are evaluated on **every user turn** in every state S1–S7. SX is terminal for AI fault assessment — no path returns from SX to S4/S5.

## 2. Intake slots (S3)

Order fixed. Each slot: validation + max 2 re-prompts → offer human callback.

| # | Slot | Type | Validation | Mandatory |
|---|---|---|---|---|
| 1 | state_of_accident | enum AU states | non-NSW → state_scope_guard string → SX callback | Y |
| 2 | datetime_location | date+time+suburb/intersection | date ≤ today; NSW locality | Y |
| 3 | accident_type | enum: rear-end / roundabout / merge / T-intersection / reversing / parking / other | one of | Y |
| 4 | user_vehicle | make/model/colour/rego | rego format AU | Y |
| 5 | other_vehicles | same fields, "unknown" allowed | — | Y |
| 6 | movement_description | guided free text | stationary/moving + direction prompts | Y |
| 7 | damage_locations | enum multi: front/rear/left/right/multiple — both vehicles | — | Y |
| 8 | control_devices | enum: lights/give-way/stop/roundabout/none | — | Y |
| 9 | police_attendance | yes/no/unsure (+ event number if yes) | — | Y |
| 10 | witnesses | yes/no (+ name/contact) | — | N |
| 11 | dashcam | yours/theirs/neither/unsure | — | N |
| 12 | photos_taken | yes/no (no → prompt now if at scene) | — | N |
| 13 | other_driver_details | name/rego/insurer | "refused/unknown" allowed | N |
| 14 | injuries | none/minor/serious | **asked in S1, confirmed here; serious → SX immediately** | Y |

## 3. Channel variants

| Channel | Differences builders must model |
|---|---|
| Voice | Short turns; confirm each slot back before next; DTMF fallback for slots 1,3,7,8,9; master disclaimer read in full once, short-form thereafter |
| Web chat | Multi-step form with chat wrapper; progress indicator; QR entry pre-loads "I've just had an accident" context (skips S0 offer straight to S0a) |
| SMS | Follow-up/nudge only: post-tow check-in, evidence reminder, PDF link, callback confirmation. No intake, no fault content. Links only |

## 4. Sub-flows (S2)

**S2a Tow:** location (GPS web / verbal-confirm voice) → on-road/car-park/private → hazards (fuel leak, on bend → advise 000 first) → vehicle details → callback number → provide {{TOW_PROVIDER_REF}} → log ref in intake record.

**S2b Rental:** eligibility explainer (fixed framing — entitlement language is general, not advice) → licence details → vehicle class → pickup location → duration → provide {{RENTAL_PARTNER_REF}} → note in intake.
