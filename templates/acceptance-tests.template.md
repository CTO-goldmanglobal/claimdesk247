# Acceptance Test Template
**Used from Stage 2 onward.** Fables writes the cases into the stage request; the builder implements them as automated tests and submits a green report. Audits read the report, not the code.

## How it works
- Each case is a scripted conversation: fixed user inputs → expected machine outcome.
- Outcomes are checked against **observable facts** (which band, which escalation, was disclaimer attached, which state reached) — not wording quality.
- Tests are deterministic and free to re-run, so every later stage keeps every earlier test green (regression).
- Test IDs are permanent and shared across stages. Never renumber.

## Case format

```yaml
- id: T-<stage>-<nnn>
  gate: G-XX            # the audit gate this proves
  scenario: rear-end    # rule-tree scenario or flow area
  inputs:               # ordered user turns
    - "I was stopped at lights and got hit from behind"
    - state: NSW
    - injuries: none
  expect:
    band: likely
    disclaimer_attached: true
    escalation: none
    end_state: S8-CLOSE
```

## Mandatory case coverage (Fables specifies; builder must not skip)

| Area | Min cases | Must include |
|---|---|---|
| Each rule-tree scenario | 4 each (1 per band) | the worked Scenario 1 cases as fixtures |
| Escalation triggers | 1 per trigger (7) | serious injury fires **before** any fault output; dispute mid-flow; advice request |
| State-scope guard | 2 | non-NSW → guard string + callback, no band assigned |
| Disclaimer attach | every fault-output case | `disclaimer_attached: true` asserted, all bands |
| No-percentage rule | 3 | assert output contains no digit-% pattern applied to the user |
| Dead-end / abandon | 2 | drop mid-intake → ref issued, follow-up queued |
| Channel constraint | 2 | SMS body contains no fault/legal content |

## Report format (goes in delivery manifest)
```
TOTAL: <n>  PASS: <n>  FAIL: <n>
Failures: <T-id>: expected <x> got <y>
Coverage: <gate IDs exercised>
```
**Green = zero failures.** A delivery with any red test is returned before audit (Operating Rules §3).
