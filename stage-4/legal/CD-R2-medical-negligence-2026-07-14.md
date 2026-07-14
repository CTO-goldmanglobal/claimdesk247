# CD-R2 — Touting / Claim-Farming Analysis: Medical Negligence Tree

| Field | Value |
|---|---|
| **Document** | CD-R2 redo — Medical Negligence (`rule-tree.nsw.medneg.v1.json`) |
| **Author** | Legal-Engineering Analyst, ClaimDesk 247 |
| **Date** | 2026-07-14 |
| **Status** | DRAFT for Legal Head review |
| **Tree** | `stage-3/app/data/rule-tree.nsw.medneg.v1.json` v1.0.0, hash `4e4fe60ac4c2`, signed 2026-07-05 (provisional) |
| **Operator** | ClaimDesk 247 (the operator entity — `{{OPERATOR_NAME}}` / `{{FIRM_NAME}}` in `stage-3/app/config.py`). Goldman Global Financial Pty Ltd is the smash-repair partner, NOT the operator. |
| **Companion docs** | `item-2c-rule-tree-medneg.md`; the three-sibling set: `CD-R2-public-liability-2026-07-14.md`, `CD-R2-property-damage-2026-07-14.md`; `PD-COUNSEL-MEMO-2026-07-14.md` |

> **Note on comparability.** No standalone motor CD-R2 analysis file was found in the repo. The motor analysis is referenced in `00-INDEX.md` §"Provisional, not final" but never normalised into its own `stage-4/legal/CD-R2-*.md` artefact. This document and its PL/PD siblings deliberately share an identical structure so the motor analysis can be retro-fitted later. Flag for follow-up: normalise motor to `stage-4/legal/CD-R2-motor-<date>.md`.

---

## 1. What this tree decides

The med-neg sub-tree is **structured intake + near-universal escalation** under the **Civil Liability Act 2002 (NSW)** with the medical-specific provisions: **s5O** (peer professional opinion — the standard of care is judged by reference to peer professional opinion widely accepted by peer professionals), **s5P** (other non-negligence circumstances for professionals), and **s5D** (causation). Scenarios mn1–mn7 capture the fact pattern (surgical outcome, misdiagnosis delay, medication error, birth injury, cosmetic/dental, consent-not-informed, and a catch-all). The design posture, per `item-2c-rule-tree-medneg.md`, is **escalation-dominant**: only hard filters resolve without a human (no harm → `unclear`; outside limitation → `esc-limitation`; not NSW provider → `esc-state-scope`; pure communication complaint → HCCC pathway). **No substantive med-neg scenario ever emits a `likely`/`possible` band, even when the tree is signed.** IX-03 is the test that enforces this property.

Medical negligence is, by definition, a **personal injury claim** (it is a claim for personal injury damages founded on an alleged breach of the professional standard of care). For CD-R2 purposes, it is squarely **Lane 2** and squarely within the claim-farming regulatory surface.

## 2. What counts as "touting" / "claim-farming" for this claim type

The instruments that bear on med-neg are the same as for PL, with two additional overlays:

- **NSW Legal Profession Uniform Law (Application) Act 2014 (NSW)** and the **Legal Profession Uniform General Rules 2015**, adopting the **Legal Profession Uniform Law** ("LPUL") as in force in NSW. LPUL **ss258–263** prohibit the soliciting of, and the paying/receiving of consideration for the referral of, **personal-injury claims** (which includes medical negligence). (Section numbers in the ss258–263 range — Legal Head to confirm the exact consolidated numbering, because the LPUL was renumbered on assent of amending statutes.)
- **Claim Farming Practices Prohibition Act 2025 (NSW)** — the standalone NSW statute. As introduced, it targeted the buying, selling, soliciting, and referring of personal-injury claims and personal-injury information, whether or not a law firm is in the chain, with civil and criminal consequences. The definition of "personal injury claim" in the Act should be confirmed against the consolidated text — but med-neg is the paradigm personal-injury claim and is well within the policy intent.
- **Health Care Complaints Act 1993 (NSW)** and the role of the **Health Care Complaints Commission (HCCC)** — not a touting statute, but it is the alternate pathway the engine uses for pure communication/manner complaints (`esc-hccc` pathway). It is relevant because it correctly diverts a class of intake that is *not* a damages claim away from any referral plumbing.
- **Civil Liability Act 2002 (NSW)** itself does **not** create a touting/claim-farming offence; the CD-R2 surface is the LPUL + the 2025 Act. CLA s5O/s5P/s5D govern the substance of liability.

