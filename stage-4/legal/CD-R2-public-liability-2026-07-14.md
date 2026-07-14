# CD-R2 — Touting / Claim-Farming Analysis: Public Liability Tree

| Field | Value |
|---|---|
| **Document** | CD-R2 redo — Public Liability (`rule-tree.nsw.pl.v1.json`) |
| **Author** | Legal-Engineering Analyst, ClaimDesk 247 |
| **Date** | 2026-07-14 |
| **Status** | DRAFT for Legal Head review |
| **Tree** | `stage-3/app/data/rule-tree.nsw.pl.v1.json` v1.0.0, hash `dc824c3559ab`, signed 2026-07-05 (provisional) |
| **Operator** | ClaimDesk 247 (the operator entity — `{{OPERATOR_NAME}}` / `{{FIRM_NAME}}` in `stage-3/app/config.py`). Goldman Global Financial Pty Ltd is the smash-repair partner, NOT the operator. |
| **Companion docs** | `item-2b-rule-tree-public-liability.md`; the three-sibling set: `CD-R2-medical-negligence-2026-07-14.md`, `CD-R2-property-damage-2026-07-14.md`; `PD-COUNSEL-MEMO-2026-07-14.md` |

> **Note on comparability.** No standalone motor CD-R2 analysis file was found in the repo. The motor analysis is referenced in the sign-off package prose (`00-INDEX.md` §"Provisional, not final") but never normalised into its own `stage-4/legal/CD-R2-*.md` artefact. The three sibling documents produced today (PL, med-neg, PD) deliberately share an identical structure (regulatory surface → engine conduct → lane → referral fee → recommendation) so that the motor analysis can be retro-fitted to the same template later. Flag for follow-up: normalise motor to `stage-4/legal/CD-R2-motor-<date>.md`.

---

## 1. What this tree decides

The PL sub-tree classifies non-motor personal-injury claims under the **Civil Liability Act 2002 (NSW)** ("CLA") — slip/trip, falling object, inadequate lighting, defective premises, and a catch-all (`pl6-other`). Liability turns on duty of care, breach, the s5B/s5C reasonable-precautions framework, and s5R contributory negligence. The injury IS the claim — there is no "property-only" PL lane. All six scenarios ship escalation-dominant of an injury, and the PL-specific triggers (`esc-vulnerable`, `esc-workers-comp`, `esc-govt-defendant`, `esc-limitation`, plus the shared `esc-injury`, `esc-fraud`, `esc-dispute`, `esc-multiparty`, `esc-advice`, `esc-serious-injury`) route to a human, never monetised per-lead by the engine.

The scenarios emit a band of `likely` / `possible` / `unclear` / `insufficient` only after Legal Head signs the tree hash; before signing, every PL classification escalates as `unsigned-scenario` (CD-E4).

## 2. What counts as "touting" / "claim-farming" for this claim type

PL personal-injury claims sit squarely in the regulatory surface that the claim-farming statutes target — i.e. **Lane 2** in the firm's lane taxonomy. The relevant instruments:

- **NSW Legal Profession Uniform Law (Application) Act 2014 (NSW)** and the **Legal Profession Uniform General Rules 2015**, which adopt the Legal Profession Uniform Law (LPUL) as in force in NSW. LPUL **ss258–263** prohibit the referral of personal-injury/workers-compensation claims for a referral fee and the soliciting of such claims ("claim-farming") in the course of, or in connection with, the provision of legal services. (Section numbers in the ss258–263 range — Legal Head to confirm the exact cross-referenced provision numbers as consolidated, because the LPUL was renumbered on assent of the amending statutes.)
- **Claim Farming Practices Prohibition Act 2025 (NSW)** — the standalone NSW statute referenced in `item-2d` and in `MULTI-STATE-ROLLOUT-PLAN.md`. It is broader than the LPUL: it prohibits the buying, selling, soliciting, or referring of *personal injury claims* (and related work-claim information) **whether or not a law firm is in the chain**, with both civil and criminal consequences. As introduced it targeted CTP injury claims; the policy scope as enacted should be confirmed by Legal Head against the latest consolidated text — in particular whether the definition of "personal injury claim" captures non-CTP injury claims (slip/trip, medical negligence). The conservative assumption for this memo is that **PL personal injury is within the policy intent of the 2025 Act**, regardless of whether every paragraph captures it textually.
- **Civil Liability Act 2002 (NSW)** itself does **not** create a claim-farming or touting offence; it governs the substance of the claim (duty/breach/causation/damage; s5B/s5C; s5O for professionals; s5R contributory negligence; ss15–16 intentional acts; div_provisions for recreational/services). The CD-R2 surface is therefore the LPUL + the 2025 Act, not the CLA itself.

