# Stage 4 — End-to-End QA Plan + Go-Live Checklist
**Run against the live staging URL, not local.** Complements the 73 automated tests (which still run via the weblink runner, G-62).

---

## Part A — End-to-end QA journeys (manual + scripted, on staging)

| QA | Journey | Pass condition |
|---|---|---|
| QA-1 | Web intake, rear-end, no injury → `likely` | band shown, disclaimer inline, PDF generates, brief created |
| QA-2 | Web intake, serious injury at triage | escalates before any fault output; warm transfer / callback path |
| QA-3 | Voice intake (transcript harness), give-way unclear | confirm-back each slot; master disclaimer once + short-form; band `unclear` |
| QA-4 | Voice, advice request mid-call | deflected, never answered; routes to human |
| QA-5 | Tow flow, fuel-leak hazard | 000 advisory before continuing; provider ref emitted |
| QA-6 | Rental flow | general-info framing, no "entitled"; partner ref emitted |
| QA-7 | Non-NSW state | state-scope guard, no classification, callback |
| QA-8 | Consent declined | nothing persisted in Supabase (verify by query) |
| QA-9 | Dashboard as customer/anon | denied (DB-level, not just hidden UI) |
| QA-10 | Dashboard as legal_staff w/o MFA | blocked until MFA satisfied |
| QA-11 | Audit log edit attempt | rejected; append-only confirmed at DB |
| QA-12 | Audit log export as admin | full records export |
| QA-13 | CR-4-01: messy real STT phrasing on a follow-up | handled or cleanly re-prompts (no crash, no wrong band) |

Capture: screenshots + the session reference for each, into `stage-4/sign-off-package/qa-evidence/`.

---

## Part B — Go-live gate checklist (all must be ✅ before Stage 5 production)

**Residency (one-way doors — verify, screenshot)**
- [ ] Supabase region = Sydney (ap-southeast-2)
- [ ] Vercel PII functions = `syd1`
- [ ] Azure (when RAG lands) = Australia East — N/A this stage

**Security**
- [ ] CORS locked to exact project slug + production domain — foreign `*.lovable.app` blocked (CR-5-02, G-55)
- [ ] Rate limiting on `/api/session` (CR-5-03, G-56)
- [ ] MFA enforced on all dashboard roles (G-57)
- [ ] RLS verified by query: customer/anon read nothing (G-53)
- [ ] `audit_log` UPDATE/DELETE rejected by policy (G-54)
- [ ] No PII in URLs (re-verified live)
- [ ] `x-test-mode` inert in production (G-59)
- [ ] Service-role key not in client bundle

**Correctness**
- [ ] 99/99 green against deployed API (G-62; Stage 2 30 + Stage 3 50 + Stage 2.5 19; was 87/87 pre-T4/T6/T8, 79/79 pre-T1, 75/75 pre-MFA, 73/73 pre-Stage-2.5). *Verified 2026-06-21 03:10 UTC+10 post-fast-forward.*
- [ ] Supabase adapter passes full suite (G-51)
- [ ] All Part A QA journeys pass (G-58)
- [ ] Carry-in CRs landed: 5-01, 5-04, 4-01, 4-02 (G-60)

**Sign-off package (Loop Request §12)**
- [ ] All 8 items assembled with live evidence (G-61)
- [ ] Insurer-correspondence decision made (build now vs Phase 2 — §7 of build request)
- [ ] §14 open questions logged for Stage 5 token resolution

---

## Part C — Sign-off package index (deliver in stage-4/sign-off-package/)

| # | §12 item | Artefact | Live evidence |
|---|---|---|---|
| 1 | Disclaimer text | disclaimers.v1.complete.json | screenshot on staging screen + voice transcript |
| 2 | Rule tree + framing | rule-tree.nsw.v3.json + rule-tree-review.md | sample classifications |
| 3 | Escalation triggers | 7-trigger list | QA-2/QA-4 evidence |
| 4 | Privacy + consent wording | disclaimers privacy/recording strings | QA-8 evidence |
| 5 | Customer PDF template | live PDF sample | QA-1 PDF |
| 6 | Insurer correspondence draft | template OR "Phase 2" note | per §7 decision |
| 7 | Retention + storage policy | residency evidence + retention setting | region screenshots |
| 8 | Audit log spec | schema + immutability proof + export | QA-11/QA-12 |

The firm conducts **one consolidated review** (Loop Request §12). Revisions are incorporated in one cycle at Stage 5.

---
*Prepared by Fables · 2026-06-13 · Go-live gates are blocking — Stage 5 production does not start until every box is ✅.*
