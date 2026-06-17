# Item 5 — Customer PDF Summary Template

## Builder evidence (CODE)

- `stage-3/app/pdf_gen.py:render_summary_pdf` — sections per `stage-2/spec/pdf-summary.v1.md`.
- `stage-2.5/tests/run_acceptance.py` — T-25-007, T-25-008 verify PDF served via opaque ref only; no PII in URL.

## Template sections (per `pdf-summary.v1.md`)

1. Cover (firm letterhead, reference, date)
2. Intake summary (state, datetime, accident type, parties, damage, injuries)
3. Fault statement (resolved from `{{...}}` tokens; band or escalation)
4. Disclaimers (full master text)
5. Evidence checklist
6. References (rule tree path, scenario id)

## Deployer evidence (capture against staging)

- [ ] Generate a sample PDF from staging with the REAR_END_INTAKE. Save as `qa-evidence/sample-pdf-rear-end.pdf`.
- [ ] Sign-off: get the firm to tick this row.

Status: [ ] Pending capture    [ ] Captured
