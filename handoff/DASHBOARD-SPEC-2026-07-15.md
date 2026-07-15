# Dashboard Spec — ClaimDesk 247

**Date:** 2026-07-15
**Status:** Spec for the **backend** chat to implement. Frontend will wire against these contracts once live.
**Scope:** Three distinct dashboard surfaces, each with its own audience, auth posture, and data contract.

**Companion context (read first):**
1. `handoff/RECEPTIONIST-ROBOT-SPEC-2026-07-15.md` — the customer-facing chat vision; this spec is the natural follow-on for the staff + operator surfaces.
2. `lovable-ui/src/routes/dashboard.tsx` — the existing **layout demo** (hardcoded rows, broken brief-download button). Real data wiring is what this spec asks for.
3. `stage-4/legal/CD-R3-injury-lead-generation-2026-07-14.md` — injury firewall baseline. Every dashboard that touches case data must honour it (no injury-lead monetisation surface anywhere).

---

## Why three dashboards, not one

ClaimDesk has three distinct audiences, each with different data access needs, different auth postures, and different legal exposure. Collapsing them into one "admin dashboard" creates security holes (a panel-shop staffer seeing lawyer-only brief contents) and UX problems (a customer logging in to check their case shouldn't land on a staff workflow).

| Dashboard | Audience | Auth | Primary job |
|---|---|---|---|
| **A. Staff dashboard** | Legal staff, admins, panel-shop staff | Supabase auth + AAL2 (MFA) + role claim | Work cases: read briefs, assign cases, manage sign-off, see their queue |
| **B. Customer dashboard** | The customer who filed the case | Supabase auth (magic link, AAL1) — same identity captured at intake | Track their own case, add notes/photos, download their PDF, see next step |
| **C. Operator dashboard** | The ClaimDesk operator/admin (internal) | Supabase auth + AAL2 + operator role claim | System health, audit log, rule-tree sign-off status, evidence retention, rate-limit monitoring |

All three are gated by **Supabase Row Level Security** server-side. The UI auth checks are convenience, not security.

---

## A. Staff dashboard (`/dashboard`)

### What's there today

`lovable-ui/src/routes/dashboard.tsx` is a **layout demo**:
- Hardcoded `ROWS` array of 4 fake cases (lines 21-32, refs `NSW-48xx`)
- StatCard values hard-coded (`12` open intakes, `4` awaiting assessment, etc.)
- Role switcher (panel_shop / legal / admin) for preview only — UI not security
- "Brief" download button is a bare `<a href={briefUrl(ref)} target="_blank">` (line 146) — **403s in production** because `/api/brief` requires `Authorization: Bearer <jwt>` (AAL2) and a bare `<a>` attaches none

### What the backend needs to ship

#### A1. `GET /api/staff/cases` — staff case queue

Role-filtered list of cases the staff member is allowed to work. **Not the same as** `/api/cases?user_id=<id>` (which is customer-scoped to one Supabase user).

```
GET /api/staff/cases?role=legal_staff&status=open&page=1&page_size=50
Authorization: Bearer <supabase access token, AAL2>

→ 200 {
      "items": [
        {
          "ref": "GF-XXXXXXXX",
          "created_at": "2026-07-15T10:30:00Z",
          "state": "NSW",
          "claim_type": "property_damage",
          "band": "likely" | null,            // null for escalated/no-band
          "escalated": "esc-injury" | null,   // injury firewall flag
          "intake_completed": true,
          "evidence_count": 3,
          "notes_count": 2,
          "assigned_to": "lawyer@example.com" | null,
          "status": "open" | "in_review" | "escalated" | "closed",
          "customer": {                       // populated when identity captured
            "name": "Jane Citizen",
            "mobile": "+61 4XX XXX XXX",
            "email": "jane@example.com"
          }
        }
      ],
      "total": 47,
      "page": 1,
      "page_size": 50
    }
```

**Role scoping (non-negotiable):**
- `panel_shop_staff` → sees only cases with `intake_completed=true` + a damage/vehicle context (so they can schedule repairs); no identity, no lawyer brief
- `legal_staff` → sees full queue; can read brief + identity; cannot change role assignments
- `admin` → full queue + assignment + sign-off management

**Injury firewall (CD-R3):** cases flagged `escalated: "esc-injury"` are visible to legal_staff/admin only; panel_shop_staff never sees them. The list endpoint must filter by caller role.

#### A2. Fix `/api/brief/{ref}` authentication path for browser fetch

The endpoint exists and the auth contract is correct (`Authorization: Bearer`, AAL2 required). What's missing is **a documented fetch helper** so the frontend can use it instead of the bare `<a>` workaround.

Recommend the backend ship a small client-side helper doc + verify the CORS allow-list includes the frontend origin for the brief path. Frontend will then do:

```ts
const { data: session } = await supabase.auth.getSession();
const res = await fetch(briefUrl(ref), {
  headers: { Authorization: `Bearer ${session.access_token}` },
});
const blob = await res.blob();
// → object URL → download
```

The current `lovable-ui/src/routes/dashboard.tsx:146` `<a target="_blank">` pattern is broken and should not be revived.

#### A3. `POST /api/staff/cases/{ref}/assign` — case assignment

```
POST /api/staff/cases/{ref}/assign
Authorization: Bearer <AAL2> (admin role only)
{ "assign_to_email": "lawyer@example.com" }

→ 200 { "ref": "GF-XXXXXXXX", "assigned_to": "lawyer@example.com" }
```

Audit: `case_assigned` (old + new assignee).

#### A4. `GET /api/staff/signoffs` — pending rule-tree sign-offs (admin only)

Lists rule-tree scenarios awaiting Legal Head sign-off so admins can see what's blocking go-live for a new state/claim-type.

```
GET /api/staff/signoffs
Authorization: Bearer <AAL2> (admin role only)

→ 200 {
      "trees": [
        { "label": "VIC.property_damage", "version": "1.0.0-vic-stage1",
          "scenarios": 7, "signed_current": 0, "live": false },
        { "label": "QLD.property_damage", ... }
      ]
    }
```

This already exists inline in `/healthz` — extract it as a dedicated auth-gated endpoint.

---

## B. Customer dashboard (`/my-cases`)

### What's there today

Nothing. The frontend route doesn't exist yet. **`GET /api/cases?user_id=<id>` already ships** (parent `3908090`) — returns cases bound to a Supabase auth identity. The work here is mostly frontend, plus one backend touch.

### Backend contract (already shipped — verify shape)

```
GET /api/cases?user_id=<supabase_user_id>
→ 200 {
      "cases": [
        {
          "ref": "GF-XXXXXXXX",
          "created_at": "...",
          "state": "NSW",
          "claim_type": "property_damage",
          "band": "likely" | null,
          "escalated": "esc-injury" | null,
          "intake_completed": true,
          "evidence_count": 3,
          "pdf_url": "/api/pdf/<ref>"
        }
      ]
    }
```

### What the backend needs to ship

#### B1. `GET /api/case/{ref}/status` — customer-facing status summary

The customer doesn't see raw `band` or `escalated` values — they see a status string. The receptionist spec calls for the robot to greet returning customers with *"Hi {name} — your case GF-XXXXXXXX is {status}."* That status string needs a backend source (so it's consistent across chat + dashboard + emails).

