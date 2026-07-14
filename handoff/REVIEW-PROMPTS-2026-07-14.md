# Review Prompts — ClaimDesk 247 (2026-07-14)

Two prompts, one per stream. Paste each into its own Fables or ChatGPT 5.6 chat.
Both prompts point at files (no pasting) per the token rule.

---

## A. Backend review prompt

```
You are reviewing the BACKEND of ClaimDesk 247 — a 4-claim-type legal engine
(motor / property_damage / public_liability / medical_negligence) with a hash-
bound Legal Head sign-off gate. Review for correctness, legal-compliance gaps,
security, and architecture. Point at files; do not paste.

Repo: CTO-goldmanglobal/claimdesk247, branch cursor/founding-state-claimdesk247
HEAD: 9ed4ecf

SCOPE TO REVIEW (backend only — frontend is a separate review):
- stage-3/app/engine.py            — pure fault engine, multi-state PD
- stage-3/app/state_machine.py     — intake slots, consent, state-scope guard
- stage-3/app/audit.py             — append-only audit log
- stage-3/app/config.py            — token/disclaimer resolution
- stage-3/app/data/                — rule trees (NSW motor/PL/PD/med-neg + 7 non-NSW PD)
- stage-2.5/app/wrap.py            — FastAPI endpoints (session/consent/slot/classify/evidence/disclosure)
- stage-4/app/evidence_store.py    — S3 Sydney evidence store + InMemory dev adapter
- stage-4/scripts/                 — sign_rule_trees.py, apply_evidence_lifecycle.py, run_evidence_retention.py
- stage-4/legal/                   — PD counsel memo + CD-R2 analyses (2026-07-14)
- stage-4/db/0004_evidence_metadata.sql — case_evidence table + RLS

WHAT LANDED THIS WEEK (review focus):
1. National PD rollout — all 8 AU jurisdictions signed live (NSW + VIC/QLD/WA/SA/TAS/ACT/NT).
   NSW hashes must be unchanged (3964e668 motor / 1f13febaf6c0 PD / dc824c3559ab PL /
   4e3fe60ac4c2 med-neg). NT limitation is 3 years; all others 6.
2. PD recovery disclosure wire (PD-COUNSEL-MEMO §3.3): GET /api/disclosure/property_damage
   fires pd_disclosure_presented; consent grant fires pd_disclosure_acknowledged sibling.
3. Evidence upload: POST /api/intake/{ref}/evidence → S3 Sydney, consent-gated, audit-logged,
   image-only (JPEG/PNG/WebP/HEIC), 10MB cap, 20-file-per-case cap.
4. Retention scheduler: run_evidence_retention.py (EventBridge target).

VERIFY HEALTH BEFORE REVIEWING:
  cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py    # 50/50 + 26 injury-ext
  cd ../stage-2.5 && python3 tests/run_acceptance.py            # 26/26
  cd .. && python3 stage-4/scripts/sign_rule_trees.py --verify  # 11 trees live

REVIEW QUESTIONS:
1. Injury firewall (IX-12): is esc-injury truly unreachable-by-band in every state?
   Check _check_global_escalations ordering in engine.py.
2. Multi-state sign-off isolation: can a content change in one state's PD tree ever
   stale another state's hash? Verify the per-tree hashing claim (_compute_scenarios_hash).
3. PD disclosure audit pair (pd_disclosure_presented + pd_disclosure_acknowledged):
   are these sufficient evidence to defeat an ACL "I wasn't told" complaint? Any gap
   vs PD-COUNSEL-MEMO §3.3? Can a session grant consent without the presented-event firing?
4. Evidence endpoint: any path where a file lands in S3 without consent or without an
   audit entry? Check the 403 gate, the validation order, and the InMemory vs S3 split.
5. Retention scheduler (run_evidence_retention.py): any path where it deletes an object
   the audit log can no longer reference? Audit entries MUST survive the purge.
6. Security: secrets in env vs code, PII in URLs (the ref is opaque — verify), RLS gaps
   on case_evidence, IAM scope on the S3 bucket (least privilege?).
7. Legal: does the PD counsel memo's "NSW GO, QLD CONDITIONAL, others VERIFY" actually
   match what the engine enforces? The engine emits bands nationally; is that premature
   given the §2.2 per-state licensing verify items?

Flag P0 / P1 / P2. Cite file:line. Do not propose code — propose findings + recommended
changes; the build seat will implement.
```

---

## B. Frontend review prompt

