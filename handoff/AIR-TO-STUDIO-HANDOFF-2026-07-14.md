# Handoff Note — MacBook Air → Mac Studio

**Date:** 2026-07-14
**From:** MacBook Air (`~/Smash repair Engine/`)
**To:** Mac Studio (`/Volumes/Goldman Global/businesses/claimdesk247/`)
**Branch:** `cursor/founding-state-claimdesk247`
**Reason:** Continue ClaimDesk 247 work on the Studio.

---

## ⚠️ CRITICAL — read this first

**At the moment this note was written, today's work on the Air was UNCOMMITTED.**
If you are reading this on the Studio and `git pull` brought it across, then the work
**was committed and pushed** — proceed normally. If the new files below are NOT present
after your pull, the work has not been pushed yet and you are looking at a stale tree —
**stop and check with Finn before doing anything**.

---

## What was built today (2026-07-14) — full inventory

### 1. Brand change — CR-6-01 operator resolution

Operating entity for `claimdesk247.com.au` resolved to **ClaimDesk 247**.
Goldman Global Financial Pty Ltd is **not** the operator. Smash-repair partner for
the launch case is **Petersham Prestige Smash Repairs**.

- `stage-3/app/config.py` — `{{FIRM_NAME}}` and new `{{OPERATOR_NAME}}` token → "ClaimDesk 247"; new `{{PANEL_SHOP_NAME}}` token → "Petersham Prestige Smash Repairs"
- `lovable-ui/src/routes/__root.tsx` — footer carries compliant operator line
- `lovable-ui/src/lib/config.ts` — `PANEL_SHOP_NAME` exported, reads `VITE_PANEL_SHOP_NAME`

### 2. "ClaimDesk robot" — `/intake` widget + photo upload + S3 storage

- `lovable-ui/src/routes/intake.tsx` — chat-style re-skin, `?ref=` shareable, `?embed=1` widget mode
- `lovable-ui/src/routes/embed/intake.tsx` — dedicated embeddable route
- `lovable-ui/src/components/EvidenceUploader.tsx` — multi-file upload UI
- `lovable-ui/src/lib/image-resize.ts` — client-side 1600px / JPEG q80 resize (~13× smaller)
- `lovable-ui/src/lib/api/{client,types}.ts` — session/evidence/case API client + types
- `stage-2.5/app/wrap.py` — `POST/GET /api/intake/{ref}/evidence`, `GET /api/case/{ref}`, consent gate, audit log
- `stage-4/app/evidence_store.py` — `S3EvidenceStore` (primary, lazy boto3) + `InMemoryEvidenceStore` (tests/dev)
- `stage-4/db/0004_evidence_metadata.sql` — `case_evidence` table + RLS
- `stage-4/scripts/apply_evidence_lifecycle.py` — opt-in S3 lifecycle setter (Standard → Glacier @ 90d)
- `engine-deploy/requirements.txt` — `boto3>=1.34` added
- `.env.example` — full env-var template

### 3. Legal / compliance docs (4 new)

- `stage-4/legal/CD-R2-public-liability-2026-07-14.md`
- `stage-4/legal/CD-R2-medical-negligence-2026-07-14.md`
- `stage-4/legal/CD-R2-property-damage-2026-07-14.md` — **GO**
- `stage-4/legal/PD-COUNSEL-MEMO-2026-07-14.md` — PD commercially deployable in NSW subject to 3 gates
- `stage-4/legal/EVIDENCE-UPLOAD-DESIGN-2026-07-14.md` — design doc (why S3 not Drive/Supabase)
- `stage-4/EVIDENCE-STORAGE-SETUP.md` — AWS bucket + IAM + lifecycle runbook

### 4. Tests

- `stage-2.5/tests/run_acceptance.py` — 4 new evidence tests (T-25-020..023)
- `stage-2.5/acceptance-tests.stage25.yaml` — 4 new entries + `G-EV` gate
- **Full suite green: 99/99** (stage-3 50 + injury-ext 26 + stage-2.5 23)
- All 11 rule trees still live (`sign_rule_trees.py --verify`)

---

## What is NOT done — carryover for the Studio

### A. Commit + push (if not already done)

If this note's work is not yet on origin, on the Air run:

```bash
gh auth switch -u CTO-goldmanglobal          # resolve the logged-out state
cd "/Users/finn/Smash repair Engine"

# submodule first
cd lovable-ui && git add -A && git commit -m "feat(ui): chat-style intake widget, embed mode, evidence uploader, ClaimDesk 247 branding" && git push origin main && cd ..

# then main repo
git add -A && git commit -m "feat(pd+evidence): ClaimDesk 247 operator branding, photo upload to S3 Sydney, PD counsel memo + CD-R2 analyses" && git push origin cursor/founding-state-claimdesk247
```

### B. Manual AWS setup (Finn only — can't be done by an agent)

