# ClaimDesk 247 — Cursor / MiniMax Build Handoff (Master)
**Date:** 2026-06-14 · **From:** Fables/Opus (plan + audit seat) · **To:** Cursor + MiniMax (build seat) · **Audit after build:** Opus 4.8 · **Final gate:** Legal Head (human yes/no)
**Read first, then build in loop order (§7). Don't break the governance rules in §6.**

---

## 1. What this is
ClaimDesk 247 = AI accident-intake + **deterministic NSW fault-guidance engine** for Goldman Forge Legal. A guided intake collects facts → a fixed, lawyer-approved **rule tree** returns a confidence **band** (`likely/possible/unclear/insufficient`, never a %) → sensitive cases **escalate to a human**. LLM is assistive only (sort/draft/retrieve), never decides the band.

**Dev model:** Plan (Fables/Opus) → **Build (you)** → Code audit (Opus, test-based) → Amend → Legal Head yes/no → close loop. Work is organised as **loops L0–L3** — see `CLAIMDESK247-LOOP-ROADMAP.md`. You're building **L0 remaining + L1**.

## 2. Repos, hosting, regions (Australia-only)
| Thing | Where |
|---|---|
| Frontend repo | `CTO-goldmanglobal/claimdesk247-76a0b7de` — TanStack Start + Vite + Nitro. **Two-way-syncs with Lovable** (see §8). |
| Engine repo | `CTO-goldmanglobal/claimdesk247-engine` — FastAPI. Root: `api/index.py`, `requirements.txt`, `vercel.json` (regions `["syd1"]`), `stage-2.5/`, `stage-3/`, `stage-4/`. Branches: `main` (prod), `qa-preview` (preview env). |
| Frontend host | Vercel project `claimdesk247-76a0b7de`, region `syd1`, domain `claimdesk247.com.au` (Cloudflare DNS, grey-cloud CNAME). Env: `VITE_API_BASE_URL`→engine, `VITE_SUPABASE_URL/ANON_KEY`, `VITE_MFA_REQUIRED=true`, `NITRO_PRESET=vercel`. |
| Engine host | Vercel project `claimdesk247-engine`, region `syd1`. Env: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (secret, server-only), `APP_ENV` (`production` on prod; `preview` on the `qa-preview` branch), `CORS_ALLOWED_ORIGINS`, `RATE_LIMIT_PER_MIN/BURST`. |
| Database | Supabase **Sydney `ap-southeast-2`**, project ref `mvzzglmegkchlmjartbm`. Tables: `intake_sessions`, append-only `audit_log` (+ `user_roles`/`has_role`/`is_staff`). RLS staff-read. |

**vite.config.ts must keep `nitro: { preset: "vercel" }`** (the Lovable wrapper defaults to Cloudflare → empty Vercel output → 404). Don't remove it.

## 3. Current state (what's live & verified)
- Engine live in syd1; `/healthz` green; full intake→band→PDF works against the live Sydney DB.
- **75/75 automated tests** green against the deployed engine (stage-2 30 · stage-3 27 · stage-2.5 18).
- Verified: RLS (anon reads 0 rows), append-only audit (anon write → 401 `42501`), CORS exact-origin, rate-limit (5/min/IP prod), MFA TOTP/AAL2 enforced (`VITE_MFA_REQUIRED=true`), server-side AAL2 on `/api/brief` **built but flag-gated** (`BRIEF_AUTH_MODE=stub` default).
- L0 live-site P0s fixed (commit `144516e`): no `tel:000`, no fabricated testimonials, clean meta.
- Rule tree `stage-3/app/data/rule-tree.nsw.v3.json` v3.0.0 = **6 scenarios** + 7 escalation triggers.

### 3.1. T1 closure (2026-06-15) — G-PROD-LOCK + G-VER shipped
- **L0 T1 done.** Engine enforces the per-scenario `legal_signoff` gate; unsigned or stale-signed scenarios escalate instead of returning a band. The current rule-tree content hash is:
  ```
  rule_tree_hash = 1ddabeb5c441fa8790e56e00a8bfe3ef75a2680ae6077817f53a0191ee4f7c72
  ```
  This is the version Legal Head must sign against. Once B1–B6 carry `legal_signoff.approved = true, version = <this hash>`, the engine returns bands again.
