# ClaimDesk 247 — Complete Question Tree (Optus Audit)

**Date:** 2026-07-15
**Purpose:** External audit of every question the engine asks a customer,
across all four claim types, and the band logic each scenario applies.

**Engine:** https://claimdesk247-engine.vercel.app/healthz
**Customer site:** https://claimdesk247.com.au/intake
**Operator:** ClaimDesk 247 · Powered by Goldman Forge

---

## How the engine decides what to ask

Two-tier question flow:

1. **Fixed slots** — same for every customer in a claim type. e.g. every
   PD intake asks for state, collision type, vehicles, etc.
2. **Scenario-specific classification questions** — fired AFTER the fixed
   slots, depending on which accident scenario was resolved. e.g. rear-end
   asks user_position + brake_lights; reversing asks user_action + both_moving.

Escalations (injury, fraud, multiparty, etc.) can fire at any point and
short-circuit further questions — those customers go straight to a human.

---

## Tier 1 — Fixed slots (asked in order, per claim type)

### Motor (NSW only — IDs 1-14)

Traditional fault-band engine. Customer reports their own accident.

  [  1] state_of_accident (enum) (required) — options: NSW, VIC, QLD, WA, SA, TAS, ACT, NT, outside_nsw
  [  2] datetime_location (text) (required)
  [  3] accident_type (enum) (required) — options: rear-end, T-intersection, roundabout, merge, reversing, car_park, parked_hit, intersection_signalised, turning_right, sideswipe_same_direction, multi_vehicle, not_listed
  [  4] user_vehicle (text) (required)
  [  5] other_vehicles (text) (required)
  [  6] movement_description (text) (required)
  [  7] damage_locations (multienum) (required) — options: front, rear, left, right, multiple
  [  8] control_devices (enum) (required) — options: lights, give-way, stop, roundabout, none
  [  9] police_attendance (enum) (required) — options: yes, no, unsure
  [ 10] witnesses (text) (optional)
  [ 11] dashcam (enum) (optional) — options: yours, theirs, neither, unsure
  [ 12] photos_taken (enum) (optional) — options: yes, no
  [ 13] other_driver_details (text) (optional)
  [ 14] injuries (enum) (required) — options: none, minor, serious

**Frontend variant** inserts the claim_type question (id 100) after state
so the customer picks motor/PL/PD/med-neg up front.

**Scenario routing** (after the 14 slots, one of these scenarios is picked
based on `accident_type`):

- `s1-rear-end` — Rear-end collision
- `s2-giveway-t` — Give way / T-intersection
- `s3-roundabout` — Roundabout
- `s4-lane-merge` — Lane change / merge
- `s5-reversing` — Reversing
- `s6-multi-chain` — Multi-vehicle / chain
- `s7-car-park` — Car park / parking-lot manoeuvre
- `s8-signalised-intersection` — Traffic-light intersection
- `s9-right-turn-oncoming` — Right turn across oncoming traffic
- `s10-sideswipe-same-direction` — Sideswipe (same direction)
- `s11-parked-vehicle` — Parked / stationary vehicle struck

### Property Damage (NSW live; 7 other AU states unsigned) — IDs 1, 100, 400-416

Recovery-framed: not-at-fault driver recovers repair + hire + towing from
the at-fault driver's comprehensive insurer (Arsalan v Rixon).

  [  1] state_of_accident (enum) (required) — options: NSW, VIC, QLD, WA, SA, TAS, ACT, NT, outside_nsw
  [100] claim_type (enum) (required) — options: motor, property_damage, public_liability, medical_negligence
  [400] collision_type (enum) (required) — options: rear-end, T-intersection, give_way, reversing, parked_hit, parking, sideswipe_same_direction, lane_change, car_park, other
  [401] incident_date (text) (required)
  [402] user_vehicle (text) (required)
  [403] other_vehicles (text) (required)
  [404] movement_description (text) (required)
  [405] damage_locations (multienum) (required) — options: front, rear, left, right, multiple
  [406] police_attendance (enum) (required) — options: yes, no, unsure
  [407] police_event_number (text) (optional)
  [408] witnesses (text) (optional)
  [409] dashcam (enum) (optional) — options: yours, theirs, neither, unsure
  [410] photos_taken (enum) (optional) — options: yes, no
  [411] other_driver_details (text) (required)
  [412] at_fault_uninsured (enum) (required) — options: yes, no, unsure
  [413] repairer_quote (text) (optional)
  [414] vehicle_class (enum) (optional) — options: small, sedan, suv_4wd, ute_van, prestige_luxury, commercial_heavy, unsure
  [415] hire_need (enum) (optional) — options: yes_needed, no_not_needed, unsure
  [416] injuries (enum) (required) — options: none, minor, serious

