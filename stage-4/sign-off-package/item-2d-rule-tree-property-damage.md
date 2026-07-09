# Item 2d — Property Damage Rule Tree (rule-tree.nsw.pd.v1.json)

Demand-Engine / Lane 1 beachhead (spec: `THIRD-PARTY-MOTOR-CLAIM-FOCUS-2026-07-05.md` §3-4, `HOW-TO-WIN-3P-MOTOR-2026-07-05.md`). This is the not-at-fault motor **property damage** recovery product — Lane 1 — distinct from the CTP **injury** scheme (Lane 2 / MAIA).

## Governing law

Common-law **negligence** for the liability question, plus **Arsalan v Rixon; Nguyen v Cassim [2021] HCA** (274 CLR 606) for the like-for-like hire / recovery question. NOT the Motor Accidents Injuries Act 2017 (NSW) — that is the CTP injury scheme (Lane 2) and is firewalled off by `esc-injury`.

- Duty of care + breach + causation + damage (standard negligence).
- Road-rule duties: RR126 (safe distance), RR72/73 (give way), RR96 (reversing), RR148 (lane change).
- Arsalan: the not-at-fault owner recovers like-for-like hire **including loss of amenity/enjoyment**, not bare "use". Disputes now fight on reasonableness of rate / duration / mitigation — a case-law + quantum problem the Legal Engine is built for.

## Lane classification (the firewall that makes this product legal to own outright)

| Lane | What it is | Claim-farming ban? | Non-law-firm "handle the case"? |
|---|---|---|---|
| **Lane 1 — Property damage (this tree)** | Not-at-fault driver recovers repair + hire + towing from at-fault driver / their comprehensive insurer | **No** — outside the NSW Claim Farming Practices Prohibition Act 2025 (injury only) | **Yes** — Carbiz, Right2Drive, Not My Fault already do, no law firm required |
| Lane 2 — CTP injury | MAIA statutory benefits / common law | **Yes — criminal** | No — law firm only; `esc-injury` hard-firewalls any PD intake mentioning injury to the PI pathway |

**Red line (board-level):** any injury mention in a PD intake routes to `esc-injury` → PI pathway, never monetized per-referral. Enforced by IX-12 across all collision types × {minor, serious}.

## Builder evidence (CODE)

- `stage-3/app/data/rule-tree.nsw.pd.v1.json` (v1.0.0, claim_type=property_damage)
- Scenarios: pd1-rear-end, pd2-failure-to-give-way, pd3-reversing, pd4-parked-vehicle-struck, pd5-changing-lanes-sideswipe, pd6-car-park, pd7-other (catch-all → escalation)
- Engine integration: `stage-3/app/engine.py` — `PD_COLLISION_TYPE_TO_SCENARIO`, `_resolve_scenario(claim_type=property_damage)`, `_band_pd()`, global trigger `esc-uninsured-driver` (gated to motor + property_damage)
- State machine: `stage-3/app/state_machine.py` — `PD_SLOTS` (ids 400-416), registered in `BRANCH_SLOTS`
- Frontend: `stage-2.5/app/wrap.py` — PD slots in `SLOT_UI`, `property_damage` + PD options in `_OPTION_LABELS`
- Per-tree hashing: bound to this tree's own scenarios[] hash; independent of motor / PL / med-neg (IX-14).
- `/healthz` reports `rule_tree_versions.property_damage = {version: "1.0.0", scenarios: 7, signed: 0, live: false}`.

## Ship posture — escalate-everything until signed

Every PD scenario ships with `legal_signoff: {approved: false, version: ""}`. Until Legal Head signs this tree's hash, every PD classification returns `escalation="unsigned-scenario"`. This is the safe launch posture and matches the engine's existing behaviour (CD-E4).

**Important distinction from med-neg (item 2c):** PD IS deterministically bandable once signed. Unlike med-neg's escalation-dominant posture (IX-03 — never emits likely/possible), PD's settled liability patterns (rear-end, give-way, reversing, parked-vehicle-struck) genuinely support `likely` / `possible` bands when signed. IX-15 proves this: a clear rear-end (user in front, stopped) bands `likely`; the following driver bands `possible`; pd7-other caps at `unclear`.

