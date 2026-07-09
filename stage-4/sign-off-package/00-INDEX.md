# Stage 4 Sign-Off Package — Legal Firm Review

**Project:** AI Legal Receptionist + Accident Intake System
**Stage:** 4 of 5 (Phase 1 MVP) — Staging Deploy · AU Region · QA · Sign-Off
**Issued:** 2026-06-13 · **Refreshed:** 2026-06-14 (live evidence captured — see "Live verification status" below) · **Sign-off gate closed:** 2026-07-05 (Legal Head provisional approval — see "Sign-off event" below)
**Loop:** Fables (Plan) → Cursor + MiniMax M3 (Build) → Fables (Audit)
**Governed by:** `LOOP-OPERATING-RULES.md`

This package is the **single consolidated deliverable** for legal-firm sign-off (Loop Request §12). The firm conducts one review; revisions are absorbed in one cycle at Stage 5.

> ## 🔏 SIGN-OFF EVENT — 2026-07-05
>
> Legal Head gave provisional approval to proceed ("go ahead") on 2026-07-05, with final sign-off gated on the UX level being complete. The G-PROD-LOCK / G-VER sign-off gate has been **closed** by signing all four rule trees via `stage-4/scripts/sign_rule_trees.py`:
>
> | Tree | Scenarios | Hash (SHA-256, first 12) | Live |
> |------|-----------|--------------------------|------|
> | motor | 11 | `3964e668d905` | ✅ true |
> | property_damage | 7 | `1f13febaf6c0` | ✅ true |
> | public_liability | 6 | `dc824c3559ab` | ✅ true |
> | medical_negligence | 7 | `4e3fe60ac4c2` | ✅ true |
>
> **Signed by:** Legal Head — Goldman Global, provisional approval pending final UX-level sign-off (2026-07-05).
>
> **Effect:** the engine now EMITS bands for signed scenarios (was: escalated everything as `unsigned-scenario`). `/healthz` reports `live: true` for all four trees. Any later edit to a scenario invalidates its hash and the engine re-escalates as `stale-signoff` until re-signed (G-VER).
>
> **Caveat — PROVISIONAL:** this sign-off is recorded against the builder's content hashes and authorises the engine to emit bands for internal/staging validation. It is NOT the final commercial sign-off. The remaining gates are: (1) the UX-level review (in progress — home page reframed to the PD beachhead, `ClaimType` extended), (2) the counsel memo for PD (agent licensing + ACL/CHOICE disclosures + fee structure), and (3) the CD-R2 redo for each tree's touting/claim-farming surface. Verify before any public deployment with `python3 stage-4/scripts/sign_rule_trees.py --verify`.

**Status legend**
- [CODE] — Builder evidence. Lives in the repo, attached for review.
- [DEPLOYER-EVIDENCE] — Live infra evidence the Goldman org deployer must capture against the staging URL. The preflight script (`stage-4/scripts/preflight.py`) verifies these automatically and the deployer attaches the run output.
- [PENDING-FIRM] — Awaiting a firm decision or value (see Open Questions below).

---

## Index — 8 Sign-Off Items (+ 3 personal-injury / property-damage extension items)

