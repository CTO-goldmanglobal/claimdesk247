# Builder Self-Audit + Delivery Manifest
**Builder (Cursor + MiniMax) completes this and submits it WITH the delivery.**
A delivery missing any required item is returned unopened — this protects your audit budget (Operating Rules §3).

## Delivery header
- Stage: ____   Spec version built against: v__   Delivery date: ____
- Builder run ref: ____

## 1. Gate self-check
For every gate in the stage request, mark and point to evidence:

| Gate ID | Pass? (Y/N) | Where satisfied (file · section/node/test ID) |
|---|---|---|
| G-01 | | |
| G-02 | | |
| … | | |

> Mark N honestly. A declared N is planned around. A hidden N that surfaces in audit burns a full revision cycle.

## 2. Traceability matrix
Attached: `deliverables/traceability.md` — every requirement → deliverable → section. (Required, not optional.)

## 3. Automated test report (Stage 2+)
```
TOTAL: __  PASS: __  FAIL: __
```
Must be green to submit. Paste full report or attach `deliverables/test-report.txt`.

## 4. Known gaps
List anything incomplete and why. Empty list = claim of full completion.
- ____

## 5. Change requests raised this stage
- CR-__-__: <what the spec didn't cover>   (Fables rules on these at audit)

## 6. Compliance quick-scan (legal-domain hard checks — confirm each)
- [ ] No numeric fault % applied to the user anywhere
- [ ] Master disclaimer attaches to every fault-information output
- [ ] All 7 escalation triggers reachable from every intake state; escalation is terminal
- [ ] Injury asked before any fault output
- [ ] Corrected rule citations only (r72/r73, r296) — no r71, r298, no customer-facing case law
- [ ] [FIRM-TBC] values are tokens, none hardcoded
- [ ] Privacy/recording consent precedes any PII collection

> These mirror the P0 gates. If any is unchecked, do not submit — fix first. Cheap to fix now, expensive to fix in audit.

---
**Submit only when:** all required items present, tests green, compliance quick-scan fully checked or gaps declared.
