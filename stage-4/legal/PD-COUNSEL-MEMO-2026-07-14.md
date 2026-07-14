# PD-COUNSEL-MEMO — Property Damage Recovery Product (Lane 1 Beachhead)

| Field | Value |
|---|---|
| **To** | Legal Head, Goldman Global |
| **From** | Legal-Engineering Analyst, ClaimDesk 247 |
| **Date** | 2026-07-14 |
| **Re** | Commercial-deployment compliance clearance for the Property Damage (PD) recovery product — debt-collection / agent licensing by state, ACL / CHOICE disclosures, and fee-structure confirmation |
| **Status** | DRAFT for Legal Head review and sign-off |
| **Trigger** | `stage-4/sign-off-package/item-2d-rule-tree-property-damage.md` line 68: "Confirm counsel memo … is in hand BEFORE any live PD deployment." |
| **Operator entity** | **ClaimDesk 247** (`{{OPERATOR_NAME}}` / `{{FIRM_NAME}}` in `stage-3/app/config.py`). Goldman Global Financial Pty Ltd is **not** the operator; Petersham Prestige Smash Repairs is the panel-shop partner for the launch case (`{{PANEL_SHOP_NAME}}`). |
| **Companion docs** | `CD-R2-property-damage-2026-07-14.md` (touting/claim-farming — GO); `CD-R2-public-liability-2026-07-14.md`; `CD-R2-medical-negligence-2026-07-14.md`; `item-2d-rule-tree-property-damage.md`; `EVIDENCE-UPLOAD-DESIGN-2026-07-14.md` |

---

## Executive summary

This memo closes the four commercial-deployment gates itemised in `item-2d` §"Regulatory flags — REQUIRE COUNSEL MEMO BEFORE LAUNCH". The **technical** deployment of the band-emitting PD engine was cleared by the CD-R2 analysis (`CD-R2-property-damage-2026-07-14.md` — **GO**, subject only to the perpetual injury-firewall invariant). This memo addresses the four **commercial** gates that remain before ClaimDesk 247 may take a paying PD customer.

1. **CD-R2 (touting) for PD** — CLEARED. See §1; full analysis at `CD-R2-property-damage-2026-07-14.md`.
2. **Debt-collection / commercial-agent licensing by state** — analysed per state at §2. **NSW, ACT, TAS: GO.** **VIC, WA, SA, NT: VERIFY** (licensing regime or debt-collector definition may capture the recovery-negotiation activity). **QLD: CONDITIONAL GO** (licensing regime bites; engage the QLD process before launch there). No state presents a hard blocker; the question in every case is whether ClaimDesk 247's conduct crosses from *facilitating an arm's-length insurance recovery* into *debt collection as a business* or *legal practice*. See §2.
3. **ACL / CHOICE disclosures** — draft disclosure text and placement specification at §3. **Engineering follow-up:** wire the drafted text into the consent gate and timestamp the disclosure event in the audit log. The text is drafted; the wiring is a flagged task (this memo does not wire it).
4. **Fee-structure confirmation** — lawful Lane 1 menu laid out at §4. **Per-lead pricing for PD is prohibited by policy** (lawful in Lane 1 but disciplined out to preserve the clean Lane 1/Lane 2 separation). The final choice (fixed fee vs % of recovered) is a **Legal Head / operator decision** — this memo does not pick; it lays out the lawful options and the constraint.

**Bottom line:** The PD product is **commercially deployable in NSW today** subject to (a) Legal Head approving the §3 disclosure text, (b) Legal Head / operator picking a §4 fee structure, and (c) the perpetual injury-firewall invariant (zero consideration for any injury-mentioning matter). Multi-state commercial rollout proceeds state-by-state per the §2 table.

---

## 1. CD-R2 (touting / claim-farming) for PD

**Status: CLEARED — GO.**

The full analysis is at `CD-R2-property-damage-2026-07-14.md`. The load-bearing conclusion, restated in one paragraph for completeness:

> The PD claim type sits **outside** the statutory claim-farming prohibition surface. The NSW Legal Profession Uniform Law ss 258–263 and the *Claim Farming Practices Prohibition Act 2025* (NSW) both target **personal-injury** claims; property-damage recovery is not a personal-injury claim and is therefore outside their scope. The engine is inbound-only (no cold contact with collision victims), produces a deterministic liability band (not a referral), and hard-firewalls any injury-mentioning intake to `esc-injury` → PI pathway (IX-12, the board-level invariant). The conduct is on the right side of a line that does not, in any event, bite.

