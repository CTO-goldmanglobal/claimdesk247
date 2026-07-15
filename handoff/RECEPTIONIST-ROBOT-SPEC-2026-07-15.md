# Receptionist Robot Spec — ClaimDesk 247

**Date:** 2026-07-15
**Status:** Spec for the frontend chat to implement. Backend endpoints are live.
**Scope:** Customer-facing robot at `/intake`. Replaces today's form-with-chat-bubbles with a real conversational receptionist that builds the case file, captures identity, uploads photos in-chat, and hard-firewalls injury matters.

**Legal baseline (CD-R3, non-negotiable):** the robot CANNOT collect injury leads. Any injury mention → hard stop → escalate to human callback. No monetisation, no per-lead fee, no referral. The engine already enforces this (`esc-injury`, fail-closed). The frontend must honour it.

---

## 1. What changes from today

| Today | Receptionist vision |
|---|---|
| Form fields with chat bubbles painted on | One question at a time, button choices, real transcript |
| Engine collects accident facts only | Engine also collects customer identity (name, mobile, email) |
| No login — `?ref=` is the only "memory" | Supabase Auth (email magic link) → customer comes back, sees their cases |
| Photo upload is a separate uploader AFTER classification | Photo upload is INLINE in the chat ("any photos of the damage? Tap to upload") |
| No case readback | Robot uses `/api/intake/{ref}/review` after each answer to phrase the next question contextually |
| Rigid: question → next question | Customer can scroll up, correct prior answers, add notes |

---

## 2. Identity capture (NEW — engine slots + Supabase Auth, synced)

### 2.1 New engine slots

Add three new slots to every claim-type branch in `stage-3/app/state_machine.py`:

| Slot | Type | Options | Mandatory | When asked |
|---|---|---|---|---|
| `customer_name` | text | — | yes | First thing after consent |
| `customer_mobile` | text | — | yes | After name |
| `customer_email` | text | — | yes | After mobile (drives the magic-link login) |

These are NOT optional — the lawyer cannot call back without them. The engine validates + audit-logs them like any other slot.

**Backend work (this chat, next):**
- Add the three slots to `MOTOR_SLOTS`, `PD_SLOTS`, `PL_SLOTS`, `MEDNEG_SLOTS`
- They come AFTER consent, BEFORE the state question
- The PDF (`pdf_gen.py`) must include them in the brief so the lawyer has them
- The intake brief (`intake_brief.py`) must include them

### 2.2 Supabase Auth (login → memory → come back)

**Frontend owns this** (Supabase JS SDK runs in the browser):

1. After the customer enters their email, the frontend calls `supabase.auth.signInWithOtp({ email })` — magic link lands in their inbox
2. Customer clicks → Supabase redirects back to `/intake?ref=<existing-ref>` with a session
3. Frontend calls a NEW backend endpoint `POST /api/session/{ref}/bind-user { supabase_user_id }` to bind the case to their auth identity
4. On return visits, the customer logs in → frontend lists their cases via `GET /api/cases?user_id=<supabase_user_id>` (NEW endpoint, returns all cases bound to that user)

**Backend work (this chat, next):**
- `POST /api/session/{ref}/bind-user` — binds a Supabase user_id to the session; audit-logs `case_bound_to_user`
- `GET /api/cases?user_id=<id>` — returns all sessions bound to that user (consent-gated per case)
- Session dataclass gets a new field: `supabase_user_id: Optional[str]`

### 2.3 Sync between engine slots and Supabase Auth

The engine slots (`customer_name`, `customer_mobile`, `customer_email`) are the source of truth for the case file (lawyer brief). The Supabase `auth.users` table is the source of truth for login. They sync at bind time:

```
Customer enters email in chat
  → engine stores customer_email slot
  → frontend calls supabase.auth.signInWithOtp({ email })
  → customer clicks magic link
  → frontend calls POST /api/session/{ref}/bind-user { supabase_user_id }
  → engine records supabase_user_id on the session
  → future logins: GET /api/cases?user_id=<id> returns this case
```

