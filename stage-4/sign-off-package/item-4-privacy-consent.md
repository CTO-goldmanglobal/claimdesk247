# Item 4 — Privacy Notice + Consent Wording

## Builder evidence (CODE)

- `stage-3/app/data/disclaimers.v1.complete.json` — `privacy_collection`, `recording_consent`, `consent_revocation`.
- `stage-3/app/state_machine.py:acknowledge_consent` — gates all PII writes (G-22).
- `stage-2.5/tests/run_acceptance.py` — T-25-002 verifies consent must come first.

## Wording (verbatim)

The exact strings live in `disclaimers.v1.complete.json`. The privacy collection string is the Privacy Act 1988 + APP-compliant notice; the recording consent is the separate voice-recording consent.

## Deployer evidence (capture against staging)

- [ ] QA-8: run a session that explicitly declines consent. Query Supabase `intake_sessions` — the row must not exist.
- [ ] Verify the consent screen text on staging Lovable.
- [ ] Sign-off: get the firm to tick this row.

Status: [ ] Pending capture    [ ] Captured