**What "touting" / "claim-farming" means for med-neg specifically:**

1. Approaching a patient (or family) known or suspected to have suffered harm in the course of medical treatment and offering to refer them to a lawyer.
2. Soliciting patient information from hospitals, practices, or insurers for referral.
3. Paying or receiving consideration for the referral of a med-neg matter.
4. Marketing that induces patients to bring med-neg claims ("if you've been injured by [treatment X], contact us for compensation").

**Med-neg is the highest-sensitivity Lane 2 claim type** — both ethically and legally. The HCCC has a documented record of investigating and publicly identifying parties involved in inappropriate solicitation of patients. The reputational surface is at least as material as the legal surface.

## 3. Where the engine sits relative to that line

**Engine conduct, as built:**

- The engine is an **intake and triage tool**. It does not itself provide legal services, does not pay or receive consideration for med-neg referrals, and does not solicit. There is no per-lead or success-fee plumbing in the med-neg code path.
- The **escalation-dominant design** is the central CD-R2 control for this tree: no substantive med-neg classification emits a `likely`/`possible` band; every substantive matter escalates with `escalation="medneg-requires-assessment"`. The engine therefore **cannot** be characterised as recommending or steering a med-neg claim — it is structuring the case file for a human.
- The hard filters (no harm, limitation, state-scope, HCCC) divert clearly-out-of-scope intake away from any referral pathway.
- The intake flow is **inbound only**. The consumer initiates. No cold contact, no patient-list scraping, no solicitation of any patient, no inducements to bring a med-neg claim.
- The audit log timestamps every consent event (CD-D3) and every escalation.

**Conclusion on the line:** The med-neg tree's behaviour as built is **on the right side of the line**, and **more defensibly so than PL** because of the escalation-dominant design. The reasons are the same three independent invariants as PL:

1. **No solicitation.** The engine never initiates contact with a patient.
2. **No consideration.** No per-lead or per-referral payment in the med-neg code path; absence of consideration is the load-bearing fact.
3. **The matter does not stay inside the engine, AND the engine does not even band it.** Every substantive med-neg classification escalates without a band; IX-03 enforces this property. The engine is structurally incapable of recommending or steering a med-neg claim — it captures intake for a human reviewer.

**What would move the engine across the line:**

- Introducing per-lead or per-referral fees on med-neg escalations.
- Any outbound contact to people known or suspected to have suffered medical harm (DMs, comments, scraped patient lists, "have you been injured by [treatment]?" content).
- Breaching the escalation-dominant design — i.e. allowing any substantive med-neg scenario to emit a `likely`/`possible` band. This is what IX-03 prevents; the test must stay green forever (it is the core safety property for this tree).
- Branding the med-neg flow with outcome promises ("you could receive $X").

## 4. Lane classification

| Lane | Includes | Claim-farming ban? | Engine permitted to "handle" end-to-end without a law firm? |
|---|---|---|---|
| **Lane 1 — Property damage only** | Not-at-fault motor property recovery | **No** | **Yes** (beachhead, see `CD-R2-property-damage-2026-07-14.md`) |
| **Lane 2 — CTP injury** | MAIA statutory benefits + common-law | **Yes — criminal** | No — law firm only |
| **Lane 2 — PL personal injury** | Civil Liability Act 2002 (NSW) injury claims | **Yes** | No — law firm only; SaaS-to-firm triage |
| **Lane 2 — Medical negligence (THIS TREE)** | CLA s5O/s5P/s5D medical professional liability | **Yes** (paradigm personal-injury claim; within LPUL ss258–263 and the 2025 Act) | **No** — substantive conduct, expert evidence, settlement, and court filing require a practising certificate; the engine's role is structured intake to a lawyer, not handling |

**Med-neg is the highest-sensitivity Lane 2-adjacent claim type.** The engine's role must stay strictly **structured-intake-to-the-firm**, not triage that produces a recommendation. The escalation-dominant design is the architectural feature that keeps this true.