**What "touting" / "claim-farming" means in this lane:**

1. Approaching a person known or suspected to have suffered an injury (or a relative) and offering to refer, introduce, or recommend them to a lawyer / law firm / claims-management business, in exchange for value.
2. Soliciting the details of an injured person from a third party (e.g. a hospital, employer, insurer, repairer) for onward referral.
3. Paying or receiving consideration (money or otherwise) for the referral of a personal-injury claim.
4. Knowingly facilitating (1)–(3) through software, marketing, or intermediary services.

The LPUL offences are framed around legal-services providers and their agents; the 2025 Act extends the surface to non-lawyer intermediaries. **Both apply to an intake/triage tool that touches personal-injury claims** if that tool is paid per-referral or actively solicits injury claimants.

## 3. Where the engine sits relative to that line

**Engine conduct, as built:**

- The engine is an **intake and triage tool**. It does not itself offer legal services, does not solicit, and does not pay or receive consideration for the referral of any PL claim. There is no per-lead, per-referral, or success-fee plumbing in the code path for `claim_type=public_liability`.
- All PL scenarios resolve to a **liability band** (likely/possible/unclear/insufficient) for triage purposes, and **every** substantive PL classification routes to a human reviewer via the shared escalation triggers (`esc-injury`, `esc-serious-injury`, `esc-vulnerable`, `esc-advice`, `esc-fraud`, `esc-dispute`, `esc-govt-defendant`, `esc-workers-comp`, `esc-limitation`).
- The PL intake flow is **inbound only**: the consumer initiates. The engine does not cold-contact injured people, does not scrape hospital/insurer/police data, does not post on social media offering to refer injured people. (This matches the inbound-only rule in `DEMAND-ENGINE-PLAYBOOK-2026-07-05.md` §1.)
- The injury scenarios themselves never auto-monetise: there is no per-referral consideration to any law firm or AMC, and the audit log (`audit_log`) timestamps the consent event (CD-D3) and every escalation event.

**Conclusion on the line:** The PL tree's behaviour as built is **on the right side of the line**, for three independent reasons:

1. **No solicitation.** The engine never initiates contact with an injured claimant. The claim-farming statutes (LPUL ss258–263 and the 2025 Act) target the *solicitation* and the *exchange of consideration* — neither is present.
2. **No consideration.** There is no per-lead or per-referral payment in the PL code path. The absence of consideration is the single most load-bearing fact and must be preserved as a board-level invariant.
3. **The matter does not stay inside the engine.** Every substantive PL classification escalates to a human reviewer; the engine emits a triage band, not legal services. The band is not, of itself, "claim-farming" because it is not a referral and not a solicitation.

**What would move the engine across the line:**

- Introducing per-lead or per-referral fees on PL escalations to a law firm or AMC.
- Adding any outbound contact to people the engine knows or suspects are injured (DMs, comments, scraped contacts).
- Branding or marketing the PL flow as "we will get you compensation" / outcome promises (ACL s18/s29 risk independently — see counsel memo §3).
- Permitting the injury firewall (`esc-injury`) to leak PD→PL→PI without explicit consumer choice.

## 4. Lane classification

| Lane | Includes | Claim-farming ban? | Engine permitted to "handle" end-to-end without a law firm? |
|---|---|---|---|
| **Lane 1 — Property damage only** | Not-at-fault motor property recovery | **No** (out of scope of LPUL ss258–263 and the 2025 Act, both of which target *personal injury*) | **Yes** — the beachhead, see `CD-R2-property-damage-2026-07-14.md` |
| **Lane 2 — CTP injury** | MAIA statutory benefits + common-law | **Yes — criminal** | No — law firm only |
| **Lane 2 — PL personal injury (THIS TREE)** | Civil Liability Act 2002 (NSW) injury claims | **Yes** (within the policy scope of LPUL ss258–263 and the 2025 Act; confirm exact textual scope) | **No** — substantive conduct, settlement, and court filing require a practising certificate under the LPUL; the engine's role is SaaS-to-the-firm triage, not handling |

