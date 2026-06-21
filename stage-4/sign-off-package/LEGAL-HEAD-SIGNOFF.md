# Legal Head Sign-Off — ClaimDesk 247 Fault Engine (NSW)
**For:** the firm's reviewing lawyer ("Legal Head") · **Prepared by:** Fables (Cowork) · **Date:** 2026-06-14

## How to use this (2 minutes to read)
This is a **yes/no** review. You are confirming that (a) the **fault rules** the system applies are legally sound, (b) the **exact words shown to the public** are acceptable, and (c) the **safety behaviours** (disclaimers, escalation, no definitive fault) are correct.

- **You do not edit code.** Tick **YES** to approve an item as written, or **NO** + a one-line note on what to change. The dev loop (Cursor/MiniMax build → Opus audit) implements every change; nothing ships without your YES.
- **Two groups below:** **LIVE** = already built, tested (99/99; was 87/87 pre-T4/T6/T8, 79/79 pre-T6, 75/75 pre-MFA, 73/73 pre-Stage-2.5), running in staging — these need sign-off to launch Stage 1. **PROPOSED (Phase 2)** = drafted but **not yet coded** — your yes/no here decides what we build next, so we don't code something you'd reject (saves the redo).
- **The system never states definitive fault and never shows a percentage.** It gives a *band* — likely / possible / unclear / insufficient — always with a disclaimer, and routes anything sensitive to a human.

---

## PART A — Global safety & framing (sign once)

| # | Item | What it means | YES / NO + note |
|---|------|---------------|-----------------|
| A1 | **Output framing** | Engine outputs a band (*likely / possible / unclear / insufficient*), **never a percentage**, **never** "you are/aren't at fault". Always "general information… depends on full evidence." | ☐ YES ☐ NO |
| A2 | **Master disclaimer (verbatim, shown/spoken every result)** | *"What I'm about to share is general information about how these types of accidents are usually understood under NSW road rules — it is not legal advice, and it does not determine who is legally at fault. Only your insurer, a lawyer, or a court can do that. A lawyer will review your full situation."* | ☐ YES ☐ NO |
| A3 | **Consent to record (verbatim)** | *"This call may be recorded for quality and legal purposes… handled under the Privacy Act 1988. If you'd prefer not to be recorded, you can continue… Do you consent…?"* | ☐ YES ☐ NO |
| A4 | **Privacy notice (before any personal info collected)** | References Privacy Act 1988, **Australian-region storage**, retention period, and who can access. Shown before any PII. | ☐ YES ☐ NO |
| A5 | **Escalation to a human (7 triggers)** | These STOP the questions and hand to a person (no band given): **serious injury · police attended · request for legal advice · 3+ vehicles · outside NSW · hit-run/impaired driver · consent declined.** | ☐ YES ☐ NO |
| A6 | **Data residency & retention** | All data stored in **Australia (Sydney)** only; retention = **____ years** (firm to set). | ☐ YES ☐ NO |
| A7 | **Customer PDF summary** | Customer receives a plain summary of what they reported + disclaimer + an evidence checklist. **No fault band printed** in the customer copy. | ☐ YES ☐ NO |

---

## PART B — Fault logic, scenario by scenario

For each: the **plain-English fault rule**, the **NSW Road Rule cited** (please confirm or correct the citation), and the **exact "likely" message the customer sees**. Tick YES/NO.

### LIVE NOW (built, tested — needed for Stage 1 launch)

**B1 · Rear-end collision** — *Rule favours the front vehicle.*
Fault rule: the following driver must keep a safe distance, so usually bears fault.
Cited: **Road Rule 126** (safe following distance).
Customer is told: *"In most rear-end collisions in NSW, the following driver is considered responsible for maintaining a safe following distance (Road Rule 126). Your description matches this common pattern. Whether it applies here depends on the full evidence."*
☐ YES ☐ NO — note: ____________________

**B2 · Give way / T-intersection** — *Favours the through-road vehicle.*
Fault rule: a driver entering from a terminating road / give-way must give way to the continuing road.
Cited: **Road Rules 72 & 73.**
Customer is told: *"Under NSW Road Rules 72 and 73, drivers entering from a terminating road (including most T-intersections) must give way to vehicles on the continuing road…"*
☐ YES ☐ NO — note: ____________________

**B3 · Roundabout** — *Favours the circulating vehicle.*
Fault rule: a driver entering a roundabout gives way to any vehicle already in it.
Cited: **Road Rule 114.**
Customer is told: *"Under NSW Road Rule 114, a driver entering a roundabout must give way to any vehicle already in the roundabout…"*
☐ YES ☐ NO — note: ____________________

**B4 · Lane change / merge** — *Favours the vehicle already in the lane.*
Fault rule: a driver changing lanes/merging gives way to vehicles already there; in a zip merge the vehicle ahead has priority.
Cited: **Road Rules 148 & 149.**
Customer is told: *"Under NSW Road Rules 148 and 149, a driver changing lanes or merging must give way to vehicles already in the destination lane…"*
☐ YES ☐ NO — note: ____________________

**B5 · Reversing** — *Favours the non-reversing vehicle.*
Fault rule: a driver must not reverse unless the path is clear.
Cited: **Road Rule 296.**
Customer is told: *"Under NSW Road Rule 296, a driver must not reverse their vehicle unless the path is clear…"*
☐ YES ☐ NO — note: ____________________

