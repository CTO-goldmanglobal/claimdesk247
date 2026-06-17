# Cursor UX Handoff — ClaimDesk 24/7 (paste into a new Cursor chat)
**Project:** AI Legal Receptionist + Accident Intake System (NSW, Australia)
**Repo:** `https://github.com/CTO-goldmanglobal/claimdesk247-76a0b7de.git` (Lovable-generated UI)
**Live (stub):** https://claimdesk247.lovable.app · **Date:** 2026-06-13

You are working on the **UX only**. A separate deterministic engine decides fault and owns all legal wording. Your job is to make the interface excellent and call into that engine — never reimplement it.

---

## 1. Current state
- Lovable built a calm, governance-forward intake UI (serif headings, navy, quiet). Branded **"Goldman Intake"** in-app though the domain is `claimdesk247`. **Brand decision needed** — pick one public B2C name (recommend "ClaimDesk 24/7"; "Goldman Intake" reads internal/B2B).
- Landing page leads with the right governance promises: "no fault percentages", "confidence in words — likely, possible, unclear", "data hosted in Sydney", "nothing personal sits in a web link".
- Flow verified live: consent gate is first (before any data), then one question per step ("Step 1 of 5"), chat layout. URL stayed clean (no PII in query).
- **It runs a placeholder engine** ("Preview mode" banner). Real assessments need the engine endpoint wired (see §4).

## 2. The hard rules (do not violate — this is a legal product)
1. **Never write fault/liability logic.** Call `/api/classify`; render exactly what it returns. No band decided client-side.
2. **Never write or reword disclaimers or "general information" text.** Render the API's strings verbatim. Don't "make them friendlier."
3. **Never show a fault percentage.** Confidence words only: likely / possible / unclear / insufficient.
4. **No PII in URLs or query params.** POST bodies + opaque session reference (`GF-XXXXXXXX`) only.
5. **Staff dashboard behind auth**, server-side (Supabase RLS) — not just hidden UI. MFA required for legal/admin roles.
6. **Service-role key never in client code.**

## 3. The API contract (call these — don't build the logic behind them)
| Endpoint | Method | Purpose |
|---|---|---|
| `/api/session` | POST | start session → reference + consent state |
| `/api/consent` | POST | accept → first slot; decline → abandoned, nothing persisted |
| `/api/slot` | POST | submit one answer → next slot or `next: classify` |
| `/api/classify` | POST | → `{ band, outputText, disclaimerText }` (disclaimer already resolved — render as-is) |
| `/api/pdf/:ref` | GET | customer PDF (9 sections) |
| `/api/brief/:ref` | GET | legal-firm brief (role-gated, MFA) |
| `/healthz` | GET | liveness |

Engine base URL comes from env (`ENGINE_BASE_URL`). Backed by `stage-2.5/app/wrap.py`.

## 4. What to build / fix (UX backlog)
1. **Wire the real engine** — replace the placeholder; point at `ENGINE_BASE_URL`; remove the preview-mode stub path for production.
2. **Resolve the brand** — one name across domain + UI + logo.
3. **Confirm the full intake** — production flow is **14 slots** (not 5). Verify the UI collects all mandatory slots; "Step 1 of 5" looks like a placeholder simplification.
4. **Results screen** — render `band` as a confidence word + `disclaimerText` inline, verbatim. No percentage, ever. Add the escalation state (when API returns `{escalation, next: escalated}` show the calm "a lawyer will call you" handoff, no band).
5. **Consent + privacy copy** — must come from the API's FIXED strings, not hardcoded in components.
6. **Staff dashboard** — auth-gate it (Supabase RLS + MFA); it should not be a prominent public button on the consumer hero.
7. **PDF + brief** — wire `/api/pdf/:ref` (customer) and `/api/brief/:ref` (legal, role-gated).
8. **Accessibility + mobile** — stressed users on phones; large tap targets, one action per screen.

## 5. Design direction (keep it)
Calm and trustworthy beats loud. Energy through momentum ("2 min to start", clear steps), not pressure. No crash imagery, no countdown timers, no "act now". One primary action per screen. The disclaimer visible, not buried — it's a trust feature here, not fine print.

## 6. How to test your work (weblink harness already exists)
Once the engine is wired to the deployed URL:
```
BASE_URL=https://<preview-url> python3 stage-2.5/tests/run_acceptance.py
```
18 HTTP cases assert parity (UI/engine agree), resolved disclaimers, no percentages, escalation short-circuit, role-gating, MFA. Green = the governance promises on the landing page are true at runtime, not just claimed.

## 7. Boundary reminder
If the UI ever looks like it's *deciding* or *advising* rather than *collecting and displaying*, that's the line. The engine decides; you render. The full governance spec is `architecture/LOVABLE-BUILD-CONTRACT.md` — if anything here is ambiguous, the contract wins.