```
You are reviewing the FRONTEND of ClaimDesk 247 — a TanStack Start + Vite +
shadcn/ui customer-facing site for a legal-tech product. Review for UX,
accessibility, security (XSS / PII leakage), legal-copy compliance, and
architecture. Point at files; do not paste.

Repo: CTO-goldmanglobal/claimdesk247, branch cursor/founding-state-claimdesk247
HEAD: 9ed4ecf
Frontend lives in: lovable-ui/ (submodule → CTO-goldmanglobal/claimdesk247-76a0b7de)

SCOPE TO REVIEW (frontend only — backend is a separate review):
- lovable-ui/src/routes/__root.tsx        — shell, footer, <head> meta, error boundary
- lovable-ui/src/routes/index.tsx         — landing page (PD-first hero, NSW-branded)
- lovable-ui/src/routes/intake.tsx        — chat-style intake widget (the "robot")
- lovable-ui/src/routes/embed/intake.tsx  — embeddable variant
- lovable-ui/src/routes/dashboard.tsx     — staff sign-in (legal_staff role)
- lovable-ui/src/components/BandBadge.tsx
- lovable-ui/src/components/EvidenceUploader.tsx
- lovable-ui/src/lib/api/client.ts        — fetch wrapper, all endpoints
- lovable-ui/src/lib/api/types.ts         — request/response shapes
- lovable-ui/src/lib/config.ts            — FIRM_PHONE, PANEL_SHOP_NAME
- lovable-ui/src/lib/image-resize.ts      — client-side 1600px / JPEG q80

WHAT THE FRONTEND DOES TODAY:
1. Landing page leads with PD recovery ("Not at fault? We handle the whole recovery").
   Copy is NSW-branded in the footer ("NSW road-rule trained") and landing meta.
2. /intake is a chat-style widget: loading → consent → question → classifying → result.
   Supports ?ref=<ref> (share/resume) and ?embed=1 (iframe variant).
3. /embed/intake is the dedicated embeddable route (same component, stripped chrome).
4. EvidenceUploader appears after consent + classify, resizes client-side, uploads multipart.
5. Dashboard is staff sign-in (legal_staff role → /api/brief/:ref, MFA-gated backend-side).
6. Footer on every page: "Operated by ClaimDesk 247. Smash-repair services by {PANEL_SHOP_NAME}."

BACKEND CONTRACT THE FRONTEND CALLS (do not review these — just verify the calls):
- POST /api/session {channel, ref?, consentGranted?} → {ref, consentRequired, consentGranted, next}
- POST /api/consent {reference, accept}
- POST /api/slot {ref, slot, value} → {next, progress}
- POST /api/classify {ref} → {band, disclaimerText, escalation?, reference}
- GET /api/disclosure/{claim_type}?ref=<ref> → {claim_type, disclosure_text}  ← NEW
- POST /api/intake/{ref}/evidence (multipart) → EvidenceItem
- GET /api/intake/{ref}/evidence → {reference, count, items[]}
- GET /api/case/{ref} → CaseFile

REVIEW QUESTIONS:
1. PD disclosure (NEW backend endpoint): the intake consent screen does NOT currently
   fetch /api/disclosure/property_damage and render it above the consent button. For PD
   intakes, the disclosure text MUST render above consent, scrollable-to-acknowledge,
   and the consent button should be disabled until ack. Where exactly does this wire in
   intake.tsx? Propose the placement and state-machine change.
2. PII / data leakage: any path where PII (name, phone, accident details) ends up in a
   URL, a query string, an OG tag, or an error report? Check intake.tsx, client.ts,
   lovable-error-reporting.ts.
3. Accessibility: chat-style intake — is keyboard navigation complete? Focus traps?
   Screen-reader announce on new system messages? Color contrast on BandBadge?
4. Legal-copy compliance: the engine emits bands (likely/possible/unclear/insufficient).
   Does the UI ever frame these as a conclusion ("you are at fault") rather than general
   information? Check BandBadge + result screen in intake.tsx. The disclaimer text must
   always be rendered verbatim alongside the band.
5. NSW-only branding vs national product: footer says "NSW road-rule trained", landing
   meta targets NSW, but the engine is now national (VIC/QLD/WA/SA/TAS/ACT/NT + NSW).
   What copy needs to change? Should it be state-aware (detect from slot 1 answer)?
6. Evidence uploader UX: progress %, HEIC messaging (only Safari resizes client-side —
   other browsers pass HEIC through; is the user told?), error states, retry, file-count
   cap messaging.
7. Embed mode: ?embed=1 / /embed/intake — any way for the host page to extract the user's
   ref or PII via postMessage, referrer, or URL? Verify the iframe is sandboxed correctly.
8. Performance: image-resize runs on the main thread. For 10MB HEIC files this can JANK
   the UI for seconds. Should it be a Web Worker?

Flag P0 / P1 / P2. Cite file:line. Do not propose polished code — propose findings +
recommended changes; the build seat will implement.
```

---

## How to use these

1. Open two new Fables (or ChatGPT 5.6) chats.
2. Paste prompt A into one, prompt B into the other.
3. Send the reviewer the repo + branch + HEAD so they can pull.
4. Bring findings back to the relevant build chat (backend here, frontend in the other Cursor chat).

---

*Prepared 2026-07-14. Two streams, two prompts, one repo.*
