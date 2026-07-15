# Landing Page Rebuild Spec — ClaimDesk 247

**Date:** 2026-07-16
**Status:** Implementation-ready spec. A GLM seat builds + commits this.
**Scope:** Rebuild the customer landing page (`lovable-ui/src/routes/index.tsx`) + footer (`lovable-ui/src/routes/__root.tsx`). No backend work. No new routes. No new dependencies.

**Why:** The live landing (claimdesk247.com.au) is under-furnished — thin content, big whitespace gaps, no trust scaffolding, and (critically) no link to the `/crash` Golden Rules PWA. This rebuild makes the page *trustworthy* by leading with radical transparency: in a sector with a claim-farming reputation, the differentiator is publishing what we WON'T do.

**Reviewed against Opus governance spine** (`handoff/PROJECT-SUMMARY-FOR-OPUS.md`, 2026-06-13) + the NSW-only engine state as of backend `743a214` (2026-07-15). Key alignments enforced below:
- **Geography: NSW-only.** Engine accepts `NSW` + `outside_nsw` (which escalates to human callback). Do NOT promise "Australia-wide" anywhere — it overpromises against an engine that can't deliver. Chips, footer, and FAQ must reflect this.
- **No fault decision by us** (Opus §3.2). The FAQ must include "Do you tell me if I was at fault?" → "No."
- **Fixed disclaimers rendered verbatim** (Opus §3.3). Every new section that could read as advice carries "general information, not legal advice."
- **Fee structure not specified.** Stage 5 Legal Head decision (Opus §14). The "how do you make money?" FAQ stays structural — "paid by the at-fault insurer, never by you, fee agreed up front" — not specific (no %, no contingency wording).
- **CD-R3 injury firewall as headline trust asset** — strategic upgrade from Opus's compliance framing. Don't soften it.

---

## Guardrails (READ FIRST — non-negotiable)

1. **No fabricated proof.** A prior commit (`144516e fix(launch-safety)`) deliberately removed fake testimonials + a fake `tel:000`. Do NOT reintroduce testimonials, star ratings, case counts, review quotes, or any social proof that isn't real. Use only *verifiable* trust: data-hosting location, the legal posture, the panel-shop partner, "Powered by Goldman Forge".
2. **CD-R3 legal line.** Customer claim types are ONLY motor + property_damage. Never mention public-liability or medical-negligence as things "we help with". Injury → firewall (stop + human callback), never a paid lawyer referral.
3. **Only verifiable claims.** No "NSW road-rule trained", no "#1", no "trusted by thousands". Keep to what's true: free to start, at-fault insurer pays, Australia-hosted data, sealed evidence, you can stop anytime.
4. **Reuse existing design tokens.** The page already uses: `teal` / `teal-soft`, `coral` / `coral-soft` / `coral-foreground`, `sky-soft`, `gold`, `accent`, `foreground` / `muted-foreground`, `border`, `card`, `background`. Use these — do NOT introduce new colors. Icons come from `lucide-react` (already imported).
5. **Phone is gated.** `HAS_FIRM_PHONE` is currently false. Any phone CTA must be wrapped in `{HAS_FIRM_PHONE && (...)}` — never ship a dead `tel:` link.
6. **Mobile-first.** Most traffic is a stressed person on a phone. Every section must read well at 390px. Test at 390px and 1440px.
7. **Verify before done:** `npx tsc --noEmit` clean, `npm run build` clean, screenshot at both widths.

---

## The strategy in one line

