# Item 7 — Data Retention + Storage Policy

## Builder evidence (CODE)

- `architecture/INFRA-PROVISIONING-CHECKLIST.md` — region + retention + ownership.
- `stage-3/app/config.py:STAGE2_TOKENS["{{RETENTION_PERIOD}}"]` — default `"7 years"`, overridable at runtime (CR-4-02).
- `stage-4/app/supabase_store.py` — DB schema for `intake_sessions` + `audit_log`.

## Policy (draft)

- **Region:** Supabase Sydney (ap-southeast-2). Vercel PII functions in `syd1` (Australia).
- **Retention:** {{RETENTION_PERIOD}} (default 7 years, firm to confirm).
- **Backup:** PITR + daily backups (Supabase paid tier).
- **Immutability:** audit_log is append-only at the DB level (G-54).
- **Export:** admin can export the full audit log.

## Deployer evidence (capture against staging)

- [ ] Screenshot: Supabase project settings → region = `ap-southeast-2` (Sydney).
- [ ] Screenshot: Vercel project settings → function region = `syd1`.
- [ ] The final `{{RETENTION_PERIOD}}` value (default 7 years; firm to confirm).
- [ ] Sign-off: get the firm to tick this row.

Status: [ ] Pending capture    [ ] Captured
