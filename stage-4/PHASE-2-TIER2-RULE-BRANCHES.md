# Phase-2 Tier-2 Rule Branches — build spec
**Prepared by:** Fables (Cowork) · **Date:** 2026-06-14 · **For:** firm legal sign-off → Cursor/MiniMax build → Opus audit
**Target file:** append to `scenarios[]` in `stage-3/app/data/rule-tree.nsw.v3.json` (alongside Tier-1; version → `3.1.0`).

> Same rules as Tier-1: tree is authoritative, RAG advisory only; outputs are **bands, never percentages**, each carries `{{ATTACH:master}}`; the global 7 escalation triggers still apply on top. ⚠️ **All `rule_citations` are UNVERIFIED indicative references — the firm confirms or strikes them against the NSW Road Rules 2014 before launch. Not legal advice; never customer-facing.**

## Classification routing additions
| accident_type value | routes to |
|---|---|
| `driveway_emergence` | P2-05 |
| `u_turn` | P2-06 |
| `head_on` | P2-07 |
| `dooring` | P2-08 |
| `intersection_unmarked` | P2-09 |

---

## P2-05 — Emerging from driveway / private property
```json
{
  "id": "s11-driveway-emergence",
  "name": "Emerging from driveway / property",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r74", "title": "Giving way when entering/leaving a road-related area or driveway (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s11-q1", "slot": "dw_user_role", "question_web": "At impact you were:", "question_voice": "Were you pulling out of a driveway or property, or already driving on the road?", "answer_type": "enum", "options": ["emerging_from_driveway", "on_the_road", "unsure"], "validation": "must be one option", "reprompt_max": 2},
    {"id": "s11-q2", "slot": "dw_other_role", "question_web": "The other vehicle was:", "question_voice": "And the other vehicle?", "answer_type": "enum", "options": ["emerging_from_driveway", "on_the_road", "unsure"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "A vehicle entering the road from a driveway or private property must give way to vehicles already travelling on the road; fault generally rests with the emerging driver.", "favours": "road_vehicle"},
  "exceptions": [
    {"id": "s11-e1", "probe_question": "Was the road vehicle speeding, on the wrong side, or otherwise driving unlawfully?", "slot": "road_at_fault_factor", "effect": "downgrade_band"},
    {"id": "s11-e2", "probe_question": "Had the emerging vehicle already fully completed entering and straightened in the lane before impact?", "slot": "emergence_complete", "effect": "flag_unclear"}
  ],
  "damage_consistency_check": {"expected": "front/side of emerging vehicle to side of road vehicle", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "user on_the_road AND other emerging_from_driveway AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND >=1 exception unconfirmed or present", "band": "possible"},
    {"when": "emergence_complete OR roles unsure OR damage inconsistent", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "A vehicle entering the road from a driveway or property in NSW must give way to traffic already on the road. Where you were on the road and the other driver emerged into your path, fault generally rests with the emerging driver. Whether it applies depends on the full evidence. {{ATTACH:master}}", "text_voice": "A vehicle pulling out of a driveway has to give way to traffic already on the road in New South Wales. If you were on the road and they pulled out into you, fault usually rests with them — though it depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This matches the driveway give-way pattern, but a factor you've described can change it. A lawyer will review. {{ATTACH:master}}", "text_voice": "This looks like the driveway pattern, but something you mentioned can change it, so a lawyer will review. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "Where the emerging vehicle had already merged, or roles aren't certain, fault isn't clear-cut and needs a lawyer's assessment. {{ATTACH:master}}", "text_voice": "If the other car had already merged, or roles aren't certain, a lawyer will need to assess fault. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail to describe the usual pattern here. {{ATTACH:master}}", "text_voice": "I don't have enough detail yet. {{ATTACH:master}}"}
  ],
  "escalation_overrides": []
}
```

## P2-06 — U-turn collision
```json
{
  "id": "s12-u-turn",
  "name": "U-turn collision",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r38", "title": "Giving way when making a U-turn (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s12-q1", "slot": "ut_user_role", "question_web": "At impact you were:", "question_voice": "Were you making the U-turn, or driving normally when the other car U-turned?", "answer_type": "enum", "options": ["making_u_turn", "other_made_u_turn", "unsure"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "A driver making a U-turn must give way to all other vehicles and pedestrians; fault generally rests with the U-turning driver.", "favours": "non_uturning_driver"},
  "exceptions": [
    {"id": "s12-e1", "probe_question": "Was the other driver speeding or driving unlawfully at the time?", "slot": "other_at_fault_factor", "effect": "downgrade_band"},
    {"id": "s12-e2", "probe_question": "Had the U-turn been fully completed and the car travelling straight before impact?", "slot": "uturn_complete", "effect": "flag_unclear"}
  ],
  "damage_consistency_check": {"expected": "impact geometry consistent with one vehicle crossing/turning across the other's path", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "other_made_u_turn AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND >=1 exception unconfirmed or present", "band": "possible"},
    {"when": "uturn_complete OR role unsure OR damage inconsistent", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "A driver making a U-turn in NSW must give way to all other traffic. Where the other driver U-turned across your path, fault generally rests with them. Whether it applies depends on the full evidence. {{ATTACH:master}}", "text_voice": "A driver making a U-turn has to give way to everyone else in New South Wales. If they U-turned across you, fault usually rests with them — though it depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This matches the U-turn give-way pattern, but a factor you've described can change it. A lawyer will review. {{ATTACH:master}}", "text_voice": "This looks like the U-turn pattern, but something you mentioned can change it, so a lawyer will review. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "Where the U-turn was already complete, or roles aren't certain, fault isn't clear-cut and needs a lawyer's assessment. {{ATTACH:master}}", "text_voice": "If the U-turn was already finished, or roles aren't certain, a lawyer will need to assess fault. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail to describe the usual pattern here. {{ATTACH:master}}", "text_voice": "I don't have enough detail yet. {{ATTACH:master}}"}
  ],
  "escalation_overrides": []
}
```