- **Commits on engine repo `main`:**
  - `7a8d3d8` — feat(engine): G-PROD-LOCK + G-VER — Legal Head signoff gate (T1)
  - `d09ba47` — chore(tests): Vercel Protection Bypass + cross-stage regression note (test-infra)
  - `c858803` — feat(engine): T6 scenario-question injection (L1 dep) — wires `classification_questions` into the live flow
- **Live evidence:** `https://claimdesk247-engine.vercel.app/healthz` returns `rule_tree_hash` + `api_version: 0.2.5.0`. `POST /api/scenario-question` is live (returns 404 for unknown session, which is the correct error path). Region: `syd1`.
- **Tests:** 79/79 in working folder (75 baseline + 4 new T-1-01..T-1-04); 47/48 in engine repo clone (the 1 fail is the by-design cross-stage regression, documented in test docstrings). With T6 added: 90/90 in working folder (79 + 11 new T-6); 58/60 in engine clone (the 2 by-design cross-stage regressions are documented in test docstrings).
- **L0 remaining (build seat, gated on human/setting actions):** T2 (AAL2 activation, gated on D-2 staff enrol) · T3 (monitoring/rollback, doc-only design ready). L0 closes when Legal Head signs B1–B6.
- **L1 next:** T6 ✅ shipped. T4 (Phase-2 scenarios) is now unblocked — T6 is its mandatory dependency.

