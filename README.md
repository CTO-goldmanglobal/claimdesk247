# AI Legal Receptionist + Accident Intake System
### Powered by Goldman Forge

A 24/7 AI legal receptionist for motor-vehicle accident intake across web, voice, and SMS — structured intake, NSW fault pre-assessment (general information, not legal advice), evidence guidance, and tow/rental coordination. Built on a governed, deterministic core with an immutable audit trail.

**Delivery:** Goldman Forge · **Domain sign-off:** legal firm (TBC) · **Co-delivery:** smash-repair panel-shop partner
**Build loop:** Fables (Plan & Audit) → Cursor + MiniMax M3 (Build) · UX via Lovable · RAG via Azure AI Foundry
**Stack:** Supabase (Sydney) · Vercel (`syd1`) · Azure AI Foundry — DeepSeek V4 Flash (AU, ISO 42001)

---

## How this project is built
Every stage runs a closed loop: **Fables defines the spec → Cursor + MiniMax build → Fables audits against numbered gates → pass or one consolidated revision.** A deterministic rule engine — never an LLM — decides fault; the LLM layer (later) only retrieves and phrases. See `LOOP-OPERATING-RULES.md`.

## Read in this order
1. `LOOP-OPERATING-RULES.md` — how the build loop runs (budget, gates, revisions, spec-change protocol)
2. `architecture/ARCHITECTURE-VISION-PHASE-3.md` — confirmed stack + governed RAG roadmap (for the firm)
3. `architecture/LOVABLE-BUILD-CONTRACT.md` — what the UX may build vs must call into (authoritative)
4. `architecture/LOVABLE-PROMPT.md` — paste-ready build prompt derived from the contract
5. `architecture/INFRA-PROVISIONING-CHECKLIST.md` — Vercel + Supabase setup for cto@goldman
6. `templates/` — acceptance-test and self-audit templates used every stage

## Build progress
| Stage | Scope | Status |
|---|---|---|
| 1 | Conversation design · NSW rule tree · persona · disclaimers | ✅ Closed (audit pass) |
| 2 | Web intake · fault engine · PDF summary | ✅ Closed (30/30 tests) |
| 3 | Voice · tow/rental · admin dashboard · intake brief | ✅ Closed (27/27 + regression) |
| 4 | AU-region deploy · MFA · staging QA · sign-off package | 🔄 In progress — AU deploy live (Supabase Sydney + Vercel; claimdesk247.com.au). Remaining: `syd1` functions, app MFA, staging QA, sign-off package |
| 5 | Legal-firm revisions · production | — |

**Stage 4 progress (2026-06-13):** Supabase (Sydney) schema + RLS + append-only audit live; Vercel build fixed and serving; `claimdesk247.com.au` + `www` wired via Cloudflare (SSL issued); dashboard auth-guard shipped; rebranded to ClaimDesk 247. Open: Vercel `syd1` function region, app-level MFA (spec in `handoff/VERCEL-DEPLOY-FIX.md`), staging QA pass, and the legal-firm sign-off package. See `architecture/INFRA-PROVISIONING-CHECKLIST.md` for the itemised status.

Each stage folder holds its build request, acceptance tests, spec files, and the Fables audit report.

## Governance spine (non-negotiable)
Engine decides, LLM describes · grounded-only generation · human verification on unclear/insufficient bands · provenance logged per answer · all data and inference in-region (Australia). Capability grows only with governance.

---
*Powered by Goldman Forge · finn@goldmanglobal.com.au · Status: pre-approval build, internal until legal-firm sign-off.*