## P2-07 — Head-on / wrong side / unsafe overtaking
```json
{
  "id": "s13-head-on",
  "name": "Head-on / wrong side / unsafe overtaking",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r132", "title": "Keeping to the left of the centre of the road (verify)", "status": "UNVERIFIED"},
    {"rule": "r140-r144", "title": "Overtaking only when safe / sufficient clear road (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s13-q1", "slot": "ho_other_side", "question_web": "The other vehicle was:", "question_voice": "Was the other vehicle on the wrong side of the road, or overtaking when it hit you?", "answer_type": "enum", "options": ["on_wrong_side", "overtaking", "neither", "unsure"], "validation": "must be one option", "reprompt_max": 2},
    {"id": "s13-q2", "slot": "ho_user_side", "question_web": "You were:", "question_voice": "And were you on your correct side of the road?", "answer_type": "enum", "options": ["on_correct_side", "also_crossed", "unsure"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "A driver on the incorrect side of the centre line, or overtaking without a clear and safe road, generally bears fault; the driver on the correct side is favoured.", "favours": "correct_side_driver"},
  "exceptions": [
    {"id": "s13-e1", "probe_question": "Did you also cross the centre line, even partly?", "slot": "user_crossed", "effect": "flag_unclear"},
    {"id": "s13-e2", "probe_question": "Was the other driver avoiding a hazard or obstruction when they crossed?", "slot": "other_avoiding_hazard", "effect": "downgrade_band"}
  ],
  "damage_consistency_check": {"expected": "front-to-front or front-corner impact consistent with a head-on / overtaking sideswipe", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "user on_correct_side AND other on_wrong_side/overtaking AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND >=1 exception unconfirmed or present", "band": "possible"},
    {"when": "user_crossed OR sides unsure OR damage inconsistent", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "A driver who crosses to the wrong side of the road, or overtakes without a clear and safe road, generally bears fault in NSW. Where you were on your correct side and the other vehicle crossed into you, fault generally rests with that driver. Whether it applies depends on the full evidence. {{ATTACH:master}}", "text_voice": "A driver on the wrong side of the road, or overtaking when it isn't safe, usually bears fault in New South Wales. If you were on your correct side and they crossed into you, fault generally rests with them — though it depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This matches the wrong-side / unsafe-overtaking pattern, but a factor you've described can change it. A lawyer will review. {{ATTACH:master}}", "text_voice": "This looks like the wrong-side pattern, but something you mentioned can change it, so a lawyer will review. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "Where both vehicles crossed the line, or the sides aren't certain, fault isn't clear-cut and needs a lawyer's assessment. {{ATTACH:master}}", "text_voice": "If both cars crossed the line, or the sides aren't certain, a lawyer will need to assess fault. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail to describe the usual pattern here. {{ATTACH:master}}", "text_voice": "I don't have enough detail yet. {{ATTACH:master}}"}
  ],
  "escalation_overrides": [
    {"condition": "injuries == 'serious'", "action": "route_to_esc-injury"}
  ]
}
```
> Head-on collisions frequently involve injury — the global `esc-injury` trigger will usually fire first and route to a human regardless of band. The override is listed explicitly for clarity.

