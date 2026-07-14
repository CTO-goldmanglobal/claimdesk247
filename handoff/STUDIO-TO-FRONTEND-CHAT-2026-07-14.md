# Handoff — Backend Chat → Frontend Chat (ClaimDesk 247)

**Date:** 2026-07-14
**From:** Backend infrastructure chat (Mac Studio, `cursor/founding-state-claimdesk247`, HEAD `9ed4ecf`)
**To:** Frontend / customer-facing chat (separate Cursor chat)
**Why:** User split the work — backend here, frontend there. Both streams to be reviewed by Fables + ChatGPT 5.6.

---

## ⚠️ Scope rule for the frontend chat

**Do NOT touch backend files.** Anything under `stage-3/`, `stage-2.5/app/`, `stage-4/app/`, or `stage-4/db/` is owned by the backend chat. Frontend work lives in `lovable-ui/` only (the submodule at `CTO-goldmanglobal/claimdesk247-76a0b7de`).

The submodule is its own git repo. When you commit frontend work:

```bash
cd lovable-ui
git add -A && git commit -m "..."
git push origin main          # submodule remote
cd ..
git add lovable-ui            # bump the submodule pointer in the parent
git commit -m "chore(submodule): bump lovable-ui for <reason>"
git push origin cursor/founding-state-claimdesk247
```

Always push the submodule FIRST, then bump the parent pointer. A parent commit pointing at an unpushed submodule SHA is the classic broken-submodule trap.

---

## Where the frontend lives

```
lovable-ui/
├── src/
│   ├── routes/
│   │   ├── __root.tsx           # shell + footer + <head> meta + error boundary
│   │   ├── index.tsx            # landing page (PD-first hero)
│   │   ├── intake.tsx           # main chat-style intake widget (the "robot")
│   │   ├── embed/intake.tsx     # embeddable variant (?embed=1)
│   │   ├── dashboard.tsx        # staff sign-in (legal_staff role → /api/brief)
│   │   ├── auth.tsx
│   │   └── sitemap[.]xml.ts
│   ├── components/
│   │   ├── BandBadge.tsx        # likely/possible/unclear/insufficient pill
│   │   ├── EvidenceUploader.tsx # multi-file upload UI (image-resize + xhr)
│   │   └── ui/                  # shadcn-style primitives
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts        # fetch wrapper, all endpoints, no PII in URLs
│   │   │   └── types.ts         # request/response shapes
│   │   ├── config.ts            # public runtime config (FIRM_PHONE, PANEL_SHOP_NAME)
│   │   ├── config.server.ts     # server-only secrets
│   │   ├── image-resize.ts      # client-side 1600px / JPEG q80 resize (~13×)
│   │   ├── preview-engine.ts    # stub for Vercel preview without backend
│   │   ├── supabase.ts
│   │   └── lovable-error-reporting.ts
│   ├── hooks/
│   ├── router.tsx, start.ts, server.ts
│   └── styles.css
├── public/
└── package.json                 # TanStack Start + Vite + shadcn + Tailwind 4
```

---

## What the frontend does today (as of `9ed4ecf`)

1. **Landing (`/`)** — PD-first hero: "Not at fault? We handle the whole recovery." NSW-focused (footer + copy). Hero CTA → `/intake`.
2. **Intake (`/intake`)** — chat-style widget. State machine: `loading → consent → question → classifying → result`. `?ref=<ref>` resumes a shared case. `?embed=1` strips chrome for iframing.
3. **Embed (`/embed/intake`)** — dedicated embed route (same component, embed layout).
4. **Evidence uploader** — appears after consent + classify. Resizes client-side (`image-resize.ts`), uploads via `uploadEvidence()` in `api/client.ts`.
5. **Dashboard (`/dashboard`)** — staff sign-in. Legal-staff role hits `/api/brief/:ref` (MFA-gated on the backend).
6. **Footer (`__root.tsx`)** — operator line: "Operated by ClaimDesk 247. Smash-repair services by {PANEL_SHOP_NAME}."

---

## What the backend just shipped (frontend may need to react)

These landed in the backend chat and may require frontend follow-up:

### 1. PD recovery disclosure (PD-COUNSEL-MEMO §3.3) — NEW endpoint