```
GET /api/case/{ref}/status
(query: ?user_id=<supabase_user_id> for RLS)

→ 200 {
      "ref": "GF-XXXXXXXX",
      "status_label": "We've received your details" |
                      "Your case is being reviewed" |
                      "We're recovering your repair costs" |
                      "We need some information from you" |
                      "Your case is on hold" |
                      "A lawyer will call you" |        // injury firewall
                      "Closed",
      "status_detail": "Optional one-liner with the next step",
      "next_step": "We'll call you within 1 business day" | null,
      "updated_at": "2026-07-15T..."
    }
```

The mapping (case state → status_label) is **engine/business logic** and must live server-side, not be derived in the frontend (the frontend shouldn't decide what "your case is on hold" means).

#### B2. Verify RLS: customer can read ONLY their own cases

`GET /api/cases?user_id=<id>` is rate-limited to prevent enumeration (already noted in the endpoint comment). Audit-confirm that a customer passing someone else's `user_id` gets 403, not the data. This is the load-bearing privacy invariant for the customer dashboard.

---

## C. Operator dashboard (`/operator`)

### What's there today

Nothing — not even a frontend route. The backend has the data but no endpoints exposing it.

### What the backend needs to ship

#### C1. `GET /api/operator/audit` — audit log viewer

```
GET /api/operator/audit?action=evidence_uploaded&ref=<ref>&since=2026-07-01&page=1
Authorization: Bearer <AAL2> (operator role only)

→ 200 {
      "events": [
        {
          "id": "...",
          "ts": "2026-07-15T10:30:00Z",
          "session_id": "...",
          "user": "client IP" | "user email" | "system",
          "action": "consent_granted" | "evidence_uploaded" | "slot_corrected" | ...,
          "inputs": {...},                    // reference, filename, etc.
          "rule_path": [...],
          "output": {...}
        }
      ],
      "total": 1234
    }
```

The AUDIT append-only log exists (`stage-3/app/audit.py`); this is the read surface. Filters: action, ref, since/until, user. Operator role only — staff and customers never see this.

#### C2. `GET /api/operator/health` — system health summary

Consolidates `/healthz` + retention status + rate-limiter state + S3 bucket state into one ops surface.

```
GET /api/operator/health
Authorization: Bearer <AAL2> (operator role only)

→ 200 {
      "engine": { "version": "...", "rule_tree_hash": "..." },
      "rule_tree_versions": {...},            // from /healthz
      "evidence_store": {
        "backend": "s3" | "memory",
        "bucket": "...",
        "objects_total": 1234,
        "size_bytes": 4567890,
        "glacier_objects": 12
      },
      "rate_limiter": { "active_sessions": 23, "blocked_ips": 2 },
      "sessions": { "active": 47, "escalated_injury": 3 }
    }
```

#### C3. `POST /api/operator/retention/run` — manual retention trigger

The retention scheduler (`stage-4/scripts/run_evidence_retention.py`) runs on EventBridge. Operators need a manual trigger for testing + incident response.

```
POST /api/operator/retention/run
Authorization: Bearer <AAL2> (operator role only)
{ "dry_run": true }

→ 200 { "purged": 0, "archived_to_glacier": 23, "errors": [] }
```

Audit: `retention_triggered` (operator email + dry_run flag).

---

## Auth model (cross-cutting)

All three dashboards use **Supabase auth + role claims**. The backend must read the role from the verified JWT, not from a query param or a request body (those are spoofable).

```
verified_jwt.claims.app_metadata.claimdesk_role
  → "customer" | "panel_shop_staff" | "legal_staff" | "admin" | "operator"
```

AAL requirements:
- Customer dashboard: AAL1 (magic link)
- Staff dashboard: AAL2 (TOTP/WebAuthn)
- Operator dashboard: AAL2 + operator role claim

The existing `/api/brief/{ref}` already implements the AAL2 check correctly (`stage-2.5/app/wrap.py:1261`). Reuse that pattern.

---

## Implementation order (recommended)

1. **B2 (RLS verification)** — defensive, no new code, just confirming the privacy invariant holds before any dashboard work depends on it
2. **A1 (staff case queue)** — unblocks the frontend rewrite of `/dashboard` (which today is fake)
3. **A2 (brief fetch helper doc)** — quick, fixes a known-broken button
4. **B1 (case status)** — small, unblocks the customer dashboard's status display
5. **A3 (case assignment)** — small
6. **C1 (audit viewer)** — medium, the AUDIT log already has the data
7. **C2 (system health)** — extract from `/healthz`
8. **A4 + C3 (sign-offs + retention)** — operator convenience

Items 1-5 unblock the frontend (staff + customer dashboards). Items 6-8 are operator-only and can ship later.

---

## What the frontend owns (NOT this spec)

Once the backend ships, the frontend work is:
- Replace `dashboard.tsx` hardcoded `ROWS` with `GET /api/staff/cases` data
- Wire the brief download via `fetch` + Supabase session token (not `<a>`)
- Build `/my-cases` customer dashboard route
- Build `/operator` operator route
- Replace the role-switcher (preview-only) with the actual role from the JWT

This spec is **backend-only**. Frontend will write its own spec once these contracts are live.

---

## Legal lines that still hold

- **Injury firewall (CD-R3):** panel_shop_staff never sees injury-escalated cases; the staff case queue filters by role. No customer-side injury monetisation surfaces anywhere.
- **RLS:** all case data reads are gated server-side by Supabase Row Level Security. The UI auth gate is convenience.
- **Audit:** every dashboard read of case data fires an audit event (case_viewed / cases_listed). The operator dashboard's audit viewer is the operator's eyes on this trail.
- **No PII in URLs:** all case refs are opaque `GF-XXXXXXXX` strings; customer identity travels in JWT claims + headers, not query params.

---

*Spec prepared 2026-07-15 on Mac Studio. Companion to RECEPTIONIST-ROBOT-SPEC. Backend chat: implement the endpoints above, then ping the frontend chat to wire the dashboards.*