## P2-08 — Car-door opening ("dooring")
```json
{
  "id": "s14-dooring",
  "name": "Car-door opening (dooring)",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r269", "title": "Opening doors / leaving them open so as to cause danger or obstruction (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s14-q1", "slot": "dr_user_role", "question_web": "At impact you were:", "question_voice": "Were you the moving vehicle, or the one whose door was opened?", "answer_type": "enum", "options": ["moving_vehicle", "door_opener", "unsure"], "validation": "must be one option", "reprompt_max": 2},
    {"id": "s14-q2", "slot": "dr_moving_speed", "question_web": "The moving vehicle was:", "question_voice": "Was the moving vehicle going at a normal speed in its lane?", "answer_type": "enum", "options": ["normal_in_lane", "too_fast_or_close", "unsure"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "A person opening a vehicle door (or leaving it open) must not cause danger or obstruction to others; fault generally rests with the door-opener where a passing vehicle was travelling normally.", "favours": "passing_vehicle"},
  "exceptions": [
    {"id": "s14-e1", "probe_question": "Was the passing vehicle travelling too fast, too close, or partly out of its lane?", "slot": "passing_at_fault_factor", "effect": "downgrade_band"},
    {"id": "s14-e2", "probe_question": "Had the door been open and visible for some time before impact?", "slot": "door_open_prior", "effect": "flag_unclear"}
  ],
  "damage_consistency_check": {"expected": "passing vehicle side/front damage aligned with an opened door", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "user moving_vehicle AND normal_in_lane AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND >=1 exception unconfirmed or present", "band": "possible"},
    {"when": "door_open_prior OR roles unsure OR damage inconsistent", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "A person opening a car door in NSW must not do so where it causes danger to others. Where you were passing normally in your lane and a door was opened into your path, fault generally rests with the person who opened it. Whether it applies depends on the full evidence. {{ATTACH:master}}", "text_voice": "A person opening a car door in New South Wales must not do it in a way that endangers others. If you were passing normally and a door opened into you, fault usually rests with the person who opened it — though it depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This matches the dooring pattern, but a factor you've described can change it. A lawyer will review. {{ATTACH:master}}", "text_voice": "This looks like the dooring pattern, but something you mentioned can change it, so a lawyer will review. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "Where the door was open and visible for some time, or roles aren't certain, fault isn't clear-cut and needs a lawyer's assessment. {{ATTACH:master}}", "text_voice": "If the door was already open and visible, or roles aren't certain, a lawyer will need to assess fault. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail to describe the usual pattern here. {{ATTACH:master}}", "text_voice": "I don't have enough detail yet. {{ATTACH:master}}"}
  ],
  "escalation_overrides": []
}
```

## P2-09 — Unmarked / uncontrolled intersection
```json
{
  "id": "s15-unmarked-intersection",
  "name": "Unmarked / uncontrolled intersection",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r72-r73", "title": "Giving way at an intersection without signs/signals; give way to the right (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s15-q1", "slot": "um_relative_position", "question_web": "Relative to the other vehicle, it approached from your:", "question_voice": "Did the other vehicle come from your right, your left, or opposite?", "answer_type": "enum", "options": ["my_right", "my_left", "opposite", "unsure"], "validation": "must be one option", "reprompt_max": 2},
    {"id": "s15-q2", "slot": "um_turning", "question_web": "At the intersection you were:", "question_voice": "Were you going straight or turning?", "answer_type": "enum", "options": ["straight", "turning_left", "turning_right"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "At an intersection without signs or signals, a driver must give way to a vehicle approaching from the right; a turning driver gives way to a vehicle going straight. Fault generally rests with the driver who failed to give way.", "favours": "vehicle_on_the_right_or_going_straight"},
  "exceptions": [
    {"id": "s15-e1", "probe_question": "Were there in fact any signs, lines or signals at the intersection?", "slot": "controls_present", "effect": "flag_unclear"},
    {"id": "s15-e2", "probe_question": "Was the give-way vehicle clearly already through the intersection first?", "slot": "other_through_first", "effect": "downgrade_band"}
  ],
  "damage_consistency_check": {"expected": "impact geometry consistent with the stated approach directions", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "other approached from my_left (you had right of way) AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND >=1 exception unconfirmed or present", "band": "possible"},
    {"when": "controls_present OR directions unsure OR damage inconsistent", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "At an intersection without signs or signals in NSW, drivers must give way to vehicles approaching from the right (and turning drivers give way to those going straight). Where the other vehicle came from your left and failed to give way, fault generally rests with that driver. Whether it applies depends on the full evidence. {{ATTACH:master}}", "text_voice": "At an intersection with no signs or lights in New South Wales, you give way to vehicles coming from your right. If the other vehicle came from your left and didn't give way, fault generally rests with them — though it depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This matches the give-way-to-the-right pattern, but a factor you've described can change it. A lawyer will review. {{ATTACH:master}}", "text_voice": "This looks like the give-way-to-the-right pattern, but something you mentioned can change it, so a lawyer will review. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "Where signs or signals were in fact present, or the approach directions aren't certain, fault isn't clear-cut and needs a lawyer's assessment. {{ATTACH:master}}", "text_voice": "If there were actually signs or signals, or the directions aren't certain, a lawyer will need to assess fault. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail to describe the usual pattern here. {{ATTACH:master}}", "text_voice": "I don't have enough detail yet. {{ATTACH:master}}"}
  ],
  "escalation_overrides": []
}
```

---

## Build checklist (same as Tier-1)
1. **Firm:** confirm/replace each `rule_citations`; approve `default_pattern` favours + output wording (bands only, no %).
2. **Build:** append the 5 objects to `scenarios[]`; add the 5 `accident_type` routing options; keep version `3.1.0` (or `3.2.0` if Tier-2 ships separately).
3. **Tests:** ≥2 acceptance cases per branch in `acceptance-tests.stage3.yaml`; keep the 75-test regression green.
4. **Audit (Opus):** determinism, band-only output, disclaimer attach, escalation overrides intact, no regression.
5. **Measure:** re-run the coverage backtest.

*Indicative spec. Fault principles and rule references are unverified starting points for the legal firm — not legal advice.*