**One board-level condition carried forward from CD-R2:** the injury-firewall invariant — `esc-injury` stays green (IX-12) and **zero consideration, ever, changes hands for any matter that mentions injury**. This condition is referenced throughout this memo and is the commercial mirror of the architectural firewall.

**Open item for Legal Head (from CD-R2 §7):** confirm the textual scope of the 2025 Act's "personal injury claim" definition, to put the Lane 1 exclusion beyond doubt.

---

## 2. Debt-collection / commercial-agent licensing by state

### 2.1 The threshold question — is ClaimDesk 247 "debt collecting"?

ClaimDesk 247, as operator of the PD product, will:

- Intake the not-at-fault driver's accident facts (the engine's band-emission function).
- **Negotiate recovery** of the repair, hire, and towing quantum with the at-fault driver's comprehensive insurer (or the at-fault driver directly if uninsured and the matter stays out of the `esc-uninsured-driver` trigger).
- Recover the amount and remit to the consumer, less the agreed recovery service fee (§4).

The question each state's law asks is whether that middle activity — *negotiating and recovering a debt owed to another person* — is a **licensable debt-collection / commercial-agent activity** in that state, and whether it crosses into the provision of **legal services** under the Legal Profession Uniform Law (the "Uniform Law").

**General principle (all states):** merely *facilitating* an insurance recovery on behalf of a named principal, where the principal remains the decision-maker and the facilitator does not hold themselves out as a law firm and does not conduct litigation in their own name on the principal's behalf, is generally **not** legal practice. The state-by-state variation is in the **debt-collection / commercial-agent** licensing layer, not the legal-practice layer.

### 2.2 Per-state table

| State | Licensing regime that may bite | GO / VERIFY / NO-GO | Notes |
|---|---|---|---|
| **NSW** | No general debt-collector licensing regime. *Property, Stock and Business Agents Act 2002* (NSW) ("PSBA") governs "debt collectors" only in specific contexts; the standalone debt-collection licence that exists in some states **does not exist in NSW**. Uniform Law (NSW) governs legal practice. | **GO** | NSW is the lightest regime. As long as ClaimDesk 247 does not hold out as a law firm and does not conduct litigation without instructions from a solicitor, no NSW licence is required for the recovery-negotiation activity. *Verify:* that the PSBA "commercial agent" definition (if arguable) is not triggered by the recovery-negotiation activity — on its face the PSBA commercial-agent category is narrow; confirm with counsel. |
| **ACT** | No general debt-collector licensing regime mirroring the eastern-states model. *Agents Act 2003* (ACT) is real-estate focused. | **GO (verify)** | Light regime. *Verify:* that no ACT instrument captures the recovery-negotiation activity. Low risk. |
| **TAS** | No general debt-collector licensing regime comparable to QLD/VIC. | **GO (verify)** | Light regime. *Verify:* same as ACT. Low risk. |
| **VIC** | *Agents and Private Investigators Act 2004* (Vic) (or its successor) — Victoria licences **commercial agents / debt collectors**. Whether ClaimDesk 247's recovery-negotiation activity falls within the Victorian "commercial agent" definition is a **verify** item. Uniform Law (Vic) governs legal practice. | **VERIFY** | Engage Victorian counsel to determine whether the recovery-negotiation, as conducted by ClaimDesk 247, requires a commercial-agent licence under the Victorian Act. If it does, obtain the licence before commercial launch in VIC. |
| **WA** | *Debt Collectors Licensing Act 1964* (WA) (or successor) — WA has a debt-collector licensing regime. | **VERIFY** | Engage WA counsel. Determine whether the activity is "debt collecting" within the WA Act; licence if required. |
| **SA** | SA has historically regulated debt collectors; current instrument to be confirmed. | **VERIFY** | Engage SA counsel to identify the current instrument and whether the activity is captured. |
| **NT** | Limited regime; verify current position. | **VERIFY** | Engage NT counsel (or rely on a national firms-of-solicitors opinion) to confirm no capture. Low-to-moderate risk. |
| **QLD** | *Property Occupations Act 2014* (Qld) and the debt-collection / commercial-agent framework administered via OFT Queensland. QLD has a **licensing regime** that is more clearly engaged by debt-collection activity than NSW's. | **CONDITIONAL GO** | QLD is the highest-friction state. Before commercial launch in QLD: (a) determine whether the recovery-negotiation activity requires an OFT licence; (b) if yes, obtain it; (c) if a "no licence needed" opinion is obtained, retain it on file. Do **not** launch commercially in QLD until this is resolved. |