**B6 · Multi-vehicle / chain** — *Context-dependent.*
Fault rule: each driver owes a standard duty of care; where one clearly failed to keep a safe gap, that often points to responsibility. (3+ vehicles also escalates to a human.)
Cited: **Road Rule 126** + general duty.
Customer is told: *"Under NSW road rules (including Road Rule 126…), each driver in a multi-vehicle collision owes a standard duty of care…"*
☐ YES ☐ NO — note: ____________________

### PROPOSED — Phase 2 (NOT yet built; your yes/no decides what we code)
> ⚠️ Citations below are **drafts to confirm or correct.**

**B7 · Car park / parking-lot manoeuvre** — *Favours the vehicle in the through-aisle.*
Fault rule: a vehicle in the aisle generally has priority over one reversing out of / entering a bay.
Draft citation: **Rule 296 (reverse safely)** + car-park give-way — *confirm.*
Customer would be told: *"In most NSW car-park collisions, a vehicle travelling in the aisle generally has priority over one reversing out of or entering a parking bay… depends on the full evidence."*
☐ YES ☐ NO — note: ____________________

**B8 · Signalised (traffic-light) intersection** — *Favours the driver with the green.*
Fault rule: the driver who entered against a red (or turned unsafely against oncoming) bears fault.
Draft citation: **Rules 56 & 59** — *confirm.*
Customer would be told: *"Where one driver proceeds lawfully on a green light and another enters against a red, fault in NSW generally rests with the driver who disobeyed the signal…"*
☐ YES ☐ NO — note: ____________________

**B9 · Right turn across oncoming traffic** — *Favours the straight-through driver.*
Fault rule: a driver turning right must give way to oncoming traffic (absent a green arrow).
Draft citation: **Rule 62** — *confirm.*
Customer would be told: *"A driver turning right across oncoming traffic in NSW must give way to that traffic. Where you were proceeding straight and the other driver turned across your path, fault generally rests with the turning driver…"*
☐ YES ☐ NO — note: ____________________

**B10 · Sideswipe (same direction)** — *Favours the lane-holding driver.*
Fault rule: a driver changing lanes must ensure it is clear; the one who left their lane bears fault.
Draft citation: **Rules 146 & 148** — *confirm.*
Customer would be told: *"On a multi-lane road in NSW, a driver changing lanes must ensure the lane is clear. Where you held your lane and the other vehicle moved into it, fault generally rests with the lane-changing driver…"*
☐ YES ☐ NO — note: ____________________

**B11 · Emerging from driveway / property** — *Favours the vehicle already on the road.*
Fault rule: a vehicle entering the road from a driveway/property gives way to road traffic.
Draft citation: **Rule 74** — *confirm.*
Customer would be told: *"A vehicle entering the road from a driveway or property in NSW must give way to traffic already on the road…"*
☐ YES ☐ NO — note: ____________________

**B12 · U-turn collision** — *Favours the non-U-turning driver.*
Fault rule: a driver making a U-turn must give way to all other traffic.
Draft citation: **Rule 38** — *confirm.*
Customer would be told: *"A driver making a U-turn in NSW must give way to all other traffic. Where the other driver U-turned across your path, fault generally rests with them…"*
☐ YES ☐ NO — note: ____________________

**B13 · Head-on / wrong side / unsafe overtaking** — *Favours the driver on the correct side.* (Usually also escalates on injury.)
Fault rule: a driver on the wrong side of the centre line, or overtaking unsafely, bears fault.
Draft citation: **Rule 132 (keep left of centre) + 140–144 (overtaking)** — *confirm.*
Customer would be told: *"A driver who crosses to the wrong side of the road, or overtakes without a clear and safe road, generally bears fault in NSW…"*
☐ YES ☐ NO — note: ____________________

**B14 · Car-door opening ("dooring")** — *Favours the passing vehicle.*
Fault rule: a person opening a door must not cause danger to others.
Draft citation: **Rule 269** — *confirm.*
Customer would be told: *"A person opening a car door in NSW must not do so where it causes danger to others. Where you were passing normally in your lane and a door was opened into your path, fault generally rests with the person who opened it…"*
☐ YES ☐ NO — note: ____________________

**B15 · Unmarked / uncontrolled intersection** — *Favours the vehicle on the right / going straight.*
Fault rule: with no signs/signals, give way to the vehicle on your right; turning gives way to straight.
Draft citation: **Rules 72–73 area / give-way-to-the-right** — *confirm (this differs from the signed give-way in B2).*
Customer would be told: *"At an intersection without signs or signals in NSW, drivers must give way to vehicles approaching from the right…"*
☐ YES ☐ NO — note: ____________________

---

## PART C — Case-law references to confirm or strike
These appear in the rule tree's internal notes only (**never customer-facing**). Please confirm, correct, or strike:

| Reference | Used for | Confirm / Strike |
|-----------|----------|------------------|
| *Solomon v NRMA 2026* | multi-vehicle split | ☐ confirm ☐ strike ☐ correct: ____ |
| *PXAYL v NRMA 2025* | merge — vehicle already in lane | ☐ confirm ☐ strike ☐ correct: ____ |

---

## PART D — Overall sign-off

- [ ] **Part A (global safety & framing)** approved
- [ ] **Part B — LIVE scenarios (B1–B6)** approved for Stage 1 launch
- [ ] **Part B — PROPOSED scenarios (B7–B15)** — approved to build: list any NOs above
- [ ] **Part C** references resolved

**Legal Head:** ___________________________  **Position:** ______________  **Date:** __________

**Overall:** ☐ Approved to proceed ☐ Approved with the noted changes ☐ Not approved

*Any "NO" or note becomes a change request; the dev loop implements and re-presents only the changed items for your final YES. You never touch code.*