**Scenario routing** (after the slots, based on `collision_type`):

- `pd1-rear-end` — Rear-end collision (not at fault)
- `pd2-failure-to-give-way` — Failure to give way (T-intersection / give-way sign)
- `pd3-reversing` — Reversing collision
- `pd4-parked-vehicle-struck` — Parked/stationary vehicle struck
- `pd5-changing-lanes-sideswipe` — Changing lanes / sideswipe (same direction)
- `pd6-car-park` — Car-park manoeuvre collision
- `pd7-other` — Other collision type (catch-all)

### Public Liability (NSW only — IDs 1, 100, 200-209)

Slip/trip/fall in a public place. NSW-only by design.

  [  1] state_of_accident (enum) (required) — options: NSW, outside_nsw
  [100] claim_type (enum) (required) — options: motor, public_liability, medical_negligence
  [200] incident_date (text) (required)
  [201] pl_location (enum) (required) — options: supermarket, shopping_centre, footpath_council, private_premises, workplace, construction_site, rental_property, commercial_premises, stairwell, car_park, corridor, other
  [202] hazard_type (enum) (required) — options: wet_surface, spill, rain_tracked, cleaning, uneven_surface, broken_pavement, mat, cabling, step, pothole, falling_object, stock, signage, inadequate_lighting, defective_premises, broken_rail, broken_stair, fixture, other_public_place, other
  [203] hazard_warned (enum) (required) — options: yes, no, unsure
  [204] hazard_duration (enum) (required) — options: just_happened, short, long, extended, 30min_plus, unsure
  [205] claimant_activity (enum) (optional) — options: walking_normally, rushing, carrying_items, on_phone, browsing, working, other
  [206] defendant_type (enum) (optional) — options: private_occupier, council, public_authority, government, business, unknown
  [207] at_work (enum) (optional) — options: yes, no, unsure
  [208] harm_severity (enum) (required) — options: none, minor, serious, permanent_impairment, death
  [209] injuries (enum) (required) — options: none, minor, serious

**Scenario routing** (based on `hazard_type`):

- `pl1-slip-wet-surface` — Slip on a wet surface
- `pl2-trip-uneven-surface` — Trip on an uneven surface
- `pl3-falling-object` — Struck by a falling object
- `pl4-inadequate-lighting` — Incident caused by inadequate lighting
- `pl5-defective-premises` — Injury caused by defective premises
- `pl6-other-public-place` — Other public-place injury (catch-all)

### Medical Negligence (NSW only — IDs 1, 100, 300-309)

Escalation-dominant: the slots exist to structure the case file for the
lawyer; no med-neg scenario ever emits a band.

  [  1] state_of_accident (enum) (required) — options: NSW, outside_nsw
  [100] claim_type (enum) (required) — options: motor, public_liability, medical_negligence
  [300] provider_type (enum) (required) — options: gp, hospital, specialist, surgeon, dentist, cosmetic, pharmacy, birth_centre, other
  [301] provider_public_private (enum) (optional) — options: public, private, unsure
  [302] treatment_type (enum) (required) — options: surgical_outcome, misdiagnosis_delay, medication_error, birth_injury, cosmetic, dental, consent_not_informed, other
  [303] incident_date (text) (required)
  [304] harm_severity (enum) (required) — options: none, minor, serious, permanent_impairment, death
  [305] outcome_nature (enum) (required) — options: unexpected_outcome, suspected_error, not_sure, communication_only
  [306] second_opinion (enum) (optional) — options: yes, no, not_yet
  [307] at_work (enum) (optional) — options: yes, no, unsure
  [308] multiple_providers (enum) (optional) — options: yes, no, unsure
  [309] injuries (enum) (required) — options: none, minor, serious

