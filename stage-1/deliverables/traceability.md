# Traceability Matrix — D5
**Project:** AI Legal Receptionist + Accident Intake System
**Maps every Stage 1 requirement (build request §3 and §4) to the artefact and section that satisfies it.**
**Status legend:** PASS = requirement satisfied; PARTIAL = partial coverage noted; OPEN = gap to address at audit.
**Audit date:** 2026-06-13 · **Auditor:** Cursor + MiniMax M3 (Build, self-audit) for Fables (Plan + Audit)

---

## A. Deliverable coverage (build request §3)

| Req ID | Requirement summary | Deliverable | Section / node / key | Status |
|---|---|---|---|---|
| D1 | Mermaid master flow diagram (channel-agnostic core) | `deliverables/flows.md` | §1 Master flow | PASS |
| D1 | Mermaid re-prompt pattern (voice sub-pattern, max 2 re-prompts) | `deliverables/flows.md` | §2 voice variant, after main diagram | PASS |
| D1 | Mermaid voice variant | `deliverables/flows.md` | §2 Voice channel variant | PASS |
| D1 | Mermaid web chat variant | `deliverables/flows.md` | §3 Web chat variant | PASS |
| D1 | Mermaid SMS variant | `deliverables/flows.md` | §4 SMS channel variant | PASS |
| D1 | Mermaid escalation interrupt handling | `deliverables/flows.md` | §5 Escalation interrupt handling | PASS |
| D1 | Mermaid tow sub-flow (S2a) | `deliverables/flows.md` | §6 Tow sub-flow | PASS |
| D1 | Mermaid rental sub-flow (S2b) | `deliverables/flows.md` | §7 Rental sub-flow | PASS |
| D1 | Every state in spec appears in ≥1 diagram; no orphan states; every path terminates | `deliverables/flows.md` | §8 State coverage map | PASS |
| D1 | Slot coverage with re-prompt pattern | `deliverables/flows.md` | §9 Slot coverage | PASS |
| D2 | Rule tree JSON validating against `spec/rule-tree.nsw.v1.json` schema | `deliverables/rule-tree.nsw.v1.complete.json` | top-level `scenarios` (6 scenarios) | PASS |
| D2 | Scenario 1 canonical (from spec) | `rule-tree.nsw.v1.complete.json` | `s1-rear-end` | PASS |
| D2 | Scenario 2 worked to canonical depth | `rule-tree.nsw.v1.complete.json` | `s2-giveway-t` | PASS |
| D2 | Scenario 3 worked to canonical depth | `rule-tree.nsw.v1.complete.json` | `s3-roundabout` | PASS |
| D2 | Scenario 4 worked to canonical depth | `rule-tree.nsw.v1.complete.json` | `s4-lane-merge` | PASS |
| D2 | Scenario 5 worked to canonical depth | `rule-tree.nsw.v1.complete.json` | `s5-reversing` | PASS |
| D2 | Scenario 6 worked to canonical depth | `rule-tree.nsw.v1.complete.json` | `s6-multi-chain` (incl. `n/a_esc_routed` band for 3+ vehicles) | PASS |
| D2 | Human-readable companion for legal firm | `deliverables/rule-tree-review.md` | full document | PASS |
| D2 | Rule citations use corrected numbers from §2 | `rule-tree.nsw.v1.complete.json` | `rule_citations` arrays; uses r72, r73, r114, r126, r148, r149, r296 only | PASS |
| D2 | Bands only: likely / possible / unclear / insufficient (and n/a_esc_routed for s6) | `rule-tree.nsw.v1.complete.json` | `band_logic` and `outputs[*].band` for all 6 scenarios | PASS |
| D2 | No numeric fault percentage in tree outputs | `rule-tree.nsw.v1.complete.json` | verified by grep — zero matches for `\%` or split figures | PASS |
| D2 | References for legal-firm verification (case names) | `rule-tree.nsw.v1.complete.json` + `rule-tree-review.md` | `references_for_legal_verification` | PASS |
| D3 | Persona brief conforming to spec | `deliverables/persona-brief.md` | full document | PASS |
| D3 | Name via `{{PERSONA_NAME}}` token | `persona-brief.md` | every utterance uses token | PASS |
| D3 | ≥20 utterances category (a) greeting/triage | `persona-brief.md` | §3(a) — 22 utterances | PASS |
| D3 | ≥20 utterances category (b) intake | `persona-brief.md` | §3(b) — 22 utterances | PASS |
| D3 | ≥20 utterances category (c) fault info | `persona-brief.md` | §3(c) — 20 utterances | PASS |
| D3 | ≥20 utterances category (d) escalation handoff | `persona-brief.md` | §3(d) — 21 utterances across 4 sub-categories | PASS |
| D3 | ≥20 utterances category (e) legal-advice deflection | `persona-brief.md` | §3(e) — 21 utterances | PASS |
| D3 | ≥15 prohibited utterances | `persona-brief.md` | §4 — 23 entries | PASS |
| D3 | Behavioural rules (8 hard rules) | `persona-brief.md` | §2 | PASS |
| D4 | Disclaimer + framing pack extending spec | `deliverables/disclaimers.v1.complete.json` | `strings` block | PASS |
| D4 | FIXED strings verbatim (master, pdf_footer, sms_constraint, state_scope_guard) | `disclaimers.v1.complete.json` | `strings.master`, `strings.pdf_footer`, `strings.sms_constraint`, `strings.state_scope_guard` | PASS |
| D4 | `master_voice_short` ≤40 words, 4 mandatory elements | `disclaimers.v1.complete.json` | `strings.master_voice_short` (24 words; all 4 elements present) | PASS |
| D4 | `recording_consent` BUILDER_DRAFT | `disclaimers.v1.complete.json` | `strings.recording_consent` | PASS |
| D4 | `privacy_notice` BUILDER_DRAFT, web ≤120 words | `disclaimers.v1.complete.json` | `strings.privacy_notice.text.web` (116 words) | PASS |
| D4 | `escalation_handoff` 4 variants (injury / dispute / advice / complexity) | `disclaimers.v1.complete.json` | `strings.escalation_handoff.variants` | PASS |
| D4 | `session_close` voice + web variants | `disclaimers.v1.complete.json` | `strings.session_close.variants` | PASS |
| D5 | This traceability matrix | `deliverables/traceability.md` | this document | PASS |

