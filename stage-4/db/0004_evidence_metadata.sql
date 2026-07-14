-- 0004_evidence_metadata.sql
-- Feature 2: metadata table for customer-uploaded photo evidence.
--
-- **Storage decision (2026-07-14, user-confirmed):** the file BYTES live in
-- AWS S3, Sydney region ap-southeast-2 (two-tier lifecycle: Standard → Glacier
-- Deep Archive at 90 days; expire at the retention horizon). The metadata
-- row lives here in Postgres so the case-file view can enumerate evidence
-- without LISTing S3. See:
--   * EVIDENCE-STORAGE-SETUP.md        — AWS bucket + IAM + lifecycle runbook
--   * EVIDENCE-UPLOAD-DESIGN-2026-07-14.md — full storage rationale
--
-- Why S3 Sydney two-tier (NOT Supabase Storage, NOT Google Drive, NOT Mac Studio):
--   * Same Sydney region as the engine's privacy-notice promise ("Australia-only").
--   * Uncapped — 8GB Supabase Storage ceiling would fill within months.
--   * Cheap — Standard ~$0.0255/GB/mo, Glacier Deep Archive ~$0.0011/GB/mo.
--     At 500GB blended ~$3-5 AUD/mo; client-side resize makes it ~13x cheaper.
--   * Same auth/audit surface — the engine mints short-TTL signed URLs after the
--     consent gate; the audit_log chain records every read/write/delete.
--
-- This migration is IDEMPOTENT — safe to re-run.
-- Run order: 0002 → 0003 → 0004.

begin;

-- ---------------------------------------------------------------------------
-- case_evidence — one row per uploaded evidence file. NOTE: this table holds
-- NO direct customer PII (no names, no contact details); it stores the opaque
-- intake reference, the S3 key (also reference-keyed), and a SHA-256 of the
-- file bytes for tamper-evidence. The uploaded_by column does carry the
-- uploader's IP (customer) or email (staff) for the audit chain — that is
-- operator metadata, not customer-supplied PII, and is treated as personal
-- data under the Privacy Act 1988 (retention matches the audit_log policy).
-- ---------------------------------------------------------------------------
create table if not exists public.case_evidence (
    evidence_id          uuid primary key default gen_random_uuid(),
    reference            text not null,                       -- GF-XXXXXXXX, opaque
    s3_key               text not null,                       -- {reference}/{uuid}.{ext}
    s3_bucket            text not null,
    content_type         text not null,                       -- canonical image MIME
    size_bytes           integer not null check (size_bytes > 0),
    content_hash_sha256  text not null,                       -- tamper-evidence
    uploaded_at          timestamptz not null default now(),
    uploaded_by          text not null,                       -- client IP | staff email
    -- Soft-delete for retention purge. The S3 object is deleted too; this
    -- column keeps the row for audit (the audit_log itself is append-only).
    deleted_at           timestamptz,
    -- Lifecycle mirror — set to 'GLACIER_DEEP_ARCHIVE' once the lifecycle
    -- rule transitions the object. Read-only hint; the truth lives in S3.
    storage_class        text not null default 'STANDARD'
);

-- Index for list-by-reference (the GET endpoint's only hot query).
create index if not exists case_evidence_reference_idx
    on public.case_evidence (reference, uploaded_at)
    where deleted_at is null;

-- Index for the retention purge (find rows older than the horizon).
create index if not exists case_evidence_uploaded_at_idx
    on public.case_evidence (uploaded_at)
    where deleted_at is null;

-- Enforce the per-case count cap at the DB too. The app validates first, but
-- a belt-and-braces trigger prevents a runaway client from exceeding 20 rows
-- per case even if the app cap is bypassed (e.g. concurrent uploads).
create or replace function public.case_evidence_enforce_cap()
returns trigger
language plpgsql
as $$
declare
    n integer;
begin
    select count(*) into n
      from public.case_evidence
     where reference = new.reference
       and deleted_at is null;
    if n >= 20 then
        raise exception 'case_evidence cap reached for reference %', new.reference
            using errcode = '23301';
    end if;
    return new;
end;
$$;

drop trigger if exists case_evidence_cap_trigger on public.case_evidence;
create trigger case_evidence_cap_trigger
    before insert on public.case_evidence
    for each row execute function public.case_evidence_enforce_cap();

-- Prevent updates to the integrity columns — soft-delete + storage_class are
-- the only fields that should ever change post-insert. The hash, key, size,
-- and content_type are immutable for the row's lifetime.
create or replace function public.case_evidence_immutable_fields()
returns trigger
language plpgsql
as $$
begin
    if new.content_hash_sha256 is distinct from old.content_hash_sha256
       or new.s3_key is distinct from old.s3_key
       or new.size_bytes is distinct from old.size_bytes
       or new.content_type is distinct from old.content_type
       or new.reference is distinct from old.reference then
        raise exception 'case_evidence integrity fields are immutable'
            using errcode = '0A000';
    end if;
    return new;
end;
$$;

drop trigger if exists case_evidence_immutable_trigger on public.case_evidence;
create trigger case_evidence_immutable_trigger
    before update on public.case_evidence
    for each row execute function public.case_evidence_immutable_fields();

-- ---------------------------------------------------------------------------
-- RLS — mirror intake_sessions posture. service_role bypasses RLS for
-- server-side writes (G-53). Authenticated staff read for the dashboard;
-- anon + customer roles get nothing from this table — the HTTP layer mints
-- short-TTL signed S3 URLs for the customer browser instead.
-- ---------------------------------------------------------------------------
alter table public.case_evidence enable row level security;
grant select on public.case_evidence to authenticated;

drop policy if exists "Staff can read case_evidence" on public.case_evidence;
create policy "Staff can read case_evidence"
    on public.case_evidence for select to authenticated
    using (public.is_staff(auth.uid()));

commit;

-- -----------------------------------------------------------------------
-- Verify (run after applying):
-- -----------------------------------------------------------------------
-- 1. As service_role (engine): INSERT a row → succeeds.
-- 2. As anon: SELECT * FROM public.case_evidence;        → 0 rows
-- 3. As a staff session: SELECT * FROM public.case_evidence LIMIT 1;  → rows visible
-- 4. UPDATE public.case_evidence SET content_hash_sha256='x' WHERE ...;
--    → ERROR: case_evidence integrity fields are immutable
-- 5. INSERT 21 rows for one reference on the 21st → ERROR: cap reached
