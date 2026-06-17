# NSW Rule Tree — Human-Readable Companion
**For legal-firm review (Loop Request §12, items 1–3).**
**Companion to:** `rule-tree.nsw.v1.complete.json` (machine-readable)
**Jurisdiction:** NSW only
**Prepared by:** Cursor + MiniMax M3 (Build) for Fables (Audit) · 2026-06-13

---

## 1. Purpose and audience

This document explains, in plain legal-English, how the AI receptionist reasons about accident fact patterns. It is intended to be read by a NSW lawyer signing off on the system. It mirrors the structure of the JSON but is written for review, not for execution. Where the JSON and this document disagree, the JSON is authoritative for the build; the legal firm's role is to amend the JSON via the change protocol in §6 below.

---

## 2. Global design principles

**Bands, not percentages.** The system never assigns a numeric fault percentage or split to the user's case. The output is one of four qualitative bands:

- **likely** — the described pattern closely matches the common case under the relevant road rule, with no complicating factors disclosed.
- **possible** — the pattern is a reasonable fit, but one or more disclosed factors could change the assessment.
- **unclear** — the facts do not fit a single pattern neatly, or the damage profile is inconsistent with the reported sequence.
- **insufficient** — the system did not collect enough detail (after the maximum re-prompts) to match a pattern.

A fifth value, `n/a_esc_routed`, is used by Scenario 6 (multi-vehicle) when the count threshold triggers immediate escalation before band logic runs.

**General information only.** Every output is framed as "general information about how these types of accidents are usually understood" and explicitly disclaims that it is not legal advice and does not determine who is at fault. The master disclaimer is attached to every fault-information output, in full on first read, in short form thereafter on voice calls.

**No case citations to customers.** The two cases cited in the source Loop Request (*Solomon v NRMA 2026*, *PXAYL v NRMA 2025*) are **unverified**. They appear only in §10 of this document for the legal firm to confirm or strike. They are not in any customer-facing string.

**Escalation overrides band output.** Seven global escalation triggers (see §4) can fire at any point in any state. When they fire, the AI assessment stops and the matter is handed to a human. There is no path from escalation back into fault assessment.

---

## 3. Scenarios

### 3.1 Scenario 1 — Rear-end collision (canonical example, complete in spec)
- **Rule cited:** Road Rule 2014 (NSW) r126 — Keeping a safe distance behind vehicles.
- **Default pattern:** the following driver is usually responsible for maintaining a safe gap.
- **Exception probes:** sudden braking, brake-light failure, front vehicle reversed, chain push.
- **Damage consistency check:** rear damage on front vehicle AND front damage on rear vehicle. Mismatch caps the band at `unclear`.
- **Escalation override:** chain of 3+ vehicles routes to Scenario 6, which then triggers `esc-multiparty`.

### 3.2 Scenario 2 — Give way / T-intersection
- **Rules cited:** r72 (give way sign or line at intersection) and r73 (T-intersection). *Corrected from the Loop Request's "r71–72" — that was wrong.*
- **Default pattern:** the driver on the terminating road gives way to traffic on the continuing road.
- **Exception probes:** obstructed sight lines, simultaneous entry, defective or missing signage, traffic lights overriding signs, other vehicle speeding.
- **Damage consistency check:** front damage on terminating-road vehicle AND side (nearside) damage on through-road vehicle. Mismatch caps the band at `unclear`.
- **Escalation override:** if both road-type and other-vehicle motion are `unsure`, route to a lawyer rather than guess.

### 3.3 Scenario 3 — Roundabout
- **Rule cited:** r114 — Giving way when entering or driving in a roundabout.
- **Default pattern:** entering driver gives way to traffic already in the roundabout.
- **Exception probes:** other vehicle failed to indicate, simultaneous entry, multi-lane conflict, other vehicle stopped in the roundabout for no apparent reason.
- **Damage consistency check:** front of entering vehicle AND side of circulating vehicle (entry contact), or side of both vehicles (lane-change contact). Mismatch caps the band at `unclear`.
- **Escalation override:** multi-lane conflict in the circulating portion of the roundabout routes to a lawyer.

