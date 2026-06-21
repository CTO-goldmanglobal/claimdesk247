# ClaimDesk 247 — Governance & Compliance Pack
**Operator:** `{{OPERATOR_NAME}}` [Legal Head / firm decision] · **System:** ClaimDesk 247 (NSW accident intake + fault-guidance engine)
**Technical supplier:** Goldman Forge · **Underlying platform:** ForgeWright (Goldman Forge's product)
**Brand framing (Jun 20, 2026):** claimdesk247.com.au is an independent product site; goldmanglobal.com.au is the Goldman Forge showcase site that displays ClaimDesk 247 as one of its products (one-directional, no parent/child link). The operator of claimdesk247.com.au is the firm/ClaimDesk entity — not Goldman Forge Legal, not Goldman Global Financial Pty Ltd.
**Status:** ⚠️ **DRAFT for firm + Privacy Officer ratification.** These documents close the "no document exists" gap identified in the review. They are working drafts to be reviewed, completed where marked `[FIRM]`, dated, owned, and adopted — they are not yet ratified policy. · **Prepared by:** Fables (Cowork) · 2026-06-14

Contents: 1) AI Management Policy · 2) AI System Impact Assessment + Risk Register · 3) Privacy Impact Assessment (APP mapping) · 4) Data Breach Response Plan · 5) Data Handling Procedures (access/correction, retention/destruction) · 6) Supplier Register. Mapped to **ISO/IEC 42001:2023** and the **Privacy Act 1988 (Cth) / Australian Privacy Principles**.

---

## 1. AI Management Policy *(ISO 42001 A.2)*
**Purpose.** Govern the responsible design, deployment and operation of AI within ClaimDesk 247.

**Principles (binding on the system):**
1. **Deterministic decision.** Legal fault guidance is produced by a fixed, version-controlled, lawyer-approved rule set — never by a generative model. Generative AI is assistive only (sorting input, drafting, retrieval) and never sets a fault band.
2. **Human authority.** A qualified lawyer (Legal Head) approves the fault logic and customer wording before release; defined triggers route matters to a human in real time.
3. **Transparency.** Every output carries a verbatim "general information, not legal advice" disclaimer and a band — never a percentage or a verdict.
4. **Auditability.** Every interaction is logged to an append-only audit trail; the legal decision is reproducible.
5. **Privacy & residency.** Consent-first; data stored in Australia only; minimal collection; defined retention.
6. **Change control.** No change reaches the public without passing the code audit **and** the Legal Head sign-off, bound to a rule-tree version.

**Scope.** The intake engine, fault rule tree, assistive AI components, staff dashboard, and supporting infrastructure.
**Roles.** Plan/Audit (Fables, senior model) · Build (Cursor/MiniMax) · Code audit (Opus) · Legal Head (firm lawyer) · Data/Privacy Officer `[FIRM]` · System owner `[FIRM]`.
**Review cadence.** This policy reviewed `[FIRM: e.g. every 12 months]` and on any material change.

---

## 2. AI System Impact Assessment + Risk Register *(ISO 42001 A.5)*
**System & affected parties.** Members of the public reporting accidents (primary, potentially vulnerable/distressed); firm staff; partners (tow/rental/insurer). **Intended use:** general guidance + intake. **Out of scope / prohibited use:** definitive fault determination, legal advice, decisions about injury claims, anything outside NSW.

**Risk register (top risks):**
| # | Risk | Likelihood | Impact | Controls in place | Residual / action |
|---|------|-----------|--------|-------------------|-------------------|
| R1 | User mistakes guidance for legal advice | Med | High | Verbatim disclaimer every output; band-not-verdict; no % | Legal Head confirms wording; monitor complaints |
| R2 | Wrong fault band given | Low | High | Deterministic tree; lawyer-approved; damage-consistency check; escalation; 99/99 tests (Stage 2 30 + Stage 3 50 + Stage 2.5 19; was 87/87 pre-T4/T6/T8, 79/79 pre-T6) | Backtest vs historical claims `[action]` |
| R3 | Distressed/injured user not escalated | Low | High | `esc-injury` + 6 other triggers stop the machine | Periodic transcript review `[action]` |
| R4 | Generative component influences fault | Low | High | Architecture forbids it; tree is sole authority; disagreement → escalate | G-PROD-LOCK enforces (below) |
| R5 | PII exposure / breach | Low | High | RLS, MFA/AAL2, append-only audit, AU-only, no PII in URLs | Pen-test `[action]`; breach plan §4 |
| R6 | Approved legal logic silently changed | Med | High | Version-bound sign-off (G-VER) | Implement G-VER |
| R7 | Out-of-NSW / out-of-scope misuse | Med | Med | `esc-scope` trigger; jurisdiction = NSW only | Multi-state = future scope |
| R8 | Bias in input-classification step | Med | Med | Decision is deterministic; classification only sorts | Fairness review of classifier `[action]` |

**Conclusion:** highest-severity risks (wrong fault / advice / non-escalation / silent drift) are controlled by design; the open actions are *backtest, pen-test, fairness review, and the G-VER/G-PROD-LOCK gates*.

