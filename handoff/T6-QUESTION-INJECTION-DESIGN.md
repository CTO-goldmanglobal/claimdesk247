# T6 — Conversational Question Injection Design (L1 dependency)
**Prepared by:** Cursor / MiniMax (build seat) · **Date:** 2026-06-15
**Task:** L1 T6 per `CURSOR-HANDOFF-MASTER.md` §7 — wire each scenario's `classification_questions` into the live intake flow so the engine actually *asks* the discriminating questions before banding.
**Critical:** T6 is the load-bearing dependency for T4–T7. Without it, T4–T5's band functions have no inputs and would default. The handoff is explicit: *"This sub-step is mandatory, not optional."*
**Inputs read:** `CURSOR-HANDOFF-MASTER.md` §7, `stage-3/app/state_machine.py`, `stage-3/app/engine.py` (T1-aware), `stage-2.5/app/wrap.py` (T1-aware), `stage-3/app/data/rule-tree.nsw.v3.json` (the 6 existing scenarios' `classification_questions`).

---

## 1. The current state (before T6)

Today, the state machine walks the **fixed 14** `SLOT_DEFINITIONS` in order:

```
slot 1: state_of_accident → enum
slot 2: datetime_location → text
slot 3: accident_type     → enum      ← THIS is the scenario-routing slot
slot 4: user_vehicle      → text
...
slot 14: injuries         → enum      ← escalation can fire here (G-19)
```

After slot 14, `run_classification()` is called, which hands `session.intake` to the engine. The engine resolves the scenario by `accident_type` and tries to compute a band.

**The bug:** each scenario in the rule tree has its own `classification_questions` (e.g. s1-rear-end asks `user_position`, `user_motion`, `chain_count`; s3-roundabout asks `collision_location`, `user_indicating`, `other_indicating`, `lane_count`). These questions are *not* asked. The engine's band functions read them from `session.intake`, but they're never populated — so the band functions see `None` for all scenario-specific inputs and return `unclear` or `insufficient` defaults.

**The 6 existing scenarios are already in this state.** Today, every live classify call returns a default because the scenario questions weren't asked. (G-PROD-LOCK's escalation envelope currently masks this — the engine escalates because the scenarios are unsigned, so the band default was never visible. Once Legal Head signs, this bug surfaces immediately.)

**T6 fixes this by injecting the scenario's `classification_questions` into the flow after the scenario is resolved.**

---

## 2. The fix (high-level)

### 2.1 New state inserted between S3 and S4

```
S3-SLOT14 (current end of fixed intake)
    ↓
S3.5-INJECT-QUESTIONS  ← NEW: ask the resolved scenario's classification_questions
    ↓
S4-CLASSIFY (current classify)
```

**The injection logic:**
1. After `accident_type` is set (slot 3), look up the scenario via `ACCIDENT_TYPE_TO_SCENARIO`.
2. After the 14 fixed slots are filled, look up the scenario again, then ask the scenario's `classification_questions` *one at a time* in order. Each question populates a key in `session.intake` keyed by the question's `slot` field (e.g. `user_position`, `chain_count`).
3. After all scenario questions are filled, transition to S4 and call `classify()`.

### 2.2 The scenario-resolution timing

The scenario needs to be resolved **twice**:

1. **At slot 3** (early resolution): so we can show scenario-aware copy in slots 4–14 if we want (optional — see §2.3). For L1, this is *not* required; the existing 14 slots are scenario-agnostic and that's fine.
2. **At slot 14** (late resolution): so we know which `classification_questions` to ask in S3.5.

The current code resolves the scenario at slot 3 implicitly (via the `accident_type` value) but doesn't act on it. **T6's job: after slot 14, look up the scenario, and if it has `classification_questions`, ask them.**

### 2.3 What about scenario-aware copy in slots 4–14?

Out of scope for T6. The 14 fixed slots ask generic things (user vehicle, other vehicles, movement description, damage locations, control devices, police attendance, witnesses, dashcam, photos, other driver details, injuries) that are valid for every scenario. **No slot 4–14 needs to change.** This is by design — the 14 slots are the "common law" intake; the scenario questions are the "specifics that discriminate."

