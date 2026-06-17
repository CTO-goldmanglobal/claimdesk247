# Lovable Build Contract — UX on the Right Base
**Purpose:** give Lovable a foundation that keeps the engine and disclaimers authoritative, and makes the deployed app testable via a weblink.
**Date:** 2026-06-13 · Fables → Lovable build
**Reads with:** `ARCHITECTURE-VISION-PHASE-3.md`, the Stage 2/3 build requests, `LOOP-OPERATING-RULES.md`

---

## 1. The boundary — what Lovable builds vs what it calls into

| Lovable BUILDS (UX) | Lovable MUST CALL INTO (authoritative, do not reimplement) |
|---|---|
| Multi-step intake forms, chat wrapper, dashboard screens | The fault engine `classify(intake)` — **the only thing that decides band** |
| Styling, layout, responsiveness, embeddable widget shell | The FIXED disclaimer + framing strings — render verbatim, never reword |
| Auth screens, role-gated navigation | Supabase RLS policies — access enforced server-side, not by hiding UI |
| Status tags, notes, PDF download buttons | The audit-log writer — append-only, never client-editable |

**Hard rule:** Lovable must not generate its own fault logic, its own confidence wording, or its own disclaimer copy. If it offers to "make the result friendlier" or "explain who's at fault," that's a violation of the no-advice guardrail. The UI displays the engine's output strings; it does not author them.

## 2. Contract endpoints (the seam Lovable consumes)
Expose the engine + flow behind a stable API so the UX and the test runner both target the same contract:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/session` | POST | start session, returns reference + consent state |
| `/api/slot` | POST | submit one slot value, server validates, returns next slot |
| `/api/classify` | POST | run engine on completed intake → `{ band, outputKey, disclaimerResolved }` |
| `/api/pdf/:ref` | GET | render 9-section customer PDF |
| `/api/brief/:ref` | GET | legal-firm intake brief (role-gated) |
| `/healthz` | GET | liveness for the deployed weblink |

- `classify` returns the engine's band + the **already-resolved** disclaimer text. Lovable renders it; it never re-resolves `{{...}}` or re-bands.
- No PII in URLs or query params (use POST bodies + session reference).

## 3. Supabase base (get this right at creation)
- Region: **Sydney** (confirmed).
- `intake_sessions`, `audit_log` tables behind **RLS**: `customer` cannot read any dashboard data; `panel_shop_staff` / `legal_staff` / `admin` scoped per Loop Request §9.
- `audit_log`: RLS policy **blocks UPDATE and DELETE** for all roles (append-only). Lovable's UI gets a read-only view only.
- Service-role key never shipped to the client; all writes go through server functions.

## 4. Vercel base
- PII-touching functions deployed to **`syd1`** (Australia), not a US/EU edge region.
- A **staging deployment** (preview URL) is the test target — see §5.

## 5. Testing against the weblink (what you asked for)
The acceptance suites (30 Stage 2 + 27 Stage 3) become **black-box HTTP tests** against the deployed preview URL, so you test the real running app, not a local stub:

1. Point the runner at the Vercel preview URL: `BASE_URL=https://<preview>.vercel.app`.
2. Each YAML case drives `/api/session` → `/api/slot` × n → `/api/classify` and asserts the same `expect` (band, escalation, disclaimer present, no %).
3. A `x-test-mode` header (staging only) seeds deterministic time/refs so runs are reproducible. **Disabled in production.**
4. `/healthz` gate first — runner aborts if the deployment is down.
5. Green = both suites pass against the live URL. Same bar as before: green before audit.

This gives you a single shareable link where anyone (you, Fables, the firm) can exercise the flow, and the same link is what the automated suite hammers. Keep the engine assertions intact: the weblink must produce the **same bands** as the local engine (gate G-29 parity, now across HTTP).

## 6. What this protects
The split stack (Lovable UX + Cursor/MiniMax engine + Azure RAG later) only stays governed if there is exactly one place that decides fault and one set of disclaimer strings. This contract makes the UX a renderer over that authority, so adding the RAG layer later changes *how answers are phrased*, never *who decides* — and the weblink tests prove it on every deploy.

---
*Build contract — hand to Lovable with the architecture-vision note.*