| # | §12 item | Artefact (CODE) | Live evidence (DEPLOYER-EVIDENCE) | Status |
|---|----------|-----------------|----------------------------------|--------|
| 1 | All disclaimer text (screen + voice) | `stage-3/app/data/disclaimers.v1.complete.json` + `stage-1/spec/disclaimers.v1.md` | Screenshot of /api/classify response with `disclaimerText` populated + voice transcript (QA-1) | [CODE] |
| 2 | Fault rule tree + output framing (MOTOR) | `stage-3/app/data/rule-tree.nsw.v3.json` + `stage-1/deliverables/rule-tree-review.md` | Sample classifications from staging (T-25-001 to T-25-005) | [CODE] — **SIGNED 2026-07-05 (11/11 scenarios, hash `3964e668d905`)** |
| **2b** | **Public Liability rule tree (NEW)** | `stage-3/app/data/rule-tree.nsw.pl.v1.json` + `stage-4/sign-off-package/item-2b-rule-tree-public-liability.md` | `/healthz` rule_tree_versions + IX-01/05/06/09 green | **[CODE] — SIGNED 2026-07-05 (6/6 scenarios, hash `dc824c3559ab`); bands now emitted** |
| **2c** | **Medical Negligence rule tree (NEW)** | `stage-3/app/data/rule-tree.nsw.medneg.v1.json` + `stage-4/sign-off-package/item-2c-rule-tree-medneg.md` | `/healthz` rule_tree_versions + IX-02/03/04 green | **[CODE] — SIGNED 2026-07-05 (7/7 scenarios, hash `4e3fe60ac4c2`); escalation-dominant by design (IX-03)** |
| **2d** | **Property Damage rule tree (NEW — Lane 1 beachhead)** | `stage-3/app/data/rule-tree.nsw.pd.v1.json` + `stage-4/sign-off-package/item-2d-rule-tree-property-damage.md` | `/healthz` rule_tree_versions + IX-11..17 green | **[CODE] — SIGNED 2026-07-05 (7/7 scenarios, hash `1f13febaf6c0`); bands emitted deterministically (IX-15)** |
| 3 | Escalation trigger list (7 motor + 4 injury-ext + 1 PD-ext = 12 triggers) | `stage-3/app/engine.py:_check_global_escalations` + the trigger lists in each rule tree's `global_escalation_triggers` | QA-2 (serious injury) and QA-4 (advice request) transcripts | [CODE] + [DEPLOYER-EVIDENCE] |
| 4 | Privacy notice + consent wording | `stage-3/app/data/disclaimers.v1.complete.json` (privacy + recording) | QA-8 (consent declined) — verify nothing persisted in Supabase | [CODE] + [DEPLOYER-EVIDENCE] |
| 5 | Customer PDF summary template | `stage-3/app/pdf_gen.py` (output uses `spec/pdf-summary.v1.md`) | QA-1 PDF generated from staging | [CODE] + [DEPLOYER-EVIDENCE] |
| 6 | Insurer correspondence draft | **§7 OPEN DECISION** | See §7 below — either template or "Phase 2" note | [PENDING-FIRM] |
| 7 | Data retention + storage policy | `architecture/INFRA-PROVISIONING-CHECKLIST.md` (region + retention rules) | Region screenshots (Supabase = Sydney; Vercel PII = syd1) + retention value | [CODE] + [DEPLOYER-EVIDENCE] |
| 8 | Audit log specification | `stage-3/app/audit.py` (immutable in-process log) + `stage-4/app/supabase_store.py` (DB schema with append-only policies) | QA-11 (UPDATE/DELETE rejected) + QA-12 (export as admin) | [CODE] + [DEPLOYER-EVIDENCE] |

> **Personal-injury + property-damage extension (2026-07-05) — SIGN-OFF CLOSED:** Items 2b (PL), 2c (med-neg) and 2d (PD) are sub-trees in the per-`claim_type` registry. All four trees were **signed on 2026-07-05** via `stage-4/scripts/sign_rule_trees.py` after Legal Head gave provisional approval. Per-tree hashing (CD-E4) means each tree's sign-off is bound to its own scenarios[] hash, independent of the others — re-signing one does not affect the rest.
>
> **Provisional, not final.** The sign-off authorises the engine to emit bands for staging/internal validation. Before any commercial deployment: (1) the **CD-R2 (touting/claim-farming) analysis MUST be redone separately for each tree** — the motor analysis covers none of them (PL/med-neg = Civil Liability Act 2002; PD = common-law negligence + Arsalan, with its own ACL/debt-collection-agent licensing surface); (2) the **PD counsel memo** must be delivered (agent licensing + ACL/CHOICE disclosures + fee structure); (3) the **UX-level review** must be signed off.
>
> **Item 2d (PD) is the strategic beachhead** per `HOW-TO-WIN-3P-MOTOR` / `THIRD-PARTY-MOTOR-CLAIM-FOCUS`: Lane 1 (property damage) is outside the claim-farming ban, needs no law firm, and is where the engine's deterministic banding is strongest. The injury firewall (IX-12) is the red line that keeps it clean of Lane 2 (CTP injury / claim-farming) exposure.