**PL is Lane 2-adjacent.** The engine's role must stay strictly **SaaS-to-the-firm / triage**, not claims-handling. The Lane 1 commercial model (operate outright, no law firm required) **does not transfer** to PL.

## 5. The referral-fee question for this tree

| Pattern | Lawful? | Notes |
|---|---|---|
| Engine is paid a per-lead fee by a law firm for each PL intake sent across | **NO** — unlawful | Captured by LPUL ss258–263 and the 2025 Act for personal-injury claims. Do not implement. |
| Engine is paid a success/contingency fee per settled PL claim | **NO** — unlawful | Same prohibition; "success fee" is still consideration for a referral of a personal-injury claim. |
| Law firm subscribes to the engine as a SaaS tool and pays a flat software subscription unrelated to volume | **Likely lawful — verify** | The lawyer is buying software, not buying referrals. Confirm structure with counsel: the subscription must not vary with the number of PL leads received, and there must be no "introduction" character to the payment. LPUL **s258** (verify exact number) frames the offence around *referral*; a pure software licence is not a referral. |
| Engine operator refers PL escalations to a panel law firm for **zero consideration**, audit-logged | **Lawful** | This is the firewalled pattern. No consideration either way; the audit log records the absence of payment. This is the only pattern that is unambiguously clean for Lane 2. |
| Repairer / referrer is paid a fee per PL lead by the engine or the law firm | **NO** — unlawful | The same prohibition applies to upstream referrers; the 2025 Act reaches non-lawyer intermediaries. |

**Recommended pattern for PL:** the engine operator (ClaimDesk 247) refers PL escalations to the panel PI firm **for zero consideration**, and the firm licenses the engine as SaaS on a flat subscription unrelated to PL lead volume. The injury firewall (`esc-injury` for the cross-lane PD case; the PL-specific `esc-serious-injury` / `esc-vulnerable` / `esc-govt-defendant` triggers within PL) is the architectural guardrail that keeps this pattern audit-clean.

## 6. Recommendation

**CONDITIONAL GO for live deployment of the PL tree**, subject to the following conditions:

1. **Zero-consideration invariant (board-level).** No per-lead, per-referral, or success fee on any PL matter, in either direction between ClaimDesk 247 and any law firm, repairer, or AMC. This is the single load-bearing condition.
2. **Inbound-only marketing posture.** The marketing surface (web, bot, social, SEO) must not cold-contact injured claimants and must not promise outcomes. The "answer-first" pattern in `DEMAND-ENGINE-PLAYBOOK` §5 is the correct posture.
3. **Lane 1 firewall.** The `esc-injury` trigger (cross-lane, PD→PI) and the in-tree injury escalations (`esc-serious-injury`, `esc-vulnerable`) must remain green in `tests/run_injury_extension.py`. IX-12 (the cross-lane test) is the binding control.
4. **SaaS-subscription structure with the panel firm.** Confirm with the panel firm that the commercial relationship is a flat software subscription (volume-unrelated), not an introduction arrangement. Document the structure in the engagement letter.
5. **Statute confirmation.** Legal Head to confirm the exact consolidated section numbers in the LPUL and the textual scope of the 2025 Act's "personal injury claim" definition (whether it captures non-CTP injury claims). Until confirmed, treat PL as fully within the Lane 2 surface.
6. **ACL / outcome-promise guard.** Customer-facing copy in the PL flow must not promise outcomes. This overlaps with item 1 of the PD counsel memo (`PD-COUNSEL-MEMO-2026-07-14.md` §3) — same ACL s18/s29 surface.

Subject to (1)–(6), the PL tree may be deployed live. The escalation-dominant posture (every substantive PL matter escalates to a human) is what keeps the product defensible.

## 7. Open items for Legal Head

- Confirm exact LPUL section numbers and the 2025 Act's "personal injury claim" textual scope.
- Approve the flat-subscription engagement structure with the panel PI firm.
- Confirm the limitation period for PL matters in NSW (CLA limitation is via the *Limitation Act 1969* (NSW) s50 — generally 3 years from discoverability; the `esc-limitation` buffer of 2.5 years is conservative; verify against the latest consolidated text).
- Confirm whether any PL scenario's "likely"/"possible" band output crosses into the provision of legal advice (CLA s5B/s5C analysis applied to facts) — if so, the band output should be re-characterised as triage only, with copy revisions.

---

*End of CD-R2 — Public Liability analysis. DRAFT for Legal Head review. Operator entity: ClaimDesk 247.*