### 2.3 The "legal services" boundary (all states — Uniform Law)

Separate from the debt-collection layer, every state asks whether the activity crosses into **legal practice** regulated by the Legal Profession Uniform Law (NSW/Vic) or the state's Legal Profession Act (elsewhere).

The boundary is generally drawn at:

- **Conducting or instituting court proceedings** on another's behalf.
- **Holding out as a legal practitioner** or law firm.
- **Preparing documents** in contemplation of proceedings in a manner that is more than clerical (the "preparation of documents" limb of legal practice).

**ClaimDesk 247's intended conduct sits on the right side of this boundary** as long as:

1. It does not hold out as a law firm (the operator is "ClaimDesk 247", not a firm name; the footer and disclaimers make this clear per CR-6-01).
2. It does not institute or conduct court proceedings — if proceedings become necessary (e.g. because the at-fault insurer disputes the recovery and Local Court proceedings are required), those proceedings are conducted **by a solicitor instructed by the consumer**, not by ClaimDesk 247. This is the §3 disclosure's whole point: the consumer is told *before consent* that proceedings may be brought **in their name** (by a lawyer they instruct), with potential credit exposure.
3. The **demand letter** product (the Arsalan-cited demand, an intended differentiator) is framed as a commercial recovery demand prepared by or for the principal, not as legal advice. *Engineering note:* when the demand-letter generator is built, its output must carry a "this is a recovery demand prepared on your instructions; it is not legal advice" framing and must not cross into advising the consumer on the merits or on litigation strategy.

**Open item for Legal Head:** confirm the §2.3 boundary analysis — in particular, confirm that the intended demand-letter product, as scoped, does not constitute legal practice. If any feature of the demand-letter product would cross the line, that feature must be re-scoped.

### 2.4 Recommendation

- **Launch commercially in NSW now** (subject to §3 and §4 below and the injury-firewall invariant).
- **Proceed state-by-state** for VIC, WA, SA, NT, ACT, TAS per the verify items; do not market or contract in-of-state until the verify item is cleared for that state.
- **Hold QLD** until the OFT position is resolved.

---

## 3. ACL / CHOICE mandatory disclosures

### 3.1 Why this is mandatory

The third-party motor recovery sector carries a documented trust deficit. CHOICE (and predecessor ACCC/ASIC commentary) has flagged that consumers in the not-at-fault recovery market are routinely **not told** that:

- If the at-fault insurer disputes the recovery, proceedings may need to be brought **in the consumer's name** (the consumer is the principal; the recovery facilitator is not the plaintiff).
- There is therefore potential **credit exposure** for the consumer — an adverse costs order or a disputed liability finding attaches to the named party (the consumer), not to the recovery facilitator.

This is the sector's core trust failure. Mandatory pre-consent disclosure is both:

1. **The compliance posture** — under the *Australian Consumer Law* (Sch 2 *Competition and Consumer Act 2010* (Cth)) ("ACL"), failing to disclose a material matter such as this in a consumer transaction risks contravening **s 18** (misleading or deceptive conduct, by silence) and the **unsolicited consumer agreement / unfair-contract-terms** provisions (ACL Pt 2-3) where applicable. A consumer who later discovers they were the named principal and bore the credit risk, having not been told, has a live ACL complaint. Pre-consent disclosure **closes** that risk.
2. **The market differentiator** — ClaimDesk 247 leads with this disclosure. The competitor AMCs do not. This is the trust signal.

### 3.2 Draft disclosure text (for the consent gate)

The following plain-English block is drafted for placement at the **consent gate** of the PD intake — i.e. it must be presented to the consumer **before** consent is recorded (before any PII is collected or any slot is filled). The audit log must timestamp the disclosure event (the `CD-D3` consent gate already timestamps consent; this disclosure must be a recorded sibling event).