Follow `stage-4/EVIDENCE-STORAGE-SETUP.md` end-to-end:

1. Create bucket `claimdesk247-evidence-prod` in **`ap-southeast-2`** (Sydney), block-all-public-access, SSE-KMS
2. Create IAM user `claimdesk247-evidence-engine` with least-privilege policy (scoped to that one bucket)
3. Run `stage-4/db/0004_evidence_metadata.sql` in the Supabase SQL editor (order: 0002 → 0003 → 0004)
4. Apply lifecycle: `python3 stage-4/scripts/apply_evidence_lifecycle.py`
5. (Prod) Create a KMS Customer Managed Key, set `EVIDENCE_KMS_KEY_ID`
6. Add env vars to **Vercel** (Production + Preview): `EVIDENCE_BUCKET_NAME`, `EVIDENCE_S3_REGION=ap-southeast-2`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION=ap-southeast-2`, optional `EVIDENCE_KMS_KEY_ID`, `EVIDENCE_MAX_FILE_MB=10`, `EVIDENCE_MAX_FILES_PER_CASE=20`, `EVIDENCE_SIGNED_URL_TTL=900`
7. Run the §7 end-to-end verify curls

### C. Legal Head decisions (from PD counsel memo §6)

| # | Decision | Section |
|---|---|---|
| 1 | Approve the §3.2 disclosure text (or revise) | counsel memo §3.4 |
| 2 | Pick a fee structure: fixed / % of recovery / hybrid (per-lead PROHIBITED) | counsel memo §4.4 |
| 3 | Confirm §2.3 legal-practice boundary for future demand-letter product | counsel memo §2.3 |
| 4 | VIC/WA/SA/NT debt-collection licensing verify items — engage state counsel | counsel memo §2.2 |
| 5 | QLD OFT position — resolve before QLD commercial launch | counsel memo §2.2 |

### D. Engineering follow-ups (flagged, not built)

- **Wire the PD disclosure text into the consent gate** + timestamp disclosure-presented and disclosure-acknowledged events in the audit log (counsel memo §3.3)
- **Retention scheduler** — `EvidenceStore.delete_for_retention()` exists but no scheduled job calls it (needs EventBridge cron)
- **S3 Object Lock** — recommended in design doc for stronger immutability, not enabled (must be set at bucket creation)
- **HEIC resizing** — only Safari resizes client-side; other browsers pass HEIC through (server validates + stores)

### E. Security carryover (older)

- **Revoke old GitHub PAT** (`github_pat_11CDGMEAQ0…`) server-side on GitHub — it was stripped locally but is still live
- **Archive stale `claimdesk247-engine` repo** — user decided to archive, not yet executed
- **Delete `~/.git-credentials.purged-backup-2026-07-10`** once osxkeychain confidence is established

---

## Mac Studio first-actions checklist

When you sit down at the Studio:

```bash
cd "/Volumes/Goldman Global/businesses/claimdesk247"

# 1. Identity guard — must be CTO-goldmanglobal (3-business Mac)
gh auth status

# 2. Pull the latest (rebases, syncs submodule, checks identity)
./scripts/sync-from-origin.sh

# 3. Verify the work landed
git log -3 --oneline
ls stage-4/legal/PD-COUNSEL-MEMO-2026-07-14.md   # should exist
ls stage-4/app/evidence_store.py                  # should exist

# 4. Health check
cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py   # 50/50 + 26 injury-ext
cd ../stage-2.5 && PYTHONPATH=. python3 tests/run_acceptance.py  # 23/23
cd .. && python3 stage-4/scripts/sign_rule_trees.py --verify    # all trees live

# 5. Frontend typecheck
cd lovable-ui && npx tsc --noEmit
```

If any of step 3's `ls` fails → the work wasn't pushed from the Air. **Stop and check with Finn.**
If step 1 shows the wrong gh account → **stop**, do NOT switch accounts autonomously, ask Finn.
If step 2 reports divergence → **stop**, show Finn the divergence, do NOT auto-resolve.

---

## The hybrid / real-case context

This is the framing Finn gave today:

- **Operating entity:** ClaimDesk 247
- **Smash-repair partner (launch case):** Petersham Prestige Smash Repairs
- **Real car-accident case** is flowing through the smash repair right now, used as the
  implementation/test vector for the website.
- Because a **real customer's PII** is in scope, the privacy notice / retention / consent
  gates are no longer theoretical — they must be correct for this person. The AWS Sydney
  storage choice (not Google Drive, not Mac Studio local) was made specifically to keep
  the AU-storage + immutability promises the privacy notice makes.

Keep this context front-of-mind: any change that touches PII handling must clear the
consent gate, write to the audit log, and stay in the Sydney region.

---

*Prepared 2026-07-14 on MacBook Air. Carry this note to the Studio.*
