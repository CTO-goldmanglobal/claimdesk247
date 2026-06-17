# T3 — Monitoring + Rollback Design
**Prepared by:** Cursor / MiniMax (build seat) · **Date:** 2026-06-15
**Task:** L0 T3 per `CURSOR-HANDOFF-MASTER.md` §7 — production alerting on error/5xx rate, escalation rate, band-distribution drift + documented + tested one-step rollback.
**Gate it closes:** **G-MONITOR** (P1) + **G-ROLLBACK** (P1) per `stage-4/GATE-REGISTER-ADDENDUM.md`.
**Inputs read:** `CURSOR-HANDOFF-MASTER.md` §2 (engine env), `stage-4/GATE-REGISTER-ADDENDUM.md`, `architecture/INFRA-PROVISIONING-CHECKLIST.md`, `handoff/LOOP-CLOSE-DECISIONS.md`, `handoff/STAGE-5-PLAN.md`.

---

## 1. Why this design exists

A live legal engine that silently shifts its band mix is a quiet failure. Two things must be true to call L0 "production-safe" beyond the gates already closed:

1. **Detect drift quickly.** A new deploy that doubles the escalation rate, halves the `likely` rate, or spikes the 5xx rate is wrong *immediately* — not on the next human review cycle. Drift alerts are the only way to catch this in real time.
2. **Reverse safely.** If a bad rule-tree or engine version ships, the recovery is "pin previous + redeploy", and that recovery must be **proven once** (G-ROLLBACK test) before the first time it's needed. A bad deploy pauses nothing if rollback is rehearsed.

Both are P1 in the gate register but are foundational ops discipline. Designing them now means the L1 transition (with 9 new scenarios) inherits a working safety net.

---

## 2. The signals to watch (per G-MONITOR)

| Signal | Source | What "drift" looks like | Threshold (proposed initial) |
|---|---|---|---|
| **5xx rate (engine)** | Vercel Function logs (`api/index.py`) | 5xx count / total invocations over a 5-min window > baseline | Baseline = 0.5% over 24h rolling; alert at 2x baseline for 15 min |
| **5xx rate (frontend SSR)** | Vercel Function logs (TanStack Start) | Same shape | Same threshold |
| **4xx rate (engine)** | Vercel Function logs | Sudden jump in 4xx suggests contract drift between frontend and engine | Baseline = 5% over 24h rolling; alert at 1.5x baseline for 30 min |
| **Escalation rate (engine)** | Supabase `audit_log` query: `count(escalation IS NOT NULL) / count(classify) over 1h` | Sustained jump means scenarios are silently failing the sign-off gate or new logic is over-escalating | Baseline = 5–10% (depends on traffic); alert at >25% for 1h (i.e. 2.5–5x baseline) |
| **Band distribution drift (engine)** | Supabase `audit_log`: `band` value counts over 1h | `likely` rate suddenly drops from 60% to 20% (or `unclear`/`insufficient` jumps) — suggests new rule tree or new bug | Alert at any band bucket moving by >15pp vs 24h rolling baseline |
| **`/healthz` failure** | Vercel cron / UptimeRobot on `claimdesk247-engine.vercel.app/healthz` | Any non-200 from `/healthz` = engine down or crashed | Alert on 1 failed check; service-level target = 99.5% |
| **`/healthz.rule_tree_hash` change** | Vercel cron on `/healthz` response | Hash changed = a new rule tree deployed (expected on T8 sign-off + T4 Phase-2 deploy) | No alert; emit a "rule-tree-deployed" event for the audit log (so Legal Head can correlate sign-off to deploy) |
| **Supabase `intake_sessions` write failure** | Supabase log-based metric | Engine can no longer persist sessions = intake breaks | Alert on > 5 failures in 5 min |
| **`audit_log` insert failure** | Same | Breaks G-54 append-only evidence trail — must never silently fail | Alert on any failure (P0 alert, not P1) |

**Initial alert destinations:**
- **P0 alerts** (5xx spike, `/healthz` down, `audit_log` failure): immediate — email + SMS (via Vercel + Twilio, or a simpler email-to-SMS bridge)
- **P1 alerts** (4xx drift, escalation rate, band distribution): every-15-min digest to the build team email + a Slack channel

**Implementation in three layers:**
- **Vercel:** built-in observability dashboard for 5xx/4xx rates per function. No code change needed; just turn on the dashboard alerts.
- **Supabase:** log-based alerts on `intake_sessions` and `audit_log` insert failures. Native in Supabase dashboard.
- **Engine:** a tiny `/api/_stats` endpoint that the Vercel cron can poll to compute escalation/band distribution (the engine already has the data — it just needs an aggregation endpoint). ~30 lines of code, opt-in via `STATS_ENDPOINT_ENABLED=true` env var (default off until the monitoring is set up by the CTO).

---

