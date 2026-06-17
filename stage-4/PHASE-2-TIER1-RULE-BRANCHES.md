# Phase-2 Tier-1 Rule Branches — build spec
**Prepared by:** Fables (Cowork) · **Date:** 2026-06-14 · **For:** firm legal sign-off → Cursor/MiniMax build → Opus audit
**Target file:** append these objects to `scenarios[]` in `stage-3/app/data/rule-tree.nsw.v3.json` (bump version → `3.1.0`).

> **Architecture note (hybrid RAG + tree + human gate).** The tree is the *authoritative* fault decision; RAG is advisory only (sort free-text → scenario/slots; surface rule/precedent text to the human; draft text) and never sets a band. Each branch below is self-contained: entry questions, fault pattern, exceptions, damage check, band logic, verbatim outputs (band — **never a percentage** — + `{{ATTACH:master}}` disclaimer), and escalation overrides. The global 7 escalation triggers (serious injury, police, advice, multi-party, out-of-NSW, hit-run/impaired, no-consent) still apply on top of every branch.
>
> ⚠️ **All `rule_citations` below are UNVERIFIED indicative references for the firm to confirm or strike against the NSW Road Rules 2014 before launch.** They are never customer-facing.

---

## Classification routing (the "sort" step)
Before a branch runs, the engine sorts the case into a scenario from `accident_type` + a few discriminator slots. Add these `accident_type` options and routing:

| accident_type value | routes to |
|---|---|
| `car_park` | P2-01 |
| `intersection_signalised` | P2-02 |
| `turning_right` | P2-03 |
| `sideswipe_same_direction` | P2-04 |

If `accident_type` is free-text/ambiguous, the RAG classifier proposes a candidate scenario; the engine still confirms it via the branch's `classification_questions`. No match after reprompts → `insufficient` → human gate.

---