> **Important — please read before you continue.**
>
> ClaimDesk 247 helps you, the not-at-fault driver, recover the cost of your vehicle repairs, a like-for-like hire vehicle, and towing from the at-fault driver or their insurer. We do this as your recovery agent, on your instructions. **You remain the owner of your claim.** This means:
>
> - **You are the principal.** Any recovery is made in your name. If the matter settles, the payment comes to you (less our agreed fee, which we tell you before you agree to anything).
> - **If the at-fault driver or their insurer disputes the claim**, court proceedings — if they become necessary — would be brought in **your name**, conducted by a lawyer you instruct. You would be the plaintiff. That carries a **potential cost risk**: in the rare event a court found against you, you could be liable for some of the other side's costs.
> - **Your credit record could be affected** if a disputed matter is not resolved.
>
> We will tell you at every step what is happening and what your options are. You can stop at any time. If at any point we think you should get independent legal advice, we will tell you so.
>
> This service is **not** legal advice, and ClaimDesk 247 is **not** a law firm.

### 3.3 Placement and engineering requirements

- **Where:** the consent gate of the PD intake flow (`stage-3/app/state_machine.py` — the consent state precedes all PII collection). The disclosure must render above the consent control and must be scrollable-to-acknowledge (or explicitly acknowledged) before the consent action is enabled.
- **Audit:** the disclosure-presented event and the disclosure-acknowledged event must each be written to the immutable audit log (`stage-3/app/audit.py`), timestamped, with the session reference. This is the evidentiary record that the consumer was told — it is what defeats a later "I wasn't told" complaint.
- **Engineering follow-up (flagged — this memo does NOT wire it):** the disclosure text at §3.2 must be added to the PD consent-gate UI, and the two audit events must be added to the consent path. A dedicated engineering task should be raised against this memo. The `EVIDENCE-UPLOAD-DESIGN-2026-07-14.md` doc's consent-gate work is the natural place to fold this in, but they are distinct requirements.

### 3.4 Open items for Legal Head

- **Approve the §3.2 text** (or revise it). The text is drafted to be plain-English and consumer-tested in tone; Legal Head may tighten any limb.
- Confirm whether the disclosure should be **re-presented** at any later point (e.g. immediately before the demand letter is sent, where the "proceedings in your name" limb becomes operative) — recommended, as a second touchpoint reduces the silence risk further.
- Confirm whether an **ACL unfair-contracts review** of the consumer-facing recovery agreement (the terms that attach the fee) is warranted as a belt-and-braces step. Recommended.

---

## 4. Fee-structure confirmation

### 4.1 The lawful Lane 1 menu

The following fee structures are **lawful** for the PD product (Lane 1):

| Structure | Description | Lawful? | Notes |
|---|---|---|---|
| **Fixed recovery service fee** | A fixed dollar amount per successfully recovered matter, charged to the consumer and disclosed before consent. | **Lawful** (Lane 1) | The cleanest structure. Easy to disclose; easy for the consumer to understand; no quantum-contingent alignment. |
| **% of recovered amount** | A percentage of the recovered amount (e.g. of the repair + hire + towing total). | **Lawful** (Lane 1) | The standard AMC structure. Aligns the operator with maximising recovery, which is in the consumer's interest, but must be capped or structured so the consumer always receives the bulk of the recovery. Disclose before consent. |
| **Hybrid (fixed floor + capped %)** | A fixed minimum plus a percentage above a threshold, with an absolute cap. | **Lawful** (Lane 1) | Combines predictability with alignment. Must be disclosed clearly. |

### 4.2 Per-lead pricing — PROHIBITED by policy

**Per-lead pricing for PD is lawful in Lane 1** (the statutes do not bite — see CD-R2 §5), but **ClaimDesk 247 prohibits it by internal policy**. The reason is discipline, not law:

> Per-lead pricing is the signature economic pattern of Lane 2 claim-farming — the thing the *Claim Farming Practices Prohibition Act 2025* (NSW) and LPUL ss 258–263 exist to stop. Even though it is technically lawful in Lane 1, adopting it would (a) blur the clean Lane 1 / Lane 2 separation that is the product's core defensibility, (b) create a perverse incentive to maximise intake volume rather than recovery quality, and (c) invite the reputational association with claim-farming that the product's marketing explicitly positions against.