### 3.2. T6 closure (2026-06-16) — scenario-question injection shipped
- **L1 T6 done.** Each scenario's `classification_questions` is now injected into the live flow after the 14 fixed intake slots. The state machine has a new `S3.5-INJECT-QUESTIONS` state; the new endpoint `POST /api/scenario-question` serves the question list to the frontend; the band functions now actually have the inputs they need (user_position, user_motion, chain_count, etc.).
- **What changed for the user:** zero visible change for the 6 existing scenarios (they all had `classification_questions` already; now they're asked). The UX change is at slot 3: `accident_type="other"` (or any future enum value with no scenario) fast-fails to `unmapped-accident-type` escalation immediately, instead of after 12 more slots.
- **What changed for the engine:** the `state` and `accident_type` keys in the intake dict are now mirrored to the canonical engine keys so the state-machine path is engine-callable. `"other"` was removed from `ACCIDENT_TYPE_TO_SCENARIO` per T6 §6.7.
- **Acceptance:** 11 new T-6 tests added (10 in stage-3, 1 in stage-2.5). All 11 pass. No regressions in T-3 or T-1 or T-25.
- **Unblocks:** T4 (Phase-2 scenario build). The `T4-PHASE2-TEMPLATE-S7-CAR-PARK.md` template is now executable as-is — wire a new scenario's `classification_questions` in the rule tree, and T6's machinery picks them up.

## 4. Key files you'll touch
| File | Role |
|---|---|
| `stage-3/app/data/rule-tree.nsw.v3.json` | The rule tree (scenarios, bands, citations). **Add Phase-2 scenarios here.** |
| `stage-3/app/engine.py` | `_load_rule_tree`, `_resolve_scenario`, `ACCIDENT_TYPE_TO_SCENARIO`, `_band_s1…s6`, `_damage_consistency`. **Add `_band_s7…s15` + routing.** |
| `stage-3/app/state_machine.py` | `SLOT_DEFINITIONS` (the fixed 14 intake slots), `submit_slot`, `_next_slot_index`. **Add scenario-question injection here.** |
| `stage-2.5/app/wrap.py` | FastAPI dual-contract API: `SLOT_UI` (prompt copy), `/api/session|slot|classify|pdf|brief`, `_verify_supabase_jwt`, `BRIEF_AUTH_MODE`. |
| `stage-3/app/data/disclaimers*.json` | Verbatim disclaimer/consent/privacy strings. |
| `stage-4/app/supabase_store.py` | `SupabaseStore` (prod) + `LocalSqliteStore`. |
| `stage-2.5/tests/run_acceptance.py`, `stage-3/tests/...`, `acceptance-tests.stage3.yaml` | Test suites. **Add ≥2 cases per new scenario.** |

## 5. How to run & test
```bash
# local (in-memory engine):
(cd stage-2  && PYTHONPATH=. python3 tests/run_acceptance.py)   # 30
(cd stage-3  && PYTHONPATH=. python3 tests/run_acceptance.py)   # 27
(cd stage-2.5&& python3 tests/run_acceptance.py)                # 18 + regression  → 75/75
uvicorn api.index:app --port 8000   # smoke: GET /healthz

# remote vs a preview deploy (needs Vercel Protection Bypass + preview env APP_ENV=preview):
VERCEL_BYPASS=<protection-bypass-secret> \
BASE_URL=https://claimdesk247-engine-git-qa-preview-cto-goldmanglobals-projects.vercel.app \
APP_ENV=preview python3 stage-2.5/tests/run_acceptance.py     # expect 18/18
```
**Pushing:** the engine repo auto-deploys on push to `main` (prod) / `qa-preview` (preview). Pushes must come from the CTO identity/token (a git-author security rule blocks non-team identities).

## 6. Governance guardrails — DO NOT BREAK (Opus audits these)
1. **Bands only, never a percentage**, never a definitive "at fault" verdict.
2. **Verbatim disclaimer** on every result (`{{ATTACH:master}}` resolves to the master disclaimer). Don't reword approved legal strings.
3. **Deterministic decision** — no LLM in the band path. New logic is data/code in the tree, reproducible + unit-tested.
4. **Escalation overrides** stay intact (serious injury, police, advice, multi-party, out-of-NSW, hit-run/impaired, no-consent → human, no band).
5. **Append-only audit** — never UPDATE/DELETE `audit_log`. Corrections are new rows.
6. **AU residency** — no offshore processing; **no PII in URLs/query strings**.
7. **No secrets in git.** Service-role/JWT only via server env. (A Protection Bypass secret was used for testing and **deleted** — generate a fresh one if needed; rotate any exposed key.)

## 7. Build queue — in loop order

### L0 (remaining engineering) — do first
**T1 · G-PROD-LOCK + G-VER (engine enforcement).** *Files: rule-tree JSON, `engine.py`, `wrap.py`.*
- Add per-scenario metadata: `"legal_signoff": { "approved": bool, "version": "<rule-tree-version-hash>", "by": "...", "date": "..." }`.
- In `run_classification`/`_assign_band`: if the resolved scenario's `legal_signoff.approved != true` **or** its `version` ≠ the current rule-tree version hash → **return escalation (human), not a band.** (This is G-PROD-LOCK + G-VER: unsigned or stale-approval scenarios never serve a band in prod.)
- Compute a rule-tree version hash at load; expose it in `/healthz`.
- Tests: signed scenario → bands; unsigned/stale → escalates. Acceptance: existing 6 marked signed once Legal Head confirms; new ones unsigned until signed.

**T2 · Activate server-side AAL2 on `/api/brief`.** *Files: `wrap.py` (done, flag-gated), frontend dashboard.*
- Frontend: fetch the brief with `Authorization: Bearer <supabase access_token>` (from `supabase.auth.getSession()`) and render JSON — **drop the `?as_email=` URL param** (PII-in-URL). Then set `BRIEF_AUTH_MODE=jwt` on the engine. Engine already verifies ES256 via JWKS + requires `aal2` + legal/admin.

**T3 · Monitoring + rollback.** Production alerting on error/5xx rate, escalation rate, band-distribution drift; document + test a one-step rollback (pin previous rule-tree/engine version → redeploy → healthz+smoke).

### L1 — Phase-2 scenario build (the headline loop)
**T4 · Add 9 scenarios → rule tree (v3.1.0).** Specs ready in `stage-4/PHASE-2-TIER1-RULE-BRANCHES.md` + `PHASE-2-TIER2-RULE-BRANCHES.md` (car-park, signalised, right-turn, sideswipe, driveway, U-turn, head-on, dooring, unmarked). Append the JSON objects; bump version.

**T5 · Band functions + routing.** Add `_band_s7…_band_s15` in `engine.py` reproducing each branch's `band_logic` deterministically; add `ACCIDENT_TYPE_TO_SCENARIO` entries + damage-consistency maps. Pattern = copy an existing `_band_sN`.

**T6 · ⚠ Conversational question-injection (the dependency — mandatory).** Today the live flow asks only the fixed 14 `SLOT_DEFINITIONS`; the per-scenario `classification_questions` (e.g. `user_position`, `sight_lines`, light colour) are **not asked**, so band functions have no inputs and would default. Build dynamic injection: after `accident_type` is known and the scenario resolved, the state machine asks that scenario's `classification_questions` (surface them through `wrap.py`'s `SLOT_UI`/SlotQuestion shape). **Regression-guard all 6 existing scenarios** — this touches the shared flow.

