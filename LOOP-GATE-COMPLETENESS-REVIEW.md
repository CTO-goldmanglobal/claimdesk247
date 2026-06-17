# Loop Gate-Completeness Review — "no incomplete loop"
**Prepared by:** Fables (Cowork, planning seat) · **Date:** 2026-06-14
**Why:** the loop only stays in flow if every stage *closes completely*. A missing gate is how a loop *looks* closed but isn't — and that's the trap that later forces a redo and kills momentum. This is the planning pass to find those holes now.

## The loop, as it actually runs
```
PLAN (Fables, expensive model)
   → BUILD (Cursor/MiniMax)
   → CODE AUDIT (Opus, test-based — every audit is code/tests)
   → AMENDMENT (fix the NOs)
   → RE-AUDIT (Opus)
   → LEGAL HEAD (human: YES/NO on substance, not code)   ← the gate just added
   → CLOSE stage → next loop
```
Two review layers, correctly separated: **code audit = is it built right** (automated, testable); **legal head = is it legally right** (human yes/no). Good. The gaps are at the *seams* between them.

---

## Gates that EXIST and hold
Stage 4 gate set G-50…G-62 (deploy, AU residency, RLS, append-only, CORS, rate-limit, MFA, regression 75/75, sign-off package). These are solid and now mostly green.

## Gates that are MISSING (the holes that cause "incomplete loop")
Ordered by risk. P0 = add before the next loop closes; P1 = add this stage.

| ID | Missing gate | The hole it closes | Owner | Pri |
|----|--------------|--------------------|-------|-----|
| **G-LH** | **Legal Head sign-off is a recorded gate** | Today sign-off is a *package*, not a tracked gate. Make the per-scenario YES/NO a formal gate output, stored, and **bound to a rule-tree version** (below). | Fables + Legal | **P0** |
| **G-PROD-LOCK** | **No unverified legal logic reaches production** | A scenario marked `…_UNVERIFIED` is only a *field* today — nothing physically stops it serving real users. Needs a hard gate: production refuses any scenario whose legal-sign-off ≠ YES for the deployed version. | Eng | **P0** |
| **G-VER** | **Sign-off bound to a version hash** | Legal approves *v3.1.0*. If anyone later edits an approved output string or fault rule, the approval must auto-invalidate and re-trigger Legal Head. Without this, approved legal wording can silently drift. | Eng | **P0** |
| **G-AMEND** | **Amendment-closure / re-audit gate** | The loop must not close while any audit-finding or legal NO is open. A gate that says: every NO → change → **re-audited (code) + re-confirmed (legal)** before close. This is literally the "no incomplete loop" gate. | Fables | **P0** |
| **G-ROLLBACK** | **Tested rollback** | If a bad rule-tree/engine version ships, you need a one-step revert (pin previous version + redeploy), proven once. Momentum-safe: a bad deploy pauses nothing — you roll back and continue. | Eng | P1 |
| **G-FEEDBACK** | **Human-determination capture (the flywheel)** | Every escalation/human override should log the final fault determination → feeds (a) which scenario to build next, (b) the coverage backtest, (c) RAG training. Without it the hybrid loop never learns and "coverage" stays a guess. | Eng + Legal | P1 |
| **G-COVERAGE** | **Backtest before each scenario batch ships** | Replace the indicative 70–85% with a measured number against historical claims, each release. Ties "measure, don't guess" into the gate set. | Data | P1 |
| **G-MONITOR** | **Post-launch drift watch** | Monitor escalation rate, band distribution, error/500 rate; alert on drift. A live legal engine that silently shifts its band mix is a quiet failure. | Ops | P1 (Stage 5) |

---

## What this protects (your principle, made mechanical)
- **Right direction up front** → the PLAN gate (expensive model) is already where the spend goes. Keep it.
- **Flow / no stops** → G-ROLLBACK + G-PROD-LOCK mean a problem *reverts or is blocked at the edge*, it doesn't halt the pipeline.
- **No incomplete loop** → G-AMEND makes "all NOs resolved + re-audited" a literal close condition; G-LH + G-VER make legal approval permanent and version-true, so a loop can't *look* closed while approval is stale.
- **Legal = yes/no, never coding** → G-LH records the human decision; every change is implemented by the dev loop, then re-presented as a single changed item for final YES.

## Recommended next action (one loop)
1. Add **G-PROD-LOCK + G-VER + G-LH + G-AMEND** to the Stage-4/5 gate list (P0) — these four are the "incomplete-loop" guards.
2. Legal Head runs the sign-off packet on the **6 LIVE** scenarios → unlocks Stage 1 launch.
3. On YES for the **9 PROPOSED**, dev loop builds them (engine band-functions + tests), Opus re-audits, version bumps to 3.1.0, sign-off re-bound to that version.
4. Add G-ROLLBACK + G-FEEDBACK + G-COVERAGE + G-MONITOR into Stage 5.

*Planning artifact. The four P0 gates are the cheapest possible insurance against the redo trap — they're process/config, not new product scope.*
