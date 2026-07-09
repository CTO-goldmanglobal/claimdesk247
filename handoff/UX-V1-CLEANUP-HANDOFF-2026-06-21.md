# UX v1 Audit Cleanup — Handoff & Deploy Steps

**Date:** 2026-06-21 17:05 UTC+10
**Author:** Cursor (Finn's session)
**Branch:** `fix/v1-ux-audit-cleanup` (1 commit ahead of `main`)
**Commit:** `10cf735` — fix(ux): v1 audit cleanup — operator name, stats, lang, staff nav, P0-3 PDF
**Audit ref:** `~/Deepconnet/clients/goldman-forge/ClaimDesk-UX-Audit-Report-2026-06-14.md`

---

## What's in this branch

### Closed fixes (6 items)

| # | Audit ID | Fix | Files |
|---|---|---|---|
| 1 | UX-13 | Operator name consistency — removed `author: "Goldman Forge Legal"`; now `ClaimDesk 247` | `src/routes/__root.tsx` |
| 2 | UX-11 | `lang="en"` → `lang="en-AU"` (both root HTML and SSR fallback error page) | `src/routes/__root.tsx`, `src/lib/error-page.ts` |
| 3 | UX-4 | "2 min" stat replaced with "~5 min · to complete your intake" | `src/routes/index.tsx` |
| 4 | UX-3 | "Data stays in Australia" → "Data hosted in Australia" (in two places); "No win, no worry" removed (PI-advertising) | `src/routes/__root.tsx`, `src/routes/index.tsx` |
| 5 | UX-12 | Staff sign-in moved from desktop nav + mobile nav into existing footer | `src/routes/__root.tsx`, `src/routes/index.tsx` |
| 6 | UX-10 | New "How ClaimDesk works" trust section added to home page | `src/routes/index.tsx` |

### Live customer-bug fix (P0-3 frontend)

| # | Issue | Fix | Files |
|---|---|---|---|
| 7 | P0-3 | Frontend `intake.tsx` `ResultPanel` decodes `pdf_base64` from classify response into a Blob URL; sets `download` attribute; falls back to URL-based download for back-compat | `src/routes/intake.tsx`, `src/lib/api/types.ts` |

**Engine side:** the matching `pdf_base64` field is already in production at
`https://claimdesk247-engine.vercel.app/healthz` → `api_version 0.2.5.1`. The
frontend change in this branch is the consumer side that was missing locally.

### Plumbing for future work

| # | Item | Files |
|---|---|---|
| 8 | `src/lib/config.ts` — D-8 firm-phone plumbing (`FIRM_PHONE`, `HAS_FIRM_PHONE`, `firmPhoneHref()`) | `src/lib/config.ts` |
| 9 | `lovable-ui/.gitignore` — added `.vercel/` (Nitro build output) and `.bun/` (Bun cache) | `.gitignore` |

### Regenerated (auto)

- `src/routeTree.gen.ts` — TanStack Start router codegen artifact

---

## Verification

```bash
cd ~/Smash repair Engine/lovable-ui
bunx tsc --noEmit          # → 0 errors
bunx vite build            # → ✓ built in 331ms, Nitro preset for Vercel
```

Manual grep checks (all clean):
- `grep -rn "Goldman" src/` → no hits
- `grep -rn "Data stays" src/` → no hits
- `grep -rn "No win" src/` → no hits
- `grep -rn "2 min" src/routes/` → no hits
- `grep -rn 'lang="en"' src/` → no hits (only `en-AU`)
- `grep -rn "Staff sign in" src/routes/` → only in `auth.tsx` and the footer (correct)

---

## What's NOT in this branch (gated / deferred)

| # | Item | Reason deferred |
|---|---|---|
| UX-2 | Consent / disclaimer placement on intake | SSR work needed |
| UX-5 | JS-only intake / slow first paint | SSR work needed |
| UX-6 | Save-and-resume | Backend state machine work needed |
| UX-7 | Photo upload + OCR | Storage pipeline needed |
| UX-8 | Callback SLA wording | Legal Head decision needed |
| UX-9 | Confirmation / reference / status tracking | Email/SMS + status page needed |
| UX-11 | Full a11y pass | Manual audit on rendered UI |

Tracked in `~/Deepconnet/clients/claimdesk-247/AI_TASKS.md` and the engagement's
`LOVABLE-NEXT-STEPS-2026-06-14.md`.

---

## Deploy path (user action required)

**Hard blockers before any `git push`:**

1. **Rotate the GitHub PAT** in `lovable-ui/.git/config`. Per `PAT-ROTATION-RUNBOOK.md`
   in this same folder, the current PAT is exposed in plaintext and must be rotated
   before any further push. This is a P0 security incident.

2. **Switch the active `gh` user.** Current user is `HermesGoldmanglobal`; the engagement
   requires `CTO-goldmanglobal`. Run:
   ```bash
   gh auth switch --user CTO-goldmanglobal
   ```

**After PAT rotation + `gh` switch:**

3. **Option A — PR flow (recommended for review):**
   ```bash
   cd ~/Smash repair Engine/lovable-ui
   git push -u origin fix/v1-ux-audit-cleanup
   ```
   Open the PR on GitHub; Vercel will spin up a preview deploy. Once approved, merge
   to `main` and Vercel will deploy to production.

4. **Option B — direct push (faster, no review):**
   ```bash
   cd ~/Smash repair Engine/lovable-ui
   git push origin main          # push the merge from main
   ```
   Or amend `144516e` directly — but this skips the PR review which is what the
   guardrail §7 prefers.

5. **Verify the deploy:**
   - Open `https://claimdesk247.com.au`
   - Hard-refresh (Cmd+Shift+R) to bypass cache
   - Check: home page no longer shows "2 min", "No win, no worry", or "Goldman Forge Legal"
   - Check: footer now has "Staff sign in" link
   - Check: `lang="en-AU"` (DevTools → Elements → `<html lang="en-AU">`)
   - For P0-3: complete a full intake and click "Download my summary (PDF)" — file
     should download directly without a 404

---

## File map (all changes local, untracked by remote)

```
modified:   .gitignore                                +6  (added .vercel/, .bun/)
modified:   src/lib/api/types.ts                      +8  (added pdf_base64?: string)
new file:   src/lib/config.ts                         +41 (FIRM_PHONE plumbing)
modified:   src/lib/error-page.ts                     +1  (lang="en-AU")
modified:   src/routeTree.gen.ts                      +10 (regenerated by router codegen)
modified:   src/routes/__root.tsx                     +51 (UX-11, UX-12, UX-13)
modified:   src/routes/index.tsx                      +128 (UX-3, UX-4, UX-10, UX-12)
modified:   src/routes/intake.tsx                     +42  (P0-3 frontend, error-state phone link)
```

276 insertions, 25 deletions across 8 files (plus 1 deleted file).

---

## What I did NOT touch (and why)

- **Engine (`~/Smash repair Engine/stage-*`)**: the P0-3 fix is already live in
  production (`api_version 0.2.5.1`). The other uncommitted engine work (T6 wiring,
  T-25-019, s7-s15 scenarios) is deferred per the prior session decision (Q1 1a).
- **Engine-t1 (`~/claimdesk247-engine-t1/`)**: marked archived + read-only with a
  `README.md` per Q3 3a. No changes.
- **Engagement docs (`~/Deepconnet/clients/claimdesk-247/*`)**: updated AI_CHANGELOG
  only. Did not touch PROJECT_BRIEF, AGENTS.md, AI_TASKS.md — those don't need
  updates for a UX cleanup.
- **Audit doc (`ClaimDesk-UX-Audit-Report-2026-06-14.md`)**: did not modify — the
  audit is a frozen report. Findings are tracked in `AI_TASKS.md` instead.

---

## If you want me to deploy for you

Per the guardrail §3 and §7, I cannot push (PAT + gh user are user actions). But I
*can*:

- Merge `fix/v1-ux-audit-cleanup` → `main` locally once you're ready
- Prepare a PR description for GitHub
- Draft a release-note for the Vercel deploy preview
- Run a full audit-doc reconciliation sweep if you want the v1 audit marked as
  "findings resolved" with reference to this commit

Say the word.