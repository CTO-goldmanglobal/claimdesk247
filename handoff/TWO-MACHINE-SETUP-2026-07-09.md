# Two-Machine Setup — ClaimDesk 247 (MacBook Air + Mac Studio)

**Created:** 2026-07-09
**Purpose:** Run the same Cursor workspace on a MacBook Air (hands-on coding) and a Mac Studio (Paperclip governance + heavier runs), kept in sync over Tailscale + git.
**Target path on Mac Studio:** `/Volumes/Goldman Global/businesses/claimdesk247`

---

## 0. Architecture (the 30-second version)

```
   GitHub (origin) ──────────────────────────────────── single source of truth
        ▲                                   ▲
        │ git push                          │ git push / pull
        │                                   │
  MacBook Air                         Mac Studio
  ~/Smash repair Engine/              /Volumes/Goldman Global/businesses/claimdesk247/
  - hands-on coding                   - Paperclip agent heartbeats (governance)
  - Cursor agent                      - Cursor agent (same workspace, heavier jobs)
  - git sync                          - long test runs, audits, sign-off tooling
        │                                   │
        └────────── Tailscale ──────────────┘
                  (machine-to-machine, not for git)
```

**Git is the sync mechanism. Paperclip is the governance layer. Tailscale is the network.** They are three separate concerns — don't try to make git do governance, or Tailscale do sync.

- **Git** keeps the *code* identical on both machines. Push on one, pull on the other. Always commit before switching machines.
- **Paperclip** assigns and tracks *work* (tasks, approvals, heartbeats). It lives on the Mac Studio by default. The MacBook Air can see the same Paperclip company but doesn't need an agent running.
- **Tailscale** lets the two machines reach each other (SSH, file share, Paperclip local adapter, `cursor://` handoffs). It is **not** a substitute for committing — if you edit on the Air and want it on the Studio, push to git, don't drag files over Tailscale.

---

## 1. First-time setup on the Mac Studio

### 1.1 Prerequisites

```bash
# On the Mac Studio, check you have:
xcode-select -p            # Command Line Tools (git)
which cursor               # Cursor IDE
which node && node -v      # for Paperclip CLI (npx)
which python3              # for the engine + sign-off tooling
which brew                 # for installing anything missing
```

Install what's missing:
```bash
xcode-select --install                          # if git is missing
brew install node python git-lfs                # if node/python missing
# Cursor: download from cursor.com
```

### 1.2 Authenticate git + gh (same identity as the Air)

The repos live under `CTO-goldmanglobal`. Use the **same** GitHub identity on both machines so commits attribute correctly.

```bash
# gh CLI login (follow the browser prompt) — use the CTO-goldmanglobal account
gh auth login
# verify
gh auth status

# set your git identity if not already global
git config --global user.name  "CTO Goldman Global"
git config --global user.email "cto@goldmanglobal.com.au"
```

### 1.3 Create the target folder + clone (recursive, for the submodule)

```bash
# Create the parent structure
mkdir -p "/Volumes/Goldman Global/businesses"
cd "/Volumes/Goldman Global/businesses"

# Clone WITH --recursive so lovable-ui (the submodule) comes with it
git clone --recursive \
  https://github.com/CTO-goldmanglobal/claimdesk247.git \
  claimdesk247

cd claimdesk247

# Verify the submodule landed
git submodule status
# Expect: 5bd99d4... lovable-ui  (no leading '-' if initialized)
```

> If you forget `--recursive`, run this inside the clone:
> ```bash
> git submodule update --init --recursive
> ```

### 1.4 Verify the engine is healthy on the Studio

```bash
cd "/Volumes/Goldman Global/businesses/claimdesk247"

# Run the full suite — should be 86/86 green with signed trees
cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py
# Expect: TOTAL: 50  PASS: 50  FAIL: 0
#         [injury-extension] TOTAL: 17  PASS: 17  FAIL: 0

cd ../stage-2.5 && PYTHONPATH=. python3 tests/run_acceptance.py
# Expect: TOTAL: 19  PASS: 19  FAIL: 0

# Confirm the sign-off gate is closed (all 4 trees live)
cd .. && python3 stage-4/scripts/sign_rule_trees.py --verify
# Expect: [OK] for all four trees; "All trees live"
```

If these don't pass on a fresh clone, **stop** — something diverged and you don't want to build on top of it.

### 1.5 Install Paperclip

Paperclip runs on the Studio as the governance layer. It is **not** installed on the repos — it runs as a service/CLI that points at your workspace.

```bash
# Install the Paperclip CLI (npm global)
npm install -g paperclipai

# Verify
paperclipai --version

# Authenticate / set up your company
paperclipai login   # or follow the onboarding flow for your company
```

