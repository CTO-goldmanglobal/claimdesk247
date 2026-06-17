# ClaimDesk 247 — Loop-Based Development Roadmap
**Operator:** Goldman Forge Legal · **Prepared by:** Fables (Cowork, planning seat) · **Date:** 2026-06-14
**Supersedes:** progress-map / horizon framing. **Absorbs:** the independent Market Review & Gap Analysis (14 Jun 2026, 20 gaps) + our internal showcase §9–§10 + the gate-completeness review.

> **Why loop-based, not a progress map.** A progress bar says *how far*; it hides whether a stage actually *closed*. We run **stages as loops** because a loop has a hard close condition — and "no incomplete loop" is the whole discipline. Each stage below is one loop. It does not close (and the next does not start) until its **exit gate** is green.

---

## The loop template (every stage runs this)
```
ENTRY GATE  →  PLAN (Fables, senior model — get direction right)
            →  BUILD (Cursor / MiniMax)
            →  CODE AUDIT (Opus — test-based, every audit is code/tests)
            →  AMEND (resolve findings)  →  RE-AUDIT
            →  LEGAL HEAD (human yes/no — substance only, never code)   ← last step before anything ships
            →  EXIT GATE (all P0 gates green · no open finding · no open Legal NO · version-bound sign-off)
            →  CLOSE → next loop
```
Loop-integrity gates apply to every stage: **G-PROD-LOCK** (prod refuses unsigned scenarios), **G-VER** (sign-off bound to rule-tree version hash), **G-LH** (legal yes/no recorded), **G-AMEND** (cannot close with anything open). Legal Head is always the **final gate before launch of that loop's output.**

---

## Stage map (each stage = one loop)

| Loop | Theme | Goal | Exit gate (must be green to close) |
|------|-------|------|------------------------------------|
| **L0** | Lock & Launch | Make it real and safe to switch on | Legal YES on 6 live scenarios · 4 P0 gates closed · live-site + consumer-law fixes shipped · NSW advertising/touting cleared · doc pack v1 + ADM disclosure live |
| **L1** | Prove & Measure | Replace estimates with evidence; start the flywheel; deepen coverage | Measured coverage published · flywheel capturing determinations · **Phase-2 scenarios live (Legal-signed)** · evidence-intake v1 · pen-test passed |
| **L2** | Channel & Intelligence | Meet users where they are; scale reviewers | Voice live on the *same* deterministic tree · RAG advisory in use (never sets a band) · first integration in production |
| **L3** | Scale & Moat | Product → platform | 2nd jurisdiction shipped · engine licensable · ISO/IEC 42001 audit booked/achieved |

---

## L0 — Lock & Launch  *(entry: now · this is the current loop)*
**Goal:** remove every cheap way this can go wrong before switch-on. Per the external audit, this comes **before** new scenarios.

