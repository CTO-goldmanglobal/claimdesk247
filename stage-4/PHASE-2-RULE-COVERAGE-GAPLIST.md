# Phase-2 Rule-Coverage Gap List — NSW Fault Scenarios
**Prepared by:** Fables (Cowork) · **Date:** 2026-06-14 · **Status:** for firm decision
**Purpose:** identify common NSW two-vehicle accident scenarios **not yet** in the engine, so the firm can choose which to add in Phase 2 and lift auto-assessment coverage from the current ~70–85% of moving-collision claims toward fuller two-vehicle coverage.

> **How coverage works today:** the engine confidently *bands* (likely / possible / unclear / insufficient) the 6 scenarios below. **Anything else already escalates to a human** via the 7 triggers — so nothing is mishandled; the gap is purely "auto-banded vs human-callback." Adding a scenario moves it from callback to instant band.
>
> **Governance unchanged:** every scenario still outputs a confidence **band, never a percentage**, with verbatim disclaimers, and serious-injury / police / advice / out-of-scope still escalate. New fault logic is **legal content the firm must author/approve** — the entries below are indicative starting points, not legal advice, and every NSW rule reference must be confirmed against the Road Rules 2014 before use.

---

## Currently covered (rule-tree v3.0.0 — 6 scenarios)
Rear-end · Give-way / T-intersection · Roundabout · Lane-change / merge · Reversing · Multi-vehicle / chain.
Plus 7 escalation triggers (serious injury, police attended, advice request, multi-party, out-of-NSW, hit-run/impaired, no-consent).

---

## Candidate Phase-2 scenarios

Tiers reflect **frequency × contestability** (how often it happens AND how often fault is genuinely disputable, i.e. worth auto-banding). Complexity is the build/legal effort to add. "Today" = how the engine handles it now.

### Tier 1 — high frequency, add first
| ID | Scenario | Typical NSW fault principle *(firm to confirm vs Road Rules 2014)* | Why it matters | Today | Complexity |
|----|----------|--------------------------------------------------------------------|----------------|-------|-----------|
| P2-01 | **Car-park / parking-lot manoeuvres** (reversing from a bay vs through-aisle traffic; two cars reversing; aisle vs aisle) | Vehicle in the through-aisle generally has priority; the car leaving a bay / reversing gives way | Parking incidents are among the single most common claims (≈18% of all claims in one insurer set) | Reversing rule partly applies; most car-park geometry escalates | Medium |
| P2-02 | **Signalised (traffic-light) intersection** — red-light runner; turning-on-green vs straight | Driver against the red light at fault; green arrow vs filter rules | Very common, usually clear-cut once light state is known | Often escalates (give-way scenario is unsignalised) | Medium |
| P2-03 | **Right-turn across oncoming traffic** (turning right vs vehicle going straight) | Turning driver must give way to oncoming through-traffic | Classic high-volume intersection prang | Partly via give-way; dedicated logic needed | Medium |
| P2-04 | **Sideswipe — both vehicles moving, same direction** (lane drift / parallel lanes) | Driver who left their lane / failed to keep lane bears fault | Common on multi-lane roads; contestable | Merge rule adjacent but not identical | Low–Medium |

### Tier 2 — common, add next
| ID | Scenario | Typical NSW fault principle *(confirm)* | Why it matters | Today | Complexity |
|----|----------|------------------------------------------|----------------|-------|-----------|
| P2-05 | **Emerging from driveway / private property / kerb** | Vehicle entering the road gives way to vehicles already on it | Frequent in suburban claims | Escalates | Low–Medium |
| P2-06 | **U-turn collision** | U-turning driver must give way to all other traffic | Distinct fault rule | Escalates | Low |
| P2-07 | **Head-on / wrong side of centre line / unsafe overtaking** | Driver on the incorrect side / overtaking unsafely at fault | Lower frequency but high severity (often co-escalates on injury) | Usually escalates (injury trigger) | Medium |
| P2-08 | **Car-door opening ("dooring")** — moving vehicle vs opened door | Person opening the door must not cause a hazard | Common in CBD / cyclist contexts | Escalates | Low |
| P2-09 | **Unmarked / uncontrolled intersection** (no signs/lights) | Give way to the right; turning gives way to straight | Distinct from the signed give-way/T scenario | Partly via give-way logic | Medium |

### Tier 3 — specialist / consider escalate-only
| ID | Scenario | Note | Recommended |
|----|----------|------|-------------|
| P2-10 | **Lane-filtering motorcycle** | Legal in NSW only under conditions (low speed, not school zones, etc.); fault is nuanced and rider-specific | Likely keep as **escalate** in Phase 2 |
| P2-11 | **Cyclist / pedestrian involved** | Vulnerable-road-user + injury sensitivity | **Escalate** (already injury-trigger adjacent) |
| P2-12 | **Multi-lane roundabout lane-discipline** | Refinement of existing roundabout scenario rather than new | Enhancement to s3-roundabout |
| P2-13 | **Parked & unattended vehicle hit** (other driver left / unknown) | No live fault dispute; often hit-and-run | **Escalate** (hit-run trigger) |
| P2-14 | **Single-vehicle** (animal, object, weather, loss of control) | No second party to assess fault against | Out of scope — intake + escalate |

---

## Suggested approach
1. **Firm picks the tier(s)** to fund for Phase 2 (recommendation: all of Tier 1 → biggest coverage lift for least scenarios).
2. For each chosen scenario, the **firm authors the fault logic + confirms the exact Road Rules 2014 provision(s)**; Fables specs it as a rule-tree branch (same band vocabulary + disclaimers); Cursor/MiniMax builds; Opus audits; new acceptance tests added to keep regression green.
3. **Measure, don't guess:** before/after, backtest the rule tree against a sample of the firm's or insurer's historical claims to get a *real* coverage % rather than the indicative 70–85%.

## What this does NOT change
Bands stay bands (no percentages to customers); disclaimers stay verbatim; serious-injury/police/advice/out-of-scope keep escalating; AU data residency unchanged. Adding scenarios only converts more "callback" cases into instant bands.

---
*Indicative planning document. All NSW fault principles and rule references are unverified starting points for the legal firm to confirm or strike — not legal advice.*