**Policy rule:** ClaimDesk 247 charges a **recovery service fee** (fixed or % of recovered) — never a per-lead fee — for the PD product. Referral fees paid **to or by** repairers, towers, and non-law-firm AMCs are lawful Lane 1 commerce (the industry-standard pattern) and are permitted; they are a separate economic channel from the consumer-facing recovery fee and must be disclosed where relevant.

### 4.3 The constraint

- The chosen fee structure must be **disclosed to the consumer before consent** (folds into the §3 disclosure regime).
- The structure must never attach any consideration to a matter that mentions injury (the injury-firewall invariant — zero consideration for any injury-mentioning matter, ever).
- The structure must not create an incentive to discourage the consumer from seeking independent legal advice when the engine's escalation triggers fire (`esc-advice`, `esc-dispute`, `esc-fraud`, `esc-uninsured-driver`).

### 4.4 Open items for Legal Head / operator

- **Pick a fee structure** from the §4.1 menu (fixed / % / hybrid). This is a **Legal Head + operator decision**. This memo does not pick — it lays out the lawful menu and the §4.2/§4.3 constraints.
- Confirm the chosen structure complies with §4.3 and that the consumer-facing agreement is ACL-clean (cross-reference §3.4).

---

## 5. Recommendations

1. **Approve commercial deployment of the PD product in NSW**, subject to:
   - (a) approval of the §3.2 disclosure text and the §3.3 wiring task;
   - (b) selection of a §4.1 fee structure;
   - (c) the perpetual injury-firewall invariant (zero consideration for any injury-mentioning matter; IX-12 stays green).
2. **Proceed state-by-state** for VIC / WA / SA / NT / ACT / TAS per the §2.2 verify items; **hold QLD** until the OFT position is resolved.
3. **Raise the engineering follow-up** to wire the §3 disclosure text and audit events into the consent gate (sibling to the evidence-upload consent-gate work).
4. **Confirm the §2.3 legal-practice boundary** — in particular for the future demand-letter product — so that the demand generator does not cross into legal practice when it is built.
5. **Retain this memo and its CD-R2 companion on file** as the commercial-deployment compliance record for the PD product.

## 6. Open items requiring Legal Head decision

| # | Item | Section |
|---|---|---|
| 1 | Confirm the textual scope of the 2025 Act's "personal injury claim" definition (CD-R2 carry-forward). | §1 |
| 2 | NSW PSBA "commercial agent" — confirm not triggered. | §2.2 (NSW) |
| 3 | VIC / WA / SA / NT licensing verify items — engage state counsel or obtain a national opinion. | §2.2 |
| 4 | QLD OFT position — resolve before QLD commercial launch. | §2.2 |
| 5 | Confirm the §2.3 legal-practice boundary, esp. for the demand-letter product. | §2.3 |
| 6 | Approve the §3.2 disclosure text (or revise). | §3.4 |
| 7 | Decide whether to re-present the disclosure before the demand letter is sent. | §3.4 |
| 8 | ACL unfair-contracts review of the consumer-facing recovery agreement. | §3.4 |
| 9 | Pick a §4.1 fee structure (fixed / % / hybrid). | §4.4 |

## 7. Items this memo could NOT resolve, and why

- **The exact current debt-collection / commercial-agent instrument in each of VIC/WA/SA/NT** and the precise scope of the QLD OFT regime. These require either engagement of state counsel or a single national-firm opinion. This memo flags the risk and the action; it does not substitute for that advice. Marked VERIFY / CONDITIONAL GO accordingly.
- **The §4.1 fee-structure choice.** This is a commercial decision for the operator and Legal Head; the memo's role is to lay out the lawful menu and the constraint, not to select.
- **The §2.3 demand-letter boundary.** The demand-letter product is not yet built; the boundary analysis can only be finalised when its feature scope is fixed. This memo sets the guard-rail (no legal advice, no holding-out, no conducting proceedings); the engineering task must implement to that guard-rail.

---

## Sign-off

| Role | Name | Decision | Date |
|---|---|---|---|
| Legal Head, Goldman Global | | ☐ Approved   ☐ Approved with conditions   ☐ Not approved | |
| Operator (ClaimDesk 247) | | ☐ Acknowledged | |

*End of PD counsel memo. DRAFT for Legal Head review. Operator entity: ClaimDesk 247. Prepared by Legal-Engineering Analyst, 2026-07-14. Companion docs: CD-R2-property-damage-2026-07-14.md; item-2d-rule-tree-property-damage.md.*