```http
GET /api/disclosure/property_damage?ref=<ref>
→ { claim_type: "property_damage", disclosure_text: "Important — please read…" }
```

- Backend fires `pd_disclosure_presented` audit on this call.
- When the user then grants consent, backend fires `pd_disclosure_acknowledged` as a sibling audit event.
- **Frontend gap:** the intake consent screen does NOT currently fetch + render this disclosure. The `consent` stage in `intake.tsx` shows a generic privacy blurb. For PD intakes, the disclosure text from `/api/disclosure/property_damage` must render above the consent button, scrollable-to-acknowledge.

### 2. Multi-state intake (national PD) — dropdown already expanded

Backend accepts `state_of_accident` ∈ {NSW, VIC, QLD, WA, SA, TAS, ACT, NT, outside_nsw}. Frontend motor/PD slot for state should offer the same list. Check `intake.tsx` renders the engine's enum verbatim (it usually does — the UI iterates `slot.options`).

### 3. Band emission in non-NSW states — already works

Backend now emits bands (e.g. `likely`) for clear rear-end in VIC/QLD/WA/etc. Frontend `BandBadge` already handles the enum. No change needed; verify after the next deploy.

### 4. Evidence endpoint — already integrated

`uploadEvidence`, `listEvidence`, `getCase` in `api/client.ts` are wired. `EvidenceUploader.tsx` uses them. No change needed unless UX polish is wanted.

---

## What the frontend chat should NOT need to do

- Any backend logic, rule tree, sign-off, audit, RLS, or SQL.
- Anything that emits a band, resolves a disclaimer, or stores PII.
- Anything that touches S3, Supabase, or the audit log directly.

If a frontend change seems to require a backend change, **stop and request it in the backend chat** — do not work around it client-side.

---

## Health check before frontend work

```bash
cd "/Volumes/Goldman Global/businesses/claimdesk247"

# 1. Sync (per two-machine rule)
gh auth status                                  # MUST be CTO-goldmanglobal
./scripts/sync-from-origin.sh

# 2. Backend green (proves the contract the frontend calls)
cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py    # 50/50 + 26 injury-ext
cd ../stage-2.5 && python3 tests/run_acceptance.py            # 26/26

# 3. Frontend typecheck + lint
cd ../lovable-ui
npm install                  # if node_modules missing
npx tsc --noEmit
npm run lint
```

If `tsc` or `lint` fails, fix in the frontend chat — do not push broken TypeScript.

---

## Open items the frontend chat should pick up

| # | Item | File |
|---|------|------|
| 1 | Render the PD disclosure (`GET /api/disclosure/property_damage`) above the consent button for PD intakes; gate the consent button on scroll-to-bottom or explicit ack | `src/routes/intake.tsx` (consent stage) |
| 2 | Verify the state dropdown reflects all 8 AU jurisdictions after the engine enum expanded | `src/routes/intake.tsx` |
| 3 | Verify the intake widget's `?ref=` share/resume path still works after the evidence + disclosure additions | `src/routes/intake.tsx` |
| 4 | Landing page is NSW-branded ("NSW road-rule trained") but the product is now national — Legal Head decision needed on whether to reframe copy state-by-state or stay NSW-led | `src/routes/index.tsx`, `__root.tsx` footer |
| 5 | `EvidenceUploader` UX polish (progress %, HEIC messaging, error states) | `src/components/EvidenceUploader.tsx` |
| 6 | Accessibility pass on the chat-style intake (keyboard nav, screen reader, focus traps) | `src/routes/intake.tsx` |

Item 1 is the load-bearing one — it's the legal-compliance gap the backend just exposed.

---

## Cross-chat coordination

- **Backend chat** owns: engine, API, rule trees, sign-off, evidence store, audit, RLS, retention.
- **Frontend chat** owns: `lovable-ui/` only.
- **Both chats** push to the same branch (`cursor/founding-state-claimdesk247`) — **always `./scripts/sync-from-origin.sh` before starting work** to avoid stepping on each other.
- **Review prompts:** Fables + ChatGPT 5.6 review prompts for both streams are in `handoff/REVIEW-PROMPTS-2026-07-14.md`.

---

*Prepared 2026-07-14 on Mac Studio. Frontend chat: start here, sync first, stay in `lovable-ui/`.*
