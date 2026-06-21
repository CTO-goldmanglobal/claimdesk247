# ClaimDesk 247 — System Showcase & Honest Review Brief
**Product:** ClaimDesk 247 — AI legal receptionist + accident-intake & fault-guidance engine (NSW)
**Operator:** Goldman Forge Legal (panel-shop / law-firm intake)
**Document purpose:** (1) a complete picture of the system — scope, AI design, governance, hybrid-RAG plan, development loop, and compliance posture (ISO/IEC 42001, Privacy Act 1988); and (2) a deliberately **honest standpoint** of what is *missing* vs the current market and vs Goldman Forge's ambition, written so an independent reviewer (another model/chat or a human assessor) can critique it and propose improvements.
**Prepared by:** Fables (planning/audit seat) · **Date:** 2026-06-14 · **Status:** for external review — claims below are stated at their true maturity (built / planned / unverified) on purpose.

> **Reviewer's instruction:** treat every "✅ done" as a claim to test and every "gap" as an invitation to add more. We *want* the holes found now. Honesty over polish.

---

## 1. Executive summary
ClaimDesk 247 takes an accident report from a member of the public (web today; voice planned), **collects and structures** the facts through a guided intake, **classifies** the accident into a known NSW scenario, applies a **deterministic fault rule tree** to return a *confidence band* (not a percentage, never a verdict), and **hands anything sensitive to a human lawyer**. It is built as a **hybrid system**: a deterministic, auditable engine for the legal decision, a (planned) retrieval layer to assist humans, and a human gate as the final authority.

The differentiator is **governance, not cleverness**: the fault decision is deterministic and testable (no LLM hallucination in the legal path), every step is logged to an append-only audit trail, all data stays in Australia, and a qualified lawyer signs off the legal substance before launch. The trade-off is **scope**: today it covers 6 common NSW collision scenarios (≈70–85% of two-vehicle *moving* collisions, indicative), single jurisdiction, web channel.

What is genuinely live and verified: the engine deployed in Sydney, full intake→band→PDF, **99/99 automated tests against the deployed API as of 2026-06-21** (was 87/87 pre-T4/T6/T8, 79/79 pre-T6, 75/75 pre-MFA, 73/73 pre-Stage-2.5), row-level security and append-only audit proven by query, AU data residency, MFA, CORS lockdown, rate limiting. What is planned or partial is stated plainly in §9–§10.

---

## 2. Scope of the engine work

### 2.1 What the engine does
1. **Collect** — a guided, consent-first intake. The engine drives the questions (it "owns" the conversation); the website renders them. 14 intake slots; 10 mandatory.
2. **Unify & sort** — normalises free-form answers into a structured intake record and classifies it into one scenario.
3. **Run the tree** — applies the deterministic rule tree → a **band**: `likely / possible / unclear / insufficient`.
4. **Human gate** — 7 escalation triggers stop the machine and route to a lawyer (no band given).
5. **Output** — verbatim disclaimer every time; a customer PDF summary (facts + checklist, **no band printed**); an internal brief for staff (role-gated).

### 2.2 Current rule coverage
| Live (rule tree v3.0.0) | Escalation triggers (→ human) |
|---|---|
| Rear-end · Give-way/T-intersection · Roundabout · Lane-change/merge · Reversing · Multi-vehicle/chain | Serious injury · Police attended · Advice request · 3+ vehicles · Outside NSW · Hit-run/impaired · Consent declined |

**Proposed Phase-2 (drafted, not built):** car-park, signalised intersection, right-turn-across-oncoming, sideswipe, driveway emergence, U-turn, head-on/overtaking, dooring, unmarked intersection → would take coverage from 6 → 15 scenarios.

### 2.3 Output philosophy (non-negotiable)
The engine **never** outputs a percentage or a definitive "you are at fault." It outputs a band + the disclaimer: *"general information… not legal advice… does not determine who is legally at fault. Only your insurer, a lawyer, or a court can do that."*

---

## 3. AI design

### 3.1 Deterministic-first, not LLM-first
The legal decision (which scenario, which band, which exceptions fired) is made by a **deterministic rule tree**, not by a language model. This is the central design choice: it is auditable, reproducible, unit-testable, and cannot hallucinate fault. Each scenario branch carries: classification questions, a default fault pattern, exceptions, a damage-consistency check, band logic, verbatim outputs, and escalation overrides.

### 3.2 Where AI/LLM is used (and isn't)
- **Is used (assistive):** turning messy free-text into structured slots / candidate scenario (classification assist); drafting summaries and correspondence; (planned) retrieving the relevant rule/precedent text for the human reviewer.
- **Is never used:** to *decide* the fault band. If an assistive model and the tree disagree, the case escalates and the tree's determination stands.

