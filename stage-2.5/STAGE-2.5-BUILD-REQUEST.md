# Stage 2.5 Build Request — Engine-as-Endpoint (the API Lovable calls)
**Project:** AI Legal Receptionist + Accident Intake System
**Loop:** Fables (Plan) → Cursor + MiniMax M3 (Build) → Fables (Audit)
**Stage:** 2.5 (bridge between the built engine and the Lovable UX) · **Issued:** 2026-06-13 · Goldman Forge / Fables
**Consumes:** `stage-3/app/` (engine, state_machine, pdf_gen, intake_brief, dashboard, auth, audit)
**Pairs with:** `architecture/LOVABLE-BUILD-CONTRACT.md` (the endpoints below ARE that contract)

---

## 0. Why this stage exists
Lovable's prompt calls `/api/session`, `/api/slot`, `/api/classify`, `/api/pdf/:ref`, `/api/brief/:ref`, `/healthz`. The logic behind all of these **already exists** in `stage-3/app/`. This stage does **not** build new logic — it **exposes the existing engine and flow over HTTP** so the UX and the weblink tests target one real contract. Zero fault logic is written here. If you find yourself writing classification, stop — call `app.engine.classify`.

---

## 1. Scope
- **In:** a thin HTTP API (FastAPI, already in the stack) wrapping the existing engine, state machine, PDF, brief, audit, and auth. Deployable to Vercel `syd1`. CORS for the Lovable origin.
- **Out:** any new fault/disclaimer logic; UI (Lovable); the RAG layer; production data store (still `SessionStore` Protocol — Supabase adapter is Stage 4).

---

## 2. The contract (implement exactly — Lovable depends on these shapes)

| Endpoint | Method | Request | Response | Backed by |
|---|---|---|---|---|
| `/healthz` | GET | — | `{ status: "ok", engine_version, rule_tree_version }` | static |
| `/api/session` | POST | `{ channel }` | `{ reference, consent_required: true, next: "consent" }` | state_machine S0/S0a |
| `/api/consent` | POST | `{ reference, accept: bool }` | accept → `{ next: "slot", slot }` · decline → `{ next: "abandoned" }` (no PII persisted) | S0a |
| `/api/slot` | POST | `{ reference, slot, value }` | `{ accepted, next_slot \| next: "classify", reprompt?, escalation? }` | state_machine S3 + validation |
| `/api/classify` | POST | `{ reference }` | `{ band, outputText, disclaimerText }` — **disclaimer already resolved** | `engine.classify` + disclaimer post-processor |
| `/api/pdf/:ref` | GET | path ref | PDF bytes (9-section customer summary) | pdf_gen |
| `/api/brief/:ref` | GET (role-gated) | path ref | intake brief JSON | intake_brief (legal/admin only) |

**Response rules (carry the governance across HTTP):**
- `/api/classify` returns the engine's band verbatim and the **resolved** disclaimer string. The API never re-bands and never returns an unresolved `{{...}}` token (G-18 across HTTP).
- `band` ∈ `{likely, possible, unclear, insufficient}`; fail-closed on anything else (G-16).
- Escalation: if any of the 7 triggers fired, `/api/slot` or `/api/classify` returns `{ escalation: <id>, next: "escalated" }` and **no band** — terminal (G-19/G-32).
- **No PII in URLs or query strings.** Everything keyed by opaque `reference` in the POST body. `:ref` in pdf/brief paths is the opaque session reference, not a name (G-23).
- `/api/brief` enforces role server-side (G-33) — `customer`/anon → 403.

---

## 3. Implementation constraints
- FastAPI app exposing the routes; mount the existing modules — do not duplicate them.
- **Parity is the whole point:** the band returned by `/api/classify` for a given intake MUST equal `app.engine.classify(intake).band` for the same intake. A test asserts this directly (T-25-001).
- `x-test-mode: 1` header (preview/staging only) seeds deterministic time + reference so weblink runs reproduce. **Must be a no-op / rejected in production** (env-gated).
- CORS allow-list: the Lovable preview origin + the production domain only.
- Stateless functions + `SessionStore` for state (Supabase adapter swaps in at Stage 4). No engine state in the web process.
- Secrets/service keys server-side only.

---

## 4. Acceptance gates (continue the gate-ID space)

| ID | Gate | Pri |
|---|---|---|
| G-41 | `/api/classify` band == `engine.classify` band for identical intake (HTTP parity) | P0 |
| G-42 | Disclaimer resolved in every classify response; zero unresolved `{{...}}`; band enum enforced, fail-closed | P0 |
| G-43 | Escalation short-circuits over HTTP — escalated response carries trigger id, no band, terminal | P0 |
| G-44 | No PII in any URL/query; all keyed by opaque reference | P0 |
| G-45 | `/api/brief` role-gated server-side (customer/anon → 403) | P0 |
| G-46 | `x-test-mode` works on preview, is inert in production (env-gated) | P1 |
| G-47 | `/healthz` returns engine + rule-tree versions; runner aborts if down | P1 |
| G-48 | Regression: Stage 2 (30) + Stage 3 (27) suites still green | P0 |
| G-49 | CORS limited to allow-listed origins; no wildcard in production | P1 |

## 5. Tests
- `stage-2.5/acceptance-tests.stage25.yaml` — black-box HTTP cases (`T-25-xxx`) driving the real endpoints via TestClient locally and the same cases runnable against a deployed `BASE_URL` (the weblink).
- Must also run the Stage 2 + Stage 3 suites (G-48).
- Green both ways before submit.

## 6. Delivery manifest (Operating Rules §3)
Gate self-check (G-41…G-49) · traceability · combined green report (incl. weblink run instructions) · known gaps · CRs · compliance quick-scan. **Pin test deps** (`requirements-dev.txt`) per CR-4-04 — this is where the weblink runner needs them.

## 7. Budget note
Smallest stage in the project: no new logic, just transport. The risk isn't cost, it's someone "helpfully" re-implementing classification in the API layer — G-41 parity exists to catch exactly that. Build the wrapper, prove parity, done.

---
*Prepared by Fables · finn@goldmanglobal.com.au · 2026-06-13*