Then configure Paperclip to point at this workspace:
- **Company:** your existing Paperclip company (same one the Air can see via the API)
- **Project cwd:** `/Volumes/Goldman Global/businesses/claimdesk247`
- **repoUrl:** `https://github.com/CTO-goldmanglobal/claimdesk247.git`

This can be done via the Paperclip API (see the Paperclip skill's "Project Setup Workflow") or through the Paperclip dashboard. The agent heartbeats will then run on the Studio, reading/writing that folder.

> The agent's `PAPERCLIP_*` env vars are auto-injected by Paperclip during heartbeats — you don't set them manually in your shell.

### 1.6 Open in Cursor

```bash
cd "/Volumes/Goldman Global/businesses/claimdesk247"
cursor .
```

Cursor will pick up the same workspace structure. Cursor settings, MCP servers, and skills are user-level (`~/.cursor/`) so they carry across machines automatically — **except** MCP servers that bind to absolute paths or local processes. Check those (see §4).

---

## 2. The daily two-machine workflow

### Rule 1: commit before you switch machines

Before closing the lid on the Air, or walking away from the Studio:

```bash
# on the machine you're leaving
git add -A && git commit -m "wip: <what>"
git push
```

Uncommitted work does **not** travel. Tailscale file-copy of a dirty working tree is a recipe for merge hell.

### Rule 2: pull before you start on the other machine

```bash
# on the machine you're starting on
git pull --rebase
git submodule update --recursive   # in case lovable-ui moved
```

### Rule 3: one branch at a time per concern

Don't edit the same branch on both machines simultaneously. If the Air is on `cursor/founding-state-claimdesk247`, the Studio should either be on the same branch (and pulling) or on a different branch for a different task.

### Typical day

| Time | Machine | Action |
|------|---------|--------|
| AM | Air | `git pull`, code a feature, commit, push |
| PM | Studio | `git pull`, run the full suite (heavier box), sign-off verification, push any doc updates |
| Night | Studio | Paperclip heartbeat runs against the synced tree |

---

## 3. Tailscale setup (machine-to-machine reachability)

Tailscale is for **reaching** the other machine, not for syncing code.

### 3.1 Install + auth on both machines

```bash
# Install (Mac App Store, or):
brew install --cask tailscale

# Sign in to the same Tailscale tailnet on BOTH machines
# (System Settings → Tailscale, or `tailscale up`)
```

### 3.2 Verify they can see each other

```bash
# On the Air, find the Studio's Tailscale IP/hostname
tailscale status
# Look for the Mac Studio's hostname (e.g. mac-studio.tail-scale.ts.net)

# Test SSH (enable Remote Login on the Studio: System Settings → General → Sharing)
ssh finn@mac-studio
```

### 3.3 What Tailscale is good for here

- **SSH** from Air to Studio to kick off a long test run remotely.
- **Screen sharing** to the Studio from the Air (via VNC over Tailscale).
- **Paperclip local adapter** if the Air needs to talk to a Paperclip process on the Studio.
- **`cursor://` handoffs** — start a Cursor session on the Studio from the Air.

### 3.4 What Tailscale is NOT for

- **Syncing code.** Use git. Copying files over Tailscale bypasses the audit trail and creates divergence.
- **Backing up.** Git + GitHub is the backup.

---

## 4. MCP servers + skills — the cross-machine gotcha

Cursor user-level config lives in `~/.cursor/` and syncs via your Cursor account/settings-sync. But some MCP servers bind to absolute paths or local processes and need re-checking on the Studio:

| MCP server | Air setup | Studio action |
|------------|-----------|---------------|
| `cursor-app-control` | bundled | auto (Cursor-managed) |
| `cursor-ide-browser` | bundled | auto |
| `plugin-supabase-supabase` | project-scoped | re-auth on Studio (Supabase project ref + keys) |
| `plugin-exa-exa` | bundled | auto |
| Paperclip local adapter (if used) | n/a | set up on Studio, point at its workspace cwd |

After first launch on the Studio, open Cursor Settings → MCP and confirm each server is connected. Re-auth Supabase there (the project is the same, but the local credential is per-machine).

---

## 5. Paperclip + Cursor: how they coexist

You said: *"air and studio work at git repo, both know the infrastructure, can do work thru tailscale."* — so Paperclip runs on the Studio as the orchestration/governance layer, and both machines work the git repo.

- **Studio (Paperclip host):** agent heartbeats wake up, check the Paperclip inbox, checkout tasks, do work in the `/Volumes/.../claimdesk247` tree, commit, update task status.
- **Air (coding seat):** you run Cursor directly, pull, code, push. You can see Paperclip state via the dashboard or API, but no heartbeat agent needs to run here.
- **If you want the Air to also run a Paperclip agent:** it can — just point its adapter cwd at `~/Smash repair Engine/`. Both machines share the same company; Paperclip handles checkout conflicts (a task checked out on one machine returns 409 on the other — see the Paperclip skill's "Never retry a 409").

### Commit co-authoring (Paperclip rule)

If a commit is made during a Paperclip heartbeat, the Paperclip skill requires this trailer:

```
Co-Authored-By: Paperclip <noreply@paperclip.ing>
```

Add it to any commit made by a Paperclip-agent run. Commits you make manually at the keyboard don't need it.

---

## 6. Folder mapping (reference)

| Concern | MacBook Air | Mac Studio |
|---------|-------------|------------|
| Engine + API + frontend | `~/Smash repair Engine/` | `/Volumes/Goldman Global/businesses/claimdesk247/` |
| Frontend (submodule) | `~/Smash repair Engine/lovable-ui/` | `/Volumes/Goldman Global/businesses/claimdesk247/lovable-ui/` |
| Cursor user config | `~/.cursor/` | `~/.cursor/` (same structure) |
| Engagement docs | `~/Deepconnet/clients/claimdesk-247/` | (optional) clone or symlink — see note below |
| Paperclip | (optional, view only) | installed + running |

> **Engagement docs note:** `~/Deepconnet/clients/claimdesk-247/` holds the audit/handoff/changelog markdown that lives *outside* the engine repo. To mirror it on the Studio, either (a) git-init that folder as its own repo, or (b) periodically copy it over Tailscale. It is NOT in the engine repo by design (PROJECT_GUARDRAIL isolation).

---

## 7. Verification checklist (run on the Studio after setup)

```bash
cd "/Volumes/Goldman Global/businesses/claimdesk247"

# 1. Clean clone, right branch
git status                    # clean working tree
git branch --show-current     # cursor/founding-state-claimdesk247

# 2. Submodule healthy
git submodule status          # 5bd99d4... lovable-ui (no leading '-')

# 3. Engine green
cd stage-3 && PYTHONPATH=. python3 tests/run_acceptance.py   # 50/50 + 17/17
cd ../stage-2.5 && PYTHONPATH=. python3 tests/run_acceptance.py  # 19/19

# 4. Sign-off gate closed
cd .. && python3 stage-4/scripts/sign_rule_trees.py --verify  # all 4 live

# 5. Frontend builds
cd lovable-ui && bunx tsc --noEmit                            # clean

# 6. Paperclip reachable
paperclipai agent local-cli <agent-shortname> --company-id <id>  # prints env vars

# 7. Tailscale sees the Air
tailscale status | grep -i air
```

All seven green = the Studio is ready.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `git submodule status` shows `-` prefix | submodule not initialized | `git submodule update --init --recursive` |
| Tests fail on Studio but pass on Air | working tree not in sync | `git pull --rebase && git submodule update --recursive` |
| `git push` rejected (non-fast-forward) | the other machine pushed first | `git pull --rebase` then push |
| Paperclip heartbeat can't find workspace | adapter cwd wrong | point at `/Volumes/Goldman Global/businesses/claimdesk247` |
| Cursor MCP servers missing on Studio | user-config didn't sync, or path-bound | Settings → MCP, re-auth Supabase |
| `sign_rule_trees.py --verify` reports stale | someone edited a rule tree JSON without re-signing | re-run `sign_rule_trees.py --all --by "..." --date ...` |
| Can't reach Studio from Air | Tailscale off on one side | both machines: `tailscale up` |

---

## 9. Open items before the Studio is fully live

- [ ] **Push the 4 pending commits** to `origin/cursor/founding-state-claimdesk247` (done once `gh` is switched to CTO-goldmanglobal — see chat).
- [ ] **PAT rotation** — the `lovable-ui` remote still embeds a plaintext GitHub PAT in `.git/config`. On the Studio, prefer the `gh`-managed credential helper instead of re-embedding the PAT. (Carryover from the security audit, C-1.)
- [ ] **Decide Paperclip company/project** — confirm which Paperclip company the Studio joins and create the project workspace entry pointing at the Studio cwd.
- [ ] **Mirror or repo the engagement docs** (`~/Deepconnet/clients/claimdesk-247/`) if you want them on the Studio too.

---

*Prepared 2026-07-09. Both machines share one git remote; Paperclip governs work; Tailscale connects machines. Commit before you switch, pull before you start.*
