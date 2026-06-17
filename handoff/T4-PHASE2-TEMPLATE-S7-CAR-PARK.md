# T4 — Phase-2 Scenario Build (Template: s7 Car-Park)
**Prepared by:** Cursor / MiniMax (build seat) · **Date:** 2026-06-15
**Task:** L1 T4 per `CURSOR-HANDOFF-MASTER.md` §7 — append Phase-2 scenario objects to `stage-3/app/data/rule-tree.nsw.v3.json` (bump version → 3.1.0).
**Template scenario:** **s7-car-park** (P2-01) — Tier 1, highest priority per `PHASE-2-RULE-COVERAGE-GAPLIST.md`, distinct geometry from all 6 existing scenarios.
**Source spec:** `stage-4/PHASE-2-TIER1-RULE-BRANCHES.md` (Fables-built, already a complete JSON object).
**Inputs read:** `CURSOR-HANDOFF-MASTER.md` §7, `PHASE-2-TIER1-RULE-BRANCHES.md` (P2-01, P2-02, P2-03, P2-04), `PHASE-2-RULE-COVERAGE-GAPLIST.md`, `stage-3/app/data/rule-tree.nsw.v3.json` (current 6 scenarios), `stage-3/app/engine.py` (T1-aware), `handoff/T6-QUESTION-INJECTION-DESIGN.md` (the dependency).

---

## 1. Scope of this template doc

**This is the T4 build template.** It shows how to add ONE Phase-2 scenario to the rule tree end-to-end. The other 8 Phase-2 scenarios (P2-02..P2-09) follow the same pattern, with their own scenario-specific data and a brief per-scenario diff.

**The full T4 build is 9 scenarios, all from the existing Fables specs** (`PHASE-2-TIER1-RULE-BRANCHES.md` for P2-01..P2-04, `PHASE-2-TIER2-RULE-BRANCHES.md` for P2-05..P2-09). None of the scenario JSON needs to be re-authored — the Fables spec is already complete JSON. The build work is:
1. Add the JSON to the rule tree (with `legal_signoff` field per T1 convention).
2. Add the `accident_type` enum value to slot 3 (T6 amendment §6.8 dependency).
3. Add the `ACCIDENT_TYPE_TO_SCENARIO` entry in `engine.py`.
4. Add the band function `_band_s7` (mirror of `_band_s1`..`_band_s6`).
5. Add the damage-consistency check entries if any.
6. Add ≥2 acceptance tests in `acceptance-tests.stage3.yaml` + matching dispatchers in `run_acceptance.py`.
7. Bump `rule_tree_version` from `3.0.0` to `3.1.0` (which invalidates the `rule_tree_hash`, which G-VER uses to re-trigger Legal Head sign-off).

---

## 2. The s7-car-park scenario — full build spec

### 2.1 Source JSON (from Fables spec, verbatim)

The Fables spec is already a complete JSON object:

```json
{
  "id": "s7-car-park",
  "name": "Car park / parking-lot manoeuvre",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r296", "title": "Reversing only when safe (verify)", "status": "UNVERIFIED"},
    {"rule": "car-park / road-related area give-way", "title": "Priority of through-aisle traffic (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s7-q1", "slot": "cp_user_role", ...},
    {"id": "s7-q2", "slot": "cp_other_role", ...}
  ],
  "default_pattern": {...},
  "exceptions": [...],
  "damage_consistency_check": {...},
  "band_logic": [...],
  "outputs": [...],
  "escalation_overrides": []
}
```

(Full JSON is in `stage-4/PHASE-2-TIER1-RULE-BRANCHES.md` lines 27-58.)

### 2.2 T1 amendment: add `legal_signoff` field

Per the T1 governance gate, every scenario needs a `legal_signoff` metadata block. s7 starts **unsigned** (T1 default, T8 will sign):

```json
"legal_signoff": {
  "approved": false,
  "version": "",
  "by": "",
  "date": ""
}
```