**T7 · Tests.** ≥2 acceptance cases per new scenario (a clean `likely` + an `unclear`/exception path) in `acceptance-tests.stage3.yaml`; keep the suite green (75 → ~93).

**T8 · Legal Head (final gate).** Per-scenario yes/no via `stage-4/sign-off-package/LEGAL-HEAD-SIGNOFF.md` (items B7–B15). G-PROD-LOCK keeps unsigned scenarios escalating until YES, bound to v3.1.0 (G-VER).

**T9 · Then:** coverage backtest (replace the 70–85% estimate), feedback flywheel (capture human determinations), evidence intake v1 (photo/doc upload + OCR), firm analytics dashboard. (L2/L3 in the roadmap.)

## 8. Frontend ↔ Lovable two-way sync (important)
The frontend repo syncs with Lovable. **Reference assets by committed path** (e.g. `/claimdesk-logo.png` in `public/`), **never** Lovable `.asset.json` / `/__l5e/...` URLs (they 404 off-Lovable and break the live site). If a Lovable re-sync reverts a fix (it has happened), re-apply and push from the CTO identity.

## 9. API contract (dual — don't regress either side)
- **Frontend dialect** (`ref`/camelCase): `POST /api/session {}`→`{ref,consentRequired,consentGranted}`; `POST /api/session {ref,consentGranted:true}`; `POST /api/slot {ref[,slot,value]}`→`{ref,next:SlotQuestion|null,progress}`; `POST /api/classify {ref}`→`{band,outputText,disclaimerText}`.
- **Engine-contract dialect** (`reference`/snake_case) is what the acceptance tests use — keep it working. `wrap.py` branches on which key is present.
- `SlotQuestion = {slot,prompt,inputType("text"|"single_choice"|"multi_choice"),options:[{value,label}]|null,done}`.

## 10. Reference docs (all in the repo)
- `CLAIMDESK247-LOOP-ROADMAP.md` — the loop plan (L0–L3) + gap→loop map.
- `CLAIMDESK247-SHOWCASE-AND-REVIEW.md` — full system + honest gaps; `CLAIMDESK247-EXECUTIVE-SUMMARY.md` — one-pager.
- `stage-4/GATE-REGISTER-ADDENDUM.md` — G-PROD-LOCK/G-VER/G-LH/G-AMEND + Stage-5 gates (pass tests).
- `stage-4/sign-off-package/LEGAL-HEAD-SIGNOFF.md` — the human yes/no gate.
- `stage-4/sign-off-package/GOVERNANCE-COMPLIANCE-PACK.md` — ISO 42001 + Privacy Act drafts (incl. ADM disclosure wording).
- `stage-4/PHASE-2-TIER1-RULE-BRANCHES.md` + `…TIER2…` — the 9 scenario build specs.
- `stage-4/FABLES-AUDIT-STAGE-4.md` — gate status (PASS 11 / PARTIAL 1 / OPEN 0).
- The uploaded `ClaimDesk247-Market-Review-and-Roadmap.html` — external audit (20 gaps).

## 11. Definition of done (per loop)
All P0 gates pass (incl. G-PROD-LOCK/G-VER/G-LH/G-AMEND) · automated suite green · traceability version-matched · no open audit finding or Legal-Head NO (G-AMEND) · Legal Head has signed what the loop ships. **A loop is not closed until its exit gate is green.**

---
*Build in order, keep §6 sacred, test before push, and surface any finding that would cause rework early (that's the loop discipline). Questions on intent → see the roadmap + the per-task spec docs above.*