**Lead with what we refuse to do.** The injury firewall (we can't sell your details — it's illegal) is the headline trust asset, not a hidden safeguard. Three trust pillars, each grounded in real system behaviour:
- "We can't sell your details — and here's the law that stops us" (injury firewall = feature)
- "You don't pay. The at-fault insurer does" (kills the 'what's the catch')
- "Your file, sealed and yours" (hash-bound evidence + AU hosting + zero-obligation exit ramp)

---

## Section-by-section build

The page is `lovable-ui/src/routes/index.tsx`. Rebuild the `<main>` contents in this order. Keep the existing nav `<header>` (just add the `/crash` link — see §Nav). Keep the `head()` meta as-is.

### Nav (modify existing header)

Add a "Crash checklist" link to both the desktop nav and the mobile dropdown, pointing to `/crash`:
- Desktop: in the `<nav className="hidden ... sm:flex">` next to "How it works" / "Services", add `<Link to="/crash">Crash checklist</Link>` styled like the siblings.
- Mobile dropdown: add the same link in the mobile `<nav id="mobile-nav">` list.
- The existing "Start now" button keeps `search={{ ct: "property_damage" }}`.

### 1. Hero (modify existing)

Keep the headline "Not at fault?\nWe handle the whole recovery." and the sub-paragraph. Change the CTA area to offer **two doors** instead of one:

- Primary (coral): `Chat with us — free` → `/intake?ct=property_damage` (unchanged)
- Secondary (outline): `Just had a crash? Open the checklist` → `/crash`

Rationale: a stressed person at a roadside needs the checklist first; an active claimant needs the chat. Don't force everyone into the chat.

Keep the trust chips row, **but fix the geography chip** — the existing copy says "Australia-wide, state-aware" which is now wrong (the engine accepts only NSW + `outside_nsw`-to-human-callback as of backend `743a214`, 2026-07-15). The honest chip is:

- Chip 1 (replace): `MapPin` icon → **"Live in NSW"** (or "NSW for now — more states coming" if it fits cleanly). Do NOT promise Australia-wide service — a VIC customer who reads that and then hits an NSW-only engine is the same trust fracture as the chatbot-vs-human one.
- Chip 2 (keep): `Lock` icon → "Data hosted in Australia" — this is true regardless of which state the customer is in (Supabase Sydney).

Keep the hero image.

### 2. "What's the catch?" strip (NEW — insert right after hero, before the stats)

A full-width band (`bg-teal-soft` or `bg-card` with a top/bottom border) that answers the #1 suspicion in the first scroll. Centered, one strong line + a short support line:

> **Free to start. You pay nothing.**
> The at-fault driver's insurer covers your repairs, towing and a like-for-like hire car. We never ask for your card — at any point.

Icon: `Coins` or `ShieldCheck` from lucide.

Add a small muted footnote: *"General information and claim support only — not legal advice."* (Opus governance spine §3.3: disclaimers on every section that could be read as advice.)

### 3. Stats bar (keep existing)

Keep the `~5 min / 24/7 / AU` three-stat bar as-is. It's honest and works.

### 4. Transparency block (NEW — the centerpiece)

This is the out-of-the-box differentiator. Heading: **"What we will — and won't — do."** Sub: "In a industry with a bad reputation, we think being clear about our limits is the point."

Two columns (stack on mobile). Use `Check` (green/teal) for the left, a "no" icon (`Ban` or `X`, in `coral` or muted-red) for the right.

**✅ What we do**
- Recover your repairs, towing and a like-for-like hire car from the at-fault insurer
- Build a clean, timestamped record of your accident
- Hand you your full report — yours to keep, with zero obligation
- Put a real person on the phone the moment anyone's hurt

**🚫 What we won't do**
- Sell or share your details as a "lead" — that's illegal claim-farming, and we refuse it
- Handle injury claims for a fee — if you're hurt, we stop and connect you to help at no cost
- Pressure you, or lock you in — you can stop at any point
- Ask for payment — there's nothing to pay

Add a one-line footnote under the block: *"If anyone's injured, our system stops the intake and routes you to a real person. We don't earn anything from injury matters — by design, and by law (NSW claim-farming prohibition)."*

Add a second footnote line in muted/`text-xs` text: *"General information only — not legal advice."* (Opus governance spine §3.3: fixed disclaimers rendered verbatim, on every section that could be read as advice.)

This is the load-bearing trust section. Copy above is approved-safe — use it close to verbatim.

### 5. Three calm steps (keep existing, already CD-R3-correct)

Keep the current three cards (Answer a few questions / We recover the costs / A real person steps in when it matters). Copy is already fixed for the injury firewall. No change needed.

### 6. Golden Rules checklist promo (NEW — the give-first hook)

A distinct section promoting the `/crash` PWA. Heading: **"Keep our free crash checklist on your phone."** Body:

> Hope you never need it. But if you're ever in an accident, the Golden Rules checklist walks you through the right steps — calmly, one at a time — and builds your report as you go. Works offline. No sign-up. Free.

CTA (secondary/outline or a distinct card style): `Open the checklist` → `/crash`. Optionally a small "Add to Home Screen" hint line.

Visual: use a phone-frame mock or a simple icon grid (`ShieldCheck`, `Camera`, `MapPin`, `FileText` from lucide) representing the checklist steps. Do NOT fabricate screenshots. A clean icon row is fine.

This section is the "insurance you hope never to use" hook — installing it is the relationship, the claim comes later. It's the strategic heart of the give-first model.

### 7. Trust-proof row (NEW — verifiable only)

Heading: **"Built to be trusted."** A row of 3-4 cards, each a *verifiable* trust fact (NO testimonials, NO fabricated numbers):

- **Data stays in Australia** (`Lock`/`MapPin`) — "Your details are hosted in Australia and never sold."
- **Your evidence is sealed** (`ShieldCheck`) — "Every photo and detail is timestamped and tamper-evident, so your record holds up."
- **Repairs by an accredited local shop** (`Wrench`) — use `PANEL_SHOP_NAME` from `@/lib/config` (currently "Petersham Prestige Smash Repairs").
- **Powered by Goldman Forge** (`Building2`/`Scale`) — the operator/technology backer.

Import `PANEL_SHOP_NAME` from `@/lib/config`.

### 8. How ClaimDesk works — expand FAQ (modify existing)

The current "How ClaimDesk works" has 3 Q&As. Expand to 8-9. Keep the existing three (Who we are / Is it free / What happens to my details) and add:

- **"What if I was partly at fault?"** — "Fault isn't decided at the scene — it's worked out later from the evidence. Tell us what happened; we'll give you clear general information either way. Not legal advice."
- **"What happens if someone was hurt?"** — "We stop the intake and a real person calls you back to arrange the right help. We don't handle injury claims for a fee — that's not what we do."
- **"Do I have to use your repairer?"** — "No. You choose who repairs your car and where. We work with accredited local shops, but the choice is always yours."
- **"Can I stop halfway?"** — "Yes, any time. Your report is yours to download and keep, with no obligation to continue."
- **"Do you tell me if I was at fault?"** (NEW — Opus governance spine §3.2: no fault decision by us) — "No. We give you general information based on what you tell us. Fault is decided later — by the insurer, or by a court if it gets there — from the evidence, not by us. We never tell you a percentage or a fault score."
- **"Are you available outside NSW?"** (NEW — backend `743a214` is NSW-only stage 1; honesty required) — "We're currently helping customers in New South Wales. We're expanding to other states soon. If you're outside NSW, tell us when you start — one of our team will call you within the next business day to talk through what we can do for you. We're rolling out state-by-state as each state's rules are verified and signed off. We won't pretend to know a state's laws before we do."
- **"How do you make money?"** — use this **verbatim** wording (approved by backend chat 2026-07-16, within PD-COUNSEL-MEMO §4 guardrails; do NOT embellish or specify fixed/%/hybrid — that's Legal Head open item #9): *"We charge a recovery service fee that's agreed with you up front — before you consent to anything. The fee is paid from the recovery, never billed to you separately, and the amount is always disclosed in writing before you agree. We never sell your information, and we never charge per-lead or per-referral."*

Keep the accessible `<dl>`/`<dt>`/`<dd>` structure the current section uses.

### 9. Final CTA (keep existing)

Keep "You handle the recovery. We'll handle the rest." + `Chat with us — free`. Optionally add the checklist as a secondary link here too.

### 10. Footer (modify `lovable-ui/src/routes/__root.tsx`)

Current footer: "Operated by ClaimDesk 247. Smash-repair services by {PANEL_SHOP_NAME}." (plus a stale "· Australia-wide, state-aware" line that was added in the earlier branding-neutralisation commit).

Add / fix:
- A **"Powered by Goldman Forge"** line (the receptionist/question-tree docs reference this — it belongs in the footer).
- A **`/crash` link** ("Crash checklist") alongside "Staff sign in".
- **Replace "Australia-wide, state-aware" with "Live in NSW"** — the engine is NSW-only as of `743a214`. Don't overpromise.
- Keep the existing operator + panel-shop line and the phone (gated by `HAS_FIRM_PHONE`).

---

## Component/structure notes for the implementer

- All new sections go in `index.tsx`'s `<main>`. Keep them as inline JSX or small local components in the same file — do NOT create a new components folder for this (it's one page).
- Reuse the existing section container pattern: `<section className="mx-auto max-w-6xl px-6 py-16 ...">` (or `max-w-3xl` for text-heavy blocks like FAQ).
- Icons: add any new lucide imports to the existing `import { ... } from "lucide-react"` line. Available/likely: `ShieldCheck`, `Ban`, `Coins`, `Wrench`, `Building2`, `Camera`, `FileText`, `Lock`, `Check`, `X`.
- Links: use `<Link to="/crash">` (TanStack Router) for internal, matching the existing `<Link>` usage. `/crash` is a real registered route.
- Keep `search={{ ct: "property_damage" }}` on every `/intake` CTA (fires the PD disclosure).

---

## Copy that must stay verbatim (legal-sensitive)

- The transparency block's "won't do" bullets (§4) — approved-safe wording, use close to verbatim.
- The injury-firewall footnote (§4) — do not soften "we don't earn anything from injury matters".
- The "How do you make money?" FAQ (§8) — the fee-transparency wording is deliberately precise; don't embellish.
- Every "not legal advice" disclaimer currently on the page — keep them all.

---

## Verification checklist (before commit)

```
cd lovable-ui
npx tsc --noEmit        # must be clean
npm run lint            # no NEW errors vs baseline
npm run build           # must be clean
# screenshot both widths and eyeball:
#   - 1440px desktop
#   - 390px mobile
# confirm: /crash link in nav + footer; transparency block reads well;
#   no PL/med-neg copy; no fabricated proof; no dead tel: link.
```

Commit message suggestion:
```
feat(landing): trust-first rebuild — transparency block, /crash promo, expanded FAQ

Rebuilds the landing around radical transparency (LANDING-REBUILD-SPEC
2026-07-16): the injury firewall becomes the headline trust asset, adds
the "what we won't do" block, the Golden Rules /crash checklist promo,
a verifiable-only trust row, expanded FAQ, and footer fixes (Powered by
Goldman Forge + /crash link). No fabricated proof. CD-R3 clean.
```

Then: push submodule main → bump parent pointer → deploy (preview first, promote after click-through).

---

## PREREQUISITE (do this FIRST — frontend bug the backend just exposed)

**The `/intake` chat doesn't handle slot-stage escalations.** The backend now fires `escalation: "state-scope"` at the SLOT level (mid-conversation, on the very first question if the customer picks `outside_nsw`). The current frontend only handles escalations at the CLASSIFY stage (after all questions done) via `ClassifyResponse.escalated`. A non-NSW customer who clicks through from the new landing will hit a broken flow: `applyNext` sees `next.done === true`, calls `runClassify`, which will either fail or return a confusing result.

**Fix before the landing ships** (in the same PR or a immediately preceding one):

1. **`SlotResponse` type** (`src/lib/api/types.ts`) — add optional escalation fields:
   ```typescript
   export interface SlotResponse {
     ref: string;
     next: SlotQuestion | null;
     progress: { answered: number; total: number };
     /** Present when the engine escalates mid-conversation (e.g. state-scope, esc-injury). */
     escalated?: boolean;
     escalation?: "esc-injury" | "state-scope" | "reprompt-cap" | "unmapped-accident-type";
     escalation_reason?: string;
     reference?: string;
   }
   ```

2. **`applyNext`** in both `intake.tsx` and `embed/intake.tsx` — check for `escalated` BEFORE treating `next.done` as "go to classify":
   ```typescript
   function applyNext(res: SlotResponse, ...) {
     setProgress(res.progress);
     if (res.escalated) {
       // Route to a mid-conversation handoff panel — do NOT call runClassify.
       // The engine has stopped the conversation; respect that.
       setEscalation(res.escalation, res.escalation_reason, res.reference);
       setStage("escalated");  // new stage
       return;
     }
     if (!res.next || res.next.done) { ... existing photos → classify path ... }
     ...
   }
   ```

3. **New `escalated` stage + handoff panel** — same UX shape as the existing injury firewall handoff, but with copy that varies by escalation code:
   - `esc-injury` → existing injury firewall copy (unchanged)
   - `state-scope` → warm, forward-looking: *"We're currently helping customers in New South Wales. We're expanding to other states soon. One of our team will call you within the next business day to talk through what we can do for you. Your reference is GF-XXXXXXXX."*
   - `reprompt-cap` → *"I'm having trouble understanding your answers. Let me have a real person call you to help. Your reference is GF-XXXXXXXX."*
   - `unmapped-accident-type` → *"I haven't seen an accident quite like this one. Let me have a real person call you to help. Your reference is GF-XXXXXXXX."*

   All four: ref displayed prominently, no band, no more questions, no "continue anyway". Reference comes from `res.reference` (the engine includes it).

4. **Preview-engine stub** — add a slot-stage escalation path so this can be tested in preview mode.

**This is non-negotiable for the landing ship.** The landing's "Are you available outside NSW?" FAQ promises "one of our team will call you within the next business day" — if a non-NSW customer clicks through and the chat breaks, the landing's promise becomes a lie on first contact.

---

## Out of scope (do NOT build here)

- No new backend endpoints.
- No testimonials / reviews / star ratings (until real ones exist).
- No changes to `/crash`, `/dashboard`, or the API client beyond the slot-escalation type extension above.
- No new npm dependencies.
- No hero-image replacement (P0-2 from the earlier audit — separate creative decision).

---

*Spec prepared 2026-07-16. Grounded in the live site review + lib/config.ts + the CD-R3 legal posture + verified live API probes (state-scope escalation confirmed on https://claimdesk247-engine.vercel.app). Build target: lovable-ui/src/routes/index.tsx + __root.tsx footer + the slot-escalation prerequisite in intake.tsx/embed/intake.tsx/types.ts. Verifiable trust only. Backend contract answers (Q1-Q3) verified live 2026-07-16.*