---

## 3. Detailed design

### 3.1 New constants in `state_machine.py`

```python
# T6: scenario-question injection. Add below SLOT_DEFINITIONS.
SCENARIO_QUESTION_TYPE_TO_SLOT_TYPE = {
    "enum": "enum",
    "multienum": "multienum",
    "text": "text",
    "integer": "integer",  # NEW type — need to add to _validate_slot
}

# Maximum number of times to re-ask a single scenario question before
# offering callback. T6 inherits the same cap as the fixed slots (G-26).
SCENARIO_REPROMPT_CAP = 2
```

`integer` is a new slot type the existing code doesn't have. T6 introduces it; `_validate_slot` gets a new branch.

### 3.2 New helper: `_get_scenario_questions(intake)`

```python
from app.engine import _resolve_scenario  # already exists

def _get_scenario_questions(intake: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return the classification_questions for the resolved scenario, or None
    if no scenario is resolved (e.g. accident_type missing or unmapped)."""
    scenario = _resolve_scenario(intake)  # raises if unmapped; caller guards
    return scenario.get("classification_questions", [])
```

`_resolve_scenario` already exists in `engine.py` and raises `KeyError` if `accident_type` is unknown. T6 guards against this — if `_resolve_scenario` raises, the injection is skipped (the engine's own error path handles it).

### 3.3 New state machine methods

Two new methods on the state machine:

```python
def start_scenario_questions(session: Session) -> dict[str, Any]:
    """Called after the 14 fixed slots are filled. Looks up the scenario,
    transitions to S3.5-INJECT-QUESTIONS, and returns the first question
    to ask (or 'no scenario questions' if the scenario has none).

    Returns:
        {"state": "S3.5-INJECT-QUESTIONS", "question": <q_def> | None,
         "total_questions": <int>, "answered": 0}
    """
    if session.state != "S4-CLASSIFY":
        raise RuntimeError(f"cannot start scenario questions from state {session.state}")
    questions = _get_scenario_questions(session.intake)
    if not questions:
        # No scenario questions — go straight to classify.
        return {"state": "S4-CLASSIFY", "question": None, "total_questions": 0, "answered": 0}
    session.state = "S3.5-INJECT-QUESTIONS"
    session.scenario_questions = questions  # NEW field on Session
    session.scenario_questions_answered = []
    return {
        "state": "S3.5-INJECT-QUESTIONS",
        "question": questions[0],
        "total_questions": len(questions),
        "answered": 0,
    }


def submit_scenario_question(session: Session, question_id: str, value: Any) -> dict[str, Any]:
    """Submit an answer to a scenario question. Validates against the
    question's answer_type/options. Increments re-prompt count on invalid.
    After all questions are answered, transitions to S4-CLASSIFY.

    Returns:
        On valid: {"accepted": True, "next_question": <q_def> | None,
                   "answered": <int>, "total_questions": <int>}
        On invalid (re-prompt available): {"reprompt": True, "error": "...",
                                          "reprompt_count": <int>}
        On re-prompt cap: {"escalation": "repompt-cap",
                           "end_state": "SX-ESCALATE", "reference": "..."}
    """
    if session.state != "S3.5-INJECT-QUESTIONS":
        raise RuntimeError(f"cannot submit scenario question from state {session.state}")

    # Find the current question
    if not session.scenario_questions_answered:
        # First question
        current = session.scenario_questions[0]
    else:
        # Find the first unanswered question
        answered_ids = {q["id"] for q in session.scenario_questions_answered}
        current = next((q for q in session.scenario_questions if q["id"] not in answered_ids), None)
        if current is None:
            raise RuntimeError("no more scenario questions to answer")

    if current["id"] != question_id:
        raise RuntimeError(f"question_id mismatch: expected {current['id']}, got {question_id}")

    # Validate
    valid, err = _validate_scenario_question(current, value)
    if not valid:
        # Re-prompt logic mirrors submit_slot
        session.reprompts[current["slot"]] = session.reprompts.get(current["slot"], 0) + 1
        if session.reprompts[current["slot"]] > SCENARIO_REPROMPT_CAP:
            session.state = "SX-ESCALATE"
            session.escalation = "repompt-cap"
            session.escalation_reason = f"max re-prompts on scenario slot {current['slot']}"
            session.reference = _new_reference()
            return {"escalation": "repompt-cap", "end_state": "SX-ESCALATE", "reference": session.reference}
        return {"reprompt": True, "error": err, "reprompt_count": session.reprompts[current["slot"]]}

    # Persist the answer into session.intake under the question's slot name
    session.intake[current["slot"]] = value
    session.pii_persisted = True  # G-22: scenario answers may be PII (e.g. "describe what you saw")
    session.scenario_questions_answered.append({"id": current["id"], "value": value})

    # Find the next question, or transition to S4
    answered_ids = {q["id"] for q in session.scenario_questions_answered}
    next_q = next((q for q in session.scenario_questions if q["id"] not in answered_ids), None)
    if next_q is None:
        session.state = "S4-CLASSIFY"
        return {
            "accepted": True,
            "next_question": None,
            "answered": len(session.scenario_questions_answered),
            "total_questions": len(session.scenario_questions),
            "ready_to_classify": True,
        }
    return {
        "accepted": True,
        "next_question": next_q,
        "answered": len(session.scenario_questions_answered),
        "total_questions": len(session.scenario_questions),
    }


def _validate_scenario_question(q: dict[str, Any], value: Any) -> tuple[bool, str | None]:
    """Validate a value against a scenario question's answer_type/options."""
    answer_type = q["answer_type"]
    if answer_type == "enum":
        if value not in q.get("options", []):
            return False, f"Please choose one of: {', '.join(q.get('options', []))}."
    elif answer_type == "multienum":
        if isinstance(value, str):
            value = [v.strip() for v in value.split(",")]
        if not isinstance(value, list) or not all(v in q.get("options", []) for v in value):
            return False, f"Please choose from: {', '.join(q.get('options', []))}."
    elif answer_type == "text":
        if not isinstance(value, str) or len(value.strip()) < 1:
            return False, "Please enter a value."
    elif answer_type == "integer":
        try:
            n = int(value)
        except (TypeError, ValueError):
            return False, "Please enter a whole number."
        # Some questions have a range hint in the 'validation' field
        # (e.g. ">=2; if >=3 route to esc-multiparty"). The state machine
        # can parse this for simple bounds; the engine also enforces.
        return True, None
    return True, None
```

### 3.4 New fields on the `Session` dataclass

```python
@dataclass
class Session:
    # ... existing fields ...
    scenario_questions: list[dict[str, Any]] = field(default_factory=list)
    scenario_questions_answered: list[dict[str, Any]] = field(default_factory=list)
```

### 3.5 Stage-2.5 wrapper changes (`wrap.py`)

The `/api/slot` endpoint already handles the 14 fixed slots. T6 adds handling for scenario questions:

```python
@app.post("/api/scenario-question")
def submit_scenario_question_endpoint(payload: dict):
    """Submit an answer to a scenario question. SlotQuestion-shaped response
    (matches the existing /api/slot contract) for UI consistency."""
    ref = payload.get("ref") or payload.get("reference")
    question_id = payload.get("question_id")
    value = payload.get("value")
    # ... load session, call submit_scenario_question, save session ...
    return {
        "ref": ref,
        "answered": result["answered"],
        "total_questions": result["total_questions"],
        "next": SlotQuestion(...) if result.get("next_question") else None,
        "ready_to_classify": result.get("ready_to_classify", False),
    }
```

The frontend flow becomes:
1. User fills the 14 fixed slots (existing flow).
2. The state machine returns `state: S3.5-INJECT-QUESTIONS` with the first question.
3. The UI renders the question (enum → buttons, text → input, integer → number input).
4. User submits; UI calls `/api/scenario-question`.
5. Repeat until `ready_to_classify: true`.
6. UI calls `/api/classify` (existing endpoint).

### 3.6 Frontend integration

The Lovable UI already renders `SlotQuestion` shape (`{slot, prompt, inputType, options:[{value,label}], done}`). T6's scenario questions render through the same `SlotQuestion` shape — no UI change needed beyond adding a "scenario question" rendering branch. The `SLOT_UI` catalog in `wrap.py` already exists for the 14 fixed slots; T6 either:

- (a) Builds a parallel `SCENARIO_QUESTION_UI` catalog keyed by question ID.
- (b) Falls back to a generic prompt render using the question's `question_web` field as the prompt and `options[]` as buttons.

**Recommendation: (b)** for L1. The 9 Phase-2 scenarios' questions all have `question_web` text; the UI can render it directly. (a) is nicer but adds per-question chrome that's deferrable.

### 3.7 The 6 existing scenarios: regression-guard

The 6 existing scenarios already have `classification_questions` in the rule tree. T6 wires them in. **The 75-test suite must continue to pass** — meaning the existing acceptance tests for s1–s6 must be updated to either:
- Pre-populate the `classification_questions` answers in `intake` (so the engine bands correctly without going through the state machine), OR
- Call the new `start_scenario_questions` / `submit_scenario_question` methods explicitly

**Option A** (pre-populate) is cleaner for tests — it tests the engine's band logic without coupling to the new state machine. The stage-3 acceptance tests already pass `intake` dicts directly; they can pre-populate the scenario slots.

**Option B** (call the new methods) is more end-to-end but couples tests to the new state machine wiring.

**Recommendation: Option A for existing 75 tests; add new tests for the state machine wiring (T6-specific tests).** This way the engine's band logic is tested independently of the new injection path, and the new path is tested independently of the engine.

---

## 4. Test plan (T6 acceptance)

| # | Test | Where | What it asserts |
|---|---|---|---|
| T6-1 | `start_scenario_questions` returns the first question for a known `accident_type` | stage-3 | State transitions S4-CLASSIFY → S3.5-INJECT-QUESTIONS; first question matches the rule tree |
| T6-2 | `submit_scenario_question` accepts a valid answer and returns the next question | stage-3 | State stays in S3.5; next question is the second one in the list |
| T6-3 | `submit_scenario_question` returns `ready_to_classify: true` after the last question | stage-3 | State transitions to S4-CLASSIFY; all answers are in `session.intake` |
| T6-4 | `submit_scenario_question` invalid value → re-prompt | stage-3 | Returns `reprompt: true`; `reprompt_count` increments |
| T6-5 | `submit_scenario_question` re-prompt cap hit → escalation | stage-3 | Returns `escalation: repompt-cap`; state is SX-ESCALATE; `reference` issued |
| T6-6 | Scenario with no `classification_questions` (defensive case) → go straight to classify | stage-3 | `start_scenario_questions` returns `question: None`; state stays S4-CLASSIFY |
| T6-7 | Unknown `accident_type` → `start_scenario_questions` raises `KeyError` (engine handles) | stage-3 | Propagates the engine's existing error path |
| T6-8 | Stage-2.5: `/api/scenario-question` endpoint accepts a valid answer and returns the next | stage-2.5 | 200; response shape includes `next`, `answered`, `total_questions` |
| T6-9 | All 6 existing scenarios' bands still compute correctly with the new `classification_questions` slots populated | stage-3 | Re-run T-3-001..T-3-006 with scenario slots populated; bands match expected |
| T6-10 | G-19 injury escalation still fires at slot 14 (before scenario questions) | stage-3 | Submit injuries=serious → SX-ESCALATE, never reaches S3.5 |
| T6-11 | `accident_type = "other"` → immediate escalation at slot 3 (UX fast-fail, per §6.7) | stage-3 | Submit slot 3 with value "other" → SX-ESCALATE with `escalation = "unmapped-accident-type"`; remaining slots never asked |
| T6-12 | `accident_type = "unknown_value"` (Phase-2 scenario not yet in enum) → same fast-fail as "other" | stage-3 | Submit slot 3 with an enum value not in the engine's `ACCIDENT_TYPE_TO_SCENARIO` → SX-ESCALATE with `escalation = "unmapped-accident-type"` |

**10 new tests. Total suite: 75 → 85 (existing 75 + 4 new T-1-* from T1 + 10 new T-6-* = 89, but T-3-001..T-3-006 may get split into "pre-populated" and "via state machine" variants, so the actual count may go 75 → 95).**

---

## 5. Implementation plan (in order)

| # | Action | Files | Notes |
|---|---|---|---|
| 1 | Add `integer` type to `_validate_slot` | `stage-3/app/state_machine.py` | Tiny — 3 lines |
| 2 | Add `Session.scenario_questions` and `.scenario_questions_answered` fields | `stage-3/app/state_machine.py` | Dataclass additions |
| 3 | Add `_validate_scenario_question` and `_get_scenario_questions` helpers | `stage-3/app/state_machine.py` | Per §3.2, §3.3 |
| 4 | Add `start_scenario_questions` and `submit_scenario_question` methods | `stage-3/app/state_machine.py` | Per §3.3 |
| 4a | **NEW** Add `accident_type` fast-fail in `submit_slot`: if the value is not in `ACCIDENT_TYPE_TO_SCENARIO` (e.g. "other" or a Phase-2 value not yet wired), transition to SX-ESCALATE with `escalation = "unmapped-accident-type"`. Avoids the bad UX of filling 14 slots only to fail at the end. | `stage-3/app/state_machine.py` | Per §6.7 |
| 5 | Update `submit_slot` so that after slot 14 (injuries), it sets state to S3.5-INJECT-QUESTIONS (not S4-CLASSIFY) — the orchestrator then calls `start_scenario_questions` to populate the first scenario question. **Reconcile with §3.3:** the original design had `submit_slot` auto-transition to S4-CLASSIFY, with `start_scenario_questions` flipping it back to S3.5. After this audit, the cleaner path is: `submit_slot` goes to S3.5 directly, and `start_scenario_questions` only initializes the questions list. | `stage-3/app/state_machine.py` | Small change to the slot-14 handler |
| 6 | Add the 12 T-6-* tests (10 original + 2 new T6-11, T6-12 from the fast-fail amendment) | `stage-3/tests/run_acceptance.py` | Per §4 |
| 7 | Update existing T-3-001..T-3-006 tests to pre-populate scenario slots (Option A regression-guard) | `stage-3/tests/run_acceptance.py` | Per §3.7 |
| 8 | Update `stage-2.5/app/wrap.py` to expose `/api/scenario-question` endpoint | `stage-2.5/app/wrap.py` | Per §3.5 |
| 9 | Add 1 stage-2.5 test for the new endpoint (T6-8) | `stage-2.5/tests/run_acceptance.py` | Per §4 |
| 10 | Update `acceptance-tests.stage3.yaml` with the T-6-* cases | `stage-3/acceptance-tests.stage3.yaml` | Per §4 |
| 11 | Run full test suite, confirm green | local + engine repo clone | Per LO §2 |

**Cross-loop dependency noted (informational only — not in T6's scope):** T4 (add 9 Phase-2 scenarios) must grow the `accident_type` enum in slot 3 and add `ACCIDENT_TYPE_TO_SCENARIO` entries. T6 doesn't break if T4 is incomplete — values not in the map route to `unmapped-accident-type` escalation per §6.7 / T6-12.

**Total estimate:** ~300-400 lines of code + 10 tests. **2-3 build hours.** **No engine code change.** **No rule-tree change.** **No frontend change** (the Lovable UI renders via `SlotQuestion`, which T6's responses conform to).

---

## 6. Risks + things to watch

### 6.1 The "scenario has no classification_questions" case

T6 must handle a scenario that has `[]` for `classification_questions`. The 6 existing scenarios all have 3-4 questions each, so this is hypothetical. But the spec might produce a scenario with no questions (e.g. a future scenario where the fixed-14 intake is sufficient). T6's `start_scenario_questions` returns `{question: None, ready_to_classify: true}` in that case — clean passthrough.

### 6.2 Integer validation hint parsing

Some scenario questions have hints in their `validation` field, e.g. `"validation": ">=2; if >=3 route to esc-multiparty"`. The state machine's `_validate_scenario_question` for `integer` only checks that the value is an integer; it doesn't enforce the range. The engine's own band function enforces the range (and routes to `esc-multiparty` if needed). **This is correct:** the state machine validates user input shape; the engine validates business rules. Don't conflate them.

### 6.3 PII in scenario answers

Some scenario answers are PII (e.g. s5-reversing's `user_visibility` could reveal something). The current `submit_slot` sets `pii_persisted = True` after consent. T6's `submit_scenario_question` does the same. This means scenario answers are persisted in `intake_sessions` (the Supabase store already has the column for `intake` JSON). The privacy notice (G-22) already covers "what you tell us during the intake" — scenario answers are part of the intake. No new privacy disclosure needed.

### 6.4 Existing 75-test regression-guard

The 6 existing scenarios all have `classification_questions`. If the existing T-3-001..T-3-006 tests don't pre-populate the scenario slots, they'll start failing (because the band functions see `None` for the scenario-specific inputs). T6 includes updating those 6 tests to pre-populate. This is a deliberate, documented change.

### 6.5 Performance: 3-4 extra round-trips per session

Each scenario question is a separate API call. 6 scenarios × 3-4 questions = 18-24 extra round-trips per session (average, ~3-4 per session for a typical case). This is fine for a session that takes ~30 seconds anyway. The 14 fixed slots already work this way (each is a separate `/api/slot` call). No performance concern.

### 6.6 Edge case: scenario changes mid-flow

If the user goes back and changes `accident_type` (slot 3) after answering some scenario questions, the scenario's questions are different. T6 doesn't support this case. Recommendation: **for L1, lock slot 3 once submitted.** If the user needs to change, they abandon (S9) and start over. Document this in the frontend.

### 6.7 Edge case: `accident_type = "other"` (no scenario maps)

Slot 3's enum currently includes `"other"` as a valid value. If the user selects "other", `_resolve_scenario` raises `KeyError` because no scenario maps to "other". The current design handles this in `start_scenario_questions` (test T6-7), but the user has filled the whole 14-slot intake before finding out it doesn't band. **Better UX: at slot 3, after the user selects "other", tell them immediately that this won't auto-band and offer callback.** T6 should add a pre-classification check in `submit_slot` for the `accident_type` value: if it's "other" (or any value not in the scenario map), transition to SX-ESCALATE with `escalation = "unmapped-accident-type"` and offer callback, before the user fills the remaining 12 slots. This is a small, additive change.

### 6.8 Dependency on T4: `accident_type` enum growth

The 9 Phase-2 scenarios will need new enum values in slot 3 (e.g. `car-park`, `signalised`, `right-turn`, `sideswipe`, `driveway`, `u-turn`, `head-on`, `dooring`, `unmarked`). The current enum has `rear-end / T-intersection / roundabout / merge / reversing / parking / other` — 7 values, mapping to 6 scenarios (with `parking` likely being a future s7). **T4 must grow the enum + add the `ACCIDENT_TYPE_TO_SCENARIO` entries; T6 wires the injection.** T6 doesn't break if the enum is incomplete — it just routes "other" to escalation. T4 will close the gap.

---

## 7. Acceptance criteria (T6 close)

T6 closes when:
1. All 10 T-6-* tests pass.
2. The 6 existing T-3-001..T-3-006 tests pass with their pre-populated scenario slots.
3. The full test suite is green: 75 → ~85 (depends on how T-3-* tests are restructured).
4. The `/api/scenario-question` endpoint is exposed in `wrap.py` and tested.
5. The frontend renders scenario questions via the `SlotQuestion` shape (manual smoke test, since frontend changes are out of scope for the engine repo).
6. The Opus audit (test-based) confirms: no regression in the 6 existing scenarios, the new injection path is deterministic, the escalation envelope still fires on re-prompt cap, the new `integer` slot type is validated.

---

*Prepared by Cursor / MiniMax (build seat) · ready for build once approved. The T6 work is contained — no engine code change, no rule-tree change, no frontend change (frontend smoke test only).*