---

## 3. Privacy Impact Assessment (PIA) — Privacy Act 1988 / APPs
**Data collected:** accident circumstances, vehicle details, location/time, optional contact details, optional witness/photo references. **Sensitive information:** injury status (treated as sensitive — triggers escalation; minimised).

| APP | Requirement | How ClaimDesk meets it | Gap / action |
|-----|-------------|------------------------|--------------|
| 1 | Open & transparent management | Privacy notice before any PII; this PIA | Adopt + publish policy `[FIRM]` |
| 3 | Collection of solicited PII | Consent-first; no PII stored before consent; minimal | — |
| 5 | Notification at collection | Notice states purpose, storage, retention, access | — |
| 6 | Use & disclosure | Used for intake + firm brief only | Document basis for tow/rental/insurer disclosure `[FIRM]` |
| 8 | Cross-border disclosure | **AU-only storage; no overseas disclosure** | Confirm no sub-processor egress `[action]` |
| 10 | Quality of PII | Structured intake + reprompts | — |
| 11 | Security | RLS, MFA/AAL2, append-only audit, CORS, rate-limit | Pen-test `[action]` |
| 12/13 | Access & correction | — | **Define request workflow §5** |
| — | Retention & destruction | Retention token (firm value) | **Define destruction procedure §5** |

**Automated-decision-making disclosure (AU Privacy reform — grace period to 10 Dec 2026).** The fault rule tree is automated processing that materially informs the guidance shown. Add this (or a firm-approved equivalent) to the privacy notice/policy and the engine `privacy_notice` string:
> *"ClaimDesk 247 uses an automated rules engine to give you general information about how NSW road rules usually treat your type of accident. It produces a general guidance band only — it does not decide your claim or determine legal fault, and a qualified lawyer reviews your matter. You can ask for human review at any time."*
`[FIRM]` ratifies wording → `[ENG]` inserts into the live privacy notice (one-line engine change).

**PIA verdict:** strong on transparency, collection, residency, security; actions are the access/correction workflow, retention-destruction procedure, partner-disclosure basis, sub-processor egress confirmation, and inserting the ADM disclosure above.

---

## 4. Data Breach Response Plan (Notifiable Data Breaches scheme)
**Trigger:** suspected or actual unauthorised access/disclosure/loss of personal information.
**Steps:** (1) **Contain** — revoke keys/sessions, isolate; (2) **Assess** within `[FIRM: e.g. 48h]` whether serious harm is likely; (3) **Notify** — if likely serious harm, notify affected individuals + the OAIC as soon as practicable (NDB scheme); (4) **Remediate** — fix root cause, rotate credentials, patch; (5) **Record** — log in the breach register; (6) **Review** — post-incident review feeds the risk register.
**Roles:** Incident lead `[FIRM]`; Privacy Officer `[FIRM]`; technical responder (CTO). **Contacts:** `[FIRM to complete]`. **Evidence aids:** append-only audit log supports forensic review.

---

## 5. Data Handling Procedures
**Access requests (APP 12):** individual requests via `[FIRM channel]`; identity verified; response within `[FIRM: 30 days]`; staff retrieve the individual's `intake_sessions` record (RLS-scoped); provided in a usable form.
**Correction (APP 13):** corrections recorded as a new audit entry (the original is never edited — append-only); the corrected value supersedes.
**Retention:** records kept for `[FIRM: e.g. 7 years]` from closure, then destroyed.
**Destruction:** automated purge job deletes `intake_sessions` past retention; audit-log entries are retained per legal-hold policy `[FIRM to confirm]`; destruction is itself logged.
**Minimisation:** only the slots required for intake are collected; injury detail is minimised and triggers human handover.

---

## 6. Supplier / Sub-processor Register *(ISO 42001 A.10)*
| Supplier | Service | Data location | Handles PII? | Assurance |
|----------|---------|---------------|--------------|-----------|
| Vercel | Frontend + engine hosting (functions) | **Sydney `syd1`** | In transit / ephemeral | Region-pinned; review certs `[action]` |
| Supabase | Database + auth | **Sydney `ap-southeast-2`** | **Yes (at rest)** | RLS, append-only; confirm DPA + region lock `[action]` |
| Cloudflare | DNS only | n/a (DNS) | No | DNS-only, grey-cloud |
| (LLM provider, future RAG) | Assistive inference | `[to select — AU/region]` | Possibly | **Must be assessed before RAG ships** |

**Action:** obtain/record each supplier's data-processing terms + region guarantees; assess any future LLM provider for residency before enabling the RAG layer.

---

### Adoption checklist (for the firm)
- [ ] Privacy Officer + system owner named
- [ ] `[FIRM]` placeholders completed (cadences, contacts, retention value, disclosure basis)
- [ ] Legal Head + Principal ratify policy (§1) and PIA (§3)
- [ ] Breach plan contacts populated and tested once (tabletop)
- [ ] Supplier DPAs/region terms obtained
- [ ] Open actions added to the risk register with owners + dates

*Drafts to ratify — not yet adopted policy. Closing these turns the review's red/amber compliance-documentation items green.*