**Scenario routing** (based on `treatment_type`):

- `mn1-surgical-outcome` — Surgical outcome
- `mn2-misdiagnosis-delay` — Misdiagnosis or delayed diagnosis
- `mn3-medication-error` — Medication error
- `mn4-birth-injury` — Birth injury
- `mn5-cosmetic-dental` — Cosmetic or dental treatment
- `mn6-consent-not-informed` — Consent — not informed
- `mn7-other` — Other medical-treatment matter (catch-all)

---

## Tier 2 — Scenario classification questions

These fire AFTER the fixed slots, one at a time, when the customer's
accident_type / collision_type / hazard_type / treatment_type resolves to a
specific scenario. They drive the band (`likely` / `possible` / `unclear`).

### Motor (NSW)

#### `s1-rear-end` — Rear-end collision

- **user_position** (enum): In the collision, your vehicle was:  options: front, behind, middle_of_chain
- **user_motion** (enum): Just before impact, your vehicle was:  options: stopped, moving, slowing
- **chain_count** (integer): Total vehicles involved:

  _Band logic:_ [{'when': 'pattern matched AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'pattern matched AND >=1 exception unconfirmed or present', 'band': 'possible'}, {'when': 'any flag_unclear exception OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s2-giveway-t` — Give way / T-intersection

- **road_layout** (enum): The intersection was:  options: give_way_sign_or_line, t_intersection, stop_sign, unmarked
- **user_road_type** (enum): Your vehicle was on:  options: terminating_road, through_road, unsure
- **user_motion** (enum): Just before impact, your vehicle was:  options: moving, stopped, slowing
- **other_vehicle_motion** (enum): The other vehicle was:  options: already_through, entering_same_time, unsure

  _Band logic:_ [{'when': 'user on terminating road AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'user on through road AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'user on terminating road AND >=1 exception present (sight, signage, simultaneous) AND damage consistent', 'band': 'possible'}, {'when': 'traffic lights override OR simultaneous entry AND damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s3-roundabout` — Roundabout

- **collision_location** (enum): The contact happened:  options: on_entry, while_circulating, on_exit
- **user_indicating** (enum): Your vehicle's indicators:  options: indicated_left_exit, indicated_only_entry, no_indication, unsure
- **other_indicating** (enum): The other vehicle's indicators:  options: indicated, no_indication, unsure
- **lane_count** (enum): At the point of contact, the roundabout was:  options: single_lane, multi_lane, unsure

  _Band logic:_ [{'when': 'contact on entry AND user entering AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'contact on entry AND >=1 exception present AND damage consistent', 'band': 'possible'}, {'when': 'contact while circulating or on exit AND failure to indicate (either party) AND damage consistent', 'band': 'possible'}, {'when': 'multi_lane conflict OR simultaneous entry OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s4-lane-merge` — Lane change / merge

- **merge_type** (enum): The situation was:  options: lane_change_marked, zip_merge, unsure
- **user_indicating** (enum): Your vehicle's indicator:  options: indicated, no_indication, unsure
- **other_indicating** (enum): The other vehicle's indicator:  options: indicated, no_indication, unsure
- **user_position_relative** (enum): Your vehicle was:  options: changing_into_their_lane, they_changing_into_yours, both_changing, unsure

  _Band logic:_ [{'when': 'user changing into other lane AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'zip merge AND user behind AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'user changing into other lane AND >=1 exception present (indication, simultaneous, solid line) AND damage consistent', 'band': 'possible'}, {'when': "other vehicle's unannounced move AND user established in lane", 'band': 'possible'}, {'when': 'simultaneous change OR layout dispute OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s5-reversing` — Reversing

- **user_motion** (enum): At the moment of impact, which vehicle was reversing:  options: i_was_reversing, they_were_reversing, both_reversing, unsure
- **location_type** (enum): The location was:  options: car_park, driveway, street, private_property, other
- **user_visibility** (enum): Your view to the rear was:  options: clear, partially_obstructed, very_obstructed, unsure
- **other_vehicle_state** (enum): The other vehicle was:  options: parked_stationary, moving, also_reversing, unsure

  _Band logic:_ [{'when': 'user reversing AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'user reversing AND >=1 exception present (obstruction, other unannounced move, low speed) AND damage consistent', 'band': 'possible'}, {'when': 'other vehicle reversing AND user stationary/legitimately positioned AND damage consistent', 'band': 'likely'}, {'when': 'both reversing OR low speed both moving OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s6-multi-chain` — Multi-vehicle / chain

- **chain_count** (integer): Total vehicles involved:
- **user_position** (enum): Your vehicle's position in the chain:  options: front, middle, back, side_swiped
- **user_motion** (enum): Just before the first impact to your vehicle, you were:  options: moving, stopped, being_pushed, slowing
- **chain_mechanism** (enum): The chain started with:  options: rear_hit_front, i_was_pushed_forward, side_impact_to_chain, unsure

  _Band logic:_ [{'when': 'user clearly rear-ended by another AND user stopped AND no exceptions', 'band': 'possible'}, {'when': 'user middle of chain AND pushed forward AND no exceptions', 'band': 'unclear'}, {'when': '>=1 exception present OR chain mechanism unclear OR damage inconsistent', 'band': 'unclear'}, {'when': 'chain_count >= 3', 'route': 'esc-multiparty', 'pre_band': True}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s7-car-park` — Car park / parking-lot manoeuvre

- **cp_user_role** (enum): At the moment of impact you were:  options: driving_in_aisle, reversing_from_bay, entering_bay, stationary
- **cp_other_role** (enum): The other vehicle was:  options: driving_in_aisle, reversing_from_bay, entering_bay, stationary

  _Band logic:_ [{'when': 'one party in aisle AND other reversing/entering AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'pattern matched AND >=1 exception unconfirmed or present', 'band': 'possible'}, {'when': 'both_reversing OR damage inconsistent OR roles ambiguous', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s8-signalised-intersection` — Traffic-light intersection

- **sig_user_light** (enum): As you entered the intersection, your light was:  options: green, yellow, red, green_arrow, unsure
- **sig_user_movement** (enum): You were:  options: straight, turning_left, turning_right

  _Band logic:_ [{'when': 'user on green/green_arrow AND other entered on red AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'pattern matched AND (entered_on_yellow OR exception unconfirmed)', 'band': 'possible'}, {'when': 'light_unsure on either side OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s9-right-turn-oncoming` — Right turn across oncoming traffic

- **rt_user_role** (enum): You were the driver:  options: turning_right, going_straight, unsure
- **rt_signal** (enum): If lights were present, the turning driver had:  options: green_arrow, green_no_arrow, no_lights, unsure

  _Band logic:_ [{'when': 'user going_straight AND other turning_right AND no green_arrow AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'pattern matched AND >=1 exception unconfirmed or present', 'band': 'possible'}, {'when': 'had_green_arrow OR roles unsure OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s10-sideswipe-same-direction` — Sideswipe (same direction)

- **ss_user_lane** (enum): At impact you were:  options: holding_lane, changing_lane, unsure
- **ss_other_lane** (enum): The other vehicle was:  options: holding_lane, changing_lane, unsure

  _Band logic:_ [{'when': 'user holding_lane AND other changing_lane AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'pattern matched AND >=1 exception unconfirmed or present', 'band': 'possible'}, {'when': 'both_changing OR either lane unsure OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `s11-parked-vehicle` — Parked / stationary vehicle struck

- **pv_user_motion** (enum): When the collision happened, your vehicle was:  options: parked_stationary, just_stopped, moving
- **pv_parking_legal** (enum): Was your vehicle parked legally (a marked or permitted spot, not blocking traffic)?  options: yes, no, unsure
- **pv_occupant** (enum): Was anyone inside your vehicle at the time?  options: yes, no

  _Band logic:_ [{'when': 'user parked/stationary AND parked legally AND no exceptions AND damage consistent', 'band': 'likely'}, {'when': 'pattern matched AND (parked illegally OR exception present)', 'band': 'possible'}, {'when': 'user still moving OR parking legality unsure OR door opened into traffic OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]


### Property Damage (NSW)

#### `pd1-rear-end` — Rear-end collision (not at fault)

- **user_position** (enum): In the collision, your vehicle was:  options: front, behind, middle_of_chain
- **user_motion** (enum): Just before impact, your vehicle was:  options: stopped, moving, slowing
- **chain_count** (integer): How many vehicles were involved altogether?

  _Band logic:_ [{'when': 'user was the front/stopped vehicle, no exceptions, damage consistent', 'band': 'likely'}, {'when': '1+ downgrade exception (sudden braking / brake lights)', 'band': 'possible'}, {'when': 'flag_unclear exception OR damage inconsistent', 'band': 'unclear'}, {'when': 'classification incomplete after reprompts', 'band': 'insufficient'}]

#### `pd2-failure-to-give-way` — Failure to give way (T-intersection / give-way sign)

- **road_layout** (enum): The intersection was:  options: give_way_sign_or_line, t_intersection, stop_sign, unmarked
- **user_road_type** (enum): Your vehicle was on:  options: terminating_road, through_road, unsure
- **sight_lines** (enum): How were the sight lines?  options: clear, obstructed, disputed

  _Band logic:_ [{'when': 'user on through road, no exceptions, damage consistent', 'band': 'likely'}, {'when': 'sight lines obstructed', 'band': 'possible'}, {'when': 'simultaneous entry OR damage inconsistent', 'band': 'unclear'}, {'when': 'incomplete', 'band': 'insufficient'}]

#### `pd3-reversing` — Reversing collision

- **user_action** (enum): What was your vehicle doing?  options: reversing, stationary, moving_forward, parked
- **other_vehicle_state** (enum): What was the other vehicle doing?  options: reversing, stationary, moving_forward, parked
- **location_type** (enum): Where did it happen?  options: road, car_park, driveway, other

  _Band logic:_ [{'when': 'other vehicle reversing, user stationary/forward, no exceptions', 'band': 'likely'}, {'when': 'both moving', 'band': 'unclear'}, {'when': 'user reversing', 'band': 'possible'}, {'when': 'incomplete', 'band': 'insufficient'}]

#### `pd4-parked-vehicle-struck` — Parked/stationary vehicle struck

- **pv_user_motion** (enum): Was your vehicle parked/stationary or moving when it was hit?  options: parked_stationary, just_stopped, moving
- **pv_parking_legal** (enum): Were you parked legally?  options: yes, no, unsure

  _Band logic:_ [{'when': 'parked/stationary, legally parked, no exceptions', 'band': 'likely'}, {'when': 'parked illegally / obstructing', 'band': 'possible'}, {'when': 'moving when struck OR unsure', 'band': 'unclear'}, {'when': 'incomplete', 'band': 'insufficient'}]

#### `pd5-changing-lanes-sideswipe` — Changing lanes / sideswipe (same direction)

- **ss_user_lane** (enum): Were you holding your lane or changing lanes?  options: holding_lane, changing_lane, unsure
- **ss_other_lane** (enum): Was the other driver holding their lane or changing lanes?  options: holding_lane, changing_lane, unsure

  _Band logic:_ [{'when': 'user holding lane, other changing lanes, no exceptions', 'band': 'likely'}, {'when': 'user changing lanes', 'band': 'possible'}, {'when': 'both changing OR unsure', 'band': 'unclear'}, {'when': 'incomplete', 'band': 'insufficient'}]

#### `pd6-car-park` — Car-park manoeuvre collision

- **cp_user_role** (enum): What were you doing in the car park?  options: driving_in_aisle, reversing_from_bay, entering_bay, stationary
- **cp_other_role** (enum): What was the other driver doing?  options: driving_in_aisle, reversing_from_bay, entering_bay, stationary

  _Band logic:_ [{'when': 'user in aisle, other manoeuvring, no exceptions', 'band': 'likely'}, {'when': 'aisle vehicle too fast', 'band': 'possible'}, {'when': 'both manoeuvring OR unsure', 'band': 'unclear'}, {'when': 'incomplete', 'band': 'insufficient'}]

#### `pd7-other` — Other collision type (catch-all)

_No classification questions — band comes from fixed slots or scenario is escalation-only._


### Public Liability (NSW)

#### `pl1-slip-wet-surface` — Slip on a wet surface

- **pl_location** (enum): Where did the slip happen?  options: supermarket, shopping_centre, footpath_council, private_premises, workplace, other
- **hazard_type** (enum): What made the surface wet?  options: spill, cleaning, rain_tracked, condensation, other
- **hazard_warned** (enum): Was there a wet-floor sign or warning?  options: yes, no, unsure
- **hazard_duration** (enum): How long do you think the hazard had been there?  options: just_happened, short, long, extended, 30min_plus, unsure
- **claimant_activity** (enum): What were you doing at the time?  options: walking_normally, rushing, carrying_items, on_phone, other

  _Band logic:_ [{'when': 'long-present hazard AND no warning AND claimant acting reasonably', 'band': 'likely'}, {'when': 'warning given OR short duration OR contributory factors', 'band': 'possible'}, {'when': 'transient hazard with prompt response', 'band': 'unclear'}, {'when': 'classification questions incomplete after reprompts', 'band': 'insufficient'}]

#### `pl2-trip-uneven-surface` — Trip on an uneven surface

- **pl_location** (enum): Where did the trip happen?  options: supermarket, shopping_centre, footpath_council, private_premises, workplace, other
- **hazard_type** (enum): What did you trip on?  options: broken_pavement, mat, cabling, step, pothole, other
- **hazard_warned** (enum): Was the hazard marked or warned about?  options: yes, no, unsure
- **hazard_duration** (enum): How long had the hazard been there, as far as you know?  options: just_happened, short, long, extended, 30min_plus, unsure
- **claimant_activity** (enum): What were you doing at the time?  options: walking_normally, rushing, carrying_items, on_phone, other

  _Band logic:_ [{'when': 'long-present defect AND no warning AND claimant acting reasonably', 'band': 'likely'}, {'when': 'warning OR short duration OR contributory factors', 'band': 'possible'}, {'when': 'trivial defect or trivial-damage dispute', 'band': 'unclear'}, {'when': 'classification questions incomplete', 'band': 'insufficient'}]

#### `pl3-falling-object` — Struck by a falling object

- **pl_location** (enum): Where did it happen?  options: supermarket, shopping_centre, construction_site, private_premises, workplace, other
- **hazard_type** (enum): What kind of object fell or struck you?  options: stock, signage, structure, fixture, other
- **hazard_warned** (enum): Was there any warning or barrier?  options: yes, no, unsure
- **claimant_activity** (enum): What were you doing at the time?  options: walking_normally, browsing, working, other

  _Band logic:_ [{'when': 'unsecured object AND no warning AND claimant not at fault', 'band': 'likely'}, {'when': 'contributory factors', 'band': 'possible'}, {'when': 'unclear how object fell', 'band': 'unclear'}, {'when': 'incomplete', 'band': 'insufficient'}]

#### `pl4-inadequate-lighting` — Incident caused by inadequate lighting

- **pl_location** (enum): Where did it happen?  options: stairwell, car_park, corridor, footpath_council, private_premises, other
- **lighting_state** (enum): How would you describe the lighting?  options: none, very_poor, partial_failure, flickering, other
- **hazard_warned** (enum): Was there any warning about the lighting or hazard?  options: yes, no, unsure
- **hazard_duration** (enum): Was the poor lighting an ongoing issue?  options: one_off, short, long, extended, unsure

  _Band logic:_ [{'when': 'ongoing poor lighting AND no warning', 'band': 'likely'}, {'when': 'contributory factors', 'band': 'possible'}, {'when': 'one-off outage', 'band': 'unclear'}, {'when': 'incomplete', 'band': 'insufficient'}]

#### `pl5-defective-premises` — Injury caused by defective premises

- **pl_location** (enum): Where did it happen?  options: private_premises, rental_property, commercial_premises, footpath_council, other
- **hazard_type** (enum): What was defective?  options: broken_rail, broken_stair, fixture, structural, other
- **hazard_warned** (enum): Was the defect known or reported before?  options: yes_reported, no, unsure
- **hazard_duration** (enum): How long had it been defective?  options: just_happened, short, long, extended, unsure

  _Band logic:_ [{'when': 'long-present defect AND known/not remedied', 'band': 'likely'}, {'when': 'contributory factors', 'band': 'possible'}, {'when': 'recent/sudden failure', 'band': 'unclear'}, {'when': 'incomplete', 'band': 'insufficient'}]

#### `pl6-other-public-place` — Other public-place injury (catch-all)

_No classification questions — band comes from fixed slots or scenario is escalation-only._


### Medical Negligence (NSW)

#### `mn1-surgical-outcome` — Surgical outcome

- **provider_type** (enum): Who provided the treatment?  options: gp, hospital, specialist, surgeon, dentist, cosmetic, other
- **provider_public_private** (enum): Was the provider public or private?  options: public, private, unsure
- **incident_date** (text): When did it happen?
- **harm_severity** (enum): What harm did you suffer?  options: none, minor, serious, permanent_impairment, death
- **outcome_nature** (enum): Was it an unexpected outcome or what you believe was an error?  options: unexpected_outcome, suspected_error, not_sure
- **second_opinion** (enum): Have you had a second medical opinion?  options: yes, no, not_yet

  _Band logic:_ [{'when': 'harm_severity = none', 'band': 'unclear', 'note': 'no compensable damage — still human-reviewed'}, {'when': 'otherwise', 'band': 'unclear', 'note': 'escalation-dominant: medneg-requires-assessment'}]

#### `mn2-misdiagnosis-delay` — Misdiagnosis or delayed diagnosis

- **provider_type** (enum): Who provided the diagnosis/treatment?  options: gp, hospital, specialist, other
- **incident_date** (text): When was the (mis/delayed) diagnosis?
- **harm_severity** (enum): What harm did the delay cause?  options: none, minor, serious, permanent_impairment, death
- **outcome_nature** (enum): How would you describe it?  options: misdiagnosis, delayed_diagnosis, missed_diagnosis, not_sure
- **second_opinion** (enum): Have you had a second opinion?  options: yes, no, not_yet

  _Band logic:_ [{'when': 'harm_severity = none', 'band': 'unclear'}, {'when': 'otherwise', 'band': 'unclear', 'note': 'medneg-requires-assessment'}]

#### `mn3-medication-error` — Medication error

- **provider_type** (enum): Where did the error occur?  options: hospital, pharmacy, gp, specialist, other
- **incident_date** (text): When did it happen?
- **harm_severity** (enum): What harm did you suffer?  options: none, minor, serious, permanent_impairment, death
- **outcome_nature** (enum): What kind of error?  options: wrong_drug, wrong_dose, allergy_ignored, interaction, not_sure

  _Band logic:_ [{'when': 'harm_severity = none', 'band': 'unclear'}, {'when': 'otherwise', 'band': 'unclear', 'note': 'medneg-requires-assessment'}]

#### `mn4-birth-injury` — Birth injury

- **provider_type** (enum): Where did the birth/care take place?  options: hospital, birth_centre, home, other
- **incident_date** (text): When did it happen?
- **harm_severity** (enum): Who was harmed and how seriously?  options: minor, serious, permanent_impairment, death

  _Band logic:_ [{'when': 'always', 'band': 'unclear', 'note': 'always escalate as esc-serious-injury'}]

#### `mn5-cosmetic-dental` — Cosmetic or dental treatment

- **provider_type** (enum): Who provided the treatment?  options: dentist, cosmetic, other
- **incident_date** (text): When did it happen?
- **harm_severity** (enum): What harm did you suffer?  options: none, minor, serious, permanent_impairment
- **outcome_nature** (enum): What went wrong?  options: unexpected_outcome, suspected_error, not_sure

  _Band logic:_ [{'when': 'harm_severity = none', 'band': 'unclear'}, {'when': 'otherwise', 'band': 'unclear', 'note': 'medneg-requires-assessment'}]

#### `mn6-consent-not-informed` — Consent — not informed

- **provider_type** (enum): Who provided the treatment?  options: gp, hospital, specialist, surgeon, dentist, cosmetic, other
- **incident_date** (text): When did it happen?
- **harm_severity** (enum): What harm did you suffer?  options: none, minor, serious, permanent_impairment, death
- **outcome_nature** (text): What risk do you believe wasn't disclosed?

  _Band logic:_ [{'when': 'always', 'band': 'unclear', 'note': 'medneg-requires-assessment'}]

#### `mn7-other` — Other medical-treatment matter (catch-all)

- **provider_type** (enum): Who provided the treatment?  options: gp, hospital, specialist, dentist, cosmetic, other
- **incident_date** (text): When did it happen?
- **harm_severity** (enum): What harm did you suffer?  options: none, minor, serious, permanent_impairment, death

  _Band logic:_ [{'when': 'always', 'band': 'unclear', 'note': 'medneg-requires-assessment'}]


---

## Escalation triggers (any time, any claim type)

These short-circuit the question flow. Customer goes straight to a human.

- **esc-injury** — any injury mention (slot value ≠ 'none'/absent). Hard
  firewall: never banded, never monetised. Goes to law-firm partner.
- **esc-hitrun** — hit-and-run indicated
- **esc-vulnerable** — pedestrian or cyclist involved
- **esc-fraud** — story inconsistency, rego mismatch, third-party pressure
- **esc-multiparty** — 3+ vehicles in chain
- **esc-advice** — customer asks for legal advice directly
- **esc-serious-injury** — harm_severity includes death or permanent impairment
- **esc-workers-comp** — PL/med-neg, injury at work
- **esc-govt-defendant** — PL/med-neg, defendant is a public authority
- **esc-limitation** — incident beyond the limitation horizon
  (NT 3yr - 6mo buffer; all other AU states 6yr - 6mo buffer)
- **esc-uninsured-driver** — motor + PD: at-fault driver uninsured

---

## Band enum (the only values the engine ever emits)

- **likely** — the recovery is clearly supported by the facts
- **possible** — recovery is plausible but contested
- **unclear** — facts don't deterministically resolve
- **insufficient** — incomplete intake; customer needs to provide more

The engine NEVER emits a numeric fault percentage. The band is general
information, not legal advice.

---

## Sign-off state (live NSW trees)

| Tree | Live | Signed scenarios | Hash |
|---|---|---|---|
| NSW motor | ✅ live | 11/11 | `3964e668d905…` |
| NSW property_damage | ✅ live | 7/7 | `1f13febaf6c0…` |
| NSW public_liability | ✅ live | 6/6 | `dc824c3559ab…` |
| NSW medical_negligence | ✅ live | 7/7 | `4e3fe60ac4c2…` |
| VIC/QLD/WA/SA/TAS/ACT/NT property_damage | ⚠️ stage-1 unsigned | 0/7 each | (will not emit bands) |

---

## End-to-end verify (Optus can run these)

```bash
# Health (no auth)
curl -s https://claimdesk247-engine.vercel.app/healthz | python3 -m json.tool

# Start a session
curl -s -X POST https://claimdesk247-engine.vercel.app/api/session \
  -H 'content-type: application/json' -d '{"channel":"audit"}'

# PD disclosure text (requires ?ref=...)
curl -s 'https://claimdesk247-engine.vercel.app/api/disclosure/property_damage?ref=GF-XXXX'
```

Customer-facing journey: https://claimdesk247.com.au/intake

---

*Generated 2026-07-15 from engine HEAD `ffd43f5`. Question/slot definitions
live in `stage-3/app/state_machine.py`; scenario classification questions
live in `stage-3/app/data/rule-tree.*.json`.*