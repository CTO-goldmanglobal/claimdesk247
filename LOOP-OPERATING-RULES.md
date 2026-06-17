# Loop Operating Rules — Hybrid Development (Budget Edition)
**Project:** AI Legal Receptionist + Accident Intake System
**Applies to:** every stage request in this project. Sits above the individual `stage-N/` folders.
**Issued:** 2026-06-13 · Goldman Forge / Fables

---

## 0. The one idea

Fables time is the expensive resource. Cursor + MiniMax time and automated tests are the cheap resource. **Every rule below moves verification off Fables and onto the cheap stack**, so Fables is spent writing specs and signing off — not catching mistakes a checklist or a test could have caught.

A wasted Fables audit cycle is the most expensive event in this project. The whole point is to have fewer of them.

---

## 1. Revision budget per stage

The source plan's "one revision cycle" is realistic for documents, not code. Budget honestly so you don't either rubber-stamp gaps or blow the timeline:

| Stage | Output | Budgeted Fables audit passes |
|---|---|---|
| 1 | Design docs | 1 audit + 1 revision |
| 2 | Web intake + fault engine + PDF | 1 audit + **2** revisions |
| 3 | Voice + tow/rental + dashboard | 1 audit + **2** revisions |
| 4 | Staging + QA | 1 audit + 1 revision |
| 5 | Sign-off revisions + prod | 1 audit |

**Hard rule:** a revision cycle only begins after the builder passes its own self-audit (see §3) **and** automated tests are green (see §2). Fables does not open a delivery that fails either. This single rule is what keeps the build stages inside their budget.

---

## 2. Audits are test-based from Stage 2, not document-based

Fables cannot verify runtime behaviour (does the disclaimer actually attach? does escalation fire on every turn?) by reading code. So:

- **Fables specifies the test cases** (cheap — written once, in the stage request) as scripted transcripts with expected outcomes. See `templates/acceptance-tests.template.md`.
- **The builder writes and runs the tests** (cheap stack) and submits the green results in the delivery manifest.
- **Fables audits the test report**, then spot-checks ~10% of cases by hand. It does not re-run everything manually.

Tests are free to re-run, so regression is automatic. Re-use the same test IDs across stages — Stage 3 must keep Stage 2's tests green (regression gate). Never rewrite a gate or test that already exists; reference its ID.

---

## 3. Builder self-audit gate (kills wasted cycles)

Before any delivery reaches Fables, the builder completes `templates/self-audit.template.md` and the delivery manifest. The manifest must include:

1. The traceability matrix (every gate ID → where it's satisfied) — **delivered with the build, not requested after**.
2. Green automated test report.
3. A "known gaps" list — anything the builder couldn't complete and why.

A delivery without all three is returned unopened. This costs the builder cheap time and saves Fables expensive time. An honest "known gaps" list is rewarded (Fables plans the revision around it) — a hidden gap that surfaces in audit burns a full cycle.

---

## 4. Spec-change protocol (stops silent baseline rot)

Builders **will** hit cases the spec didn't anticipate. They do **not** patch the spec themselves.

- Builder raises a one-line change request: `CR-<stage>-<n>: <what the spec doesn't cover>`.
- Fables rules on it in the audit (cheap — batched, not real-time) and bumps the spec version (`v1 → v2`) if accepted.
- Every artefact references the spec version it was built against. If versions don't match at audit, that's an automatic finding.

This is why the spec files carry `v1` in their names. Batching change requests into the scheduled audit avoids expensive mid-stage Fables interruptions.

---

## 5. Gate ID continuity

One numbering space for gates across all stages (G-01, G-02, …). A later stage that re-tests an earlier behaviour cites the existing gate ID. The audit checklist is append-only. This keeps the regression surface visible and stops the same thing being re-specified (and re-paid-for) twice.

---

## 6. Budget-specific tactics

- **Front-load Fables into specs, not reviews.** A sharper stage request (worked examples, exact strings, test cases) is the cheapest possible investment — it prevents the builder from guessing, which is what causes revision cycles. The Stage 1 rule-tree already does this with the fully-worked Scenario 1.
- **One consolidated audit per delivery, never trickle reviews.** Don't look at half a delivery. Wait for the manifest, audit once.
- **Spot-check, don't re-do.** 10% manual sample on green tests. If the sample fails, return the whole delivery to the builder — don't fix it inside the audit.
- **Reserve human (lawyer) review for Stage 4/5 only.** It's your one external check and the most expensive sign-off — don't spend it on drafts. Everything before it is internal loop.
- **Keep MiniMax doing volume, Fables doing judgement.** If you find Fables rewriting builder output rather than flagging it, the stage request wasn't specific enough — fix the spec, not the output.
- **Stop-loss:** if any stage hits its revision budget and still fails P0 gates, escalate to a scope decision (cut the failing capability to Phase 2) rather than burning an unbudgeted cycle. Document it as a CR.

---

## 7. Definition of "loop closed" (per stage)

All true, or the loop stays open:
1. All P0 gates pass.
2. Automated test report green; 10% spot-check clean.
3. Traceability matrix complete and version-matched.
4. Open change requests either resolved or deferred to a named later stage.
5. Known-gaps list empty or explicitly accepted into Phase 2.

---

*Prepared by Fables · finn@goldmanglobal.com.au · 2026-06-13*