---

## Live verification status (updated 2026-06-14)

The engine is deployed in Sydney and the deployer-evidence has now been **captured live** — this section supersedes the "to capture" notes above where they overlap.

- **Scored regression (Items 1–5, 8):** `79/79` against the deployed engine (18/18 Stage 2.5 + 30/30 Stage 2 + 31/31 Stage 3 — Stage 3 went from 27 to 31 with T-1-01..04 added by G-PROD-LOCK/G-VER 2026-06-15). Report: `stage-2.5/deliverables/test-report.txt`. Closes gates G-51 + G-62.
- **Item 1 (disclaimers):** T-25-003 green live — `disclaimerText` populated, zero unresolved tokens.
- **Item 2 (rule tree):** live classifications return valid bands with verbatim framing, no percentages (verified web intake → `likely`).
- **Item 3 (escalation):** T-25-005/006 green; serious-injury path returns the calm handoff with no fault band.
- **Item 4 (privacy/consent):** T-25-002 green; **RLS verified live** — anon reads return 0 rows on `intake_sessions`/`audit_log`/`user_roles` (G-53).
- **Item 5 (PDF):** live `/api/pdf/:ref` → valid 2-page PDF, governance-clean (no `%`, disclaimer + reference present, no fault band in customer summary); no PII in URL (T-25-007/008).
- **Item 6 (insurer correspondence):** **DECISION TAKEN — defer to Phase 2 (D-6a).** Firm signs the other 7 items. See `item-6-PHASE-2-NOTE.md`.
- **Item 7 (residency/retention):** Supabase = Sydney (`ap-southeast-2`), Vercel functions = `syd1` (G-52 verified). Retention value still firm-supplied (D-8).
- **Item 8 (audit append-only):** anon write to `audit_log` rejected live (HTTP 401, RLS `42501`); grant design = SELECT-only to `authenticated` (G-54). Belt-and-braces DB trigger written (`stage-4/db/0003_audit_log_append_only_trigger.sql`) — apply in Supabase SQL editor.
- **MFA (G-57):** enforced (`VITE_MFA_REQUIRED=true`); TOTP enrol/challenge/AAL2 step-up live. Server-side AAL2 on `/api/brief` = follow-up.

**Remaining before firm sign-off:** firm token values (table below), and the G-58 non-web QA (voice descoped to Phase 2). Full gate detail: `stage-4/FABLES-AUDIT-STAGE-4.md`.

---

## Per-item detail

### Item 1 — Disclaimer text (screen + voice)

**Builder evidence (CODE):**
- `stage-3/app/data/disclaimers.v1.complete.json` — full disclaimer catalogue (master, master_voice_short, recording_consent, privacy_collection, advice_request_refusal, s4_safety_advisory, s7_disclaimer_recap).
- `stage-3/app/config.py:resolve_strict` — applies the disclaimers + the runtime token overlay (CR-4-02).
- `stage-2.5/tests/run_acceptance.py:_drive_classify_disclaimer_present` — T-25-003 verifies `disclaimerText` is populated with zero unresolved tokens.

**Deployer evidence:**
- Run the Stage 2.5 weblink runner (`stage-2.5/tests/run_acceptance.py` with `BASE_URL` set) — T-25-003 passes.
- Capture a screenshot of the staging Lovable UI showing the disclaimer banner + the `disclaimerText` field in `/api/classify` response.
- Voice: capture a transcript of QA-1's voice flow showing the master + short-form cadence.

### Item 2 — Fault rule tree + output framing

**Builder evidence (CODE):**
- `stage-3/app/data/rule-tree.nsw.v3.json` — version 3.0.0 (with CR-3-01 parking-normalisation, CR-3-04 multipart pre-band routing).
- `stage-1/deliverables/rule-tree-review.md` — narrative review of every scenario, band, and trigger.
- `stage-3/app/engine.py:EngineResult` — deterministic, JSON-serialisable, band ∈ {`likely`, `unclear`, `not-likely`, `multiparty`, None}.