### 3.3 Bands, not scores
Four bands map to "how closely this matches a well-understood pattern," not a probability. This is deliberately conservative for a legal product and keeps the system inside "general information," not "advice."

---

## 4. Hybrid RAG + deterministic tree + human gate

```
        ┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
 user → │  COLLECT     │ →   │ UNIFY & SORT     │ →   │  RULE TREE   │ → band
        │ (intake)     │     │ (normalise/class)│     │ (deterministic)│
        └─────────────┘     └──────────────────┘     └─────────────┘
               ▲                     ▲                        │
               │                     │ (assist only)          ▼
          ┌────────────────────────────────┐          ┌─────────────┐
          │  RAG layer (advisory, planned)  │          │ HUMAN GATE  │ → lawyer
          │  rules + precedent + firm docs  │ ───────► │ (authority) │
          └────────────────────────────────┘          └─────────────┘
                                                              │
                                              determination logged → feeds back
```
**Design rule:** the tree is the single source of truth for fault; RAG is advisory (sort, surface citations to the human, draft). RAG never sets a band. The **human gate** is the final authority for everything `unclear`/`insufficient` or escalated, and every human determination is (to be) logged as the dataset that prioritises the next scenarios, backtests coverage, and trains the retrieval/classifier — the **flywheel**.

**Maturity:** deterministic tree + human gate = **live**. RAG retrieval/classifier = **architected, not yet built** (honest: today the "sort" step is rule/slot-based, not a vector-RAG).

---

## 5. Governance & gate system

### 5.1 Gates
The build runs against a numbered gate set (G-01…G-62). Stage 4 (deploy/QA/sign-off) currently stands at **PASS 11 / PARTIAL 1 / OPEN 0** — including AU residency (G-52), RLS (G-53), append-only audit (G-54), CORS lockdown (G-55), rate-limiting (G-56), MFA (G-57), and a **99/99 regression against the deployed API** (G-62/G-51).

### 5.2 Newly identified P0 gates (from the gate-completeness review)
To guarantee "no incomplete loop": **G-PROD-LOCK** (production refuses any scenario not legally signed-off for the deployed version), **G-VER** (sign-off bound to a rule-tree version hash; edits auto-invalidate approval), **G-LH** (Legal Head yes/no is a recorded gate), **G-AMEND** (a stage cannot close while any finding or legal NO is open). Plus Stage-5: rollback, feedback-capture, coverage backtest, drift monitoring.

### 5.3 Human gate / Legal Head
A qualified lawyer signs the legal substance **yes/no** (never edits code). Every NO becomes a change request implemented by the dev loop and re-presented for final YES. Sign-off covers: output framing (no %), disclaimers, consent/privacy wording, escalation triggers, residency/retention, and the fault rule + customer wording per scenario.

---

## 6. Loop development model

