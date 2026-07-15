# Brief Fetch Helper — Frontend Guide

**Date:** 2026-07-15
**Spec ref:** DASHBOARD-SPEC §A2
**Problem:** The existing `/dashboard` uses a bare `<a href={briefUrl(ref)} target="_blank">` which 403s in production because `/api/brief` requires `Authorization: Bearer <jwt>` (AAL2) and a bare `<a>` attaches no auth header.

## The fix (frontend code)

Replace the bare `<a>` with a `fetch` call that attaches the Supabase session token:

```typescript
import { supabase } from "@/lib/supabase";

async function downloadBrief(ref: string): Promise<void> {
  const { data: session } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error("Not authenticated — sign in first");
  }
  const res = await fetch(`https://claimdesk247-engine.vercel.app/api/brief/${ref}`, {
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
  });
  if (!res.ok) {
    if (res.status === 403) {
      throw new Error("MFA (AAL2) required — verify your second factor");
    }
    throw new Error(`Brief download failed: ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${ref}-brief.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
```

## Auth contract

| Requirement | Value |
|---|---|
| Header | `Authorization: Bearer <supabase_access_token>` |
| AAL level | AAL2 (MFA required) |
| Allowed roles | `legal_staff`, `admin` |
| Content-Type | `application/json` |
| Response | JSON (intake brief fields) |

## Stub mode (dev/preview without real Supabase auth)

```
GET /api/brief/<ref>?as_email=lou@legal.example
Header: X-MFA-Verified: 1
```

The stub mode is for dev/preview only. Production (`APP_ENV=production`) requires `BRIEF_AUTH_MODE=jwt` (already enforced — the engine 500s if stub is used in prod, per the P0-3 fix).

## CORS

The engine's CORS allow-list (`CORS_ALLOWED_ORIGINS`) must include the frontend origin. Verify in Vercel env vars for the engine project.