**Note:** the `version` field will get populated with the new `rule_tree_hash` after T4's `version` bump from 3.0.0 → 3.1.0. Until Legal Head signs, s7 (and the other 8 Phase-2 scenarios) will escalate via the G-PROD-LOCK gate. This is the correct fail-closed behavior.

### 2.3 The rule tree gets a new field too: `version`

The current `rule-tree.nsw.v3.json` has:
```json
"version": "3.0.0"
```

After T4, it becomes:
```json
"version": "3.1.0"
```

This version bump changes the `rule_tree_hash` (the hash includes all scenario content but not the version field — but the *signed* `version` field on each scenario's `legal_signoff` does include the version string for matching). **The 6 existing scenarios' `legal_signoff.version` fields will now mismatch the new hash → G-VER marks them as stale → all 6 need re-signing by Legal Head.**

This is by design (G-VER) but worth flagging: **after T4, the 6 existing scenarios that Legal Head has not yet signed will be re-stale.** The path to recover is the same T8 path: Legal Head signs all 9 (or all 15 once T8 runs), bound to the new hash.

### 2.4 Engine code changes

**`stage-3/app/engine.py`:**

1. Add `_band_s7` function. Mirror the structure of `_band_s1` (rear-end). The function takes `intake: dict[str, Any]` and returns `(band: str | None, escalation: str | None)`. Logic per the Fables `band_logic`:
   - Read `cp_user_role` and `cp_other_role` from intake.
   - Apply damage-consistency check (read `damage_locations`, compare to expected impact geometry).
   - Apply exception probes (`aisle_at_fault_factor`, `both_reversing`).
   - Return the matching band per the Fables spec.

2. Add `ACCIDENT_TYPE_TO_SCENARIO` entry. The current routing (from looking at `engine.py`) maps `accident_type` strings to scenario IDs. Add:
   ```python
   "car_park": "s7-car-park",
   ```
   And update the slot 3 enum to include `"car_park"` (per T6 §6.8).

3. Add `DAMAGE_CONSISTENCY["s7-car-park"]` if the existing damage-consistency machinery supports per-scenario rules. (Need to check the existing code; if it doesn't, T4 adds the scaffolding.)

### 2.5 Test additions

≥2 acceptance tests per scenario (per handoff §7 T7). For s7:

| Test | What it asserts |
|---|---|
| T-4-01 | `accident_type = car_park` + `cp_user_role = driving_in_aisle` + `cp_other_role = reversing_from_bay` + damage consistent → band = `likely` |
| T-4-02 | `accident_type = car_park` + `both_reversing = true` → band = `unclear` (or escalation `both-reversing`) |
| T-4-03 | `accident_type = car_park` + `cp_user_role` missing after reprompts → band = `insufficient` |

(2-3 tests is the spec floor; can add more for the exception paths.)

**Each test needs:**
- An entry in `stage-3/acceptance-tests.stage3.yaml`
- A dispatcher in `stage-3/tests/run_acceptance.py`
- A pre-populated intake (T6 §3.7 Option A — pre-populate scenario slots, don't go through the state machine)

### 2.6 State machine changes (slot 3 enum growth)

T6's amendment §6.8 noted this dependency. T4 adds `"car_park"` to the `accident_type` enum in slot 3:

```python
{"id": 3, "slot": "accident_type", "type": "enum", "options": [
  "rear-end", "T-intersection", "roundabout", "merge", "reversing", "parking", "other",
  # T4 additions:
  "car_park", "intersection_signalised", "turning_right", "sideswipe_same_direction",
  "driveway", "u_turn", "head_on", "dooring", "unmarked_intersection"
], "mandatory": True}
```

**Note:** `"parking"` already exists in the current enum. Fables named the new scenario `car_park` (underscore). The existing `parking` value currently routes nowhere (it's a "candidate" in the Fables spec — see `PHASE-2-RULE-COVERAGE-GAPLIST.md` P2-01, "Today: Reversing rule partly applies; most car-park geometry escalates"). **T4 should reconcile:** the existing `parking` value is an alias for `car_park`; map both to `s7-car-park` in the routing. The enum keeps both for backward-compat with existing intakes.

### 2.7 Frontend changes

The Lovable UI renders `accident_type` as a button group. The new enum values will appear as new buttons. **No UI code change** — the UI iterates over the enum and renders one button per value. (Per the handoff §8, the Lovable sync picks this up on next round-trip; the engine repo change here is independent of Lovable's render.)

### 2.8 The T4 build sequence (in order)

| # | Action | Files | Notes |
|---|---|---|---|
| 1 | Append s7 JSON object (with `legal_signoff` field) to `scenarios[]` in the rule tree | `stage-3/app/data/rule-tree.nsw.v3.json` | ~70 lines appended |
| 2 | Bump `version` from `3.0.0` to `3.1.0` | same | Single-line change; bumps `rule_tree_hash` (T1 implication: existing 6 sign-offs become stale) |
| 3 | Add `_band_s7` function | `stage-3/app/engine.py` | Mirror `_band_s1` structure; ~80 lines |
| 4 | Add `"car_park": "s7-car-park"` to `ACCIDENT_TYPE_TO_SCENARIO` | `stage-3/app/engine.py` | 1 line |
| 5 | Add `"car_park"` (and the other 8 new values) to slot 3 enum | `stage-3/app/state_machine.py` | 1 line edit |
| 6 | Add `DAMAGE_CONSISTENCY["s7-car-park"]` if needed | `stage-3/app/engine.py` | Check existing scaffolding |
| 7 | Add 3 T-4-* tests (T-4-01..T-4-03) | `stage-3/tests/run_acceptance.py` + `acceptance-tests.stage3.yaml` | Per §2.5 |
| 8 | Run full test suite, confirm green | local + engine repo clone | 75 → 78 tests |
| 9 | Stage, commit, push to engine repo `main` | git | Per the T1 pattern (local identity, push to main, Vercel auto-deploy) |

**Then repeat steps 1-9 for s8, s9, ..., s15.** Each scenario is its own commit (cleaner audit trail; per-scenario rollback possible).

---

## 3. The 8 remaining scenarios — diff summary

| ID | Name | Tier | Spec location | Distinct from existing |
|---|---|---|---|---|
| s7-car-park | Car park / parking-lot manoeuvre | 1 | `PHASE-2-TIER1-RULE-BRANCHES.md` P2-01 | Geometry: aisle vs bay (not motion) |
| s8-signalised-intersection | Traffic-light intersection | 1 | `PHASE-2-TIER1-RULE-BRANCHES.md` P2-02 | Light state is the discriminator |
| s9-right-turn-oncoming | Right turn across oncoming | 1 | `PHASE-2-TIER1-RULE-BRANCHES.md` P2-03 | Turn-direction is the discriminator |
| s10-sideswipe-same-direction | Sideswipe (same direction) | 1 | `PHASE-2-TIER1-RULE-BRANCHES.md` P2-04 | Lane-change geometry, both moving |
| s11-driveway | Emerging from driveway | 2 | `PHASE-2-TIER2-RULE-BRANCHES.md` P2-05 | Property-emergence geometry |
| s12-u-turn | U-turn collision | 2 | `PHASE-2-TIER2-RULE-BRANCHES.md` P2-06 | U-turning vs non-U-turning |
| s13-head-on | Head-on / wrong side | 2 | `PHASE-2-TIER2-RULE-BRANCHES.md` P2-07 | Side-of-centre-line is the discriminator; often co-escalates on injury |
| s14-dooring | Car-door opening | 2 | `PHASE-2-TIER2-RULE-BRANCHES.md` P2-08 | Door-opening (not moving vehicle) |
| s15-unmarked-intersection | Unmarked / uncontrolled | 2 | `PHASE-2-TIER2-RULE-BRANCHES.md` P2-09 | Right-of-way at no-sign intersection |

**Each follows the s7 template.** The build is 9 × the s7 effort, with shared per-scenario boilerplate (test scaffolding, engine routing entry, etc.) extracted to keep the per-scenario diff small.

---

## 4. Risks + things to watch

### 4.1 The 75-test regression

The 6 existing scenarios are tested in T-3-001..T-3-006. After T4, the `rule_tree_hash` changes (version bump), which (per T1 G-VER) makes the existing `legal_signoff.version` stale. **The T-3-* tests will continue to pass** (they test the engine's band logic, not the sign-off state). But the *legal* state changes: until Legal Head signs the new hash, all 9 Phase-2 scenarios escalate (as designed).

### 4.2 The slot 3 enum growth

Adding 9 new values to slot 3 changes the enum that the frontend renders as buttons. The Lovable UI re-syncs from the frontend repo, not the engine repo — so the engine-side change doesn't break the frontend. The frontend needs its own update to show the new buttons. **Out of scope for the engine repo; in scope for L1's frontend work.**

### 4.3 The T6 dependency

T4 assumes the scenario questions can be asked via T6's injection mechanism. **If T6 isn't built yet, T4's scenarios still work** (T1's G-PROD-LOCK escalation handles the unsigned-scenario case), but they don't *band* — they all escalate. The T6 → T4 order matters: T6 must ship first (or simultaneously) for the Phase-2 scenarios to actually band.

**The handoff is explicit about this:** *"Conversational question-injection (the dependency — mandatory). Without this, the band logic has no inputs and would default."*

So the **L1 build order is: T6 first, then T4.** T6 unblocks T4.

### 4.4 The 9 scenario commits

The recommendation is 9 separate commits, one per scenario. This means 9 push events to `main`, 9 Vercel auto-deploys, 9 cycles of "verify live." Per scenario is small (~5-10 minutes per scenario end-to-end). For 9 scenarios, that's ~1.5 hours of pure build + test + push + verify, possibly spread over multiple sessions.

### 4.5 The `legal_signoff.version` rotation

When T4 lands, the 6 existing scenarios' sign-off is *stale* (the hash changed). The 9 new scenarios have *no* sign-off. **T8 (Legal Head signs B7–B15 + re-signs B1–B6 against the new hash) is what brings them all back to a banded state.** Until T8, the engine escalates all 15 scenarios.

---

## 5. Acceptance criteria (T4 closes when)

1. 9 scenario JSON objects appended to `rule-tree.nsw.v3.json` (8 in addition to s7).
2. `rule_tree_version` bumped from 3.0.0 to 3.1.0.
3. 9 `_band_sN` functions added to `engine.py`.
4. 9 `ACCIDENT_TYPE_TO_SCENARIO` entries added.
5. Slot 3 enum grown from 7 values to 16 values (7 existing + 9 new).
6. ≥18 new acceptance tests (2 per scenario × 9) in the suite; all green.
7. Full test suite (75 + 18 + T1's 4 + T6's 12 = ~109) green.
8. Vercel auto-deploys each scenario commit; live `/healthz.rule_tree_hash` updates accordingly.
9. **T8 (Legal Head sign-off) follows as the loop's final gate.** T4 doesn't close until T8 is recorded.

---

## 6. Effort estimate

| Step | Per scenario | × 9 scenarios | Total |
|---|---|---|---|
| Append JSON to rule tree | 5 min | ×9 | 45 min |
| Bump version (only once for the batch) | 1 min | once | 1 min |
| Add `_band_sN` | 30-60 min | ×9 | 4.5-9 hours |
| Add routing entry | 1 min | ×9 | 9 min |
| Add enum value | 1 min | ×9 | 9 min |
| Add 2-3 tests | 30-45 min | ×9 | 4.5-6.75 hours |
| Run full test suite | 5 min | ×9 | 45 min |
| Commit + push + verify live | 5 min | ×9 | 45 min |
| **Total** | | | **~11-17 hours** |

**In context:** a full T4 build is roughly 2-3 working days of build time, possibly spread across multiple sessions. **T6 must complete first** (estimated 2-3 build hours); T4 starts after T6's tests are green.

---

*Prepared by Cursor / MiniMax (build seat) · T4 design complete. T6 must ship first; then T4 can begin per this template.*
