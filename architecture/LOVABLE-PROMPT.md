# Lovable Build Prompt — paste this into Lovable
*Derived from `LOVABLE-BUILD-CONTRACT.md` (the authoritative spec). If they ever disagree, the contract wins.*

---

Build a web app for an AI Legal Receptionist + accident intake system (NSW, Australia). You are building the **UI only**. A separate deterministic engine decides everything about fault and disclaimers — you call it, you never reimplement it.

**Hard rules (do not violate):**
- Do NOT write any fault/liability logic. Never decide or guess who is at fault. Call the `/api/classify` endpoint and display exactly what it returns.
- Do NOT write or reword any legal disclaimer or "general information" text. Render the exact strings the API returns, verbatim. Do not "make them friendlier."
- Never show a fault percentage. The system uses confidence words only: likely / possible / unclear / insufficient.
- No personal information in URLs or query params — use POST bodies and a session reference.

**Stack:**
- Supabase in the **Sydney region** for data and auth.
- Deploy on Vercel; any function that touches personal data runs in the `syd1` (Australia) region.

**Screens to build:**
1. Multi-step intake form with a chat-style wrapper: consent first, then accident details (one step per question), then a results screen that shows the engine's general-information output + disclaimer.
2. Customer "download my summary PDF" button (calls `/api/pdf/:ref`).
3. Staff dashboard with role-gated views: panel-shop staff and legal staff see different things; customers cannot reach it at all.

**API the UI calls (do not build the logic behind these — call them):**
- `POST /api/session` → start session, returns reference + consent state
- `POST /api/slot` → submit one answer, returns the next question
- `POST /api/classify` → returns `{ band, outputText, disclaimerText }` — render as-is
- `GET /api/pdf/:ref` → customer PDF
- `GET /api/brief/:ref` → legal-firm brief (legal/admin roles only)
- `GET /healthz` → health check

**Supabase data rules (enforce server-side, not just by hiding UI):**
- Use Row Level Security. `customer` role can read nothing in the dashboard. Only `panel_shop_staff`, `legal_staff`, `admin` see dashboard data, scoped per role.
- An `audit_log` table that is **append-only**: RLS must block UPDATE and DELETE for every role. The UI gets a read-only view of it.
- The Supabase service key stays server-side, never shipped to the browser.

**Make it testable by URL:** every preview deploy must expose the API endpoints above so an external test script can drive a full intake (`/api/session` → `/api/slot` × n → `/api/classify`) against the live URL and get the same results as the local engine. Add an `x-test-mode` header (staging only, off in production) that seeds a fixed time and reference so test runs are reproducible.

Mobile-responsive. Plain, calm, professional tone in the UI chrome (the actual legal wording comes from the API).

---

## Note for you (not for Lovable)
The one dependency this prompt assumes: the deterministic engine must be reachable at those `/api/*` routes. Right now it lives inside the Cursor/MiniMax app — it needs to be exposed as a small service (that's the "Stage 2.5 / engine-as-endpoint" item I flagged). Until that exists, Lovable will stub the API and the weblink tests can't prove parity. Decide whether to stand up the engine endpoint first, or let Lovable build against a stub and wire the real engine in at Stage 4.
