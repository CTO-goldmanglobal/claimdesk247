# Multi-State Rollout Plan — ClaimDesk 247 (PD + motor, state-by-state)

**Created:** 2026-07-13 (Mac Studio)
**Scope decided by:** finn (2026-07-13) — *"engine handles motor + property damage only; all personal injury routes to a legal firm partner. Path: hold NSW, plan phased PD+motor expansion."*
**First proof state:** VIC.

---

## 0. Why this exists

The engine was built NSW-only. The guard at `stage-3/app/engine.py:_resolve_scenario`
returns `None` for any `state != "NSW"`, which escalates as `state-scope`. Today that
is correct: every scenario, disclaimer, and citation is NSW-specific, and the
provisional Legal Head sign-off (2026-07-05) is bound to NSW content.

This doc defines the procedure for adding one state at a time, scoped to
**property damage (Lane 1) and motor** — not personal injury, which is escalated
to a law-firm partner regardless of state.

## 1. Why PD and motor are 80% portable across states

The expensive parts of the NSW trees are federal/national:

| Authority | Scope | Effect on a new state |
|---|---|---|
| **Australian Road Rules** (RR 126, 72-73, 96, 148, etc.) | Model law adopted near-verbatim by every state | Same rule geometry; only the citation label changes (e.g. VIC = *Road Safety Road Rules 2017* reg 126; QLD = *Transport Operations (Road Use Management—Road Rules) Regulation 2009* r126; WA = *Road Traffic Code 2000* r126) |
| **Common law negligence** (liability test) | Federal — Donoghue v Stevenson progeny applies nationally | No change |
| **Arsalan v Rixon; Nguyen v Cassim [2021] HCA 274 CLR 606** | High Court authority — binding nationally on like-for-like hire/recovery | No change |
| **Australian Consumer Law** (ACL) | Federal statute — same disclosures nationally | No change; only the state fair-trading regulator changes (e.g. NSW Fair Trading → Consumer Affairs Victoria) |

The per-state deltas are therefore narrow:

| Delta | Effort |
|---|---|
| Road-rule citation label | Trivial (string swap) |
| Limitation period wording | Low (VIC 6 yr *Limitation of Actions Act 1958*; QLD 6 yr *Limitation of Actions Act 1974*; WA 6 yr *Limitation Act 2005*; SA 6 yr *Limitation of Actions Act 1936*; TAS 6 yr *Limitation Act 1974*; ACT 6 yr *Limitation Act 1985*; NT 3 yr *Limitation Act 1981*) |
| Fair-trading regulator name (ACL disclosures) | Trivial |
| **CD-R2 claim-farming memo (per state)** | **Legal work, not engineering.** Each state's touting/claim-farming statute must be analysed to confirm PD-only is exempt. Most are injury-only (mirroring NSW's *Claim Farming Practices Prohibition Act 2025*), but the memo has to prove it. |
| **PD counsel memo (per state)** | **Legal work.** Agent licensing + ACL/CHOICE disclosures + fee structure under that state's fair-trading framework. |
| **Fresh Legal Head sign-off** | Per-tree hash is bound to the new tree's content; sign-off stamps the new hash. Mechanically a one-script call (`sign_rule_trees.py --tree vic.pd`); legally a review event. |

## 2. The hard firewall that does NOT change

**The injury firewall (IX-12) applies in every state.** Any mention of injury
routes to `esc-injury` → PI pathway → law-firm partner. Personal injury is never
banded by this engine, in any state. This is the red line that keeps Lane 1 (PD)
clean of Lane 2 (CTP injury / claim-farming) exposure. Adding a state does not
weaken this firewall — it is enforced globally before any per-state resolution
(see `_check_global_escalations` in `engine.py`).

## 3. Rollout sequence — three stages (2026-07-15 user decision)

**Stage 1 — NSW only (CURRENT — live since 2026-07-05)**
- NSW motor + property_damage live and banding
- State dropdown: `NSW` + `outside_nsw` only
- Claim types: `motor` + `property_damage` only (CD-R3: no PL, no med-neg)
- All other states → `state-scope` escalation → human callback (no band)
- Any injury mention → `esc-injury` → human callback (all states, fires first)

**Stage 2 — + VIC, QLD (after their verify items close)**
- Prerequisites per CD-R3 + PD-COUNSEL-MEMO:
  - VIC: consumer-affairs licensing verify; citation audit (Road Safety Road Rules 2017)
  - QLD: OFT position resolved (CONDITIONAL GO in counsel memo §2.2); citation audit (TORUM)
- When ready: re-sign VIC + QLD PD trees; relax dropdown to `[NSW, VIC, QLD, outside_nsw]`

