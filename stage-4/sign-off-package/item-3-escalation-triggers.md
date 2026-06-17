# Item 3 — Escalation Trigger List (7 triggers)

## Builder evidence (CODE)

- `stage-3/app/engine.py:ENGINE_TRIGGERS` (lines 482-512) — the 7 triggers.
- `stage-1/deliverables/flows.md` — narrative.
- `stage-3/app/data/rule-tree.nsw.v3.json:s6.band_logic` — multipart pre-band routing (CR-3-04).

## The 7 triggers

| # | Trigger condition | Escalation label |
|---|-------------------|------------------|
| 1 | `injuries == "serious"` | `esc-injury` |
| 2 | `police_attended == "yes"` | `esc-police` |
| 3 | `accident_type == "advice_request"` | `esc-advice` |
| 4 | `chain_count >= 3` (pre-band routing per CR-3-04) | `esc-multiparty` |
| 5 | `state_of_accident not in NSW_AREAS` | `esc-scope` |
| 6 | `accident_type in ("hit_run", "drunk_driver")` | `esc-hitrun` / `esc-impaired` |
| 7 | consent not granted | (session halts; no escalation) |

## Deployer evidence (capture against staging)

- [ ] QA-2: serious-injury session escalates before any fault output; warm-transfer or callback path shown.
- [ ] QA-4: advice-request session deflects, never answers, routes to human.
- [ ] Trigger 4 (multiparty): chain_count=3 → pre-band routing, no band rendered, escalation raised.
- [ ] Sign-off: get the firm to tick this row.

Status: [ ] Pending capture    [ ] Captured