```
PLAN (Fables · most-expensive model — get the direction right)
  → BUILD (Cursor / MiniMax)
  → CODE AUDIT (Opus · test-based — every audit is code/tests)
  → AMEND (resolve findings)
  → RE-AUDIT (Opus)
  → LEGAL HEAD (human · yes/no on substance)
  → CLOSE → next loop
```
Principles: invest in planning so the direction is right (cheapest insurance against redo); keep the flow (a problem reverts or is blocked at the edge, it doesn't halt the pipeline); a loop only closes when **complete** (all findings + legal NOs resolved and re-audited). Two clean review layers: **code audit = built right**; **legal head = legally right**.

---

## 7. Compliance posture — ISO/IEC 42001 (AI management system)
*Honest mapping. "Aligned" ≠ "certified." No certification has been sought; this is a design-level self-assessment for the reviewer to challenge.*

| ISO 42001 area (Annex A theme) | Status | Evidence / gap |
|---|---|---|
| AI policy & objectives (A.2) | 🟡 Partial | Governance principles are explicit (deterministic decision, human gate, no %); **no formal written AI policy doc** yet. |
| Roles & responsibilities (A.3) | 🟢 Aligned | Clear separation: Plan (Fables) / Build (Cursor) / Audit (Opus) / Legal Head (human). |
| AI impact assessment (A.5) | 🔴 Gap | **No formal AI system impact assessment** (affected parties, harms, mitigations) document. Recommended next. |
| System lifecycle, V&V (A.6) | 🟢 Strong | Gated loop, 79/79 automated regression (was 75/75 pre-T1), deterministic & reproducible decisions, version-controlled rule tree. |
| Data for AI (A.7) | 🟢 Aligned | AU-resident, RLS, append-only audit, consent-first, minimal collection; **no formal data-governance register** yet. |
| Transparency to users (A.8) | 🟢 Strong | Verbatim disclaimer every result; "general information, not legal advice"; band-not-verdict framing. |
| Human oversight (A.9) | 🟢 Strong | 7 escalation triggers + human gate as final authority; legal sign-off. |
| Third-party/supplier (A.10) | 🟡 Partial | Vercel/Supabase/Cloudflare documented; **no formal supplier-risk assessment** doc. |

**ISO 42001 honest verdict:** the *operational* controls (lifecycle, human oversight, transparency, data) are strong; the *documentation* controls were the gap. **Update 2026-06-14:** AI Management Policy, AI Impact Assessment + Risk Register, and Supplier Register are now **drafted** in `sign-off-package/GOVERNANCE-COMPLIANCE-PACK.md` (status: pending firm ratification). Remaining = the firm adopts/ratifies them. No rebuilds.

---

## 8. Compliance posture — Privacy Act 1988 (Cth) & APPs
*Honest mapping. Designed to support compliance; not legally certified — the firm's privacy officer should validate.*

| Australian Privacy Principle | Status | Evidence / gap |
|---|---|---|
| APP 1 — open & transparent | 🟢 | Privacy notice shown before any PII; references Privacy Act 1988. |
| APP 3 — collection of solicited PII | 🟢 | Consent-first; no PII written before consent; minimal slots. |
| APP 5 — notification of collection | 🟢 | Notice includes purpose, storage, retention, who can access. |
| APP 6 — use & disclosure | 🟡 | Scoped to intake + brief; **disclosure to tow/rental/insurer partners needs a documented basis** (Phase 2). |
| APP 8 — cross-border disclosure | 🟢 | All data stored in **Australia only**; no offshore processing — avoids APP 8 exposure. |
| APP 11 — security of PII | 🟢 | RLS, MFA/AAL2, append-only audit, CORS lockdown, rate-limit, no PII in URLs. |
| APP 12/13 — access & correction | 🔴 Gap | **No documented customer access/correction workflow.** |
| Notifiable Data Breaches scheme | 🔴 Gap | **No documented data-breach response plan.** |
| Retention / destruction | 🟡 | Retention period is a configurable token (firm sets); **destruction procedure not yet documented**. |

**Privacy honest verdict:** strong on collection, transparency, residency, and security. **Update 2026-06-14:** a **Privacy Impact Assessment, Data Breach Response Plan, and Access/Correction + Retention/Destruction procedures** are now **drafted** in `GOVERNANCE-COMPLIANCE-PACK.md` (pending firm/Privacy-Officer ratification + `[FIRM]` placeholders). Remaining = firm completes contacts/values + adopts; partner-disclosure basis to be documented by the firm.

---

## 9. Honest standpoint — what's missing (vs Goldman Forge's ambition)
*Stated plainly so it can be challenged and prioritised.*

**Product / coverage**
- Single jurisdiction (**NSW only**); no multi-state.
- 6 live scenarios (~70–85% of two-vehicle *moving* collisions, **indicative not backtested**). Real coverage % unmeasured.
- Rule citations in the tree are **builder drafts; two case-law references are UNVERIFIED** pending the Legal Head.
- **Voice channel** descoped to Phase 2 (web only today).
- No insurer/CTP, PMS, or tow/rental **integrations** (references are placeholders).
- No payments, e-signature, or document upload/OCR of police/insurer forms.

**AI / engine**
- **RAG retrieval layer not built** — the hybrid is architected; today's "sort" is rule/slot-based, not vector-RAG over rules + precedent.
- **Feedback flywheel not built** — human determinations aren't yet captured to improve the system.
- No bias/fairness or robustness testing of the classification step; no adversarial/STT testing for (future) voice.

**Security / ops / assurance**
- MFA enforced; **server-side AAL2 on the brief is flag-gated, not yet activated**; no enterprise SSO/IdP.
- No **penetration test**, no SOC 2 / ISO 27001 / ISO 42001 **certification**, no formal DR/BCP.
- No production **monitoring/alerting** (escalation-rate, band-distribution drift, error rate).
- Rate-limit is in-process (single-instance), not a durable shared limiter.

**Compliance documentation (the recurring theme) — ✅ now drafted 2026-06-14**
- AI policy, AI impact assessment, risk register, supplier register, PIA, data-breach response plan, and access/correction + retention-destruction procedures are **drafted** in `sign-off-package/GOVERNANCE-COMPLIANCE-PACK.md`. Remaining: **firm ratification** + completing `[FIRM]` placeholders (contacts, cadences, retention value). The four loop-integrity gates are formalised in `stage-4/GATE-REGISTER-ADDENDUM.md`.

**Accessibility / UX**
- No **WCAG 2.1 AA** accessibility audit.
- Dashboard analytics for the firm (volumes, band mix, escalation reasons) not built.

---

## 10. Honest standpoint — vs the current market
*Where ClaimDesk leads, and where the market is ahead.*

**Where ClaimDesk is genuinely differentiated**
- **Deterministic, auditable fault logic + human gate** — most market "AI legal" tools are either pure-LLM chat (hallucination + no audit trail) or shallow form-bots. The append-only audit + band-not-verdict + escalation governance is a real, defensible position for a regulated legal context.
- **Australian data residency by design** and consent-first intake — strong local-compliance posture.
- **A disciplined gated build loop** with a human legal sign-off baked in.

**Where the market is ahead (honest gaps to close)**
- **Breadth:** leading insurtech/legaltech intake products are multi-jurisdiction, omni-channel (web + app + voice + WhatsApp), and integrate directly with insurer/CTP systems and practice-management software.
- **Certifications:** mature competitors hold SOC 2 / ISO 27001 (and increasingly ISO 42001) — table stakes for enterprise/insurer procurement.
- **Evidence intake:** photo/video upload with damage AI, dashcam ingestion, and document OCR are increasingly standard; ClaimDesk captures these as *questions*, not artefacts.
- **Analytics & reporting** for the firm/insurer, and customer self-service status tracking.
- **Measured accuracy:** competitors quote backtested performance; ClaimDesk's coverage figure is still an estimate.

**Net positioning (honest):** ClaimDesk 247 is a **governance-grade MVP** — stronger than the market on auditability/compliance-by-design, behind the market on breadth, integrations, certifications, and measured accuracy. That is the right shape for a *legal* product at this stage, provided the compliance-documentation and measurement gaps are closed before scaling.

---

## 11. Recommended further development (priority order)
1. **Close the four P0 gates** (G-PROD-LOCK, G-VER, G-LH, G-AMEND) — cheap, prevents the incomplete-loop trap.
2. **Legal Head sign-off** of the 6 live scenarios → launch Stage 1; pre-approve the 9 Phase-2 scenarios.
3. **Compliance document pack** — AI policy, AI impact assessment + risk register (ISO 42001), PIA + breach-response + access/correction + retention-destruction (Privacy Act). High value, low build cost.
4. **Measure coverage** — backtest the rule tree against historical claims; replace the 70–85% estimate.
5. **Build the feedback flywheel** — capture human determinations; use them to prioritise scenarios + train the RAG classifier.
6. **Activate server-side AAL2** on the brief; add production monitoring/alerting + tested rollback.
7. **Phase-2 scope:** voice channel, evidence upload (photos/dashcam/OCR), firm analytics dashboard, multi-jurisdiction groundwork, integrations (insurer/CTP, PMS), WCAG audit.
8. **Pursue certification path** (ISO 27001 → ISO 42001) once documentation exists.

---

## 12. What to ask the independent reviewer
- Is the **deterministic-tree + advisory-RAG + human-gate** split the right architecture for a regulated legal product, or is there a stronger pattern?
- Are the **ISO 42001 and Privacy Act** mappings honest and complete — what's missing?
- Is the **gate set** complete, or are there failure modes with no gate?
- Is **band-not-percentage** the correct risk posture, or too conservative / not conservative enough?
- What would a NSW personal-injury / motor-accident lawyer say is **legally wrong or risky** in §2–§3?
- Against current market intake products, what is the **single most important missing capability** before this scales?

---

### Appendix — current technical facts (for verification)
- **Frontend:** TanStack Start / Vite / Nitro on Vercel (region `syd1`); domain `claimdesk247.com.au` (Cloudflare DNS).
- **Engine:** FastAPI (Stage 2.5 wrapper over Stage 3 deterministic logic) on Vercel (`syd1`); `/healthz` live.
- **Data:** Supabase (Sydney, `ap-southeast-2`); `intake_sessions` + append-only `audit_log`; RLS staff-read; service-role server-side only.
- **Tests:** 79/79 against the deployed engine (stage-2 30 · stage-3 31 · stage-2.5 18; was 75/75 pre-T1, 73/73 pre-Stage-2.5).
- **Security verified:** RLS (anon reads 0 rows), append-only (anon write rejected 42501), CORS exact-origin, rate-limit (5/min/IP), MFA TOTP/AAL2 enforced, server-side AAL2 on brief (flag-gated).
- **Rule tree:** `rule-tree.nsw.v3.json` v3.0.0; bands `likely/possible/unclear/insufficient`; 6 scenarios + 7 escalation triggers.

*This document states maturity honestly by design. Anything marked planned/partial/unverified is exactly that. Reviewers are encouraged to be hard on it — that is its purpose.*
