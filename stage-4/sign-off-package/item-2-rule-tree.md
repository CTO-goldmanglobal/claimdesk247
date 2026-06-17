# Item 2 — Fault Rule Tree + Output Framing

## Builder evidence (CODE)

- `stage-3/app/data/rule-tree.nsw.v3.json` (v3.0.0)
- `stage-1/deliverables/rule-tree-review.md`
- `stage-3/app/engine.py:EngineResult` (deterministic, JSON-serialisable)

## Deployer evidence (capture against staging)

- [ ] Sample classification: rear-end, no injury, no police, 2-car chain → `band=likely`. Save the full response.
- [ ] Sample classification: give-way, no police, 1-car → `band=unclear`. Save the full response.
- [ ] Sample classification: T-junction failure-to-give-way → `band=not-likely`. Save the full response.
- [ ] Run T-25-001..T-25-005 of the weblink runner and attach the output.
- [ ] Sign-off: get the firm to tick this row.

Status: [ ] Pending capture    [ ] Captured