**Deployer evidence:**
- Run the Stage 2.5 weblink runner. T-25-001 (`likely`), T-25-002 (`unclear`), T-25-003 (parity) all pass.
- Save 3 sample classification responses from staging as evidence.

### Item 3 — Escalation trigger list (7 triggers)

**Builder evidence (CODE):**
- `stage-3/app/engine.py:ENGINE_TRIGGERS` (lines 482-512). The 7 triggers are:
  1. `injuries == "serious"` → `esc-injury`
  2. `police_attended == "yes"` → `esc-police`
  3. `accident_type == "advice_request"` → `esc-advice`
  4. `chain_count >= 3` → `esc-multiparty` (with pre-band routing per CR-3-04)
  5. `state_of_accident not in NSW_AREAS` → `esc-scope`
  6. `accident_type in ("hit_run", "drunk_driver")` → `esc-hitrun` / `esc-impaired`
  7. `consent not granted` → implicit (no escalation; session halts)

**Deployer evidence:**
- QA-2 (serious injury) and QA-4 (advice request) transcripts from staging.
- The 7-trigger list is also exposed via the rule tree itself for transparency.

### Item 4 — Privacy notice + consent wording

**Builder evidence (CODE):**
- `stage-3/app/data/disclaimers.v1.complete.json` — `privacy_collection`, `recording_consent`, `consent_revocation` strings.
- `stage-3/app/state_machine.py:acknowledge_consent` — sets `session.consent = True` and persists; until then, no PII is written (G-22).
- `stage-2.5/tests/run_acceptance.py:_drive_consent_required_first` (T-25-002) — verifies the API refuses to slot-fill before consent.

**Deployer evidence:**
- QA-8: run a session that explicitly declines consent. Query the Supabase `intake_sessions` table; the row must not exist.

### Item 5 — Customer PDF summary template

**Builder evidence (CODE):**
- `stage-3/app/pdf_gen.py:render_summary_pdf` — sections per `stage-2/spec/pdf-summary.v1.md`: cover, intake summary, fault statement, disclaimers, evidence checklist, references.
- `stage-2.5/tests/run_acceptance.py:_drive_pdf_no_pii_in_url` (T-25-007, T-25-008) — verifies PDF served by opaque ref only; no PII in URL.

**Deployer evidence:**
- Generate a sample PDF from staging with the REAR_END_INTAKE; attach the PDF.

### Item 6 — Insurer correspondence draft

**§7 OPEN DECISION (per build request):**
- **(a)** Build the without-prejudice template now so item 6 is complete for sign-off.
- **(b)** Mark it Phase 2 and have the firm sign off the other 7 items.

**Recommendation:** **(a) if the panel-shop partner needs it at launch, else (b).** Flag to Fables so the sign-off package is honest either way.

If (a): template scaffolded at `stage-4/sign-off-package/item-6-insurer-template-TEMPLATE.md` (placeholder, not yet drafted — see CR-4-03 below).
If (b): include a "Phase 2" note at `stage-4/sign-off-package/item-6-PHASE-2-NOTE.md`.

### Item 7 — Data retention + storage policy

**Builder evidence (CODE):**
- `architecture/INFRA-PROVISIONING-CHECKLIST.md` — region = Sydney (ap-southeast-2), retention setting procedure, ownership rules.
- `stage-3/app/config.py:STAGE2_TOKENS["{{RETENTION_PERIOD}}"]` — default `"7 years"` (overridable at runtime per CR-4-02).
- `stage-4/app/supabase_store.py` — schema for `intake_sessions` + `audit_log`, with RLS.

**Deployer evidence:**
- Screenshot of the Supabase project settings page showing region = Sydney (ap-southeast-2).
- Screenshot of Vercel project settings showing function region = `syd1` (Australia).
- The final `{{RETENTION_PERIOD}}` value resolved (default 7 years; firm may override).

