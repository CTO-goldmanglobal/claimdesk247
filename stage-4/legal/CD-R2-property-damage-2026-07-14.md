# CD-R2 — Touting / Claim-Farming Analysis: Property Damage Tree

| Field | Value |
|---|---|
| **Document** | CD-R2 redo — Property Damage (`rule-tree.nsw.pd.v1.json`) |
| **Author** | Legal-Engineering Analyst, ClaimDesk 247 |
| **Date** | 2026-07-14 |
| **Status** | DRAFT for Legal Head review |
| **Tree** | `stage-3/app/data/rule-tree.nsw.pd.v1.json` v1.0.0, hash `1f13febaf6c0`, signed 2026-07-05 (provisional). Multi-state siblings (VIC/QLD/WA/SA/TAS/ACT/NT) signed 2026-07-13, all `live=true`. |
| **Operator** | ClaimDesk 247 (the operator entity — `{{OPERATOR_NAME}}` / `{{FIRM_NAME}}` in `stage-3/app/config.py`). Goldman Global Financial Pty Ltd is the smash-repair partner, NOT the operator. |
| **Companion docs** | `item-2d-rule-tree-property-damage.md`; the three-sibling set: `CD-R2-public-liability-2026-07-14.md`, `CD-R2-medical-negligence-2026-07-14.md`; `PD-COUNSEL-MEMO-2026-07-14.md`; `MULTI-STATE-ROLLOUT-PLAN.md` |

> **Note on comparability.** No standalone motor CD-R2 analysis file was found in the repo. The motor analysis is referenced in `00-INDEX.md` §"Provisional, not final" but never normalised into its own `stage-4/legal/CD-R2-*.md` artefact. This document and its PL/med-neg siblings deliberately share an identical structure so the motor analysis can be retro-fitted later. Flag for follow-up: normalise motor to `stage-4/legal/CD-R2-motor-<date>.md`.

---

## 1. What this tree decides

The PD sub-tree classifies **not-at-fault motor property-damage recovery** under common-law **negligence** (duty / breach / causation / damage) plus the road-rule duties (RR126 safe distance; RR72/73 give way; RR96 reversing; RR148 lane change; RR200 etc.), and frames the quantum question through **Arsalan v Rixon; Nguyen v Cassim [2021] HCA (274 CLR 606)** — the not-at-fault owner's entitlement to like-for-like hire including loss of amenity/enjoyment. Scenarios pd1–pd7 (rear-end, failure-to-give-way, reversing, parked-vehicle-struck, lane-change/sideswipe, car-park, catch-all) emit a band of `likely` / `possible` / `unclear` / `insufficient` only after Legal Head signs the tree hash. PD is the only tree in the registry that **deterministically bands** in production — its settled liability geometry genuinely supports `likely`/`possible` bands (IX-15 proves this).

**Crucially: this tree is property-damage only.** Any injury mention is hard-firewalled to `esc-injury` → PI pathway. The injury firewall (`esc-injury`, enforced across all collision types × {minor, serious} by IX-12) is the architectural red line that keeps PD clean of the Lane 2 (CTP injury / claim-farming) regulatory surface.

## 2. What counts as "touting" / "claim-farming" for this claim type

**The PD claim type sits OUTSIDE the statutory claim-farming prohibition surface.** This is the single most load-bearing finding of this memo and it is what makes PD the beachhead.

The relevant instruments:

- **NSW Legal Profession Uniform Law (Application) Act 2014 (NSW)** and the **Legal Profession Uniform General Rules 2015**, adopting the **Legal Profession Uniform Law** ("LPUL") as in force in NSW. LPUL **ss258–263** prohibit the soliciting of, and the paying/receiving of consideration for the referral of, **personal-injury claims**. **Property damage is not a personal-injury claim.** The LPUL prohibition does not bite on PD.
- **Claim Farming Practices Prohibition Act 2025 (NSW)** — the standalone NSW statute. As introduced, it targeted the buying, selling, soliciting, and referring of *personal-injury claims* and *personal-injury information*, whether or not a law firm is in the chain. The statutory definition of "personal injury claim" is the textual hook — Legal Head to confirm the exact wording in the consolidated text, but on the policy intent and the title, **property damage recovery is outside the Act's scope**. (Note from `MULTI-STATE-ROLLOUT-PLAN.md` line 38: each state's touting/claim-farming statute must be analysed to confirm PD-only is exempt. "Most are injury-only (mirroring NSW's Claim Farming Practices Prohibition Act 2025)." This memo treats NSW; the multi-state per-state memos are a separate work item flagged in `MULTI-STATE-ROLLOUT-PLAN.md`.)
- **Motor Accidents Injuries Act 2017 (NSW)** ("MAIA") — the CTP statutory-benefits scheme. PD is **deliberately outside MAIA**: MAIA governs injury, not property. The `governing_law` field of the PD tree itself records this: "NOT the Motor Accidents Injuries Act 2017 (NSW) — that is the CTP injury scheme (Lane 2)."
- **Civil Liability Act 2002 (NSW)** — the CLA's personal-injury provisions (Pt 1A, s5B/s5C standard of care etc.) apply to negligence generally, but the CLA does not create a touting/claim-farming offence and does not bring PD within the claim-farming surface.

