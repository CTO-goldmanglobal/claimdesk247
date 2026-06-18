# CTO Action — PAT history for the workspace brand tree

**Status:** Resolved 2026-06-18 by issuing a new fine-grained PAT.

## What happened

The original CTO Personal Access Token was scoped to only `CTO-goldmanglobal/claimdesk247-engine`. Pushing the workspace brand tree to `CTO-goldmanglobal/claimdesk247` returned HTTP 403 even though the API reported `push: true` permission on the repo — the fine-grained PAT's per-repository access list did not include the brand repo.

A new PAT was generated and used to push the workspace brand tree. The new PAT is embedded in the workspace's `.git/config` (same pattern as the engine repo). The actual PAT value is intentionally NOT recorded in this file or in any git-tracked artifact — PATs in commits trigger GitHub secret scanning and create an incident.

## Recommended follow-up (CTO)

1. **Rotate the new PAT before it expires** (the new PAT was created 2026-06-18 with a 30-day window, expiring ~2026-07-18). Best practice: store in `~/.git-credentials` only (file mode 0600), not in `.git/config` URL rewrites.

2. **Audit the new PAT's scope on github.com:**
   - https://github.com/settings/tokens?type=beta
   - Confirm "Repository access" includes both `claimdesk247-engine` AND `claimdesk247` (or "All repositories")
   - Confirm "Permissions → Contents" is **"Read and write"** (not "Read only")

3. **If the new PAT ever appeared in chat, a commit, or a config file: rotate immediately.** The first push of the workspace brand tree included a commit that contained a literal PAT string in this very file — GitHub's secret-scanning blocked the second push and the PAT should now be considered compromised. A new PAT was issued and used for subsequent work.

4. **Update the engine repo's `.git/config`** to use the latest PAT instead of the old one, so both repos route through the same credential.

## Why the original push failed even with valid scopes

Fine-grained PATs on github.com have **two independent gates**:
- **Repository access** — which repos this token can interact with.
- **Permissions** — what actions (`Contents: read` vs `Contents: read+write`).

The API endpoint `/repos/{owner}/{repo}` checks **repository access** and reports `permissions: push: true` based on the user's role on that repo. The git daemon (which serves `git push` over HTTPS) checks **permissions** at the PAT level. If `Contents` on the PAT is `read-only`, the push is rejected with 403, even though the API claims push is allowed.

The original CTO PAT had `Repository access: claimdesk247-engine only`, so even adding `claimdesk247` to its access list would not have made push work — `Contents` would also need to be `read+write`.

## Diagnostic commands (use to verify any PAT before relying on it)

```bash
# 1. Check what user the PAT authenticates as:
curl -sS -H "Authorization: token <PAT>" https://api.github.com/user \
  | grep '"login"'

# 2. Check if the PAT can read the target repo:
curl -sS -H "Authorization: token <PAT>" \
  https://api.github.com/repos/CTO-goldmanglobal/claimdesk247 \
  | grep '"id"' | head -1

# 3. Try a test clone (clone is a stricter check than API read):
git clone --depth 1 \
  https://x-access-token:<PAT>@github.com/CTO-goldmanglobal/claimdesk247.git \
  /tmp/test-clone
# If this succeeds, the PAT can read. Push may still fail if Contents=read-only.

# 4. The actual test for push:
git push https://x-access-token:<PAT>@github.com/CTO-goldmanglobal/claimdesk247.git \
  HEAD:refs/heads/test-push-probe
# Success = PAT has Contents: read+write AND repo access. Otherwise 403.
```

## Lessons learned (incident notes)

- **Never paste a PAT into chat or commit it to a tracked file.** GitHub's secret scanning will block the push AND the PAT is already in the git object database even if the push is later rewritten.
- **Fine-grained PATs require two independent permissions** (repository access + action permission). API and git daemon enforce them differently.
- **For local git operations requiring a PAT, prefer `~/.git-credentials` (file mode 0600) over `.git/config` URL rewrites.** The latter makes the PAT visible in any tool that dumps git config.
- **Never `cat` or `head` a credential file from inside a build seat.** Even if the file is in a "safe" location like `~/.git-credentials`, the build seat's output flows into the chat transcript. The 2026-06-18 incident below is a direct consequence of this rule being broken.

## Incident 3 — 2026-06-18 ~11:00 AEST: build seat `cat` of `~/.git-credentials`

### What happened

While verifying the freshly-stored new PAT, the build seat ran `cat ~/.git-credentials` to confirm the file contents. The file contained two distinct PATs on three lines (see "What was actually in the file" below). The PAT values landed in the chat transcript. **Both PATs are now considered compromised and require rotation.**

### What was actually in the file

The user had pasted the new PAT into `~/.git-credentials`, but the file also contained:
1. A pre-existing `https://CTO-goldmanglobal:<OLD_PAT>@github.com/CTO-goldmanglobal/claimdesk247.git` line (path-suffixed — git's credential helper doesn't expect paths)
2. A pre-existing `https://CTO-goldmanglobal:<OLD_PAT>@github.com/CTO-goldmanglobal/claimdesk247-engine.git` line (also path-suffixed)
3. The new line the user had just pasted: `github_pat_<NEW_PAT>` (missing the `https://<user>:<pat>@host` wrapper — not a valid credential line)

**Root cause:** the file had not been wiped before the new PAT was pasted. The malformed lines came from previous testing / forgotten scratch work.

### Containment (done)

- File was wiped: `> ~/.git-credentials` and re-created with a single placeholder line in the correct format: `https://x-access-token:REPLACE_ME_ON_NEXT_ROTATION@github.com`
- File mode confirmed: `0600`
- A short-lived backup (`~/.git-credentials.bad-2026-06-18`) was created and then `rm`'d immediately, to avoid leaving a second copy of the leaked PATs on disk
- Both repos' `.git/config` URL-rewrite blocks (which also embedded PATs) were removed. `git remote -v` is now clean in both repos.
- See `handoff/PAT-STORAGE-HOWTO.md` (engine repo) for the correct procedure.

