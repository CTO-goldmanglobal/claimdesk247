# Infra Provisioning Checklist — Vercel + Supabase (Goldman org)
**For:** cto@goldman · **Owner:** Goldman org (not an individual login)
**Project:** AI Legal Receptionist + Accident Intake System — **ClaimDesk 247**
**Date:** 2026-06-13 · Fables · **Status updated:** 2026-06-13 (provisioning executed)

This holds personal data under the Privacy Act 1988 in a legal context. Get these right at creation — several can't be changed later.

> **Scope lock:** This project is **claimdesk247.com.au only**. Do **not** mix with `finntang.com` or `wealth.goldmanglobal.com.au` — separate repos, Supabase projects, and Vercel projects. See `handoff/CLAIMDESK247-CONNECTIONS.md`.

## Ownership & access (do first)
- [x] Resources under the **Goldman org**: Supabase org `CTO-goldmanglobal`, Vercel team `cto-goldmanglobals-projects`, GitHub `CTO-goldmanglobal/claimdesk247-76a0b7de`.
- [ ] Add members with **least privilege** (developers ≠ billing ≠ production admin). *Open — review team membership.*
- [x] Production secrets server-side only — enforced in code (`.env.example`; anon/publishable key is browser-safe; `service_role` never client-side). `SUPABASE_SERVICE_ROLE_KEY` not yet set (waits on engine deploy).
- [ ] **MFA on both orgs** + app-level MFA for legal/admin (Stage 4 gate §10.5). *Open — app MFA spec written in `handoff/VERCEL-DEPLOY-FIX.md`; org MFA to confirm.*

## Supabase (can't be changed after creation)
- [x] **Region: Sydney (ap-southeast-2)** — verified in project settings. ✅
- [ ] Paid tier → **point-in-time recovery / daily backups**. *Project is on PRO — confirm PITR/backups are enabled.*
- [x] Row Level Security **ON for every table** — verified (`user_roles`, `intake_sessions`, `intake_answers`, `audit_log` all `relrowsecurity = true`). ✅
- [x] `audit_log` append-only — no UPDATE/DELETE granted to any role (incl. service_role). ✅
- [x] Roles defined: `customer` / `panel_shop_staff` / `legal_staff` / `admin` (enum `app_role`). ✅
- [ ] Retention policy — set to firm-confirmed period (suggest 7 years); `{{RETENTION_PERIOD}}` resolves at Stage 5. *Open.*

## Vercel
- [x] **Function region: `syd1` (Australia)** — set in Project → Settings → Functions to **Sydney (`syd1`) only** (removed `iad1`); redeployed. Residency for PII functions ✅.
- [x] Use a **Team** — `cto-goldmanglobals-projects`. ✅
- [ ] **Protect the production branch** (required reviewer before prod deploy). *Open.*
- [x] Preview deployments enabled (weblink test targets). ✅
- [x] Env vars scoped per environment: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `NITRO_PRESET=vercel` set (preview + production). `VITE_TEST_MODE` blank in prod. ✅
- [x] Custom domain `claimdesk247.com.au` (apex) + `www` (308/307 → apex) via Cloudflare DNS (DNS-only); SSL issued. ✅

## Build / deploy fix (added 2026-06-13)
- [x] Vercel build target fixed: `vite.config.ts` sets `nitro: { preset: "vercel" }` (Lovable wrapper otherwise skipped Nitro → 404). App serves on Vercel + custom domain. ✅
- [x] Dashboard auth-guard: `/dashboard` redirects unauthenticated visitors to `/auth` (RLS still server-side). ✅
- [x] Rebrand: "Goldman Intake" → **ClaimDesk 247** across staff UI. ✅
- [ ] **Logo** on Vercel: `index.tsx` imports a Lovable `.asset.json` whose URL (`/__l5e/...`) 404s off-Lovable. *Open — add real PNG to `public/` and reference directly.*

## Azure AI Foundry (when RAG layer starts — not yet)
- [ ] Region **Australia East**; DeepSeek V4 Flash, no-retention terms (in-region, ISO 42001).

## Sign-off linkage
Feeds the legal-firm sign-off package (Loop Request §12): item 7 (retention & storage) and §10.3/§10.5 privacy/security. Capture final region/retention/access settings as evidence. **Evidence captured so far:** Supabase region = Sydney; Vercel team = Goldman; RLS + append-only audit verified.

---
*Region and ownership choices are one-way doors — the one-way doors (Goldman ownership, Sydney region) are confirmed done. Remaining open items are reversible config: syd1 functions, branch protection, backups, retention, MFA, logo.*