---

## B. Acceptance gate coverage (build request §4)

| Gate ID | Gate text (abbreviated) | Satisfied by | Status |
|---|---|---|---|
| G-01 | All 6 scenarios present, each has default pattern + exceptions + 4-band logic + per-band output text | `rule-tree.nsw.v1.complete.json` — `s1` through `s6` all have `default_pattern`, `exceptions[]`, `band_logic[]` (4 entries), `outputs[]` (4 or 5 entries for s6) | PASS |
| G-02 | Rule citations match §2 corrections; zero occurrences of r71, r298, or unverified case names in customer-facing text | Verified by grep on all deliverable files: zero occurrences of `r71` or `r298` in any output string; case names appear only in `references_for_legal_verification` (legal-firm section) and §10 of `rule-tree-review.md` | PASS |
| G-03 | No numeric fault percentage assigned to user's case anywhere in tree outputs, sample utterances, or templates | Verified by grep on all deliverable files: no `%` followed by digits, no `60/40`, `70/30`, `100%` patterns in any customer-facing string; the only `n/a_esc_routed` band in s6 uses qualitative language per the corrected seed | PASS |
| G-04 | Master disclaimer attached to every fault-information output node; voice short-form ≤40 words with all 4 mandatory elements | Every `outputs[*]` entry in `rule-tree.nsw.v1.complete.json` ends with `{{ATTACH:master}}`; `master_voice_short` is 24 words and contains (1) general information, (2) not legal advice, (3) doesn't determine who's at fault, (4) lawyer will review | PASS |
| G-05 | All 7 escalation triggers reachable from every intake state; escalation terminal for AI assessment | `flows.md` §5 shows triggers evaluated on every user turn in S1–S7; SX is terminal in all 4 channel flow diagrams | PASS |
| G-06 | Injury question asked before any fault-information is offered; serious injury → immediate escalation before any other slot | `flows.md` §1, §2, §3 show injury check in S1 (TRIAGE) at session start, before any S3 intake slot; S3 slot 14 confirms; `master` disclaimer not read until S5; `escalation_handoff.injury` variant fires from S1 or S3 | PASS |
| G-07 | Flow has no dead ends; ABANDON path defined (session saved, reference number issued, follow-up SMS state) | `flows.md` §1 master, §2 voice, §3 web, §4 SMS all show S9 ABANDON → save partial (if consented) → reference → SMS follow-up | PASS |
| G-08 | Persona never expresses opinion on fault; legal-advice deflection utterances present and used at every advice-request intercept | `persona-brief.md` §2 rule 1 (hard rule) + §3(e) 21 deflection utterances + §4 prohibited list (23 entries) | PASS |
| G-09 | All `[FIRM-TBC]` values tokenised, none hardcoded | All occurrences of `{{PERSONA_NAME}}`, `{{FIRM_NAME}}`, `{{FIRM_PHONE}}`, `{{CALLBACK_SLA}}`, `{{RETENTION_PERIOD}}`, `{{TOW_PROVIDER_REF}}`, `{{RENTAL_PARTNER_REF}}`, `{{BUSINESS_HOURS}}` are tokens; no hardcoded values found in any deliverable | PASS |
| G-10 | State-scope guard: non-NSW → NSW-only explanation + escalation to callback, no rule-tree entry | `disclaimers.v1.complete.json` `strings.state_scope_guard` (FIXED); `flows.md` §2 and §3 show S3 slot 1 non-NSW → guard string → SX callback, bypassing S4/S5 | PASS |
| G-11 | Traceability matrix complete; every §3 requirement mapped | this document, section A above | PASS |
| G-12 | Channel variants respect constraints: SMS contains no fault/legal content in body (links only); voice confirms each slot back before proceeding | `flows.md` §4 SMS shows links and logistics only; §2 voice shows confirmation readback on every slot ("So that's a white Corolla, rego ABC123 — is that right?"); persona-brief.md §6 documents confirmation patterns | PASS |
| G-13 | Privacy/recording consent states precede any PII slot in every channel variant | `flows.md` §1, §2, §3 all show S0a CONSENT before S3 INTAKE; `disclaimers.v1.complete.json` provides both `recording_consent` and `privacy_notice` strings | PASS |
| G-14 | Plain-English check: any legal term used in customer-facing text is explained inline or listed in glossary; reading level ≤ Year 8 target | All rule tree output strings and persona utterances reviewed inline; legal terms ("give way duty", "duty of care", "zip merge") are explained in their first use within the same string. `rule-tree-review.md` §7 documents the check. | PASS |

