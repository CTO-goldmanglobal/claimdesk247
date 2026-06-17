-- Stage 4 — reconcile the live Supabase schema to the engine's SessionStore.
-- The Lovable repo's db/0001 created intake_sessions/audit_log with a DIFFERENT
-- shape than stage-4/app/supabase_store.py reads/writes (F-B in the Stage 4
-- audit). This replaces those (empty, not yet read by the live UI) with the
-- engine's expected shapes, while KEEPING the role infra (app_role enum,
-- user_roles, has_role(), is_staff()) from db/0001.
--
-- service_role (engine, server-side) bypasses RLS for writes. RLS here protects
-- the authenticated/anon (dashboard/browser) path: staff read-only, customers
-- nothing (G-53), audit_log append-only (G-54).

begin;

-- Drop the Lovable scaffolding tables (empty; live UI uses demo rows, not these).
drop table if exists public.intake_answers cascade;
drop table if exists public.intake_sessions cascade;
drop table if exists public.audit_log cascade;

-- ---------------------------------------------------------------------------
-- Engine session store (written by the engine via service_role).
-- ---------------------------------------------------------------------------
create table public.intake_sessions (
  session_id        text primary key,
  reference         text unique,
  state             text,
  intake            jsonb,
  escalation        text,
  escalation_reason text,
  engine_result     jsonb,
  created_at        timestamptz not null default now()
);
alter table public.intake_sessions enable row level security;
grant select on public.intake_sessions to authenticated;

-- G-53: only staff can read; customers/anon get nothing. service_role bypasses RLS.
create policy "Staff can read intake_sessions"
  on public.intake_sessions for select to authenticated
  using (public.is_staff(auth.uid()));

-- ---------------------------------------------------------------------------
-- Append-only audit log (G-54).
-- ---------------------------------------------------------------------------
create table public.audit_log (
  entry_id   bigint generated always as identity primary key,
  ts         timestamptz not null default now(),
  session_id text,
  actor      text,
  action     text not null,
  inputs     jsonb,
  rule_path  jsonb,
  output     jsonb
);
alter table public.audit_log enable row level security;
grant select on public.audit_log to authenticated;

-- Staff read-only. No INSERT/UPDATE/DELETE policy for authenticated => append-only
-- from any client; inserts come from the engine via service_role (bypasses RLS).
create policy "Staff can read audit_log"
  on public.audit_log for select to authenticated
  using (public.is_staff(auth.uid()));

commit;