### 3.4 Scenario 4 — Lane change / merge
- **Rules cited:** r148 (giving way when moving between marked lanes) and r149 (zip merge — vehicle ahead has priority).
- **Default pattern:** the driver crossing marked lines or merging gives way; in a zip merge, the vehicle ahead has priority.
- **Exception probes:** other vehicle's unannounced move, simultaneous lane change, solid line crossed, dispute about whether the layout was a true zip merge.
- **Damage consistency check:** sideswipe damage (side on both vehicles) or front-of-merging AND side-of-continuing. Mismatch caps the band at `unclear`.
- **Escalation override:** if the user cannot tell which vehicle was changing into which lane, route to a lawyer.

### 3.5 Scenario 5 — Reversing
- **Rule cited:** r296 — Reversing; driver must not reverse unless safe. *Corrected from the Loop Request's "r298" — that was wrong.*
- **Default pattern:** the driver reversing must ensure the path is clear.
- **Exception probes:** other vehicle's unannounced movement, view obstruction, other vehicle's illegal position, low-speed contact with both moving slightly.
- **Damage consistency check:** rear damage on reversing vehicle AND front damage on stationary/approaching vehicle (or both rear damage if both reversing). Mismatch caps the band at `unclear`.
- **Escalation override:** if the user cannot say who was reversing, route to a lawyer.

### 3.6 Scenario 6 — Multi-vehicle / chain
- **Rule cited:** r126 (safe following distance), in conjunction with general duty of care principles applicable in multi-party collisions.
- **Default pattern:** each driver's compliance with the standard duty of care is assessed. In multi-vehicle collisions, responsibility is often apportioned between the parties depending on the evidence. **The system never assigns a percentage or split to the user's case.**
- **Exception probes:** emergency stop in the chain, speeding in the chain, observed tailgating, presence of a heavy vehicle, motorcycle, or pedestrian.
- **Damage consistency check:** damage profile consistent with the reported chain mechanism (rear+front in a push chain, distributed damage in a side-impact chain). Mismatch caps the band at `unclear`.
- **Critical escalation override:** **3+ vehicles routes immediately to `esc-multiparty` before any band output is produced.** The output for this case is the escalation message, not a band output. This is a hard gate.

---

## 4. Global escalation triggers

The following seven triggers can fire at any point in any state. When any of them fire, the AI assessment stops and the matter is handed to a human. There is no override path that returns to fault assessment.

| ID | Trigger | Note for the legal firm |
|---|---|---|
| esc-injury | Any injury (minor or serious) | Serious → immediate, before any further slots. Minor → safety check completed, then escalate. |
| esc-hitrun | Hit-and-run indicated | Early intercept; details may be incomplete by design. |
| esc-vulnerable | Pedestrian or cyclist involved | Always escalate regardless of apparent severity. |
| esc-fraud | Story inconsistency, rego mismatch, third-party pressure | Use neutral wording in handoff; never accuse in customer-facing text. |
| esc-dispute | Customer disputes the AI's summary | Disagreement with the system's framing is itself a flag. |
| esc-multiparty | 3+ vehicles/parties | Hard gate on count. |
| esc-advice | Customer asks for legal advice directly | Deflect with persona utterance category (e), then offer callback. Do not answer. |

---

## 5. Confidence band output — worked example (Scenario 1)

For the same Scenario 1 fact pattern (rear-end, user in front, user stopped, no exception probes positive, damage consistent), the system produces the following voice output:

> "In most rear-end collisions in New South Wales, the driver of the following vehicle is considered responsible for keeping a safe gap. Based on what you've told me, your situation looks like a common example of that pattern — but whether it applies depends on the full evidence. What I'm about to share is general information about how these types of accidents are usually understood under NSW road rules — it is not legal advice, and it does not determine who is legally at fault. Only your insurer, a lawyer, or a court can do that. A lawyer will review your full situation."

If a `sudden_braking` exception is positive, the band drops to `possible` and the output becomes:

> "Rear-end collisions in New South Wales usually involve the following driver's duty to keep a safe gap, but you've mentioned something that can change how these are assessed. A lawyer will need to look at the details. [master disclaimer]"

The web variants mirror the same logic with slightly more concise phrasing suitable for reading on a page.

---

## 6. Change protocol for the legal firm

If the legal firm wishes to amend any band assignment, exception probe, output string, or escalation rule, the recommended process is:

1. Annotate the relevant scenario section in this document.
2. The build agent will regenerate the JSON to match, preserving all other scenarios.
3. The diff is re-audited by Fables against the G-01 to G-14 gates in the Stage 1 build request.

Edits that introduce numeric fault percentages, name unverified case law in customer-facing text, or assign a percentage to the user's case will be rejected at audit (G-02, G-03).

---

## 7. Reading-level and framing checks (G-14)

Every customer-facing string in the rule tree:
- Uses only the approved framing ("general information", "common pattern", "usually understood", "often considered").
- Avoids a conclusion about the user's specific case ("you are/aren't at fault", "they will pay").
- Contains no numeric fault percentage or split applied to the user's case.
- Names no case law.
- Explains any legal term inline (e.g. "the give way duty", "the standard duty of care") rather than relying on the reader's prior knowledge.

The target reading level is Year 8. All strings have been written to this target; the legal firm may flag any individual string for rephrasing.

---

## 8. Interaction with the conversation flow

The rule tree is invoked from state S4 (CLASSIFY) in the conversation flow (`deliverables/flows.md`). Inputs to classification come from S3 (INTAKE) slots. The flow guarantees:

- State of accident is asked in S3 slot 1, before any fault content. Non-NSW triggers the `state_scope_guard` string (FIXED) and routes to a callback, **not** into the rule tree (G-10).
- Injuries are asked in S1 (TRIAGE), and again confirmed in S3 slot 14, before any fault content. Serious injury routes to `esc-injury` immediately, before any further slot (G-06).
- Recording consent and the privacy notice are presented in S0a, before any PII is collected, in every channel (G-13).

The seven global escalation triggers are evaluated on every user turn in every state S1–S7 (G-05). They can fire from any state, not only from S4/S5.

---

## 9. What this document does not cover

- The persona, voice, and channel-specific phrasing (see `deliverables/persona-brief.md` and `deliverables/disclaimers.v1.complete.json`).
- The detailed state machine and channel variants (see `deliverables/flows.md`).
- Tow and rental sub-flows (S2a, S2b) — these are operational, not fault-related, and live in the flow document.
- Anything in Phase 2 (Loop Request §3.2).

---

## 10. References for legal-firm verification

**The following cases are cited in the source Loop Request and are UNVERIFIED. They do not appear in any customer-facing string. The legal firm should confirm or strike them before sign-off.**

- *Solomon v NRMA 2026* (cited as relevant to multi-vehicle split assessment).
- *PXAYL v NRMA 2025* (cited as relevant to merge collisions — vehicle already in lane).

**Verified citations used in the rule tree (corrected from Loop Request where applicable):**

- Road Rules 2014 (NSW) r72 — Giving way at an intersection with a give way sign or line.
- Road Rules 2014 (NSW) r73 — Giving way at a T-intersection. *(Loop Request cited r71–72; this is the correct citation.)*
- Road Rules 2014 (NSW) r114 — Giving way when entering or driving in a roundabout.
- Road Rules 2014 (NSW) r126 — Keeping a safe distance behind vehicles.
- Road Rules 2014 (NSW) r148 — Giving way when moving between marked lanes.
- Road Rules 2014 (NSW) r149 — Giving way when lines of traffic merge (zip merge).
- Road Rules 2014 (NSW) r296 — Reversing; driver must not reverse unless safe. *(Loop Request cited r298; this is the correct citation.)*

---

*End of document. For the machine-readable artefact see `rule-tree.nsw.v1.complete.json`. For traceability, see `deliverables/traceability.md`.*
