# Stage 1 Build Request — Conversation Design, NSW Rule Tree, Persona, Disclaimers
**Project:** AI Legal Receptionist + Accident Intake System
**Loop:** Fables (Plan) → Cursor + MiniMax M3 (Build) → Fables (Audit) → Pass / Revise
**Stage:** 1 of 5 (Phase 1 MVP)
**Issued:** 2026-06-13 · **Issuer:** Goldman Forge / Fables
**Source document:** `loop-dev-request-legal-ai-receptionist.md` (the "Loop Request")

---

## 0. How to use this request

This stage produces **design artefacts, not code**. Code begins in Stage 2 and will consume these artefacts directly, so every deliverable must be machine-readable or unambiguous enough to implement without interpretation.

The `spec/` folder in this package contains binding contracts:

| File | What it is | Builder obligation |
|---|---|---|
| `spec/rule-tree.nsw.v1.json` | JSON schema + seed data for all 6 scenarios; Scenario 1 fully worked as the canonical example | Complete Scenarios 2–6 to the same depth; output must validate against the embedded schema |
| `spec/disclaimers.v1.json` | Exact disclaimer/consent strings, keyed by context and channel | Use verbatim. Draft the marked `BUILDER_DRAFT` entries; do not alter `FIXED` entries |
| `spec/conversation-flow.v1.md` | State machine: states, slots, transitions, interrupts | Produce full Mermaid flow diagrams covering every state, transition, and interrupt |
| `spec/persona.v1.md` | Persona constraints and behavioural rules | Produce persona brief with ≥20 sample utterances per required category |

Anything in this document marked **[FIRM-TBC]** is pending legal-firm confirmation (Loop Request §14). Build with the placeholder shown; do not invent values.

---

## 1. Scope

### In scope (Stage 1)
1. **D1 — Conversation flow diagrams** for all three channels (voice, web chat, SMS), covering the 8-step core flow (Loop Request §5.3), all escalation interrupts, and channel-specific variants.
2. **D2 — NSW rule tree** — complete decision tree for the 6 MVP scenarios, in the JSON format specified, plus a human-readable companion document for legal-firm review.
3. **D3 — Persona brief** — full persona definition with sample utterances and prohibited-behaviour list.
4. **D4 — Disclaimer + output framing pack** — all customer-facing fixed text, channel-adapted, plus the output framing language rules.
5. **D5 — Traceability matrix** — table mapping every Stage 1 requirement (this document, §4) to the artefact and section that satisfies it.

### Out of scope (Stage 1)
- Any code, UI, telephony, PDF generation, dashboard work (Stages 2–3)
- Tow/rental partner specifics **[FIRM-TBC]** — design flows with placeholders
- Anything in Loop Request §3.2 (Phase 2 items)

---

## 2. Binding corrections to the Loop Request

Fables verified the NSW Road Rules citations during planning. The following corrections are **mandatory** — the Loop Request contains two wrong rule numbers:

| Scenario | Loop Request cites | Correct citation | Source |
|---|---|---|---|
| Give way / T-intersection | Rules 71–72 | **Rules 72–73** (r72: give way sign at intersection; r73: T-intersection) | [Road Rules 2014 (NSW) r73](https://www5.austlii.edu.au/au/legis/nsw/consol_reg/rr2014104/s73.html) |
| Reversing | Rule 298 | **Rule 296** (driver must not reverse unless safe) | [Road Rules 2014 (NSW)](https://www.austlii.edu.au/cgi-bin/viewdb/au/legis/nsw/consol_reg/rr2014104/) |

Verified as correct: r126 (safe following distance), r114 (roundabout give way), r148 (changing marked lanes), r149 (zip merge / merging lines of traffic).

**Case law caution:** the Loop Request cites *Solomon v NRMA 2026* and *PXAYL v NRMA 2025*. These citations are **unverified**. Do NOT embed case citations in any customer-facing output or in the rule tree. List them in the human-readable rule tree companion under "References for legal firm verification" only. The legal firm confirms or strikes them at sign-off.

---

## 3. Deliverable specifications

### D1 — Conversation flow diagrams
- Format: Mermaid (`flowchart TD`) inside `deliverables/flows.md`, one diagram per: (a) master flow, (b) voice variant, (c) web chat variant, (d) SMS variant, (e) escalation interrupt handling, (f) tow sub-flow, (g) rental sub-flow.
- Every state in `spec/conversation-flow.v1.md` must appear in at least one diagram. No orphan states; no dead ends — every path terminates in CLOSE, ESCALATE, or ABANDON.
- Escalation interrupts (Loop Request §6.4) must be reachable from **every** intake state, not only triage.
- Each slot collected must show its validation rule and re-prompt behaviour (max 2 re-prompts → offer human callback).

### D2 — NSW rule tree
- Format: `deliverables/rule-tree.nsw.v1.complete.json` validating against the schema in `spec/rule-tree.nsw.v1.json`, plus `deliverables/rule-tree-review.md` (human-readable, for the legal firm).
- All 6 scenarios at the depth of the worked Scenario 1 example: classification questions, exception probes, damage-consistency check, confidence-band assignment logic, and the exact output string per band.
- Confidence bands: `likely | possible | unclear | insufficient` only. **A numeric percentage must be unrepresentable in the schema** — there is no field for it; do not add one. (Exception: Scenario 6 output text may describe common split *outcomes* in general terms, per the seed text — it never assigns a split to the user's case.)
- Every output string must pass the framing rules in `spec/disclaimers.v1.json → framing_rules`.
- Each scenario node cites its rule number(s) per §2 above.

### D3 — Persona brief
- Format: `deliverables/persona-brief.md` conforming to `spec/persona.v1.md`.
- Name placeholder: "Alex" **[FIRM-TBC]** — all artefacts must reference the persona name via the token `{{PERSONA_NAME}}` so it is swappable at sign-off.
- Required: ≥20 sample utterances each for (a) greeting/triage, (b) intake questioning, (c) delivering fault general-information, (d) escalation handoff, (e) deflecting legal-advice requests. Plus a prohibited-utterances list with ≥15 entries.

### D4 — Disclaimer + framing pack
- Format: `deliverables/disclaimers.v1.complete.json` extending `spec/disclaimers.v1.json`.
- `FIXED` strings verbatim. `BUILDER_DRAFT` strings completed per their notes (voice short-form, SMS form, privacy notice, recording consent).
- Voice short-form must read aloud in ≤ 15 seconds at normal pace (≈ 40 words) while preserving the four mandatory elements: general information / not legal advice / does not determine fault / lawyer will review.

### D5 — Traceability matrix
- Format: `deliverables/traceability.md`. Columns: Requirement ID (from §4) · Deliverable · Section/node ID · Status.

---

## 4. Acceptance criteria (Fables audit gates)

Fables audits the delivery against these gates. **All P0 gates pass or the loop does not close.**

| ID | Gate | Pri |
|---|---|---|
| G-01 | All 6 scenarios present in rule tree; each has ≥1 default pattern, all seed exceptions modelled, 4-band logic, per-band output text | P0 |
| G-02 | Rule citations match §2 corrected numbers; zero occurrences of r71, r298, or unverified case names in customer-facing text | P0 |
| G-03 | No numeric fault percentage assigned to the user's case anywhere in tree outputs, sample utterances, or templates | P0 |
| G-04 | Master disclaimer attached to every fault-information output node; voice short-form ≤ 40 words with all 4 mandatory elements | P0 |
| G-05 | All 7 escalation triggers (Loop Request §6.4) reachable from every intake state; escalation is terminal for AI assessment (no override path) | P0 |
| G-06 | Injury question asked before any fault-information is offered; serious injury → immediate escalation before any other slot | P0 |
| G-07 | Flow has no dead ends; ABANDON path defined (session saved, reference number issued, follow-up SMS state) | P0 |
| G-08 | Persona never expresses opinion on fault; legal-advice deflection utterances present and used at every advice-request intercept | P0 |
| G-09 | All [FIRM-TBC] values tokenised (`{{...}}`), none hardcoded | P1 |
| G-10 | State-scope guard: non-NSW state → NSW-only explanation + escalation to callback, no rule-tree entry | P0 |
| G-11 | Traceability matrix complete; every §3 requirement mapped | P1 |
| G-12 | Channel variants respect constraints: SMS contains no fault/legal content in body (links only); voice confirms each slot back before proceeding | P1 |
| G-13 | Privacy/recording consent states precede any PII slot in every channel variant | P0 |
| G-14 | Plain-English check: any legal term used in customer-facing text is explained inline or listed in glossary; reading level ≤ Year 8 target | P1 |

**Revision protocol:** Fables returns a single consolidated gap list referencing gate IDs. One revision cycle expected (mirrors the legal-firm sign-off model, Loop Request §12).

---

## 5. Dependencies and assumptions

- Open questions §14 of the Loop Request remain unanswered → all such values are tokens (see G-09). Build proceeds; tokens resolve at Stage 5.
- NSW only. The rule tree schema includes a `jurisdiction` field fixed to `"NSW"` to make Phase 2 multi-state packs additive.
- Persona/voice characteristics target Australian English; actual TTS voice selection is Stage 3.
- This stage's artefacts feed the legal firm sign-off package (Loop Request §12, items 1–3) — write the human-readable companions for a lawyer audience, not a developer audience.

---

*Prepared by Fables (Plan stage) for Goldman Forge · finn@goldmanglobal.com.au · 2026-06-13*