### Recovery (for the CTO)

1. **Rotate the new PAT** on github.com — even though the placeholder is in the file now, the actual PAT that was in there is compromised. Generate a fresh one.
2. **Edit `~/.git-credentials`** with the new PAT. The file should contain **exactly one line** in this format:
   ```
   https://x-access-token:<NEW_PAT>@github.com
   ```
3. **Do not paste the new PAT in chat.** Use `nano ~/.git-credentials` in a Terminal outside Cursor.
4. **Verify** by running `git fetch origin` in either repo. The fetch should succeed with no prompt.

### Prevention (rule going forward)

- The build seat will never again `cat`, `head`, `tail`, `less`, or otherwise read a credential file. Verification will be done by attempting a fetch and reading the exit code, or by parsing a redacted form of the file via `sed -E 's|github_pat_[A-Za-z0-9_]+|github_pat_<REDACTED>|g'`.
- The CTO will paste new PATs directly into `nano ~/.git-credentials` from a Terminal outside Cursor, never from the chat input box.
- This incident has been added to the audit log; the audit log will be reviewed at the next integration audit cycle.

### Cross-references

- `handoff/PAT-STORAGE-HOWTO.md` (engine repo) — the correct procedure
- `handoff/INTEGRATION-AUDIT-2026-06-18.md` (P0 #3) — the original PAT-scope blocker
- `handoff/CEO-REPORT-INTEGRATION-2026-06-18.md` — CEO summary of the broader incident

---

## Incident 3 RESOLVED — 2026-06-18 ~11:45 AEST: actual root cause was stale macOS keychain entries

### The actual cause (NOT what the file content looked like)

After incident 3 was filed, attempts to push the doc with the new PAT kept returning 403 even though:
- The new PAT's API permissions were confirmed as `push: True, admin: True` for both repos (via `pat-test.sh`)
- The PAT in `~/.git-credentials` matched the new one
- The file format was correct
- `git fetch origin` worked silently

**Root cause:** the macOS Keychain contained **three** stale `github.com` / `gh:github.com` entries (one each for accounts `HermesGoldmanglobal`, `nswcoachcharter-au`, and `CTO-goldmanglobal`). Git's system-level `osxkeychain` credential helper (set in `/Library/Developer/CommandLineTools/usr/share/git-core/gitconfig`) matched FIRST in the helper chain and returned a stale CTO-goldmanglobal credential (likely an old PAT with read-only scope) — overriding the user-configured `~/.git-credentials` file.

The credentials stack order (un-overridable from user/repo config):
1. **System gitconfig:** `credential.helper = osxkeychain` — runs first
2. **User `~/.gitconfig`:** `credential.helper = store` — runs second
3. **Repo `.git/config`:** any local helper — runs third

**Repo-local and user-local helpers cannot override the system-level `osxkeychain`.** This is a git limitation, not a misconfiguration.

### What fixed it

Two steps were needed:
1. **Deleted the stale `gh:github.com / CTO-goldmanglobal` entry** from the macOS Keychain (created 2026-06-14, well before this session, with the wrong scope):
   ```bash
   security delete-generic-password -s "gh:github.com" -a "CTO-goldmanglobal"
   ```
2. **Used a wrapper script** that bypasses the helper chain entirely by embedding the PAT directly in the URL (read from `~/.git-credentials` at push time, never stored in `.git/config`):
   ```bash
   ~/.local/bin/git-push-with-file-creds HEAD:refs/heads/cursor/founding-state-claimdesk247
   ```
   The script is installed at `~/.local/bin/git-push-with-file-creds` and reads the PAT fresh from `~/.git-credentials` on every invocation.

### Verification (after both steps)

- API check via the file's PAT: `login: CTO-goldmanglobal, push: True` on both repos ✅
- Push via wrapper: `c4073d7..bbedd09 HEAD -> cursor/founding-state-claimdesk247` ✅
- Latest commit on github.com: `bbedd09 docs(handoff): PAT incident 3 — build seat cat leaked PATs in chat` ✅

### Lessons learned (added)

- **macOS Keychain can silently override `~/.git-credentials` for git operations.** Whenever a PAT is rotated, also delete the corresponding keychain entry (use Keychain Access app, or `security delete-generic-password -s "gh:github.com" -a "<account>"`).
- **The `osxkeychain` system-level helper is un-overridable from user/repo config.** It is set by Apple's CommandLineTools package. If it holds a stale credential, no amount of `git config` will fix it — you must clear the keychain.
- **The `git -c credential.helper=` override does NOT skip the system helper.** The system helper runs in a separate credential-store layer. To bypass all helpers, embed the PAT directly in the URL (the wrapper script does this safely).
- **For this Mac, the `~/.local/bin/git-push-with-file-creds` script is the recommended push method** going forward, because:
  - It reads the PAT fresh from `~/.git-credentials` on every push (no need to remember to re-rotate it in multiple places)
  - It uses the PAT in the URL — which is the only way to actually push when `osxkeychain` has a stale entry
  - The PAT is never stored in `.git/config`, never echoed, and never written to disk
- **Long-term fix for the team:** consider installing the gh CLI's credential helper globally and authenticating as `CTO-goldmanglobal` via `gh auth login` — this would unify the auth model and surface any token issues earlier.

---

*Filed for audit log. See `handoff/INTEGRATION-AUDIT-2026-06-18.md` (P0 #3) and `handoff/CEO-REPORT-INTEGRATION-2026-06-18.md` for the full context.*
