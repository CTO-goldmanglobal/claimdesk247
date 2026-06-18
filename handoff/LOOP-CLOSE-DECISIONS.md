# ClaimDesk 247 — Loop-Close Decision Memo (CTO / Council)
**Prepared by:** Fables seat (Cowork) · **Date:** 2026-06-14
**Purpose:** record the decisions the CTO/council must make to (a) **close the Stage 4 loop** and (b) **drive the remaining items to completion**. Tick each decision, then the execution plan in Part C runs.
**Scope guard:** ClaimDesk 247 only — separate from finntang.com, wealth.goldmanglobal.com.au, super-scout, nswcoachcharter.

---

## Part A — Where the loop stands (Stage 4)
Engine is live in Sydney (`claimdesk247-engine.vercel.app`, syd1), the site (`claimdesk247.com.au`) runs against the real engine end-to-end, and the database is AU-resident with RLS + append-only audit verified.

**Gate tally (2026-06-14):** PASS 6 · PARTIAL 5 · OPEN 1.
- **PASS:** G-50 (e2e live), G-52 (AU residency), G-53 (RLS), G-54 (append-only), G-56 (rate limit), G-59 (test-mode inert).
- **PARTIAL:** G-51 / G-62 (scored regression — needs preview env), G-57 (MFA built, activation pending), G-60 (carry-in CRs), G-61 (sign-off package).
- **OPEN:** G-58 (live QA of non-web journeys).

**"Loop closed" requires (Operating Rules §7):** all P0 gates pass · test report green + spot-check · traceability complete · open CRs resolved or deferred to a named stage · known-gaps list empty or accepted into Phase 2. The decisions below resolve every remaining item.

---

## Part B — Decision register
*First option in each row is the Fables recommendation. Mark your choice + initials/date.*

> **Council standing instruction (2026-06-14):** run the loop autonomously, apply the recommended option for every decision, proceed loop-after-loop, and stop only on a critical error or material risk. Decisions recorded below as **council-approved (recommended option)**; items needing a CTO settings/secret change or firm-supplied values are marked **CTO-GATED** / **FIRM-GATED** and listed in Part E.

| # | Decision | Options (recommended first) | Owner | Decision | Status |
|---|---|---|---|---|---|
| **D-1** | **MFA scope** — which roles must use 2FA? | (a) All staff roles · (b) legal_staff + admin only | Council | ✅ **(a) all staff** | Built (flag-gated) |
| **D-2** | **MFA activation** — turn enforcement on now? | (a) Yes: enable TOTP in Supabase, enrol staff, set `VITE_MFA_REQUIRED=true` · (b) Soft-launch | CTO | ✅ **(a) activate** | **DONE 2026-06-14** — TOTP already on in Supabase; `VITE_MFA_REQUIRED=true` set + frontend redeployed. ⚠️ verify one staff enrol; rollback = remove var + redeploy |
| **D-3** | **Server-side AAL2** on `/api/brief`? | (a) Yes · (b) UI gate for pilot, Phase 2 | Council | ✅ **(a) build** | Spec'd; deploy needs token test-rig (see Part E) |
| **D-4** | **Scored 73-test regression** (G-62/G-51) | (a) Preview env + run green · (b) Accept live proof | CTO | ✅ **(a) run it** | **DONE 2026-06-14 — 75/75** vs deployed preview (fixed a UNIQUE-reference 500 found in the process). G-62/G-51 closed. ⚠️ delete the exposed Protection Bypass secret. |
| **D-5** | **Voice channel** in this launch? | (a) Web-only; voice → Phase 2 · (b) Voice now | Council/Product | ✅ **(a) web-only; voice Phase 2** | Applied — G-58 scoped to web/dashboard/PDF/brief |
| **D-6** | **Insurer-correspondence template** (item 6 / CR-4-03) | (a) Defer to Phase 2 · (b) Build now | Firm | ✅ **(a) defer to Phase 2** | Applied to sign-off package |
| **D-7** | **Append-only hardening** (G-54) | (a) Add DB trigger · (b) Accept client-level | CTO/Eng | ✅ **(a) add trigger** | Migration written (`0003`); apply = CTO |
| **D-8** | **Stage 5 firm tokens** | Firm name · phone · hours · callback SLA · retention · tow · rental | Firm | ⏳ **FIRM-GATED** | Config scaffold ready; values pending |
| **D-9** | **Credential rotation** (mandatory) | Rotate `service_role` + 2 PATs; update engine env | CTO | ⏳ **CTO-GATED** | Cannot be done from the build seat (secrets) |
| **D-10** | **Go-live authorisation** | Approve once P0 gates green + sign-off complete | Council | ⏳ **HOLD** | Pending D-2/D-4 + G-58 evidence |

