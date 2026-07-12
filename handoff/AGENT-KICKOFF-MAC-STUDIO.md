# Agent Kickoff Prompt — ClaimDesk 247 @ Mac Studio

> **How to use:** On the Mac Studio, open Cursor against the folder
> `/Volumes/Goldman Global/businesses/claimdesk247`. Start a **new chat**.
> Copy the prompt block below (between the `---` lines) and paste it as your
> first message. Do NOT add anything before it — it's self-contained.

---

You are a fresh Cursor agent starting work on the **ClaimDesk 247** project on a **Mac Studio**. You have zero prior conversation context — this message is your entire onboarding. Read it fully before doing anything.

## 0. Read these FIRST (in this order), then act

1. `/Users/finn/goldmanglobal/PROJECT_GUARDRAIL.md` — practice-wide isolation rules. CRITICAL: this Mac Studio runs **3 businesses** (ClaimDesk 247 + 2 others). One wrong push leaks one client's data into another client's product. Read it before touching any file.
2. This repo's `handoff/TWO-MACHINE-SETUP-2026-07-09.md` — how this Mac Studio fits in the two-machine workflow (Air + Studio).
3. This repo's `handoff/PROJECT-SUMMARY-FOR-OPUS.md` and the top of `stage-4/sign-off-package/00-INDEX.md` — current project state.

## 1. Where you are (canonical truth — overrides any stale doc)

- **Working tree:** `/Volumes/Goldman Global/businesses/claimdesk247`
- **GitHub repo:** `CTO-goldmanglobal/claimdesk247` (the monorepo — engine + API + sign-off pack + frontend as a submodule)
- **Frontend submodule:** `lovable-ui/` → `CTO-goldmanglobal/claimdesk247-76a0b7de` (PRIVATE)
- **GitHub account for ALL ClaimDesk work:** `CTO-goldmanglobal`
- **Git author identity:** `CTO Goldman Global <cto@goldmanglobal.com.au>` (global, already set)
- **Branch:** `cursor/founding-state-claimdesk247`

> ⚠️ **STALE-DOC WARNING:** `PROJECT_GUARDRAIL.md` §2 and §12.1 still say ClaimDesk lives at `~/claimdesk247-engine-t1/` pushing to `CTO-goldmanglobal/claimdesk247-engine`. **That is OUT OF DATE.** `claimdesk247-engine` is a stale June 19 snapshot (archived in spirit, not on GitHub). The canonical repo is now `CTO-goldmanglobal/claimdesk247` (this repo). Trust this section, not the guardrail's location table.

## 2. The current project state (as of 2026-07-12)

ClaimDesk 247 is a **4-claim-type legal-engine product** (motor / property_damage / public_liability / medical_negligence) with a hash-bound sign-off gate.

- **Sign-off gate is CLOSED** — all 4 rule trees are signed (2026-07-05, Legal Head provisional approval). The engine **emits bands** (e.g. PD rear-end with user in front → `band=likely`). Verify with `python3 stage-4/scripts/sign_rule_trees.py --verify`.
- **Tests green:** 50/50 motor + 17/17 injury-extension + 19/19 stage-2.5 = 86/86.
- **Property Damage (PD) is the strategic beachhead** — Lane 1 (property damage), outside the claim-farming ban, no law firm required. The home page leads with "Not at fault? We handle the whole recovery."
- **Provisional caveat:** sign-off authorises staging/internal validation only. Before commercial deployment: PD counsel memo (agent licensing + ACL/CHOICE + fees), CD-R2 redo per tree, formal UX-level closure.

## 3. The two-machine rule (Air ↔ Studio)

This repo is worked on **two machines**: a MacBook Air and this Mac Studio, synced via git.

- **Before you start work:** `git pull --rebase && git submodule update --recursive`
- **Before you finish/switch:** commit + push. Uncommitted work does NOT travel.
- **Never edit the same branch on both machines simultaneously.**
- Paperclip runs on this Studio as the governance/orchestration layer (agent heartbeats). The Air does hands-on coding.

## 4. Before ANY `git push` (the guardrail checklist)

The Studio runs 3 businesses → verify identity every single push:
```bash
cd "/Volumes/Goldman Global/businesses/claimdesk247"
gh auth status                 # active account MUST be CTO-goldmanglobal
git remote -v                  # MUST point at CTO-goldmanglobal/claimdesk247
git branch --show-current      # cursor/founding-state-claimdesk247
git status                     # clean, or diff is exactly what you expect
```
If `gh auth status` shows a different active account, run `gh auth switch -u CTO-goldmanglobal` before pushing. Never push with the wrong account — it routes to the wrong repo/brand.

## 5. First action — verify the Studio is healthy

Run this and report the output. If any line is not green, STOP and tell me before doing anything else:
```bash
cd "/Volumes/Goldman Global/businesses/claimdesk247"
git submodule status                              # expect: 5bd99d4... lovable-ui (no leading '-')
cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py    # expect: 50/50 + 17/17
cd ../stage-2.5 && PYTHONPATH=. python3 tests/run_acceptance.py # expect: 19/19
cd .. && python3 stage-4/scripts/sign_rule_trees.py --verify   # expect: all 4 trees live
```
If `fastapi` / deps are missing: `python3 -m pip install --user -r requirements-dev.txt`.

## 6. What I (the user) want you to do first

[USER: delete this line and put your first task here. If you don't have one yet, the agent will just verify health and wait.]

---

*End of kickoff. Read guardrail → read handoff docs → verify health → confirm before acting.*
