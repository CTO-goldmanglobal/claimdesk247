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

---

*Filed for audit log. See `handoff/INTEGRATION-AUDIT-2026-06-18.md` (P0 #3) and `handoff/CEO-REPORT-INTEGRATION-2026-06-18.md` for the full context.*
