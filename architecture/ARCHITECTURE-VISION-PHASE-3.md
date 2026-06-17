# Architecture Vision — Governed Hybrid RAG (Phase 3)
**Project:** AI Legal Receptionist + Accident Intake System
**Status:** Vision + guardrails on record. **Not a scope commitment.** MVP (Stages 1–5) ships first.
**Date:** 2026-06-13 · Goldman Forge / Fables · For legal-firm awareness

---

## 1. One-line summary
A deterministic rule engine stays the source of truth; a governed, in-region RAG layer enriches how answers are retrieved and phrased; humans verify the cases that matter; an immutable audit trail records everything. Capability grows, governance grows with it — or it isn't shipped.

## 2. Confirmed stack
| Layer | Choice | Governance note |
|---|---|---|
| UX build | Lovable | Builds the interface only; calls into the engine (see Build Contract) |
| State / data | Supabase — **Sydney region** | Data at rest in Australia; RLS enforces access + audit immutability |
| Hosting | Vercel | PII-touching functions must run in `syd1` (AU), not US/EU edge |
| AI / RAG | Azure AI Foundry — **DeepSeek V4 Flash**, AU in-region, ISO 42001 | Platform-level AI management certified; application governance is ours |
| Fault logic | Deterministic rule tree (Stages 1–2) | Source of truth; never an LLM decision |
| Audit | Immutable append-only log (gate G-34) | Per-answer provenance; legal defensibility |

## 3. The governance spine (non-negotiable across all layers)
1. **Engine decides, LLM describes.** The rule tree assigns the confidence band (likely / possible / unclear / insufficient). DeepSeek retrieves vetted sources and phrases general information around that verdict. The LLM never classifies fault and never invents a rule.
2. **Grounded-only generation.** RAG answers cite vetted sources only; thin retrieval → refuse and escalate (maps to the "insufficient" band). Same disclaimer + framing rules as the rule tree apply to generated text.
3. **Human verification on the bands that need it.** "unclear" / "insufficient" auto-route to a human; "likely" is sampled for QA. Lawyer confirm/override is captured as signal.
4. **Provenance logged per answer.** Sources retrieved, prompt, model version, generated text → immutable log. This is what makes LLM-assisted legal information defensible.
5. **Residency end to end.** Storage (Supabase Sydney), inference (Azure AU), hosting functions (Vercel syd1). No PII leaves Australia.

## 4. Expansion roadmap (sequenced — do not leap)
1. **MVP** — deterministic engine, web + voice, sign-off. Governance credibility first. *(Stages 1–5, in progress.)*
2. **Hybrid RAG** — retrieval over vetted sources (NSW rules, RMS guidance, verified case law) behind the rule tree. Rules still decide; retrieval enriches phrasing and citations.
3. **GraphRAG** — promote the rule tree into a knowledge graph (driver → manoeuvre → rule → exception → precedent). Liability is relational; graph reasoning is more defensible than vector similarity over documents. The Stage 1 rule tree + Appendix A are the seed nodes.
4. **Human-in-loop feedback** — lawyer overrides adjust graph edge weights and labelled training signal; audit log is the evidence layer throughout.

## 5. What the ISO 42001 cert does and does not do
Covers: Azure's management of the AI platform (risk, governance, operations). Does **not** cover: our application's compliance — Privacy Act handling, no-advice framing, disclaimer discipline, audit completeness remain our obligations at the application layer. The cert is a floor we build on, not a ceiling that covers us.

## 6. Why the current MVP choices already point here
Deterministic core (not LLM guessing), citations stored as data, escalation routing by confidence band, and an immutable audit log built as a P0 gate from day one — these are the foundations a governed RAG/GraphRAG system needs, rather than things that would be torn out. The expansion is additive.

---
*Vision document — guardrails on record ahead of build. Scope committed only via stage requests.*
