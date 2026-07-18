# ClaimDesk 247 — Master Roadmap

**Date:** 2026-07-18 · **Author:** Cursor (Mac Studio seat) · **For:** the next chat, any seat, any machine

---

## Where the product is right now (live on claimdesk247.com.au)

### ✅ Done + live in production

**Customer-facing site:**
- Landing page rebuilt (trust-first: transparency block, $0 excess, impersonation vow, like-for-like, expanded FAQ, verifiable trust row, crash PWA promo)
- Visual polish (Lovable elevation tokens, gradients, entrance animations, CTA shadows)
- PWA: site is installable (manifest + service worker + install prompt banner + offline fallback page + app shortcuts)
- Chat-app intake with: receptionist avatar, typing indicator, compact chat header, focus management, aria-live
- Identity capture (name + mobile + email after consent, before questions)
- PD disclosure with hash + version (scrollable-to-acknowledge)
- Slot-stage escalation handling (state-scope, esc-injury, reprompt-cap, unmapped-accident-type — 4 handoff panels)
- In-chat photo upload (inline in the conversation, not a separate screen)
- Dashcam acknowledgment (metadata-only, no video upload)
- Browser-native voice: push-to-talk mic + text-to-speech toggle (FREE, no external services)
- CD-R3 compliant: claim types restricted to motor + property_damage; no PL/med-neg
- NSW-only (engine + frontend aligned)
- Customer magic-link login → `/my-cases` page (Supabase auth wired)
- "My cases" link in nav + footer (relogin path)
- Engine wired to production (`.env.production` with `VITE_API_BASE_URL`)

**Golden Rules PWA (`/crash`):**
- Full 8-screen flow (welcome → emergency → location → driver → photos → witnesses → story → review)
- Offline-first (own service worker + manifest + localStorage persistence)
- Installable (maskable icons cropped from claimdesk-logo.png)
- Injury firewall in the story screen

**Backend (owned by backend chat — context for frontend):**
- All `/api/*` endpoints live on https://claimdesk247-engine.vercel.app
- Identity capture, bind-user, case list, slot correction (PATCH)
- Dashboard endpoints: staff case queue, case assignment, sign-offs, operator audit viewer, health, retention trigger
- S3 evidence store (Sydney, SSE-KMS, signed URLs)
- NSW-only intake (stage 1 of multi-state rollout)
- 120+ acceptance tests green

**Specs written + committed:**
- `handoff/RECEPTIONIST-ROBOT-SPEC-2026-07-15.md` — the chat vision
- `handoff/DASHBOARD-SPEC-2026-07-15.md` — staff/customer/operator dashboards
- `handoff/LANDING-REBUILD-SPEC-2026-07-16.md` — landing rebuild (Opus-aligned, built)
- `handoff/CONVERSATIONAL-VOICE-SPEC-2026-07-18.md` — voice shell + migration path
- `handoff/MULTI-STATE-ROLLOUT-PLAN.md` — NSW → VIC/QLD → national

---

## What's NOT done (ranked by priority)

### P0 — launch blockers (must do before real traffic)

| # | Item | Who owns it | Effort | Why it matters |
|---|---|---|---|---|
| 1 | **Firm phone number** (D-8, Opus §14) | Legal Head | 1 decision | Without `VITE_FIRM_PHONE`, no phone CTA renders. 65+ + roadside-panic customers have no voice path. Biggest missing piece. |
| 2 | **CORS lockdown** (CR-5-02) | Backend | 1 hour | Engine accepts `*` origin. Lock to `claimdesk247.com.au` before real traffic. |
| 3 | **Hero image replacement** (P0-2 from audit) | Creative decision | Stock swap or commission | Stock support-worker photo still primes the wrong metaphor (human phone-call, not chat receptionist). |

### P1 — should do soon (quality + completeness)

| # | Item | Who owns it | Effort | Spec/reference |
|---|---|---|---|---|
| 4 | **Staff dashboard real data** (replace hardcoded ROWS) | Frontend | ½ day | Backend endpoints shipped (A1-A4). Dashboard spec §A. |
| 5 | **Brief download via fetch** (fix the broken `<a>` button) | Frontend | ¼ day | Dashboard spec §A2. Replace bare `<a>` with `supabase.auth.getSession()` + fetch + blob. |
| 6 | **Customer case-status view** (B1 endpoint → status labels) | Backend + frontend | Backend ½ day, frontend ¼ day | Dashboard spec §B1. |
| 7 | **Chip-style chat answers** (engine choices as tappable chat chips, not button groups below the bubble) | Frontend | 1-2 days | The biggest remaining "feels like real chat" gap. |
| 8 | **Real testimonials** (when first case closes with a happy customer) | Operations | Wait for real case | Cannot fabricate (Opus §3). The first honest testimonial is the most powerful marketing asset. |
| 9 | **Google Business Profile + local SEO** | Marketing | 1 day setup + ongoing | Competitors rank for "not at fault car accident Sydney". We don't yet. |