## P2-01 — Car-park / parking-lot manoeuvre
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
    {"id": "s7-q1", "slot": "cp_user_role", "question_web": "At the moment of impact you were:", "question_voice": "Were you driving along the lane, reversing out of a space, or pulling into one?", "answer_type": "enum", "options": ["driving_in_aisle", "reversing_from_bay", "entering_bay", "stationary"], "validation": "must be one option", "reprompt_max": 2},
    {"id": "s7-q2", "slot": "cp_other_role", "question_web": "The other vehicle was:", "question_voice": "And the other vehicle?", "answer_type": "enum", "options": ["driving_in_aisle", "reversing_from_bay", "entering_bay", "stationary"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "A vehicle in the through-aisle generally has priority over one reversing out of / entering a bay; the manoeuvring/reversing driver carries the duty to give way and reverse only when safe.", "favours": "aisle_vehicle"},
  "exceptions": [
    {"id": "s7-e1", "probe_question": "Was the aisle vehicle speeding or on the wrong side of the lane?", "slot": "aisle_at_fault_factor", "effect": "downgrade_band"},
    {"id": "s7-e2", "probe_question": "Were both vehicles reversing at the same time?", "slot": "both_reversing", "effect": "flag_unclear"}
  ],
  "damage_consistency_check": {"expected": "impact points consistent with stated roles (e.g. rear/corner of reversing car vs side/front of aisle car)", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "one party in aisle AND other reversing/entering AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND >=1 exception unconfirmed or present", "band": "possible"},
    {"when": "both_reversing OR damage inconsistent OR roles ambiguous", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "In most NSW car-park collisions, a vehicle travelling in the aisle generally has priority over one reversing out of or entering a parking bay, and the manoeuvring driver must give way and reverse only when safe. Your description matches this common pattern. Whether it applies here depends on the full evidence. {{ATTACH:master}}", "text_voice": "In most car-park collisions in New South Wales, the vehicle driving along the lane usually has priority over one reversing out of a space. What you've described looks like that common pattern, but whether it applies depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This matches the common car-park pattern, but a factor you've described can change how it's assessed. A lawyer will review the details. {{ATTACH:master}}", "text_voice": "This looks like the common car-park pattern, but something you mentioned can change how it's assessed, so a lawyer will look at the details. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "Car-park collisions where both vehicles were manoeuvring (or the damage doesn't clearly match) are not clear-cut. A lawyer will need to assess fault. {{ATTACH:master}}", "text_voice": "When both cars were moving in a car park, fault isn't clear-cut, so a lawyer will need to assess it. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail to describe the usual pattern here. {{ATTACH:master}}", "text_voice": "I don't have enough detail yet to describe the usual pattern. {{ATTACH:master}}"}
  ],
  "escalation_overrides": []
}
```

## P2-02 — Signalised (traffic-light) intersection
```json
{
  "id": "s8-signalised-intersection",
  "name": "Traffic-light intersection",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r56", "title": "Stopping / proceeding on a red or yellow light (verify)", "status": "UNVERIFIED"},
    {"rule": "r59", "title": "Proceeding on a green / green arrow (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s8-q1", "slot": "sig_user_light", "question_web": "As you entered the intersection, your light was:", "question_voice": "What colour was your traffic light as you entered?", "answer_type": "enum", "options": ["green", "yellow", "red", "green_arrow", "unsure"], "validation": "must be one option", "reprompt_max": 2},
    {"id": "s8-q2", "slot": "sig_user_movement", "question_web": "You were:", "question_voice": "Were you going straight, turning left, or turning right?", "answer_type": "enum", "options": ["straight", "turning_left", "turning_right"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "The driver who entered against a red light (or failed to give way on a turn against a green arrow/oncoming) generally bears fault; a driver proceeding lawfully on green is generally favoured.", "favours": "driver_with_green"},
  "exceptions": [
    {"id": "s8-e1", "probe_question": "Was your light yellow (not fully red) when you entered?", "slot": "entered_on_yellow", "effect": "downgrade_band"},
    {"id": "s8-e2", "probe_question": "Are you unsure what colour the light was?", "slot": "light_unsure", "effect": "flag_unclear"}
  ],
  "damage_consistency_check": {"expected": "impact geometry consistent with stated movements (e.g. front-to-side for a T-bone on a red-light entry)", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "user on green/green_arrow AND other entered on red AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND (entered_on_yellow OR exception unconfirmed)", "band": "possible"},
    {"when": "light_unsure on either side OR damage inconsistent", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "Where one driver proceeds lawfully on a green light and another enters against a red, fault in NSW generally rests with the driver who disobeyed the signal. Your description matches this pattern; whether it applies depends on the full evidence. {{ATTACH:master}}", "text_voice": "When one driver has a green light and the other goes through a red, fault in New South Wales usually rests with the driver who ran the red. That's what your description looks like, but it depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This resembles the signalised-intersection pattern, but the light timing you've described (e.g. entering on yellow) can change the assessment. A lawyer will review. {{ATTACH:master}}", "text_voice": "This looks like a traffic-light intersection case, but the timing you described can change things, so a lawyer will review it. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "When the light state isn't certain on one or both sides, fault isn't clear-cut and needs a lawyer's assessment. {{ATTACH:master}}", "text_voice": "If the light colour isn't certain, fault isn't clear-cut and needs a lawyer to assess it. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail about the signals to describe the usual pattern. {{ATTACH:master}}", "text_voice": "I don't have enough detail about the lights yet. {{ATTACH:master}}"}
  ],
  "escalation_overrides": []
}
```

## P2-03 — Right turn across oncoming traffic
```json
{
  "id": "s9-right-turn-oncoming",
  "name": "Right turn across oncoming traffic",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r62", "title": "Giving way when turning right at an intersection (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s9-q1", "slot": "rt_user_role", "question_web": "You were the driver:", "question_voice": "Were you the one turning right, or the one going straight through?", "answer_type": "enum", "options": ["turning_right", "going_straight", "unsure"], "validation": "must be one option", "reprompt_max": 2},
    {"id": "s9-q2", "slot": "rt_signal", "question_web": "If lights were present, the turning driver had:", "question_voice": "Were there lights, and did the turning driver have a green arrow?", "answer_type": "enum", "options": ["green_arrow", "green_no_arrow", "no_lights", "unsure"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "A driver turning right across the path of oncoming traffic must give way to that traffic (absent a green arrow in their favour); fault generally rests with the turning driver.", "favours": "straight_through_driver"},
  "exceptions": [
    {"id": "s9-e1", "probe_question": "Did the turning driver have a green turn arrow?", "slot": "had_green_arrow", "effect": "flag_unclear"},
    {"id": "s9-e2", "probe_question": "Was the oncoming driver speeding or running a red?", "slot": "oncoming_at_fault_factor", "effect": "downgrade_band"}
  ],
  "damage_consistency_check": {"expected": "front of straight-through vehicle to side/front of turning vehicle", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "user going_straight AND other turning_right AND no green_arrow AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND >=1 exception unconfirmed or present", "band": "possible"},
    {"when": "had_green_arrow OR roles unsure OR damage inconsistent", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "A driver turning right across oncoming traffic in NSW must give way to that traffic. Where you were proceeding straight and the other driver turned across your path, fault generally rests with the turning driver. Whether it applies depends on the full evidence. {{ATTACH:master}}", "text_voice": "A driver turning right has to give way to oncoming traffic in New South Wales. If you were going straight and they turned across you, fault usually rests with the turning driver — though it depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This matches the right-turn give-way pattern, but a factor you've described can change it. A lawyer will review. {{ATTACH:master}}", "text_voice": "This looks like the right-turn pattern, but something you mentioned can change it, so a lawyer will review. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "Where the turning driver had a green arrow, or roles aren't certain, fault isn't clear-cut and needs a lawyer's assessment. {{ATTACH:master}}", "text_voice": "If the turning driver had a green arrow, or the roles aren't certain, a lawyer will need to assess fault. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail to describe the usual pattern here. {{ATTACH:master}}", "text_voice": "I don't have enough detail yet. {{ATTACH:master}}"}
  ],
  "escalation_overrides": []
}
```

## P2-04 — Sideswipe, both vehicles moving same direction
```json
{
  "id": "s10-sideswipe-same-direction",
  "name": "Sideswipe (same direction)",
  "status": "PHASE2_DRAFT_UNVERIFIED",
  "rule_citations": [
    {"rule": "r146", "title": "Driving within a single marked lane (verify)", "status": "UNVERIFIED"},
    {"rule": "r148", "title": "Changing lanes / giving way when moving laterally (verify)", "status": "UNVERIFIED"}
  ],
  "classification_questions": [
    {"id": "s10-q1", "slot": "ss_user_lane", "question_web": "At impact you were:", "question_voice": "Were you keeping to your lane, or moving across into another lane?", "answer_type": "enum", "options": ["holding_lane", "changing_lane", "unsure"], "validation": "must be one option", "reprompt_max": 2},
    {"id": "s10-q2", "slot": "ss_other_lane", "question_web": "The other vehicle was:", "question_voice": "And the other vehicle?", "answer_type": "enum", "options": ["holding_lane", "changing_lane", "unsure"], "validation": "must be one option", "reprompt_max": 2}
  ],
  "default_pattern": {"description": "On a multi-lane road, the driver who left their lane / changed lanes generally bears the duty to ensure it was clear; fault favours the driver who held their lane.", "favours": "lane_holding_driver"},
  "exceptions": [
    {"id": "s10-e1", "probe_question": "Were both vehicles moving toward each other's lane at the same time?", "slot": "both_changing", "effect": "flag_unclear"},
    {"id": "s10-e2", "probe_question": "Was the lane-holding driver partly over the line too?", "slot": "holder_over_line", "effect": "downgrade_band"}
  ],
  "damage_consistency_check": {"expected": "lateral/side damage consistent with one vehicle moving into the other's lane", "on_mismatch": "band cannot exceed 'unclear'"},
  "band_logic": [
    {"when": "user holding_lane AND other changing_lane AND no exceptions AND damage consistent", "band": "likely"},
    {"when": "pattern matched AND >=1 exception unconfirmed or present", "band": "possible"},
    {"when": "both_changing OR either lane unsure OR damage inconsistent", "band": "unclear"},
    {"when": "classification questions incomplete after reprompts", "band": "insufficient"}
  ],
  "outputs": [
    {"band": "likely", "text_web": "On a multi-lane road in NSW, a driver changing lanes must ensure the lane is clear. Where you held your lane and the other vehicle moved into it, fault generally rests with the lane-changing driver. Whether it applies depends on the full evidence. {{ATTACH:master}}", "text_voice": "On a multi-lane road in New South Wales, a driver changing lanes has to make sure it's clear. If you held your lane and they moved into it, fault usually rests with the lane-changer — though it depends on the full evidence. {{ATTACH:master}}"},
    {"band": "possible", "text_web": "This matches the lane-change sideswipe pattern, but a factor you've described can change it. A lawyer will review. {{ATTACH:master}}", "text_voice": "This looks like a lane-change sideswipe, but something you mentioned can change it, so a lawyer will review. {{ATTACH:master}}"},
    {"band": "unclear", "text_web": "Where both vehicles moved laterally (or the lanes aren't certain), fault isn't clear-cut and needs a lawyer's assessment. {{ATTACH:master}}", "text_voice": "If both cars were moving across, fault isn't clear-cut and a lawyer will need to assess it. {{ATTACH:master}}"},
    {"band": "insufficient", "text_web": "I don't yet have enough detail to describe the usual pattern here. {{ATTACH:master}}", "text_voice": "I don't have enough detail yet. {{ATTACH:master}}"}
  ],
  "escalation_overrides": []
}
```

---

## Build checklist (per branch)
1. **Firm:** confirm/replace each `rule_citations` entry against the Road Rules 2014; approve the `default_pattern` favours + output wording (bands only, no %).
2. **Build (Cursor/MiniMax):** add the 4 objects to `scenarios[]`; add the new `accident_type` options + routing; bump rule-tree to `3.1.0`.
3. **Tests:** add ≥2 acceptance cases per branch (a clear `likely` + an `unclear`/exception path) to `acceptance-tests.stage3.yaml`; keep the existing 75 green (regression gate).
4. **Audit (Opus):** verify determinism, band-only output, disclaimer attach, escalation overrides intact, no regression.
5. **Measure:** re-run the coverage backtest against historical claims to quantify the lift from ~70–85%.

*Indicative spec. Fault principles and rule references are unverified starting points for the legal firm — not legal advice.*