---

## Part C — Execution plan once decisions are made
Steps run in this order; Fables (Cowork) does the build/verify items, CTO does the settings/secret items.

1. **D-9 first (security):** CTO rotates the 3 credentials; updates engine env. *(Do this regardless of other decisions.)*
2. **If D-4(a):** CTO adds a preview env on `claimdesk247-engine` (`APP_ENV=preview`, `RATE_LIMIT_PER_MIN` high) → Fables runs `BASE_URL=<preview> run_acceptance.py` → closes **G-62 / G-51**.
3. **If D-3(a):** Fables builds the AAL2 JWT-claim check on `/api/brief` (frontend forwards the token; engine validates via Supabase JWKS) → completes **G-57** server-side.
4. **If D-7(a):** Fables writes the append-only trigger migration → CTO applies it → hardens **G-54**.
5. **MFA on (D-1 + D-2(a)):** CTO enables TOTP in Supabase Auth + enrols staff → Fables sets `VITE_MFA_REQUIRED=true` and redeploys → **G-57** enforced.
6. **G-58 QA (per D-5):** Fables runs live e2e on dashboard + PDF + brief (+ voice/tow-rental if D-5(b)); captures evidence.
7. **D-6 / D-8:** build template if D-6(b); wire firm tokens into config (resolves **CR-4-02**) and refresh launch copy.
8. **Sign-off package (G-61):** Fables refreshes live-sample/region links + records D-6 decision → package complete.
9. **D-10:** Council reviews the green gate sheet + sign-off package → authorises launch.

---

## Part D — Loop-close sign-off
The loop is **closed** when D-1…D-8 are decided (and their execution items done), D-9 is complete, and D-10 is approved. Items explicitly routed to Phase 2 are accepted known-gaps per Operating Rules §7.5.

- **CTO:** _______________________  date: __________
- **Council / Firm:** _______________________  date: __________

*Linked docs: `stage-4/FABLES-AUDIT-STAGE-4.md` (gate evidence) · `handoff/ENGINE-DEPLOY-RUNBOOK.md` · `handoff/VERCEL-DEPLOY-FIX.md` (MFA spec) · `LOOP-OPERATING-RULES.md` §7.*

---

## Part E — Autonomous run log + gated boundary (2026-06-14)
Council standing instruction applied (recommended option for each decision). Executed everything safe to complete from the build seat; stopped at the items that require a CTO settings/secret change, firm-supplied values, or carry auth-risk that needs a real-token test.

**Executed & verified this run:**
- **D-5 / D-6 applied** — voice descoped to Phase 2; insurer template deferred (sign-off signs the other 7 items).
- **G-58 (web scope)** — live QA: web intake→classify `likely` ✅; PDF endpoint 200, valid 2-page governance-clean PDF ✅; brief endpoint correctly 403s without real auth ✅.
- **G-54 hardening (D-7)** — append-only trigger written: `stage-4/db/0003_audit_log_append_only_trigger.sql` (apply via Supabase SQL editor — MCP apply is read-only-blocked).
- Audit + sign-off status refreshed.

**Stopped here — each needs an action I must not/can't take from the build seat:**
- **D-2 (MFA activation)** — enable TOTP in Supabase Auth + enrol staff (Supabase setting) and set `VITE_MFA_REQUIRED=true` on the frontend Vercel project (env change). *CTO.*
- **D-4 (scored 73-run)** — add a Vercel **Preview** env on `claimdesk247-engine`: `APP_ENV=preview` + `RATE_LIMIT_PER_MIN=1000`; then Fables runs the suite. *CTO sets env; Fables runs.*
- **D-7 apply** — run `0003` in the Supabase SQL editor. *CTO.*
- **D-8 (firm tokens)** — provide values; engine reads them from env (`FIRM_NAME`, `FIRM_PHONE`, `BUSINESS_HOURS`, `CALLBACK_SLA`, `RETENTION_PERIOD`, `TOW_PROVIDER_REF`, `RENTAL_PARTNER_REF`). *Firm.*
- **D-9 (rotate credentials)** — secrets; build seat must not handle them. *CTO.*

