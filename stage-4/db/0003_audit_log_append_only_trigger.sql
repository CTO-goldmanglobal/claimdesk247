-- 0003_audit_log_append_only_trigger.sql
-- G-54 belt-and-braces hardening (Decision D-7a, 2026-06-14).
-- The 0002 schema makes audit_log append-only at the GRANT/RLS level for
-- anon/authenticated (verified live). This trigger additionally blocks
-- UPDATE and DELETE for EVERY role — including service_role and the table
-- owner — so the audit trail can never be rewritten, even by the engine.
-- INSERT remains allowed (the engine appends via service_role).

create or replace function public.audit_log_no_mutate()
returns trigger
language plpgsql
as $$
begin
  raise exception 'audit_log is append-only: % is not permitted', tg_op
    using errcode = '0A000';  -- feature_not_supported
end;
$$;

drop trigger if exists audit_log_block_mutate on public.audit_log;

create trigger audit_log_block_mutate
  before update or delete on public.audit_log
  for each row
  execute function public.audit_log_no_mutate();

-- Verify (run after applying):
--   UPDATE public.audit_log SET action = 'x' WHERE entry_id = (SELECT min(entry_id) FROM public.audit_log);
--   -- expected: ERROR  audit_log is append-only: UPDATE is not permitted
--   DELETE FROM public.audit_log WHERE entry_id = (SELECT min(entry_id) FROM public.audit_log);
--   -- expected: ERROR  audit_log is append-only: DELETE is not permitted
