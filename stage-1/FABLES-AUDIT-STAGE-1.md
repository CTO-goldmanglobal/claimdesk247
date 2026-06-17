# Fables Audit — Stage 1
**Date:** 2026-06-13 · **Auditor:** Fables · **Spec version:** v1
**Delivery:** stage-1/deliverables/ (6 files) + self-audit manifest

## Decision: **LOOP CLOSED (PASS)** — 1 carry-forward fix into Stage 2

All 14 gates verified independently by Fables (not relying on builder self-check). One minor schema-cleanliness deviation found that the builder's self-check did not flag; it is non-blocking and folded into Stage 2 rather than spending a revision cycle.

## Independent verification (re-run, not trusted)

| Gate | Result | Evidence (Fables re-check) |
|---|---|---|
| G-01 6 scenarios at canonical depth | PASS | All 6 have 4 bands, band_logic, exceptions (4–5), damage check |
| G-02 corrected citations, no case law customer-facing | PASS | 0× r71/r298 in output text; cites are r72/r73, r296, r114, r148/149, r126; case names only in `references_for_legal_verification` |
| G-03 no numeric fault % | PASS | 0 matches for `%` or `nn/nn` in any customer-facing string; **no percentage field exists in schema** |
| G-04 disclaimer attach + voice short-form | PASS | Every output ends `{{ATTACH:master}}`; voice short-form = 25 words (≤40), all 4 elements present |
| G-05 escalation from every state, terminal | PASS | flows.md: 7 triggers evaluated from S1–S7; SX has no return path |
| G-06 injury before fault | PASS | S1 TRIAGE serious-injury → SX before S4/S5 |
| G-07 no dead ends, ABANDON defined | PASS | 14 states, no orphans; S9 saves partial, issues ref, queues SMS |
| G-08 persona never opines; advice deflection | PASS | Framing leak scan clean (0 hits across 9 patterns); 23 prohibited entries |
| G-09 [FIRM-TBC] tokenised | PASS | 8 tokens used, no hardcoded values |
| G-10 state-scope guard | PASS | non-NSW → fixed guard string → callback, no band |
| G-11 traceability complete | PASS | All D + G mapped |
| G-12 channel constraints | PASS | SMS links-only; voice confirms slots back |
| G-13 consent before PII | PASS | S0a CONSENT precedes S1 in all channel variants |
| G-14 plain English / glossary | PASS (spot-check) | s2/s1 outputs read at target level; terms explained |

**10% manual spot-check:** read s1 and s2 full output sets and 14 escalation variants by hand — framing is general-information throughout, no conclusion leakage, disclaimer present. Clean.

## Finding F-1 (minor / P1) — carry forward to Stage 2

`s6-multi-chain` adds a 5th output with `band: "n/a_esc_routed"`. The band enum is fixed to `likely | possible | unclear | insufficient`. The intent is correct (3+ vehicles → immediate escalation, no assessment), but modelling it as an out-of-enum "band" inside the `outputs` array breaks the schema contract that Stage 2 will consume — a builder parsing `outputs[].band` could choke on an unexpected value.

**Required fix (do in Stage 2 kickoff, no separate cycle):** remove the pseudo-band from `outputs`; handle 3+ vehicles purely via `escalation_overrides` → SX, using the `escalation_handoff` disclaimer string. The escalation message text the builder wrote is fine — just relocate it out of the band array.

**Why not a revision cycle:** it's a one-field relocation with zero compliance impact. Per Loop Operating Rules §6 (budget tactics), batching a trivial fix into the next stage's work avoids burning a Fables revision pass. Logged as `CR-2-01` for Stage 2.

## Carried to legal-firm sign-off (not Fables' to resolve)
- Persona name (`{{PERSONA_NAME}}`, "Alex" suggested)
- All other tokens resolve at Stage 5
- Two unverified case citations — confirm or strike in `rule-tree-review.md`

## Loop status
Stage 1 closed. Builder's manifest was honest and complete; self-check missed only F-1. No revision cycle spent. Ready for Stage 2.