**D-3 — server-side AAL2 on `/api/brief` (turnkey spec; sequence AFTER D-2):**
Today the brief is behind a *stub* (`?as_email=` + `X-MFA-Verified` header — both spoofable; email-in-URL is also a privacy issue). Real version:
1. **Frontend:** fetch the brief with `Authorization: Bearer <supabase access_token>` (from `supabase.auth.getSession()`) and render the JSON — *not* a URL with `as_email` (removes PII-from-URL).
2. **Engine:** verify the JWT via Supabase JWKS (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`, PyJWT+cryptography — no shared secret needed for asymmetric keys); require `aal == "aal2"`; resolve the caller's role from `user_roles` (or app_metadata) and require `legal_staff`/`admin`. Replace the `as_email`/`X-MFA-Verified` stubs.
3. **Roll out flag-gated** (`BRIEF_AUTH_MODE=jwt`, default `stub`) so deploy is zero behaviour-change until a **real staff token** (exists only after D-2) validates the full path. *Why this waits:* shipping untested auth-verification to a legal product is a material risk — it is sequenced after D-2 so it can be tested, not blind-deployed.

**Net:** every gate that can be closed without external action is closed or evidenced. The remaining path to loop-close = CTO does D-2/D-4/D-7-apply/D-9 + firm gives D-8 → Fables runs the scored suite, builds+tests D-3, refreshes the sign-off package → Council approves D-10.

---

## D-11 — Repo visibility mismatch + PAT decision (added 2026-06-18)

**Context discovered during the workspace brand-tree push:**
- `CTO-goldmanglobal/claimdesk247-engine` → **private** ✅
- `CTO-goldmanglobal/claimdesk247` (workspace brand tree) → **PUBLIC** 🚨

The CTO's stated intent: "don't change PAT, only sole developer, project are private" — but the workspace repo is in fact public. This is a discrepancy between the CTO's mental model and the GitHub config.

**Risk if the workspace repo stays public with the current PAT:**
- The commit history of the public repo is browseable
- The PAT is currently in chat transcripts (this session, prior sessions) and the build seat has run scripts that echo it during diagnostics
- If the PAT has `repo` scope, anyone with the PAT could push to claimdesk247 (the public one) and claimdesk247-engine (the private one — if the PAT also has access to it, which it does because the user is the owner of both)
- A leaked PAT in this session was committed to a public repo and blocked by GitHub secret scanning; a subsequent attempt at push with a re-issued PAT also landed in the chat transcript

**Decision (CTO, deferred):**
- **[x] (a) Rotate the current PAT on github.com** — the leak surface is real even if the threat model is "just me" because the PAT is in a long-lived JSONL transcript. **DONE 2026-06-18 ~12:11 AEST (CTO).**
- **[ ] (b) Make the workspace repo private** — `gh repo edit CTO-goldmanglobal/claimdesk247 --visibility private` (or via the github.com UI: Settings → Danger Zone → Change repository visibility). This eliminates the public-repo risk class entirely. **DEFERRED** — the CTO will revisit this later; rotation alone is accepted for now.
- **[ ] (c) Do both (a) and (b)** — defense in depth. Recommended. **Superseded by (a).**
- **[ ] (d) Do nothing** — accept that the PAT is in transcripts; the threat actor is "anyone who can read these transcripts" (probably nobody); the public repo accepts that the brand-tree contents (handoff docs, etc.) are public. **Superseded by (a).**

**Why this is recorded here:** the CTO said "sole developer, private repos" — that's the intended posture. The actual current state has a public repo. Closing the gap between intent and state is a loop-close item. *CTO decides when to act.*

**Build seat constraints when this is decided:**
- If (a) is chosen: build seat continues to read PAT from `~/.git-credentials` (no change to the wrapper script flow). The PAT will be different; the script reads whatever is in the file at push time.
- If (b) is chosen: build seat can return to the standard `git push origin <branch>` flow (the osxkeychain override issue still exists; the wrapper script remains the safest option, but the keychain cleanup we did already made plain `git push` work too).
- If (d) is chosen: no action. Document the accepted risk in `CTO-ACTION-PAT-RESCOPE.md` under a new "Accepted risk" section.