If the customer changes their email in Supabase later, the engine's `customer_email` slot is NOT auto-updated (it's the email they gave at intake — evidentiary). The `supabase_user_id` is the stable link.

---

## 3. Chat UX (frontend owns — but here's the contract)

### 3.1 Question display + choices

Every question from the engine returns:

```typescript
{
  slot: "user_position",
  prompt: "Where were you in the collision?",
  inputType: "enum" | "multienum" | "text",
  options: ["front", "behind", "middle_of_chain"],   // null for text
  done: false
}
```

The frontend renders:
- **enum** → button group (one tap to answer)
- **multienum** → chip multi-select (tap multiple, then "Done")
- **text** → text input with a "Send" button

After the customer answers, the robot replies with a confirmation chip ("Got it — you were the front car") and the next question appears below. Scroll up to see history.

### 3.2 Contextual phrasing using `/api/intake/{ref}/review`

After every 3-4 answers, the frontend calls `GET /api/intake/{ref}/review`. The response includes `slots_filled` + `notes_count`. The robot uses this to phrase the next question:

- Slots filled = 3 → "Got your vehicle, the other driver, and the damage. Was anyone hurt?"
- Slots filled = 7 → "I've got the full picture of the accident. Let's get your contact details so we can call you back."

### 3.3 Injury firewall in the chat (CD-R3 — non-negotiable)