| Track | Item | Closes gap | Notes |
|-------|------|-----------|-------|
| Compliance | Close 4 P0 loop gates (G-PROD-LOCK, G-VER, G-LH, G-AMEND) | "4 P0 gates not closed" | Eng: enforce in code; cheap |
| **Product (P0 — urgent)** | **Fix `tel:000`** → real intake line | "Call now dials 000" | **Emergency-number misdial; fix immediately** |
| **Product (P0)** | Remove/substantiate "4.9★ / 1,200+ drivers" + named testimonial | "Unverifiable testimonials" | Australian Consumer Law |
| Product | Fix leftover "Supabase & Vercel Hub" social meta; resolve **Goldman Global vs Goldman Forge** entity | "Brand/entity drift" | Nail the operating legal entity |
| Compliance | **Verify NSW PI advertising + claimant-touting model** | "NSW advertising/touting" | Legal Head signs the tow→hire→lawyer marketing/referral model |
| Compliance | Compliance doc pack v1 (AI policy, PIA, breach, access/correction, retention) + **automated-decision disclosure** in privacy policy | "Doc pack missing" + "ADM disclosure" | Drafts exist (`GOVERNANCE-COMPLIANCE-PACK.md`); firm ratifies; ADM disclosure cheap, grace to Dec 2026 |
| Compliance | Verify the 2 open case-law citations | "Citations unverified" | Legal Head confirms/strikes |
| Security/Ops | Basic monitoring (error/escalation/band-drift) · tested rollback · activate server-side AAL2 | "No monitoring/AAL2" | Operate safely day one |
| Compliance | **Legal Head sign-off — 6 live scenarios** *(loop's final gate)* + pre-approve the 9 Phase-2 | — | Uses `LEGAL-HEAD-SIGNOFF.md` |

**L0 exit / L1 entry milestone:** Legal YES on the 6 live scenarios **and** 4 P0 gates closed **and** live-site/consumer-law fixes shipped **and** NSW advertising cleared.

---

## L1 — Prove & Measure  *(includes the Phase-2 scenario build)*
**Goal:** stop guessing, start the data moat, and deepen scenario coverage — but only on the locked, signed-off base from L0.

| Track | Item | Closes gap |
|-------|------|-----------|
| Data | Backtest coverage vs historical claims → measured, defensible accuracy per scenario | "Coverage estimated not measured" |
| Data | Build the feedback flywheel — capture every human determination as structured data | "Flywheel not built" |
| **Product** | **Phase-2 scenarios 6 → 15** — *see the dedicated loop below* | "Scenario depth" |
| Product | Evidence intake v1 — photo/document upload as artefacts + OCR; partner for damage AI | "Evidence as questions" |
| Product | Firm analytics dashboard (volumes, band mix, escalation reasons) + seed status tracking | "No analytics dashboard" |
| Security | Independent pen-test + DR/BCP + durable shared rate limiter | "No pen-test/DR/BCP" |
| Compliance | ISO 42001 docs: AI impact assessment + risk register + supplier register | "Certification groundwork" |

**L1 exit:** measured coverage published · flywheel live · Phase-2 scenarios **Legal-signed and in production** · pen-test passed.

### ▶ Dedicated loop — Phase-2 Scenario Build (6 → 15)
*The headline build, run as its own loop so it closes completely. Legal Head is the last step.*
1. **PLAN** — fault logic + NSW citations already drafted in `PHASE-2-TIER1-RULE-BRANCHES.md` + `PHASE-2-TIER2-RULE-BRANCHES.md` (9 scenarios: car-park, signalised, right-turn, sideswipe, driveway, U-turn, head-on, dooring, unmarked).
2. **BUILD — engine data + logic:** add the 9 scenario objects to `rule-tree.nsw.v3.json` (→ v3.1.0); add `_band_s7…s15` band functions + `ACCIDENT_TYPE_TO_SCENARIO` routing + damage-consistency maps in `engine.py`.
3. **BUILD — conversational question-injection (the dependency found 2026-06-14):** wire each scenario's `classification_questions` into the live intake flow so the engine actually *asks* the discriminating questions (front/rear, sight-lines, light colour, etc.). **Without this, the band logic has no inputs and would default — so this sub-step is mandatory, not optional.** Touches `state_machine.py` + `wrap.py`; regression-guard all 6 existing scenarios.
4. **TEST** — ≥2 acceptance cases per scenario in `acceptance-tests.stage3.yaml`; keep the full suite green (now 75 → ~93).
5. **CODE AUDIT (Opus)** — determinism, band-only output, disclaimer attach, escalation overrides, no regression.
6. **LEGAL HEAD (final gate)** — yes/no per scenario on fault rule + citation + customer wording (`LEGAL-HEAD-SIGNOFF.md` B7–B15). **Nothing serves production until YES (G-PROD-LOCK), bound to v3.1.0 (G-VER).**
7. **CLOSE** — only when all 9 are signed or explicitly deferred; re-run coverage backtest to measure the lift.

---

## L2 — Channel & Intelligence
**Goal:** add channels + reviewer leverage once the core is trusted and measured.

| Track | Item | Closes gap |
|-------|------|-----------|
| AI/Engine | Voice channel — STT feeding the **same** deterministic tree; adversarial/STT testing; buy/partner the voice layer | "Voice descoped" |
| AI/Engine | RAG advisory layer — vector retrieval over rules + precedent + firm docs to assist the human; **never sets a band** | "RAG not built" |
| Product | WhatsApp / SMS channels | "Omni-channel" |
| Product | Integrations v1 — one CTP insurer pilot + a practice-management system (Leap/Smokeball/Clio) + tow/hire networks | "No integrations" |
| AI/Engine | Bias/robustness testing of the classification step | (trust at scale) |
| Compliance | Begin ISO 27001 → 42001 certification path | "No certifications" |

**L2 exit:** voice live on the deterministic tree · RAG advisory in reviewer use · first integration in production.

---

## L3 — Scale & Moat
**Goal:** product → platform.

| Track | Item | Closes gap |
|-------|------|-----------|
| Product | Multi-jurisdiction groundwork — per-jurisdiction rule-tree configs; ship a 2nd state (QLD or VIC/TAC) | "Single jurisdiction" |
| GTM | Productise the governance engine — license intake SaaS to other PI firms | "Single buyer" |
| GTM | Insurer/CTP fault-triage product (auditable FNOL triage) | "New buyers" |
| Compliance | Achieve ISO/IEC 42001 certification | "No certifications" |
| Data | Proprietary NSW fault dataset → measured-accuracy benchmark | (compounding moat) |
| Product | WCAG 2.1 AA audit + remediation · enterprise SSO/IdP | "No WCAG" / SSO |

**L3 exit:** 2nd jurisdiction live · engine licensable · ISO 42001 certified.

---

## Gap → Loop coverage (every audit gap has a home — no orphans)
| Audit gap (sev) | Closed in |
|---|---|
| tel:000 (P0) · testimonials (P0) · meta/entity | L0 |
| NSW advertising/touting (P0) · 4 P0 gates (P0) · doc pack · ADM disclosure · citations | L0 |
| Coverage measured (P1) · flywheel (P1) | L1 |
| Phase-2 scenarios · evidence intake · analytics | L1 |
| Pen-test/DR/BCP (P1) · ISO docs (P1) | L1 |
| Voice (P1) · RAG (P1) · omni-channel · integrations (P1) · bias testing | L2 |
| Certifications (P1) · multi-jurisdiction · productise · dataset · WCAG · SSO (P2) | L3 |
| AAL2/rate-limit hardening (P2) | L0 (AAL2) / L1 (durable limiter) |
| Business model & pricing (P1, GTM) | **Cross-cutting — decide in L0/L1** (not a build; a commercial decision) |

> The one audit item not on a build track is **business model / pricing** — it's a commercial decision (per-claim referral vs SaaS seat vs engine licence) that should be set during L0–L1 because it shapes L3's productisation. Flagged for the firm.

---

## Current status feeding into L0
Engine live (Sydney) · 75/75 regression · RLS/append-only/CORS/rate-limit/MFA verified · server-side AAL2 built (flag-gated) · compliance pack + gate register **drafted** · Legal-Head packet ready.

**L0 progress (2026-06-14):**
- ✅ **Live-site P0 fixes shipped & verified** (commit `144516e`): `tel:000` removed from bundle + DOM (CTAs now route to `/intake`); fabricated "4.9★ / 1,200+ drivers" rating + "Jess M." testimonial removed (Australian Consumer Law); "Supabase & Vercel Hub" meta removed; `author` → Goldman Forge Legal; titles → ClaimDesk 247; OG/Twitter image → real logo.
- ✅ **ADM disclosure** wording drafted in the compliance pack (firm ratifies → one-line engine insert).
- ⏳ **Remaining L0 (owners):** firm confirms operating legal **entity** (Goldman Global vs Goldman Forge Legal); **Legal Head** signs 6 live scenarios + NSW advertising/touting model; **Eng** enforces the 4 P0 gates in code + monitoring/rollback + activate AAL2; **firm** ratifies the compliance pack.

*This roadmap is loop-based by design: progress is measured by loops **closed**, not tasks ticked. A loop closes only when its exit gate is green and the Legal Head has signed what that loop ships.*