---

## C. Spec-binding corrections verified

| Correction | Source | Verified in |
|---|---|---|
| Give way / T-intersection → r72–73 (not r71–72) | build request §2 | `rule-tree.nsw.v1.complete.json` `s2-giveway-t.rule_citations`; `rule-tree-review.md` §3.2 and §10 |
| Reversing → r296 (not r298) | build request §2 | `rule-tree.nsw.v1.complete.json` `s5-reversing.rule_citations`; `rule-tree-review.md` §3.5 and §10 |
| Verified citations r126, r114, r148, r149 | build request §2 | `rule-tree.nsw.v1.complete.json` `s1` and `s3` and `s4` and `s6` `rule_citations` |
| `Solomon v NRMA 2026` and `PXAYL v NRMA 2025` not in customer-facing text | build request §2 | Verified by grep on all output strings; appear only in `references_for_legal_verification` (legal-firm only) and `rule-tree-review.md` §10 |

---

## D. Open items requiring legal-firm confirmation

These are **not gaps in the build**; they are explicit deferrals to the legal firm at sign-off, per the build request §5 and the spec:

1. Persona name: "Alex" is the suggested default; legal firm to confirm or replace. `{{PERSONA_NAME}}` token means no code change required.
2. FIRM_NAME, FIRM_PHONE, CALLBACK_SLA, RETENTION_PERIOD, TOW_PROVIDER_REF, RENTAL_PARTNER_REF, BUSINESS_HOURS — all tokens, resolved at Stage 5 deployment.
3. The two unverified case citations in `references_for_legal_verification` are flagged for the legal firm to confirm or strike at sign-off.
4. Individual persona utterances and rule tree output strings can be rephrased by the legal firm via the change protocol in `rule-tree-review.md` §6.

---

## E. Summary

- **D1 (flows):** 7 diagrams produced, every state covered, no orphan states, escalation reachable from every state, every path terminates in CLOSE/ESCALATE/ABANDON.
- **D2 (rule tree):** 6 scenarios at canonical depth, validated JSON, human-readable companion written for legal review.
- **D3 (persona):** 5 utterance categories at 20+ each, 23 prohibited entries, hard rules documented.
- **D4 (disclaimers):** FIXED strings preserved verbatim, all 5 BUILDER_DRAFT entries completed with word counts checked.
- **D5 (this matrix):** all 5 deliverables traced to requirements; all 14 acceptance gates PASS.

**Ready for Fables audit.** Loop closes on Fables sign-off; one revision cycle expected per build request §4 revision protocol.

---

*End of traceability matrix.*