## 5. The referral-fee question for this tree

| Pattern | Lawful? | Notes |
|---|---|---|
| Engine is paid a per-lead fee by a law firm for each med-neg intake | **NO** — unlawful | LPUL ss258–263 and the 2025 Act. Do not implement. |
| Engine is paid a success fee per settled med-neg claim | **NO** — unlawful | Same prohibition. |
| Law firm subscribes to the engine as a SaaS tool on a flat subscription unrelated to med-neg lead volume | **Likely lawful — verify** | The lawyer is buying software, not referrals. Confirm the subscription does not vary with med-neg lead volume and has no "introduction" character. |
| Engine operator refers med-neg escalations to a panel med-neg firm for **zero consideration**, audit-logged | **Lawful** | The cleanest pattern. No consideration either way; audit log records the absence of payment. |
| Engine operator refers pure-communication/manner complaints to the HCCC | **Lawful** (and required) | This is the statutory pathway under the *Health Care Complaints Act 1993* (NSW); not a referral for consideration, but a signpost to the regulator. |
| Hospital / practice / referrer is paid a fee per med-neg lead | **NO** — unlawful; **and reputationally catastrophic** | Same prohibition; the HCCC surface adds regulatory scrutiny. Do not implement. |

**Recommended pattern for med-neg:** the engine operator (ClaimDesk 247) refers med-neg escalations to the panel med-neg firm **for zero consideration**, refers pure-communication complaints to the HCCC, and the firm licenses the engine as SaaS on a flat subscription unrelated to med-neg lead volume. The escalation-dominant design is the architectural guardrail.

## 6. Recommendation

**CONDITIONAL GO for live deployment of the med-neg tree**, subject to the following conditions:

1. **Zero-consideration invariant (board-level).** No per-lead, per-referral, or success fee on any med-neg matter, in either direction between ClaimDesk 247 and any law firm, hospital, practice, or AMC.
2. **Inbound-only marketing posture.** The marketing surface must not cold-contact patients and must not promise outcomes. No "have you been injured by [treatment]?" content. The "answer-first" pattern in `DEMAND-ENGINE-PLAYBOOK` §5 applies — but even answer-first content must not induce patients to bring a claim.
3. **Escalation-dominant invariant (board-level).** The IX-03 test (no substantive med-neg scenario emits `likely`/`possible`) must stay green forever. Any future change to the med-neg tree that would emit a band must be treated as a board-level decision and re-signed under CD-E4.
4. **HCCC pathway maintained.** The `esc-hccc` routing for pure communication/manner complaints must remain.
5. **SaaS-subscription structure with the panel firm.** Confirm the flat-subscription structure with the panel med-neg firm.
6. **Limitation-period confirmation.** Confirm the med-neg limitation period with Legal Head — the standard rule is via the *Limitation Act 1969* (NSW) s50, 3 years from discoverability, with the court's discretion to extend (the s50(2) factors and the s60 "just and reasonable" discretion). The `esc-limitation` buffer of 2.5 years is conservative; confirm.
7. **ACL / outcome-promise guard.** Customer-facing copy in the med-neg flow must not promise outcomes or inducements. Same ACL s18/s29 surface as PL/PD.

Subject to (1)–(7), the med-neg tree may be deployed live. The escalation-dominant design is what makes the product defensible — it is the single most important architectural property of this tree.

## 7. Open items for Legal Head

- Confirm LPUL section numbers and the 2025 Act's textual scope.
- Approve the flat-subscription engagement structure with the panel med-neg firm.
- Confirm the med-neg limitation period (Limitation Act 1969 (NSW) s50; s50(2) factors; s60 discretion) — and confirm the 2.5-year buffer is appropriate.
- Review the HCCC signpost copy for compliance with the *Health Care Complaints Act 1993* (NSW).
- Confirm whether any customer-facing output of the med-neg flow (the structured intake question set, the escalation messages) crosses into the provision of legal advice — if so, the copy should be re-characterised as general information only.

---

*End of CD-R2 — Medical Negligence analysis. DRAFT for Legal Head review. Operator entity: ClaimDesk 247.*
