# Item 2b — Public Liability Rule Tree (rule-tree.nsw.pl.v1.json)

Personal-injury extension (spec: `claimdesk-injury-extension-INSTRUCTIONS-2026-07-03.md`, Part 2).

## Governing law

NSW **Civil Liability Act 2002** — NOT the Motor Accidents Injuries Act. Liability turns on:
- duty of care (did the occupier owe one?)
- foreseeability of the risk
- reasonable precautions (CLA s5B / s5C)
- contributory negligence (CLA s5R)

## Builder evidence (CODE)

- `stage-3/app/data/rule-tree.nsw.pl.v1.json` (v1.0.0, claim_type=public_liability)
- Scenarios: pl1-slip-wet-surface, pl2-trip-uneven-surface, pl3-falling-object, pl4-inadequate-lighting, pl5-defective-premises, pl6-other-public-place (catch-all → escalation)
- Engine integration: `stage-3/app/engine.py` — `PL_HAZARD_TYPE_TO_SCENARIO`, `_resolve_scenario(claim_type=public_liability)`, `_band_pl()`
- State machine: `stage-3/app/state_machine.py` — `PL_SLOTS` (ids 200-209)
- Per-tree hashing: bound to this tree's own scenarios[] hash; independent of motor and med-neg trees.

## Ship posture — escalate-everything until signed

Every PL scenario ships with `legal_signoff: {approved: false, version: ""}`. Until Legal Head signs this tree's hash, every PL classification returns `escalation="unsigned-scenario"`. This is the safe launch posture and matches the engine's existing behaviour (CD-E4).

## What Legal Head is signing

- The 3-level band shape (likely / possible / unclear) and the conditions under which each fires (spec §2.2).
- The hazard-type → scenario mapping (spec §2.1).
- The PL-specific escalation overrides (council → esc-govt-defendant; workplace → esc-workers-comp; catch-all → human).
- The draft output text (customer-facing, never reworded by the UI).

## Regulatory flags — REQUIRE SEPARATE SIGN-OFF

- **CD-R2 (touting) MUST be redone for PL.** The motor CD-R2 analysis does NOT cover public-liability claims. The referral rules and the "is the intake touting" question differ by scheme. Do not assume the motor CD-R2 sign-off covers PL.
- **Limitation periods differ** from motor CTP and are unforgiving — hence `esc-limitation` (buffer `LIMITATION_BUFFER_YEARS = 2.5`). Confirm the exact period with Legal Head; it's a one-line constant change.

## Deployer evidence (capture against staging)

- [ ] `/healthz` reports `rule_tree_versions.public_liability = {version: "1.0.0", signed: 0, live: false}`.
- [ ] Sample PL intake (supermarket, wet-surface, no warning, long duration) → `unsigned-scenario` (pre-sign).
- [ ] After sign-off hash is applied → same intake resolves to a band (likely/possible).
- [ ] Council-footpath PL intake → `esc-govt-defendant`.
- [ ] Workplace PL intake → `esc-workers-comp`.
- [ ] PL intake with incident > 2.5 yrs ago → `esc-limitation`.
- [ ] Run `tests/run_injury_extension.py` IX-01, IX-05, IX-06, IX-09 and attach output.

Status: [ ] Pending capture    [ ] Captured
