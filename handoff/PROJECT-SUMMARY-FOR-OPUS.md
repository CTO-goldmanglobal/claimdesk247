# Project Summary — ClaimDesk 247 (context handoff)
**For:** resuming in a fresh Opus chat · **Date:** 2026-06-13 · **Owner:** finn / Goldman Forge
**Workspace:** `/Users/finn/Smash repair Engine/`

---

## 1. What this project is
An **AI Legal Receptionist + Accident Intake System** (NSW, Australia) — a 24/7 B2C product that takes motor-vehicle-accident details across web/voice/SMS, gives **general information** about NSW fault patterns (never legal advice, never a fault %), guides evidence collection, coordinates tow/rental, and hands a complete brief to a lawyer. Public brand: **ClaimDesk 247** (`claimdesk247.com.au`). Delivered by **Goldman Forge**; a legal firm is the domain sign-off authority.

## 2. How we work — the "Fables loop"
The user plays **Fables** (planner + auditor). I (the assistant) act as Fables. Builders are **Cursor + MiniMax M3** (engine/backend) and **Lovable** (UX). The loop, every stage:

> Fables writes an implementation-ready spec + numbered acceptance gates → builder builds + self-audits + ships green tests → Fables **independently re-runs** and spot-checks → pass (loop closed) or one consolidated revision.

Governing rules live in `LOOP-OPERATING-RULES.md`. Budget-tight, so: deterministic core (no LLM deciding fault), tests are the audit backbone, trivial fixes ride into the next stage as CRs rather than burning a revision cycle.

**Key principle I enforce as auditor:** I never trust the builder's green report — I re-run the suites myself and verify the gates tests can't prove (parity, server-side access, residency, no-PII-in-URL).

## 3. The governance spine (non-negotiable, across every layer)
1. **Engine decides, LLM describes.** A deterministic rule tree assigns the band; no LLM decides fault.
2. **No fault percentage** ever shown — confidence words only: `likely / possible / unclear / insufficient`.
3. **Fixed disclaimers**, rendered verbatim; fail-closed on any out-of-enum band.
4. **Escalation is terminal** for AI assessment (7 triggers route to human).
5. **Residency:** all data + inference in Australia (Supabase Sydney, Vercel `syd1`, Azure AU later).
6. **Immutable audit trail** (append-only) for legal defensibility.

## 4. Build status by stage
| Stage | Scope | Status |
|---|---|---|
| 1 | Conversation design, NSW rule tree, persona, disclaimers | ✅ Closed (audit pass) |
| 2 | Web intake, deterministic fault engine, PDF summary | ✅ Closed — 30/30 |
| 2.5 | Engine-as-endpoint (the `/api/*` contract Lovable calls) | ✅ Closed — 16/16, 73/73 total |
| 3 | Voice, tow/rental, admin dashboard, legal intake brief | ✅ Closed — 27/27 + regression |
| 4 | AU deploy, MFA, staging QA, sign-off package | 🔄 In progress (see §5) |
| 5 | Legal-firm revisions → production | — |

**Engine is the source of truth** and is reused unchanged across web + voice + HTTP (parity gates G-29/G-41 proven). Rule tree is at **v3** (post CR-3-04). Full regression baseline: **73 tests** (30 + 27 + 16).

## 5. Stage 4 — what's DONE vs OPEN (as of 2026-06-13)
The CTO executed provisioning under the **Goldman** accounts (org `CTO-goldmanglobal`, Vercel team `cto-goldmanglobals-projects`, repo `CTO-goldmanglobal/claimdesk247-76a0b7de`).

**Done (the one-way doors are correct):**
- Supabase **Sydney** region verified; RLS on every table; `audit_log` append-only (no UPDATE/DELETE to any role); roles enum `customer/panel_shop_staff/legal_staff/admin`.
- Vercel functions set to **`syd1` only** (removed `iad1`); Goldman team; env vars scoped; preview deploys on.
- Custom domain **claimdesk247.com.au** + `www` via Cloudflare; SSL issued.
- Vercel build fix (`vite.config.ts` → `nitro: { preset: "vercel" }`); dashboard auth-guard shipped; rebranded "Goldman Intake" → **ClaimDesk 247**.