### P2 — medium-term (moat-widening)

| # | Item | Who owns it | Effort | Why |
|---|---|---|---|---|
| 10 | **Conversational voice shell** (provider-agnostic, free→Telnyx) | Frontend | 1 week | Spec at `handoff/CONVERSATIONAL-VOICE-SPEC-2026-07-18.md`. Start with free browser provider, migrate to Telnyx via env var. |
| 11 | **Slot correction UI** ("edit prior answer" via PATCH) | Frontend | 1 day | Backend endpoint live. Customer scrolls up, taps prior answer, corrects it. |
| 12 | **"What happened to Annette" educational content** (claim-farming blog post) | Marketing + frontend | 1 day | High SEO value for "is [company] legitimate" searches. Positions ClaimDesk as the safe alternative. |
| 13 | **Partner law-firm visibility** (named, visible on the site) | Legal Head + frontend | 1 decision + ¼ day | Customers want to know who handles their injury handoff. |
| 14 | **VIC + QLD rollout** (stage 2 of multi-state) | Legal Head + backend | Legal review + 1 day eng each | Per `MULTI-STATE-ROLLOUT-PLAN.md`. Each state needs CD-R2 memo + PD counsel memo + sign-off. |

### P3 — long-term (Stage 3+)

| # | Item | Effort | Why |
|---|---|---|---|
| 15 | **Phone hotline** (1300 number, Telnyx PSTN, conversational AI agent) | Weeks | Elderly customers who can't type. A dedicated claims line. Stage 3 architecture. |
| 16 | **Operator dashboard** (`/operator` route — audit log viewer, health, retention controls) | 2-3 days | Backend endpoints shipped (C1-C3). Internal ops tool. |
| 17 | **National rollout** (WA/SA/TAS/ACT/NT) | Legal review + 1 day eng each | Per multi-state plan §3, stage 3. |
| 18 | **RAG layer** (Azure AI Foundry, DeepSeek, AU region) | Weeks | Opus §8. "Engine decides, LLM describes." Post-launch enhancement. |

---

## Recommended build order (next 3-5 chats)

Each line = one focused chat. Fresh context, one deliverable.

1. **Staff dashboard real data** (#4 + #5) — backend endpoints are live; frontend just needs to wire them. Biggest unblocked win.
2. **Chip-style chat answers** (#7) — the UX upgrade that makes the chat feel real.
3. **Conversational voice shell** (#10) — provider-agnostic, starts free, migrates to Telnyx. Spec is ready.
4. **Customer case-status view** (#6) — needs backend B1 endpoint first.
5. **Slot correction UI** (#11) — backend PATCH endpoint is live.

The Legal Head items (#1 phone, #3 hero image, #8 testimonials, #13 law-firm visibility, #14 multi-state) are **not engineering** — they're decisions that unblock engineering. Push for them in parallel.

---

## Key specs (read these first in any new chat)

| Spec | What it covers |
|---|---|
| `handoff/RECEPTIONIST-ROBOT-SPEC-2026-07-15.md` | The chat intake vision (identity, photos, escalation, injury firewall) |
| `handoff/DASHBOARD-SPEC-2026-07-15.md` | Staff + customer + operator dashboards |
| `handoff/LANDING-REBUILD-SPEC-2026-07-16.md` | Landing page (trust-first, Opus-aligned) |
| `handoff/CONVERSATIONAL-VOICE-SPEC-2026-07-18.md` | Voice shell (provider-agnostic, free→Telnyx) |
| `handoff/MULTI-STATE-ROLLOUT-PLAN.md` | NSW → VIC/QLD → national |
| `handoff/PROJECT-SUMMARY-FOR-OPUS.md` | The governance spine (6 non-negotiables) |

---

## The Lovable + Cursor workflow (established)

For visual/design work, Lovable generates; Cursor cleans up + deploys. Known issues:
- Lovable always bumps `@lovable.dev/vite-tanstack-config` in `package.json` (against guardrails). Revert every time.
- Lovable creates `bun.lock`. Delete every time.
- Lovable edits `routeTree.gen.ts` manually. Revert + rebuild locally.
- Lovable commits `.lovable/` metadata. Add to `.gitignore`, remove from tracking.

Pattern: Lovable pushes to `main` → Cursor syncs → reverts violations → rebuilds route tree → verifies tsc + build → deploys.

---

*Roadmap prepared 2026-07-18. Live site: https://claimdesk247.com.au. Engine: https://claimdesk247-engine.vercel.app. Branch: cursor/founding-state-claimdesk247.*