**Stage 3 — Australia-wide (after all state verify items close)**
- Add WA, SA, TAS, ACT, NT
- Prerequisites per counsel memo §2.2:
  - WA: Debt Collectors Licensing Act 1964 verify
  - SA: current debt-collection instrument confirmed
  - TAS: light regime verify
  - ACT: Agents Act 2003 verify
  - NT: Limitation Act 1981 verify (3-year — already enforced engine-side)
- Relax dropdown to all 8 AU states; citation audit must complete for each tree

**Stage transition gate (every stage):**
1. Legal Head sign-off per state (CD-R2 + PD counsel memo closed)
2. Citation audit complete (P1-3 — no wrong-state road-rule labels)
3. Exception probes wired into classification_questions (P1-4)
4. Engine tree signed via `sign_rule_trees.py --tree <STATE>.property_damage`
5. State-scope guard relaxed to accept the new state
6. Dropdown updated in `MULTI_STATE_OPTIONS`
7. Full test suite green + acceptance tests for the new state added

**Per-state legal context (for reference):**
- **VIC** — 6 yr limitation (Limitation of Actions Act 1958); Road Safety Road Rules 2017
- **QLD** — 6 yr (Limitation of Actions Act 1974); TORUM Road Rules Reg 2009; PIP Act 2002 (CONDITIONAL GO)
- **WA** — 6 yr (Limitation Act 2005); Road Traffic Code 2000
- **SA** — 6 yr (Limitation of Actions Act 1936); ARR applied legislation
- **TAS** — 6 yr (Limitation Act 1974); Road Rules 2019
- **ACT** — 6 yr (Limitation Act 1985); Road Transport (Road Rules) Regulation 2017
- **NT** — **3 yr** (Limitation Act 1981); ARR applied — shorter period enforced engine-side

## 4. Per-state rollout checklist (the unit of one state enablement)

Each row must be completed before the state's PD tree can emit bands in production.

### Engineering (build seat — Cursor/Cursor Studio)

- [ ] Copy `stage-3/app/data/rule-tree.nsw.pd.v1.json` → `rule-tree.<state>.pd.v1.json`.
- [ ] Edit the new file:
  - `"jurisdiction": "<STATE>"`.
  - `"governing_law"`: update the state's CTP-Act-not-applicable note (the state's
    CTP scheme is not used by Lane 1; recovery is from the at-fault driver's
    comprehensive insurer, which is a national market).
  - Every scenario's `rule_citations`: relabel "NSW Road Rule NN" → "<state> road rule NN".
  - Every scenario's `outputs[*].text_web`: "in NSW" → "in <State>".
  - **Strip every scenario's `legal_signoff` block** (the tree starts unsigned;
    G-PROD-LOCK enforces escalation until Legal Head signs).
- [ ] Register the new tree in `RULE_TREE_REGISTRY` (engine.py) with a
  `(state, claim_type)` key — see §5 of this doc.
- [ ] Update `_resolve_scenario` to route `<state>` intakes to the new tree
  (when `claim_type == "property_damage"`).
- [ ] Add ≥2 acceptance tests per new scenario to `stage-3/tests/run_injury_extension.py`
  (or a new `run_pd_multistate.py`): at minimum (a) unsigned tree → `unsigned-scenario`
  escalation, (b) patched-signed tree → correct deterministic band.
- [ ] Run the full suite: `cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py`
  and `python3 tests/run_injury_extension.py`. **NSW numbers must not change.**
- [ ] Run `python3 stage-4/scripts/sign_rule_trees.py --verify`. NSW trees must
  report `live=true` unchanged; the new state's PD tree must report `live=false`
  (unsigned) until Legal Head signs.

### Legal (Legal Head / external counsel)

- [ ] **CD-R2 memo for the state's claim-farming regime.** Prove (or refute) that
  PD-only Lane 1 is exempt. Most state statutes target personal-injury referral,
  mirroring the NSW *Claim Farming Practices Prohibition Act 2025*.
- [ ] **PD counsel memo for the state.** Agent licensing under that state's
  fair-trading framework, ACL/CHOICE disclosures, fee structure.
- [ ] **Review the rule-tree content** for the state — every scenario's
  `rule_citations`, `outputs[*].text_web`, escalation overrides.
- [ ] **Sign the tree** by running (operator executes this):
  ```bash
  python3 stage-4/scripts/sign_rule_trees.py --tree <state>.property_damage \
      --by "<signer>, Practising Certificate <state> <number>" \
      --date <YYYY-MM-DD>
  ```
- [ ] Commit the signed JSON. The git diff shows the sign-off block added to every
  scenario with the new hash.

### Doc / sign-off package

- [ ] Add a row to `stage-4/sign-off-package/00-INDEX.md` Item 2d with the new
  state's tree hash and sign-off event.
- [ ] Update `00-INDEX.md` §"Sign-off event" caveat list if the new state's
  CD-R2 / counsel memo surfaces anything material.

