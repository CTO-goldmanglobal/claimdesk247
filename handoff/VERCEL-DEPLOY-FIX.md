# Cursor instruction — fix the Vercel 404 (ClaimDesk)

**Repo:** `CTO-goldmanglobal/claimdesk247-76a0b7de` · **Host decision:** Vercel (domain `claimdesk247.com.au` via Cloudflare DNS) · **Date:** 2026-06-13

## Symptom
`https://claimdesk247-76a0b7de.vercel.app/` returns **404: NOT_FOUND** on every deploy. Builds finish in ~7–8s and produce **no runtime function** (Vercel runtime logs are empty). The Lovable preview (`claimdesk247.lovable.app`) works fine.

## Root cause
- Vercel project **Framework Preset = TanStack Start** → it expects the standard Vercel build output (`.vercel/output`, Build Output API).
- But `vite.config.ts` uses `@lovable.dev/vite-tanstack-config`, whose bundled Nitro is **"build-only using cloudflare as a default target"** (per the file's own comment). So `vite build` emits a **Cloudflare Worker** bundle, not `.vercel/output`.
- Vercel finds nothing to serve at `/` → 404. This is a build-target mismatch, not cache, not env, not the Vercel settings.

## Already done (do NOT redo)
- Supabase schema applied + RLS verified, project in **Sydney (ap-southeast-2)**.
- Vercel env vars set (Production + Preview): `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (publishable), and `NITRO_PRESET=vercel`.
- `NITRO_PRESET=vercel` alone did **not** fix it on redeploy — so the Lovable wrapper is not honouring that env var; the preset must be set in config.

## The fix (make Nitro build for Vercel)
1. Open `node_modules/@lovable.dev/vite-tanstack-config` and find how it forwards Nitro options (look for `preset`, `nitro`, `cloudflare`, `server`). Confirm the override key name.
2. In `vite.config.ts`, pass the Vercel preset explicitly. Most likely shape:
   ```ts
   import { defineConfig } from "@lovable.dev/vite-tanstack-config";

   export default defineConfig({
     tanstackStart: { server: { entry: "server" } },
     nitro: { preset: "vercel" },   // <- force Vercel Build Output API (verify key name against the wrapper)
   });
   ```
   If the wrapper doesn't expose a `nitro`/`preset` option, drop the wrapper for the build and configure `@tanstack/react-start` + Nitro directly with `preset: "vercel"`.
3. **Verify locally before pushing:**
   ```
   npm install
   npx vite build
   ls -la .vercel/output     # MUST exist (config.json + functions/ or static/)
   ```
   If `.vercel/output` is produced, Vercel will serve it. (A `.output/` or Cloudflare `dist/worker` instead = still wrong.)
4. Push to `main`. Vercel auto-deploys. Confirm `https://claimdesk247-76a0b7de.vercel.app/` loads the landing page (not 404) and `/intake` runs.

## Data-residency note (legal product)
After it serves, set **function region = `syd1`** in Vercel (Project → Settings → Functions, or `vercel.json` `"regions": ["syd1"]`) so accident-victim data is processed in Sydney, matching the Supabase region.

## Then: custom domain (Vercel + Cloudflare DNS)
1. Vercel → Project → Settings → **Domains** → add `claimdesk247.com.au` (and `www`). Vercel shows the target record.
2. In Cloudflare DNS (account `067eb8247f6ba389d9fee5e217ff298b`): add the record Vercel specifies — typically `CNAME` to `cname.vercel-dns.com` (apex via CNAME-flattening). Set Cloudflare **SSL/TLS mode = Full**. Proxy (orange cloud) can stay off initially while validating, then optional.
3. Wait for Vercel to verify + issue the cert.

## Status of follow-ups (updated 2026-06-13)
- **DONE — Vercel build fix** (`nitro: { preset: "vercel" }`), deployed and serving.
- **DONE — custom domain** `claimdesk247.com.au` (apex, CNAME → Vercel) + `www` (307 → apex), both DNS-only in Cloudflare; SSL issued by Vercel.
- **DONE — dashboard auth-guard**: `/dashboard` now redirects unauthenticated visitors to `/auth` (client-side check in `src/routes/dashboard.tsx`; RLS still enforces data server-side). Verified live.
- **PENDING — `SUPABASE_SERVICE_ROLE_KEY`**: set as a server-side env var on Vercel only once the Stage 2.5 engine functions are deployed. Never expose to the client.
- **PENDING — `VITE_API_BASE_URL`**: leave blank until the engine endpoint exists (keeps the UI in safe preview mode).

## MFA enforcement — spec for Cursor (do NOT just "turn on" AAL2)
Enforcing AAL2 before staff have enrolled a factor would lock everyone out. Build the enrollment flow first, then gate. Steps:

1. **Enrollment UI** (new authed screen, e.g. `/account/security`): call `supabase.auth.mfa.enroll({ factorType: 'totp' })`, render the returned `totp.qr_code` (SVG) + secret, then `supabase.auth.mfa.challenge` + `verify` with the user's 6-digit code to activate the factor.
2. **Step-up at login**: after `signInWithPassword`, call `supabase.auth.mfa.getAuthenticatorAssuranceLevel()`. If `nextLevel === 'aal2'` and `currentLevel !== 'aal2'`, show a TOTP challenge screen (`mfa.challenge` + `mfa.verify`) before proceeding to `/dashboard`.
3. **Gate the sensitive routes**: in the dashboard/brief guard, require `currentLevel === 'aal2'` for `legal_staff` and `admin` (panel_shop_staff can stay aal1 if desired). Redirect to the challenge screen otherwise.
4. **Enforce server-side too**: the engine's `/api/brief/:ref` must verify the caller's JWT `aal` claim is `aal2` for legal/admin — UI gating alone is not sufficient for a legal product.
5. Roll out: enrol the existing staff accounts before flipping enforcement on, or allow a one-time grace enrolment on first login.
Test the full enrol → challenge → gate loop locally against the live Supabase project before shipping.