### Item 8 — Audit log specification

**Builder evidence (CODE):**
- `stage-3/app/audit.py:AuditLog` — append-only at the language level (mutation methods raise `AuditMutationError`).
- `stage-4/app/supabase_store.py` — DB-level append-only enforced via RLS policies:
  ```sql
  CREATE POLICY audit_log_no_update ON audit_log FOR UPDATE USING (false);
  CREATE POLICY audit_log_no_delete ON audit_log FOR DELETE USING (false);
  ```
- `stage-3/app/dashboard.py:audit_export` — admin can download the full log.

**Deployer evidence:**
- QA-11: run a SQL `DELETE FROM audit_log WHERE entry_id=-1;` — must return "permission denied for table audit_log".
- QA-12: hit `GET /api/audit/export?as_email=admin@goldman.example` — full records returned.

---

## Open Questions for the Firm (Loop Request §14 + §7)

These are not blockers for sign-off; they are tokens that resolve at Stage 5 deployment.

| Token | Default | Firm value |
|-------|---------|-----------|
| `{{FIRM_NAME}}` | "Goldman Forge Legal" | |
| `{{FIRM_PHONE}}` | "(02) 9000 0000" | |
| `{{BUSINESS_HOURS}}` | "9:00 am to 5:30 pm, Monday to Friday" | |
| `{{CALLBACK_SLA}}` | "during the next business day" | |
| `{{RETENTION_PERIOD}}` | "7 years" | |
| `{{TOW_PROVIDER_REF}}` | "TOW-GF-001" | |
| `{{RENTAL_PARTNER_REF}}` | "RENT-GF-001" | |
| `{{OPERATOR_NAME}}` | *(none — pending Legal Head)* | **NEW: who operates claimdesk247.com.au (firm or ClaimDesk entity — not Goldman Forge Legal, not Goldman Global Financial Pty Ltd)** |
| Insurer correspondence (§7) | not yet drafted | (a) build / (b) Phase 2 |

---

## Change Requests raised for Stage 5

| CR | Action | Priority |
|----|--------|----------|
| CR-4-03 | Decide insurer-correspondence draft (§7). Build the template or mark Phase 2. | P1 |
| CR-5-05 | MFA: frontend TOTP/AAL2 enrol+challenge+gate **DONE + enforced** (2026-06-14). Remaining = server-side AAL2 JWT-claim check on engine `/api/brief` (still `X-MFA-Verified` stub). | P1 |
| CR-5-06 | Replace in-process token bucket with Vercel Edge Config / Upstash Redis (CR-5-03 production). | P2 |
| CR-5-07 | Wire the production `{{FIRM_*}}` token values (per §14). | P1 |
| CR-6-01 | **Brand framing correction (Jun 20, 2026).** claimdesk247.com.au is independent of Goldman Forge; operator = `{{OPERATOR_NAME}}` (firm/ClaimDesk entity, pending Legal Head). Do not ship "Goldman Global Financial Pty Ltd" or "Goldman Forge Legal" as operator. Footer = "ClaimDesk 247 — built on ForgeWright (a Goldman Forge product). Operated by `{{OPERATOR_NAME}}`." No back-link to goldmanglobal.com.au. (Reflected in `CTO-Build-Order-ClaimDesk-2026-06-14.md` CD-N1 and `ClaimDesk-AUDIT-TREE.md` CD-L3 + CD-E3.) | P0 |

---

## Verification

The deployer runs:
```bash
STAGING_URL=https://<preview>.vercel.app \
SUPABASE_URL=https://<ref>.supabase.co \
SUPABASE_ANON_KEY=<anon> \
SUPABASE_SERVICE_ROLE_KEY=<service-role> \
CORS_EXPECTED_ORIGIN=https://preview--smash-repair-engine.lovable.app \
python3 stage-4/scripts/preflight.py
```

Exit code 0 = all P0 gates passed. Attach the output to this index.

---

*Prepared by Fables · 2026-06-13 · One consolidated firm review. Revisions in one cycle at Stage 5.*