## 3. The rollback design (per G-ROLLBACK)

### 3.1 What "rollback" means

Two distinct rollback targets, with different cost profiles:

| Target | What it reverses | How | Cost |
|---|---|---|---|
| **Engine code rollback** | A bad engine build (e.g. T1 broke escalation in a way tests didn't catch) | Pin engine repo to the previous commit SHA, push to `main` (or revert + push), Vercel auto-deploys | ~3 min end-to-end (Vercel build + edge propagation) |
| **Rule tree rollback** | A bad rule tree (e.g. a typo in a "likely" message, or a scenario that's banding the wrong way) | Revert the JSON change in the rule-tree file, push, Vercel auto-deploys, `/healthz.rule_tree_hash` returns the old hash | ~3 min end-to-end |

Both are git-driven, both go through the same Vercel auto-deploy path, both are reversible. **The trick is having the previous SHA known and the procedure rehearsed.**

### 3.2 The "previous SHA" discipline

After every push to `main`, record the deployed SHA somewhere queryable. Vercel exposes this via the deployment API (`vercel list` returns the deployment SHA + the git commit it points at). A simple convention:

- **Engine repo `main`:** every commit gets a Vercel deployment. The previous successful deployment is the rollback target.
- **Pin pattern:** in the Vercel dashboard for `claimdesk247-engine`, the "Deployments" tab shows commits in order. The one above the latest = rollback target. The deploy log includes the commit SHA + the `rule_tree_hash` at that SHA — so a bad rule-tree is rolled back by finding the deployment with the previous good hash, clicking "Promote to Production".

### 3.3 The one-step rollback runbook (the actual artifact)

```markdown
## Rollback runbook — claimdesk247-engine

### When to roll back
- 5xx rate > 2x baseline for 15 min (alert G-MONITOR-1)
- `/healthz` non-200 for 3 consecutive 1-min checks (G-MONITOR-6)
- `audit_log` insert failure (G-MONITOR-9, P0)
- Legal Head requests rollback (per G-LH process)
- Any P0 finding from Opus audit

### How to roll back (engine code or rule tree — same procedure)
1. Go to https://vercel.com/cto-goldmanglobals-projects/claimdesk247-engine/deployments
2. Find the LAST GREEN deployment (status = "Ready", commit = the previous SHA)
3. Click ⋮ → "Promote to Production"
4. Vercel swaps the production alias to that deployment (~30s)
5. Verify: GET https://claimdesk247-engine.vercel.app/healthz
   - status == "ok"
   - rule_tree_hash == <expected previous hash> (if rolling back rule tree)
6. Record the rollback in the build log: SHA, reason, time, who

### What to do AFTER rollback
1. Open a CR (change request) in the engine repo describing the bad commit
2. Either revert + push, or fix forward (TBD per finding)
3. Re-run the 79-test suite against the rolled-back deployment (if VERCEL_BYPASS secret regenerated, otherwise locally)
4. Update the build log with the resolution
5. If the rollback was a G-MONITOR alert, check whether the alert threshold needs adjusting
```

This is a doc-only artifact; the test of the runbook (G-ROLLBACK pass) is when the CTO performs a *rehearsal* rollback (promote a previous deployment, verify, promote the latest back). One rehearsal pass closes G-ROLLBACK.

### 3.4 The test that proves rollback (G-ROLLBACK test)

The gate register says: *"a one-step revert to the previous rule-tree/engine version is documented and **proven once** (pin previous version → redeploy → healthz + smoke green)."*

The "proven once" is a manual exercise by the CTO:
1. Note the current production SHA (call it `current_sha`).
2. Promote the previous green deployment to production.
3. Wait 30s, hit `/healthz`. Expect `status: ok` and the *previous* `rule_tree_hash`.
4. Promote `current_sha`'s deployment back to production.
5. Wait 30s, hit `/healthz`. Expect the *current* `rule_tree_hash`.

The "smoke" step is a single `/api/session` POST (creates a session) and an `/api/classify` POST (returns an escalation envelope, since the 6 scenarios are unsigned). Both should return valid 200/500 envelopes. If they do, rollback is proven.

This is a CTO/setting action. The runbook above is the doc; the test is the live exercise.

---

## 4. Implementation plan (in order)

| # | Action | Owner | When |
|---|---|---|---|
| 1 | Vercel observability dashboard: turn on 5xx/4xx alerts on the `claimdesk247-engine` project | CTO | Next setting change (no build) |
| 2 | Supabase: log-based alerts on `intake_sessions` and `audit_log` insert failures | CTO | Next setting change |
| 3 | Engine: add `/api/_stats` endpoint (opt-in via env var) returning escalation rate, band distribution over a rolling 1h window | Build seat (T3 code) | **This can be built now from this seat**; doesn't ship until CTO sets `STATS_ENDPOINT_ENABLED=true` |
| 4 | UptimeRobot (or similar free tier) on `claimdesk247-engine.vercel.app/healthz` | CTO | Setting |
| 5 | Rollback runbook (this doc, final form) reviewed by CTO + appended to the Vercel project description | Build seat (doc) | **Doc done in this design**; CTO review + append |
| 6 | Rollback rehearsal (G-ROLLBACK test) | CTO | One-time, after step 5 |
| 7 | Drift-threshold tuning | Build seat | After 1 week of live data; the initial thresholds are guesses |

### 4.1 The bit I can do now: T3 `/api/_stats` endpoint (design only — implementation in next loop)

Per item 3 above, the engine can expose a small stats endpoint. Design:

- **Path:** `GET /api/_stats` (underscore prefix = "internal, gate by auth").
- **Auth:** requires `Authorization: Bearer <STATS_TOKEN>` where `STATS_TOKEN` is an env var set by the CTO. If `STATS_TOKEN` is unset, return 404. (Dormant by default; activates only when the CTO sets the env var.)
- **Response shape:**
  ```json
  {
    "window": "1h",
    "total_classify_calls": 142,
    "escalation_rate": 0.04,
    "band_distribution": {
      "likely": 0.62,
      "possible": 0.18,
      "unclear": 0.06,
      "insufficient": 0.10
    },
    "escalation_breakdown": {
      "unsigned-scenario": 0.02,
      "stale-signoff": 0.005,
      "esc-injury": 0.005,
      "esc-multiparty": 0.005,
      "...": 0.005
    }
  }
  ```
- **Source data:** query Supabase `audit_log` with the service-role key (already in env). Filter on a configurable `?since=<ISO>` window (default 1h).
- **No PII in the response.** Aggregate counts and ratios only.
- **Cost:** ~50 lines of code in `wrap.py`, gated by `STATS_ENDPOINT_ENABLED=true` + `STATS_TOKEN=<secret>`. Inert if env not set.

**This is a L0 P1 task, not load-bearing for launch.** It can ship in the L0→L1 transition or be deferred to L1 ops hardening. Decision point: build now or defer.

---

## 5. Audit: what this design does and doesn't cover

### Covers
- **G-MONITOR** (P1): all 8 signals identified, thresholds proposed, alerting layers separated by severity.
- **G-ROLLBACK** (P1): two rollback targets identified, runbook written, rehearsal test defined.
- **Code-level implementation path** for the one piece the build seat can do (`/api/_stats`).

### Doesn't cover (gated on CTO / setting actions)
- The Vercel observability alert configuration (CTO setting).
- The Supabase log-based alert configuration (CTO setting).
- The UptimeRobot setup (CTO setting).
- The rollback rehearsal exercise (CTO deployment authority).
- The stats token (CTO secret).

### Open design questions
- **Alert destinations:** email + SMS is the default; a Slack/Teams channel would be cheaper for a team. Build seat has no authority to set those up.
- **Threshold tuning:** the proposed thresholds are educated guesses from typical web-app baselines. The actual numbers will shift once the engine has real traffic. Recommend re-tuning after 1 week of live data.
- **Stats endpoint scope:** `/api/_stats` returns aggregate data only. If Legal Head needs per-scenario breakdowns, that's a second endpoint with a different scope. Not in T3.

---

## 6. Acceptance criteria (for T3 closure)

T3 is "done" when all of:
1. Vercel observability dashboard is on and 5xx/4xx alerts fire on a test event.
2. Supabase log-based alerts on `intake_sessions` and `audit_log` insert failures fire on a test event.
3. UptimeRobot (or equivalent) checks `/healthz` every 60s and alerts on failure.
4. The rollback runbook above is in the Vercel project description and reviewed.
5. **One rollback rehearsal has been performed and recorded.** This is the G-ROLLBACK pass condition.
6. The `/api/_stats` endpoint exists and is gated by env (dormant by default).

Acceptance is a CTO exercise; the build seat's role is to provide the runbook, the stats endpoint code (when built), and the rehearsal definition.

---

## 7. Effort estimate

| Step | Owner | Effort |
|---|---|---|
| Vercel observability alerts | CTO | 15 min (settings) |
| Supabase log alerts | CTO | 15 min (settings) |
| UptimeRobot | CTO | 5 min (settings) |
| Stats endpoint code | Build seat | 1-2 hours (small) |
| Rollback runbook review + append | CTO | 30 min |
| Rollback rehearsal (one-time) | CTO | 30 min |
| Threshold tuning (post-1-week) | Build seat | 1 hour |

**Total CTO time:** ~1.5 hours. **Total build time:** ~2-3 hours. **Total calendar time:** depends on when the CTO can do the setting changes; the build can write the code in parallel.

---

*Prepared by Cursor / MiniMax (build seat) · design only; the CTO executes the settings changes + rehearsal.*