**Open (reversible config):**
- Engine endpoint **not yet wired** to the live site → it still runs a **placeholder engine** (UI shows "Preview mode"). This is the highest-value next step.
- Vercel production branch protection; Supabase PITR/backups confirm; retention period (`{{RETENTION_PERIOD}}`, Stage 5); app-level **MFA** for legal/admin; real logo PNG (Lovable asset 404s off-platform); least-privilege team membership.

## 6. Open CRs carried forward (into Stage 4/5)
- **CR-5-02 — GO-LIVE BLOCKER:** lock CORS to the exact project origin + production domain; current `*.lovable.app` lets any Lovable tenant call the API.
- CR-5-03 rate-limit `/api/session`; CR-5-04 remove hardcoded `inject_band` test special-case; CR-5-01 explicit `/api/intake/:ref/extras` route.
- CR-4-01 voice robustness vs real STT; CR-4-02 wire `{{BUSINESS_HOURS}}`/`{{CALLBACK_SLA}}` to config.

## 7. Decisions still owed by finn / the firm
- **Insurer correspondence draft (§8.3)** — build now (sign-off item 6 complete) or defer to Phase 2?
- **§14 tokens** resolve at Stage 5: firm name, phone, business hours, callback SLA, retention period, approved tow/rental partners.
- Confirm production intake collects all **14 slots** (live preview showed "Step 1 of 5", likely a stub simplification).

## 8. Architecture / stack (confirmed)
- **UX:** Lovable → GitHub (`claimdesk247-76a0b7de`) → Vercel (`syd1`).
- **Data:** Supabase **Sydney**, RLS + append-only audit.
- **Engine:** deterministic Python (FastAPI wrapper at `stage-2.5/app/wrap.py`) exposing `/api/session·consent·slot·classify·pdf·brief·healthz`.
- **RAG (future, Phase 3):** Azure AI Foundry — DeepSeek V4 Flash, AU region, ISO 42001. Hybrid RAG → GraphRAG → human-in-loop, with the rule engine staying authoritative ("engine decides, LLM describes").

## 9. Key files (all under the workspace)
- `README.md` — project index + live build progress.
- `LOOP-OPERATING-RULES.md` — the loop, gates, budget tactics.
- `architecture/` — `ARCHITECTURE-VISION-PHASE-3.md`, `LOVABLE-BUILD-CONTRACT.md`, `LOVABLE-PROMPT.md`, `INFRA-PROVISIONING-CHECKLIST.md` (live status).
- `handoff/` — `CURSOR-UX-HANDOFF.md`, `CTO-SETUP-RUNBOOK.md`, this summary, plus `VERCEL-DEPLOY-FIX.md` and `CLAIMDESK247-CONNECTIONS.md` (created during deploy).
- `stage-1/` … `stage-4/` — each has its build request, acceptance tests (YAML), spec files, and `FABLES-AUDIT-STAGE-N.md`.

## 10. Immediate next actions (recommended order)
1. **Wire the Stage 2.5 engine** to the live site (set `ENGINE_BASE_URL`); flip off preview-mode. This turns the landing page's promises into verified runtime behaviour.
2. Run the **weblink tests**: `BASE_URL=https://claimdesk247.com.au python3 stage-2.5/tests/run_acceptance.py` → expect parity, resolved disclaimers, no %, escalation, MFA gates.
3. Close **CR-5-02 (CORS)** before any real traffic.
4. Finish remaining Stage 4 open items (MFA, branch protection, backups, logo), then assemble the **sign-off package** (Loop Request §12, 8 items) for the firm's single consolidated review.

## 11. Boundary note (why some things stalled)
The connected Supabase/Vercel connectors I can reach are personal accounts (`finn-tang`, `nswcoachcharter-au`), **not** Goldman — and I can't log in as the CTO or enter credentials. Provisioning was therefore done by the CTO directly (correctly, under Goldman). For future infra actions: either reconnect the connectors to the Goldman accounts, or the CTO executes from the runbook with me on standby to generate migrations/config and verify.