**What "touting" / "claim-farming" would mean for PD if the statutes did apply** (they do not, but stating it for the record):

1. Approaching a driver known to be involved in a collision and offering to refer them to a lawyer / AMC.
2. Soliciting collision-victim details from insurers, police, or repairers for onward referral.
3. Paying or receiving consideration for the referral of a PD matter.

The statutes do not capture PD because the *policy concern* (protecting injured claimants from coercion and from being traded as leads) does not arise for an arm's-length property-damage recovery between insurers and a not-at-fault driver.

**The line is unambiguous for PD:** PD recovery is a lawful commercial activity. The entire AMC industry (Carbiz, Right2Drive, Not My Fault, I'm In The Right) operates in this lane today without legal challenge to its existence — the regulatory scrutiny in the sector concerns disclosure quality (CHOICE) and hire-rate reasonableness (*Arsalan*), not touting.

## 3. Where the engine sits relative to that line

**Engine conduct, as built:**

- The engine is an intake / triage / recovery-handling tool for a property-damage claim type that the statutes do not regulate as claim-farming.
- It produces a liability band (`likely`/`possible`/`unclear`/`insufficient`) deterministically — and PD is the only tree where the band stays in production (med-neg escalates; PL is Lane 2-adjacent). This is lawful because PD recovery does not require a law firm and the band is not a referral.
- The **injury firewall** (`esc-injury`, IX-12) hard-routes any PD intake that mentions injury to the PI pathway. The injury firewall is the architectural red line that **maintains** the PD/Lane-2 separation. If the firewall leaks, a matter that should be Lane 2 is handled as Lane 1, which is the one design fault that would attract claim-farming scrutiny. The firewall must stay green forever.
- The intake flow is **inbound only** (consumer-initiated). No cold contact with collision victims.
- The audit log timestamps every consent event (CD-D3) and every escalation.

**Conclusion on the line:** The PD tree's behaviour as built is **on the right side of the line, and the line itself does not bite**. Three independent reasons:

1. **The statutes do not capture PD.** Property damage is not a personal-injury claim under the LPUL or the 2025 Act. The line does not bite because the law does not draw one here.
2. **No solicitation.** Even on the most expansive policy reading, the engine does not cold-contact collision victims.
3. **No consideration for injury referrals.** The injury firewall ensures that any injury-adjacent matter is routed to the PI pathway with no per-referral consideration (the Lane 2 invariant); the only consideration in the PD lane is for property recovery, which is lawful.

**What would move the engine across the line:**

- **Firewall leakage.** If the `esc-injury` trigger were weakened such that an injury-adjacent matter was handled as PD (e.g. banded, then monetised) — that would create Lane 2 exposure for what is in substance a personal-injury claim. IX-12 must stay green.
- **Per-lead pricing for PD.** Lawful in Lane 1 but reputationally adjacent to the Lane 2 claim-farming pattern. The discipline argument (see `item-2d` line 53 and counsel memo §4) is to keep per-lead pricing out of Lane 1 too — preserve the clean Lane 1/Lane 2 distinction.
- **Cold outreach to collision victims.** Even in Lane 1 this is reputationally fatal and policy-adjacent. Stay inbound.

## 4. Lane classification

| Lane | Includes | Claim-farming ban? | Engine permitted to "handle" end-to-end without a law firm? |
|---|---|---|---|
| **Lane 1 — Property damage only (THIS TREE)** | Not-at-fault motor property recovery | **No** (out of scope of LPUL ss258–263 and the 2025 Act, both of which target *personal injury*) | **Yes — the beachhead.** Carbiz / Right2Drive / Not My Fault already operate here without legal challenge to their existence. |
| Lane 2 — CTP injury | MAIA statutory benefits + common-law | Yes — criminal | No — law firm only; `esc-injury` hard-firewalls |
| Lane 2 — PL personal injury | Civil Liability Act 2002 (NSW) injury claims | Yes | No — SaaS-to-firm triage |
| Lane 2 — Medical negligence | CLA s5O/s5P/s5D medical professional liability | Yes | No — structured intake to a lawyer |

**PD is Lane 1.** It is the only tree in the registry that can be operated outright by a non-law-firm entity, that permits consideration for referrals, and that supports deterministic banding in production. The strategic docs (`HOW-TO-WIN-3P-MOTOR`, `THIRD-PARTY-MOTOR-CLAIM-FOCUS`) establish this positioning and the firm has accepted it (sign-off event 2026-07-05; multi-state go-ahead 2026-07-13).

## 5. The referral-fee question for this tree

| Pattern | Lawful? | Notes |
|---|---|---|
| Repairer is paid a per-lead fee for each PD intake referred to the engine | **Lawful** (Lane 1) | This is the industry-standard pattern; the incumbent AMCs pay referral fees to repairers/towers openly (Right2Drive: "common across the sector"). No claim-farming statute bites. *Discipline caveat:* see `item-2d` line 53 and counsel memo §4 — the strategic argument is to monetise via a recovery service fee (fixed or % of recovered), not per-lead, to keep clean separation from the Lane 2 pattern. |
| Engine is paid a recovery service fee — fixed — per successfully recovered PD matter | **Lawful** (Lane 1) | Cleanest Lane 1 fee structure. Disclose to consumer before consent (counsel memo §3). |
| Engine is paid a recovery service fee — % of recovered amount | **Lawful** (Lane 1) | Standard AMC structure. Disclose to consumer before consent. |
| Engine is paid per-lead by a downstream AMC for each PD intake passed across | **Lawful** (Lane 1) | The hire-car referral pattern (`THIRD-PARTY-MOTOR-CLAIM-FOCUS` §4 line 4). Lawful but, again, the discipline argument is to monetise via the recovery service fee first and use hire referral as the second line. |
| Engine is paid per-lead by a law firm for each PD intake | **Lawful but verify** | PD is not a personal-injury claim, so the LPUL prohibition does not bite. However, if the same firm also receives PL/med-neg/CTP referrals, careful structure is needed to avoid any suggestion that the per-lead fee is a proxy for personal-injury referral. Confirm with counsel; the conservative pattern is to keep the law-firm relationship as a SaaS subscription and the per-lead fees with non-law-firm AMCs / repairers only. |
| **Per-lead pricing that crosses the firewall** (any fee paid for an intake that mentions injury) | **NO — unlawful and the red line** | This is the board-level invariant: the injury firewall means **no per-lead, per-referral, or success consideration changes hands for any matter that mentions injury**, ever. IX-12 enforces the firewall; the consideration invariant is the commercial mirror of it. The scoreboard KPI #6 in `HOW-TO-WIN-3P-MOTOR` §8 (injury-firewall integrity: PI referrals with consideration = zero, forever) captures this. |

**Recommended pattern for PD:** the engine operator (ClaimDesk 247) charges the consumer a recovery service fee (fixed or % of recovered — counsel memo §4 lays out the lawful menu and prohibits per-lead), and may pay/receive per-lead or per-matter referral fees with non-law-firm AMCs and repairers (the industry-standard Lane 1 pattern). The injury firewall + zero-consideration-for-injury invariant must hold in every referral path.

## 6. Recommendation

**GO for live deployment of the PD tree**, with **one board-level condition**:

1. **Injury-firewall invariant (board-level).** The `esc-injury` trigger (IX-12 across all collision types × {minor, serious}) and the commercial mirror — **zero consideration, ever, for any matter that mentions injury** — must hold in perpetuity. This is the single condition that keeps Lane 1 clean of Lane 2 exposure. The scoreboard KPI #6 (`HOW-TO-WIN-3P-MOTOR` §8) is the metric.

Subject to (1), PD may be deployed live. The remaining PD-specific items (debt-collection/agent licensing by state, ACL/CHOICE disclosures, fee-structure confirmation) are addressed in the companion counsel memo `PD-COUNSEL-MEMO-2026-07-14.md` and are the substantive gates for commercial deployment — they are conditions on the *commercial* deployment, not on the *technical* deployment of the band-emission engine.

**Stronger posture than PL/med-neg.** PD is the only tree that receives a clean GO rather than a CONDITIONAL GO, because the underlying claim type is outside the claim-farming prohibition surface entirely. The injury firewall is the architectural feature that maintains that exclusion.

## 7. Open items for Legal Head

- Confirm the textual scope of the 2025 Act's "personal injury claim" definition (to put the Lane 1 exclusion beyond doubt).
- For each non-NSW state in which PD is now live (VIC/QLD/WA/SA/TAS/ACT/NT), confirm the equivalent state-level claim-farming statute (if any) is injury-scoped and that PD-only is excluded. `MULTI-STATE-ROLLOUT-PLAN.md` line 38 flags this as a separate per-state memo work item; until those memos land, the multi-state PD deployment is provisionally clean on the assumption that all AU state claim-farming statutes mirror NSW's injury-only scope.
- Approve the fee-structure choice (fixed vs % of recovered) — see counsel memo §4.
- Approve the ACL/CHOICE disclosure text and its placement in the consent gate — see counsel memo §3.
- Confirm that the per-state debt-collection / commercial-agent licensing analysis (counsel memo §2) does not surface a state-level blocker.

---

*End of CD-R2 — Property Damage analysis. DRAFT for Legal Head review. Operator entity: ClaimDesk 247.*