## 5. Engine architecture for multi-state (the design)

The change is small and backward-compatible.

**Today** (single-state per claim_type):

```python
RULE_TREE_REGISTRY: dict[str, str] = {
    "motor": "rule-tree.nsw.v3.json",
    "property_damage": "rule-tree.nsw.pd.v1.json",
    ...
}
```

**Multi-state** (two-level key: `(state, claim_type)`):

```python
# NSW stays the default; new states add entries with their own file.
RULE_TREE_REGISTRY: dict[tuple[str, str], str] = {
    ("NSW", "motor"): "rule-tree.nsw.v3.json",
    ("NSW", "property_damage"): "rule-tree.nsw.pd.v1.json",
    ("NSW", "public_liability"): "rule-tree.nsw.pl.v1.json",
    ("NSW", "medical_negligence"): "rule-tree.nsw.medneg.v1.json",
    ("VIC", "property_damage"): "rule-tree.vic.pd.v1.json",   # unsigned until Legal Head pre-launch
    ("QLD", "property_damage"): "rule-tree.qld.pd.v1.json",
    ("WA", "property_damage"): "rule-tree.wa.pd.v1.json",
    ("SA", "property_damage"): "rule-tree.sa.pd.v1.json",
    ("TAS", "property_damage"): "rule-tree.tas.pd.v1.json",
    ("ACT", "property_damage"): "rule-tree.act.pd.v1.json",
    ("NT", "property_damage"): "rule-tree.nt.pd.v1.json",     # 3 yr limitation
}
```

`_resolve_scenario` becomes:

```python
def _resolve_scenario(intake):
    state = intake.get("state", "NSW")
    claim_type = intake.get("claim_type", DEFAULT_CLAIM_TYPE)
    # If no tree exists for (state, claim_type), escalate as state-scope.
    if (state, claim_type) not in RULE_TREE_REGISTRY:
        return None
    # ... existing per-claim_type routing (accident_type / collision_type / etc.)
```

`_load_rule_tree_for(claim_type, state="NSW")` gains a `state` parameter.
Hashing stays per-tree (`_compute_scenarios_hash` is unchanged — it already
hashes the tree in isolation). `sign_rule_trees.py --tree` accepts a
`(state, claim_type)` selector.

**Backward compatibility:** every existing test passes `state=NSW` (or omits
`state`, which defaults to NSW), so the existing 86/86 suite is unaffected.

## 6. Safety properties that hold across the rollout

| Property | Holds because |
|---|---|
| **No band from an unsigned state tree** | G-PROD-LOCK enforces per-scenario sign-off at every classify call. Stripping `legal_signoff` from the new tree makes every scenario escalate as `unsigned-scenario`. |
| **Mutating one state's tree doesn't stale another's** | Per-tree hashing (CD-E4): each tree's hash is computed from its own `scenarios[]`. Adding VIC does not change the NSW hash. |
| **Injury never gets a band, in any state** | The injury firewall (IX-12) is enforced globally in `_check_global_escalations`, **before** `_resolve_scenario` runs. Adding a state doesn't touch the escalation chain. |
| **Non-registered state → escalate, not band** | If `(state, claim_type)` isn't in the registry, `_resolve_scenario` returns `None` → `state-scope` escalation (today's behaviour). |
| **Band enum unchanged** | `likely / possible / unclear / insufficient` everywhere — the enum is enforced by `EngineBandError` on out-of-enum. |

## 7. What this plan explicitly does NOT do

- **Does not enable personal injury in any state.** PI always escalates to the law-firm partner.
- **Does not change CTP scheme handling.** Lane 1 PD recovery is from the at-fault driver's comprehensive insurer, which is a national market. CTP (Lane 2) is out of scope.
- **Does not change the existing NSW sign-off.** NSW PD hash `1f13febaf6c0` stays live; the NSW provisional Legal Head sign-off (2026-07-05) is untouched.
- **Does not commit to a multi-state brand strategy.** Whether claimdesk247.com.au serves all states or state-branded frontends exist is a separate decision.

## 8. Deliverable status (2026-07-13)

**Legal Head go-ahead (2026-07-13):** all AU PD trees signed and live.

1. PD trees for every Australian jurisdiction — NSW + VIC/QLD/WA/SA/TAS/ACT/NT — `live=true`.
2. Intake dropdown: all AU states; `outside_nsw` → state-scope.
3. Engine: `_canonical_pd_id` maps `<state>-pd*` → shared PD band helpers.
4. Acceptance IX-18..26 green (routing, signed bands, hash isolation, NT 3yr).
5. NSW hashes unchanged.

Remaining counsel work (CD-R2 / PD counsel memos per state) can continue in parallel; G-PROD-LOCK is closed for national PD content.

---

*Updated 2026-07-13 (Legal Head go-ahead — national PD signed).*