When the customer answers `injuries: minor` or `injuries: serious` (or types anything injury-suggestive in a note — the engine's `esc-injury` is fail-closed on any value ≠ "none"), the engine returns:

```typescript
{ escalation: "esc-injury", band: null, end_state: "SX-ESCALATE", reference: "GF-XXXXXXXX" }
```

The frontend MUST:
1. Stop the question flow immediately
2. Show a calm handoff message: *"I'm sorry to hear that. I'm going to stop our chat here and have a real person call you. Your safety and recovery come first. Your reference is GF-XXXXXXXX."*
3. Display the reference number prominently
4. NOT show any band, NOT ask for more details, NOT offer to "continue anyway"

The lawyer/human calls the customer back. No lead-generation, no per-lead fee, no referral consideration — the engine records `esc-injury` on the audit trail and that's it.

### 3.4 In-chat photo/doc upload

After the customer answers the core accident questions (state, vehicles, damage, etc.), the robot offers photo upload **inline in the chat**:

> *"Great — I've got the accident details. Do you have any photos of the damage? Tap to upload (up to 20 photos, 10MB each)."*

The frontend calls `POST /api/intake/{ref}/evidence` for each file (the endpoint already exists, live since last night). Thumbnails render in the chat as the robot "receiving" them:

> *"Got the rear-damage photo. Anything else? Side angle? The other vehicle?"*

This is NOT a separate uploader screen — it's part of the conversation.

---

## 4. PD disclosure (legal compliance — already built)

For property-damage intakes, before the customer consents, the frontend MUST:

1. Call `GET /api/disclosure/property_damage?ref=<ref>` → returns the disclosure text + hash
2. Render the text in a scrollable box ABOVE the consent button
3. The consent button is DISABLED until the customer scrolls to the bottom (or taps "I've read this")
4. Customer taps "I consent" → frontend calls `POST /api/consent { reference, accept: true }`
5. Engine fires `pd_disclosure_acknowledged` audit event (carries the disclosure_hash — evidentiary)

**Already built and live.** Frontend just needs to call the endpoint and render the text.

---

## 5. Case readback / "memory"

When the customer returns (via Supabase Auth login or `?ref=` deep link):

1. Frontend calls `GET /api/intake/{ref}/review`
2. Response includes: every slot filled, every note, the band/escalation, evidence count
3. Robot greets: *"Hi {customer_name} — I've got your case GF-XXXXXXXX. Last time we spoke, you'd told me about the rear-end on Parramatta Rd. Anything you'd like to add or correct?"*
4. Customer can:
   - Add a note: `POST /api/intake/{ref}/note { text, source: "chat", kind: "addition" }`
   - Upload more photos: `POST /api/intake/{ref}/evidence`
   - (Future) Correct a prior answer: `PATCH /api/slot/{ref}` — NOT YET BUILT

---

## 6. Backend contract summary (what's live + what's new)

### Already live (frontend can wire now)

| Endpoint | Purpose |
|---|---|
| `POST /api/session` `{channel, prefill?}` | Start session; prefill from checklist PWA |
| `POST /api/consent` `{reference, accept}` | Grant consent |
| `GET /api/disclosure/property_damage?ref=<ref>` | PD disclosure text + hash (render before consent) |
| `POST /api/slot` `{ref, slot, value}` | Answer one question |
| `POST /api/classify` `{ref}` | Get the band |
| `POST /api/intake/{ref}/evidence` (multipart) | Upload a photo |
| `GET /api/intake/{ref}/evidence` | List photos |
| `GET /api/intake/{ref}/note` | (via POST) Add a free-text note |
| `GET /api/intake/{ref}/review` | Full case readback (slots + notes + band) |
| `GET /api/case/{ref}` | Customer-facing case summary |
| `GET /api/pdf/{ref}` | Download PDF (consent-gated) |

### NEW — backend work needed (this chat, next session)

| Endpoint | Purpose |
|---|---|
| `POST /api/session/{ref}/bind-user` `{supabase_user_id}` | Bind case to Supabase auth identity |
| `GET /api/cases?user_id=<id>` | List all cases for a logged-in user |
| `PATCH /api/slot/{ref}` `{slot, value}` | Correct a prior answer (append-only audit) |

### NEW — engine slots (this chat, next session)

| Slot | Type | Mandatory | Branches |
|---|---|---|---|
| `customer_name` | text | yes | ALL (motor, PD, PL, med-neg) |
| `customer_mobile` | text | yes | ALL |
| `customer_email` | text | yes | ALL (drives magic-link login) |

These come AFTER consent, BEFORE state_of_accident. The PDF + intake brief must include them.

---

## 7. Injury firewall — the red line (CD-R3)

**The robot NEVER:**
- Collects injury details beyond "was anyone hurt? (yes/no)"
- Asks about injury severity, body parts affected, treatment received
- Offers to "connect you with a personal injury lawyer"
- Monetises the injury matter in any way

**The robot ALWAYS:**
- Stops the conversation on any injury mention
- Escalates to `esc-injury`
- Routes to a human callback (law-firm partner, zero consideration)
- Records the escalation on the audit trail

This is not a product preference — it is the legal line that keeps ClaimDesk 247 outside the NSW claim-farming prohibition (CD-R3, two 2025 statutes, up to $55k/offence + 10yr for dishonest conduct).

---

## 8. Implementation order (frontend chat)

1. **Identity slots** (waiting on backend — next session)
2. **Chat UX redesign** (buttons, scroll history, contextual phrasing) — can start now against existing endpoints
3. **In-chat photo upload** (endpoint exists — wire it inline)
4. **PD disclosure rendering** (endpoint exists — wire before consent)
5. **Supabase Auth + case binding** (waiting on backend — next session)
6. **Case readback on return** (endpoint exists — wire the greeting)

Frontend can start on items 2-5 immediately. Items 1 + 6 need the backend work below.

---

## 9. Implementation order (backend chat — next session)

1. Add `customer_name`, `customer_mobile`, `customer_email` slots to all branches
2. Update PDF + intake brief to include identity
3. `POST /api/session/{ref}/bind-user` endpoint
4. `GET /api/cases?user_id=<id>` endpoint
5. `PATCH /api/slot/{ref}` endpoint (correct prior answers — append-only audit)
6. Tests for all of the above

---

*Spec prepared 2026-07-15. Backend endpoints are live on https://claimdesk247-engine.vercel.app. Legal baseline: CD-R3 (injury firewall non-negotiable).*
