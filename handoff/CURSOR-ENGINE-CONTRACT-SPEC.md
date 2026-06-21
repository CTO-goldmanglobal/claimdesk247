> ✅ **SUPERSEDED — BUILT & DEPLOYED 2026-06-14 (commit `b71c3ea`).** This F-F work was completed and verified in-session, not handed to Cursor. The engine (`stage-2.5/app/wrap.py`) now serves both the frontend contract (`ref`/camelCase) and the engine-contract tests (`reference`) on the same endpoints. Verified: 18/18 + 75/75 in workspace, live frontend-shaped flow + CORS + in-browser intake on `claimdesk247.com.au`. See `FABLES-AUDIT-STAGE-4.md` §F-F. Kept below for reference / Opus audit of the change.

---

# Cursor build spec — align engine API to the frontend contract (F-F)
**For:** Cursor + MiniMax (build) → Opus 4.8 (audit). **Date:** 2026-06-14.
**Why:** the engine is deployed and works, the frontend is wired to it, but they speak different API dialects so the live intake fails at consent. The engine must DRIVE the conversation (ask questions, collect answers, classify); the website only renders what the engine returns.

## Current state (already done — don't redo)
- Engine live: `https://claimdesk247-engine.vercel.app` (Vercel, `syd1`), `/healthz` green. Repo `CTO-goldmanglobal/claimdesk247-engine` (push with the CTO token → auto-deploys).
- Supabase (Sydney): `intake_sessions` + append-only `audit_log` match the engine's `SupabaseStore`; full intake→classify verified against the live DB.
- Frontend `claimdesk247.com.au` wired via `VITE_API_BASE_URL` → engine. Consent step currently errors (this spec fixes that).

## The mismatch (engine must change to match the frontend — frontend is Lovable-synced, leave it alone)
Frontend contract (`src/lib/api/client.ts`, `types.ts` in `claimdesk247-76a0b7de`):
| Call | Request | Expected response |
|---|---|---|
| `POST /api/session` | `{}` | `{ ref, consentRequired: true, consentGranted: false }` |
| `POST /api/session` | `{ ref, consentGranted: true }` | `{ ref, consentRequired: true, consentGranted: true }` |
| `POST /api/slot` | `{ ref }` (first question) | `{ ref, next: SlotQuestion, progress: {answered,total} }` |
| `POST /api/slot` | `{ ref, slot, value }` | `{ ref, next: SlotQuestion \| null, progress }` (next.done=true → UI calls classify) |
| `POST /api/classify` | `{ ref }` | `{ band, outputText, disclaimerText }` ✅ already matches (just accept `ref`) |
| `GET /api/pdf/:ref`, `GET /api/brief/:ref` | — | unchanged |

`SlotQuestion = { slot: string, prompt: string, inputType: "text"|"single_choice"|"multi_choice"|"date"|"yes_no", options?: {value,label}[], done: boolean }`

Engine today (`stage-2.5/app/wrap.py`): consent at `/api/consent {reference, accept}`; `reference`/snake_case; `/api/slot` returns `{id,name,type}` with **no prompt text, no labeled options**.

## Build tasks
1. **Make the frontend shape the primary contract** on `/api/session`, `/api/slot`, `/api/classify` (accept `ref`; return camelCase as above). Keep `/api/consent` as a legacy alias if convenient. Do NOT reimplement classification — call `run_classification` / the existing engine.
2. **Add a slot catalog** (engine-owned "chrome") giving each of the 14 `SLOT_DEFINITIONS` a `prompt` and labeled `options`, and map engine type→inputType: `enum→single_choice`, `multienum→multi_choice`, `yes_no`→`yes_no`, free text→`text`, date-like→`date`. Suggested starting copy (calm, plain, NSW; firm to review with the other copy):
   - state_of_accident → "Which state did the accident happen in?" (NSW/QLD/VIC/…)
   - datetime_location → "When and roughly where did it happen?"
   - accident_type → "What kind of accident was it?" (Rear-end / At an intersection / Roundabout / Merge / Reversing / Parking / Something else)
   - user_vehicle → "What were you driving? (make, model, year)"
   - other_vehicles → "What other vehicles were involved?"
   - movement_description → "In your words, what were you doing the moment it happened?"
   - damage_locations → "Where is the damage?" (Front/Rear/Left/Right/Multiple)
   - control_devices → "Were there any traffic controls?" (Lights/Give-way/Stop/Roundabout/None)
   - police_attendance → "Did police attend?" (Yes/No/Unsure)
   - witnesses → "Any witnesses? (optional)"
   - dashcam → "Any dashcam footage?" (Yours/Theirs/Neither/Unsure)
   - photos_taken → "Did you take photos?" (Yes/No)
   - other_driver_details → "Did you exchange details with the other driver? (optional)"
   - injuries → "Was anyone injured?" (None/Minor/Serious) — serious → escalates
   `progress = { answered: <count>, total: <mandatory count> }`. `next.done=true` once mandatory slots are collected (UI then calls classify). Preserve escalation short-circuit (serious injury, max-reprompts, etc.) — return it in a way the UI can show the "a lawyer will call you" state.
3. **Update the Stage 2.5 acceptance tests** (`acceptance-tests.stage25.yaml` + `run_acceptance.py`) to the new contract; keep G-41 parity (band == engine band), G-42 disclaimer-resolved, G-43 escalation, G-44 no-PII. Keep 73-regression green.
4. **Verify** *(updated 2026-06-21)*: local 99/99 (was 79/79 on 2026-06-20, 75/75 at this spec's authoring; now includes T-1-01..04 from G-PROD-LOCK/G-VER, T-25-017/T-25-018 MFA tests, T-4-01..11 G-VER closure Tier-1, T-6-* question injection, T-8-01/02 parked/not_listed, T-25-019 scenario-question), then `BASE_URL=https://claimdesk247-engine.vercel.app` against a PREVIEW deploy (set `APP_ENV=preview` on the engine's Preview env so `x-test-mode` works); then the live `claimdesk247.com.au` intake completes end-to-end.

## Governance note for Opus audit
Slot prompts/option labels are intake "chrome" (engine-owned per LOVABLE-BUILD-CONTRACT) — distinct from the fault `outputText`/`disclaimerText`, which still come verbatim from the engine and must not change. Firm reviews the prompt copy with the rest of the sign-off package.
