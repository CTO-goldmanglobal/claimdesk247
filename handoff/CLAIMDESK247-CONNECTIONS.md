# ClaimDesk 247 — Connections & Scope (for Cursor / Claude Cowork)
**Updated:** 2026-06-13 · Goldman org

## ⚠️ Scope lock — three SEPARATE projects, do not mix
| Project | Repo | Host | Notes |
|---|---|---|---|
| **ClaimDesk 247** *(this project)* | `CTO-goldmanglobal/claimdesk247-76a0b7de` | Vercel `claimdesk247-76a0b7de` → `claimdesk247.com.au` | Legal accident-intake. **All work here.** |
| finntang.com | (separate) | Vercel `finntang-com` | **Out of bounds.** |
| wealth.goldmanglobal.com.au | (separate, `super-scout`) | Vercel | **Out of bounds.** |

When working in Cursor or Cowork, only touch the `claimdesk247-76a0b7de` repo/project. Never edit, deploy, or reference the other two.

## Connections (ClaimDesk 247)
- **GitHub:** `https://github.com/CTO-goldmanglobal/claimdesk247-76a0b7de` (private, org `CTO-goldmanglobal`). Branch `main` auto-deploys to Vercel.
- **Supabase:** org `CTO-goldmanglobal`, project `claimdesk247` — ref **`mvzzglmegkchlmjartbm`**, URL `https://mvzzglmegkchlmjartbm.supabase.co`, region **ap-southeast-2 (Sydney)**. Schema + RLS applied.
- **Vercel:** team `cto-goldmanglobals-projects`, project `claimdesk247-76a0b7de`. Env vars set: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `NITRO_PRESET=vercel`.
- **DNS:** Cloudflare account `067eb8247f6ba389d9fee5e217ff298b`, zone `claimdesk247.com.au`. Apex + `www` CNAME → Vercel (DNS-only). SSL issued by Vercel.
- **Live:** `https://claimdesk247.com.au` and `https://claimdesk247-76a0b7de.vercel.app`. Lovable preview: `claimdesk247.lovable.app`.

## Deploy notes (important)
- **Git-author block:** pushes from the `finn-tang` GitHub identity are blocked by Vercel (not a team member). To deploy, commit from the **CTO GitHub account** (or invite the dev to the Vercel team once, then pushes deploy directly).
- **Build target:** must keep `nitro: { preset: "vercel" }` in `vite.config.ts` — the Lovable wrapper otherwise skips Nitro outside its sandbox and the build 404s.
- **Lovable two-way sync:** this repo syncs with Lovable. Pick one primary editor (Cursor/Cowork **or** Lovable) to avoid conflicts.

## Setting up Cursor (suggested)
1. `git clone https://github.com/CTO-goldmanglobal/claimdesk247-76a0b7de.git` (auth as CTO or a team member).
2. Copy `.env.example` → `.env`; fill `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (from Supabase → Settings → API Keys). Leave `VITE_API_BASE_URL` blank (preview mode) until the engine is deployed.
3. `npm install && npx vite build` → confirm `.vercel/output` is produced before pushing.
4. Open only this repo in Cursor — do not add the finntang / wealth.goldmanglobal repos to the same workspace.
