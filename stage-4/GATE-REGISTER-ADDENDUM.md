# Gate Register Addendum — loop-integrity & Stage-5 gates
**Prepared by:** Fables (Cowork) · **Date:** 2026-06-14 · **Extends:** the G-01…G-62 gate set + `LOOP-OPERATING-RULES.md` §7.
**Why:** formalise the missing gates found in `LOOP-GATE-COMPLETENESS-REVIEW.md` so a loop cannot *look* closed while actually incomplete.

## P0 — loop-integrity gates (add to Stage-4/5 close conditions)

### G-PROD-LOCK — no unverified legal logic in production
**Pass when:** the production engine serves a scenario **only if** its `legal_signoff == YES` for the deployed rule-tree version. Any scenario with status `*_UNVERIFIED` or `legal_signoff != YES` is forced to **escalate** (human), not banded.
**Test:** deploy a scenario flagged unverified → request a band → engine escalates instead of returning a band.
**Owner:** Eng. **Blocks:** production launch of any new scenario.

### G-VER — sign-off bound to a version hash
**Pass when:** each Legal-Head approval records the **rule-tree version hash** it approved. If the rule tree (any approved scenario/output string/fault rule) changes, affected approvals auto-invalidate and re-enter the Legal-Head queue.
**Test:** edit an approved output string → that scenario's sign-off status flips to `STALE` and it is blocked by G-PROD-LOCK until re-approved.
**Owner:** Eng. **Protects against:** silent drift of approved legal wording.

### G-LH — Legal Head sign-off is a recorded gate
**Pass when:** the per-scenario + global YES/NO from `LEGAL-HEAD-SIGNOFF.md` is captured as structured, dated, attributable records (not just a signed PDF) and is queryable per version.
**Test:** query "what is signed off for v3.1.0?" returns the item-level YES/NO + date + name.
**Owner:** Fables + Legal.

### G-AMEND — amendment-closure / re-audit
**Pass when:** the stage cannot be marked closed while **any** audit finding or Legal-Head **NO** is open. Every NO → change → **re-audited (code)** + **re-confirmed (legal)** before close.
**Test:** an open finding present → close is refused with the list of open items.
**Owner:** Fables. **This is the literal "no incomplete loop" gate.**

## P1 — Stage-5 / operations gates

### G-ROLLBACK — tested reversibility
**Pass when:** a one-step revert to the previous rule-tree/engine version is documented and **proven once** (pin previous version → redeploy → healthz + smoke green). Owner: Eng.

### G-FEEDBACK — human-determination capture
**Pass when:** every escalation/human override logs the final fault determination + reason, in a queryable store that feeds scenario prioritisation, the coverage backtest, and (future) the RAG classifier. Owner: Eng + Legal.

### G-COVERAGE — measured coverage before each scenario batch
**Pass when:** the rule tree is backtested against a sample of historical claims and the measured banded-vs-escalated coverage % is recorded for the release (replaces the indicative 70–85%). Owner: Data.

### G-MONITOR — post-launch drift watch
**Pass when:** production monitors escalation rate, band distribution, and error/5xx rate, with alerts on drift beyond `[thresholds]`. Owner: Ops.

---

## Updated "loop closed" definition (supersedes Operating Rules §7 for Stage 4+)
A stage/loop is **closed** only when: (1) all P0 gates pass **including G-PROD-LOCK, G-VER, G-LH, G-AMEND**; (2) automated test report green + spot-check; (3) traceability complete and **version-matched (G-VER)**; (4) open CRs resolved or named to a later stage; (5) known-gaps list empty or explicitly accepted to Phase 2; (6) **no open audit finding or Legal-Head NO (G-AMEND).**

*Process/config gates — not new product scope. Cheapest insurance against the redo trap.*