## What Legal Head is signing

- The 3-level band shape (likely / possible / unclear) and the conditions under which each fires per scenario (band_logic in the tree).
- The collision-type → scenario mapping (`PD_COLLISION_TYPE_TO_SCENARIO`).
- The PD-specific escalation triggers: `esc-uninsured-driver` (at-fault driver uninsured / cover unknown — recovery shifts to user's own insurer); plus the shared `esc-injury` firewall, `esc-multiparty`, `esc-fraud`, `esc-dispute`, `esc-advice`.
- The draft output text (customer-facing, recovery-framed, cites Arsalan for the hire entitlement — never reworded by the UI).
- The Arsalan authority pack (the killer artifact — see "Strategic note" below).

## Regulatory flags — REQUIRE COUNSEL MEMO BEFORE LAUNCH

This is a **different regulatory surface** from the injury trees. A counsel memo is required before any commercial PD deployment, covering:

1. **CD-R2 (touting) MUST be redone for PD.** The motor / PL CD-R2 analyses do not cover third-party property recovery. The referral rules differ (Lane 1 referral fees are lawful and standard, but the disclosure obligations differ — see (3)).
2. **Debt-collection / commercial-agent licensing by state.** NSW is the lightest regime; QLD has a licensing regime; verify whether any negotiation/agency activity crosses into "legal services" under the Uniform Law. Counsel checklist per Focus Study §4.
3. **ACL / CHOICE-flagged mandatory disclosures.** Consumers MUST be told, before consent, that if the insurer disputes the recovery, proceedings may be brought **in their name**, with potential **credit exposure**. This is the sector's documented trust deficit (CHOICE); mandatory UX disclosure is both the compliance posture and the market differentiator. (CD-D3 consent gate already timestamps this — wire the PD-specific disclosure text.)
4. **Fee-structure confirmation.** Recovery service fee (fixed or % of recovered) — confirm the lawful structure per state. Never per-lead pricing (that's the claim-farming pattern, illegal in Lane 2; keep the discipline clean in Lane 1 too).

## Strategic note — why PD is the beachhead (for context, not sign-off)

The five strategic docs (`HOW-TO-WIN-3P-MOTOR`, `THIRD-PARTY-MOTOR-CLAIM-FOCUS`, `MARKET-STUDY-LEGAL-ENGINE`, `DEMAND-ENGINE-PLAYBOOK`, `INDEPENDENT-AUDIT-REVIEW`) collectively argue PD is the beachhead: legal to own outright, revenue in 90 days, and the deterministic banding the engine is strongest at. The killer artifact this tree enables is the **authority-backed demand letter** — citing Arsalan and current Local Court authorities on rate/duration, in AGLC4, with a quantum schedule — generated deterministically from a signed PD tree. No AMC in the market has a research corpus behind its demands; they have templates. This is the demand-side of the "settle faster than anyone" contest (Focus Study §2). Legal Head sign-off on this tree is the critical path to that product value.

## Deployer evidence (capture against staging)

- [ ] `/healthz` reports `rule_tree_versions.property_damage = {version: "1.0.0", scenarios: 7, signed: 0, live: false}`.
- [ ] Sample PD intake (rear-end, user in front, stopped, 2 vehicles, no injury, other driver insured) → `unsigned-scenario` (pre-sign).
- [ ] After sign-off hash is applied → same intake resolves to band `likely`.
- [ ] PD intake with any injury (minor OR serious) → `esc-injury` (firewall — never a PD band).
- [ ] PD intake with `at_fault_uninsured: yes` → `esc-uninsured-driver`.
- [ ] PD intake with `collision_type: other` → `unclear` (catch-all, even when signed).
- [ ] Run `tests/run_injury_extension.py` IX-11 through IX-17 and attach output.
- [ ] Confirm counsel memo (CD-R2 redo + licensing + ACL disclosures + fee structure) is in hand BEFORE any live PD deployment.

Status: [ ] Pending capture    [ ] Captured
