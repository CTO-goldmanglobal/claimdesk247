# Item 8 — Audit Log Specification

## Builder evidence (CODE)

- `stage-3/app/audit.py:AuditLog` — append-only at the language level (`AuditMutationError` on mutation).
- `stage-4/app/supabase_store.py` — DB-level append-only via RLS policies:
  ```sql
  CREATE POLICY audit_log_no_update ON audit_log FOR UPDATE USING (false);
  CREATE POLICY audit_log_no_delete ON audit_log FOR DELETE USING (false);
  ```
- `stage-3/app/dashboard.py:audit_export` — admin export endpoint.

## Schema (DB)

```
audit_log
  entry_id    BIGSERIAL PK
  ts          TIMESTAMPTZ DEFAULT now()
  session_id  TEXT
  actor       TEXT
  action      TEXT
  inputs      JSONB
  rule_path   JSONB
  output      JSONB
```

## Deployer evidence (capture against staging)

- [ ] QA-11: SQL `DELETE FROM audit_log WHERE entry_id=-1;` must return "permission denied for table audit_log".
- [ ] QA-11: SQL `UPDATE audit_log SET action='x' WHERE entry_id=-1;` must return "permission denied".
- [ ] QA-12: `GET /api/audit/export?as_email=admin@goldman.example` returns full records. Save a sample.
- [ ] Sign-off: get the firm to tick this row.

Status: [ ] Pending capture    [ ] Captured
