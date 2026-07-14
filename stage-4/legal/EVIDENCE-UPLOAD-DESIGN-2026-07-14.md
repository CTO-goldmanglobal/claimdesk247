# Evidence Upload — Design Document

**Status:** Approved (user-confirmed 2026-07-14, pivot from Supabase Storage)
**Author:** Engineering
**Audience:** Legal reviewer, CTO, deployer
**Related:** `stage-4/EVIDENCE-STORAGE-SETUP.md` (runbook), `stage-4/db/0004_evidence_metadata.sql` (schema), `stage-4/app/evidence_store.py` (impl)

---

## 1. Purpose

Customers photograph their vehicle damage at the accident scene. Those photos
plus the intake summary PDF become ONE bound case file: a single reference
(`GF-XXXXXXXX`) points at the intake session, the uploaded evidence, and the
generated PDF. This document specifies the storage + API design and the
compliance properties it preserves.

The real need this serves: a customer's case file must be (a) bound together,
(b) tamper-evident, (c) retrievable by staff and the customer's lawyer for the
retention period (7 years default), and (d) hosted in Australia per the
privacy notice. This design meets all four.

---

## 2. Why S3 Sydney two-tier (not the alternatives)

| Option | Verdict | Reason |
|---|---|---|
| **AWS S3, Sydney (`ap-southeast-2`), two-tier** | **CHOSEN** | AU region (privacy-notice compliant), uncapped, cheap once the lifecycle rule is applied, mature audit + IAM surface, private-by-default buckets, signed URLs. |
| Supabase Storage | Rejected | ~8GB project ceiling — photo evidence fills it within months at the case volume we expect. Otherwise fine (same region, same RLS). |
| Google Drive | Rejected | US-hosted. Breaks the privacy notice's "stored in Australia" promise and the engine's immutability posture (no WORM, audit surface outside our control). |
| Mac Studio (on-prem) | Rejected | Single-machine uptime is a legal-evidence risk. Power loss / disk failure / coffee spill = lost evidence. AWS gives 11×9s durability across multiple Sydney AZs. |

### Cost model (Sydney region, AUD excl. GST, indicative)

* S3 Standard: ~$0.0255 / GB / month
* S3 Glacier Deep Archive: ~$0.0011 / GB / month
* At 500 GB blended (90 days Standard, then Glacier Deep Archive):
  ~**$3–5 / month** total. The 90-day lifecycle transition is what makes it
  cheap — most evidence slides to Glacier within a quarter.
* Client-side resize (1600px / JPEG q80, see §6) shrinks each upload ~13×
  (4 MB → ~300 KB), so the same case volume costs ~13× less again. This is
  the single biggest cost lever and it is free.

---

## 3. Architecture

```
                          ┌─────────────────────────────────────────┐
   Customer browser       │  stage-2.5/app/wrap.py                  │
   (lovable-ui)           │  POST /api/intake/{ref}/evidence        │
   ─────────────────────► │  GET  /api/intake/{ref}/evidence        │
                          │  GET  /api/case/{ref}                   │
   1) resize on device    │                                         │
   2) multipart upload    │  ┌── consent gate (403 if no consent)   │
                          │  ├── validate (image-only, size, count) │
                          │  ├── SHA-256 hash                       │
                          │  ├── upload to S3EvidenceStore ─────────┼──► AWS S3
                          │  ├── append audit_log ──────────────────┼──► Postgres
                          │  └── write case_evidence row ───────────┘   (audit_log,
                          └─────────────────────────────────────────┘    case_evidence)
```

Two adapters behind one `EvidenceStore` Protocol:

* **`S3EvidenceStore`** (production, lazy-imports `boto3`)
* **`InMemoryEvidenceStore`** (dev / CI / acceptance tests — no AWS needed)

The HTTP layer never branches on storage backend. Tests run against the
InMemory adapter; production picks S3 based on env vars.

---

## 4. API shape

All endpoints are consent-gated server-side (the same gate as `/api/slot` —
the engine refuses the call with `403 consent required` if the session hasn't
passed `/api/consent`). The session reference is the only PII-adjacent value
in any URL, and it is opaque (`GF-XXXXXXXX`).

### `POST /api/intake/{ref}/evidence`
* **Body:** multipart/form-data, field `file`
* **Validation (server-side, defense-in-depth):**
  * Magic-byte sniff against `{image/jpeg, image/png, image/webp, image/heic, image/heif}`
  * Size ≤ `EVIDENCE_MAX_FILE_MB` (default 10 MB)
  * Per-case count ≤ `EVIDENCE_MAX_FILES_PER_CASE` (default 20)
* **Returns 200:** `EvidenceRecord` (file_id, s3_key, sha256, signed_url, …)
* **Returns 400:** validation failure (clear customer-facing reason)
* **Returns 403:** consent not granted (the resource exists; you may not touch it)
* **Audit:** writes one `evidence_uploaded` entry with sha256, filename, content_type, size

### `GET /api/intake/{ref}/evidence`
* **Returns 200:** `{reference, count, items: [EvidenceRecord]}` — each item carries a freshly-minted signed URL (short TTL)
* **Returns 403:** consent not granted
* **Audit:** writes one `evidence_listed` entry (file_ids enumerated, so a leak of the reference is detectable)

### `GET /api/case/{ref}`
* The bound case file: `{reference, state, band, evidence, evidence_count, pdf_url, intake_completed}`
* Same consent gate
* **Audit:** writes one `case_viewed` entry
* This is the surface the customer sees once they've uploaded photos and run
  classification — "your case file": reference + photos + PDF download.

---

## 5. Bucket schema + object layout

* **Bucket:** `EVIDENCE_BUCKET_NAME` (e.g. `claimdesk247-evidence-prod`)
* **Region:** `ap-southeast-2` (hardcoded default; `EVIDENCE_S3_REGION` override exists but should never be set to anything else)
* **Public access:** BLOCKED (non-negotiable). All reads via signed URLs.
* **Encryption:** SSE-KMS, always. AWS-managed key (`aws/s3`) by default; CMK via `EVIDENCE_KMS_KEY_ID` for production.
* **Object key:** `{reference}/{uuid}.{ext}` — reference is the opaque `GF-XXXXXXXX`, never a customer name.

### Object metadata (set on upload via S3 `Metadata`):
* `original-filename` (for the dashboard; PII-adjacent but never indexed)
* `sha256` (mirror of the audit row; tamper-evidence)
* `uploaded-by` (client IP for customer, email for staff)
* `content-type` (canonical image MIME)

### Lifecycle rule (applied by `apply_evidence_lifecycle.py` or AWS console):
* `Standard → Glacier Deep Archive` at **90 days**
* `Expire (delete)` at `{{RETENTION_PERIOD}}` days (default **2555 = 7 years**)
* MUST match the engine's `RETENTION_PERIOD` token

### Metadata table — `public.case_evidence` (see `db/0004_evidence_metadata.sql`):
* Columns: `evidence_id, reference, s3_key, s3_bucket, content_type, size_bytes, content_hash_sha256, uploaded_at, uploaded_by, deleted_at, storage_class`
* Integrity columns (hash, key, size, content_type, reference) are IMMUTABLE post-insert via trigger
* Per-case count cap of 20 enforced via trigger (belt-and-braces against concurrent uploads)
* RLS: staff read, service_role write, anon/customer blocked (customer reads go through signed URLs)

---

## 6. Compliance properties preserved

| Property | How this design preserves it |
|---|---|
| **Consent gate** | Server-side check in `_require_session_with_consent()` — every upload/list/case-view refuses with 403 if the session hasn't passed `/api/consent`. UI cannot bypass. |
| **Audit log immutability** | Every upload/list/delete writes to `audit_log`, which is append-only at the DB level (migration `0003`) AND via trigger (UPDATE/DELETE blocked for every role). |
| **Tamper-evidence** | Each file's SHA-256 is recorded in: (a) the audit_log entry on upload, (b) the `case_evidence.content_hash_sha256` column, (c) the S3 object metadata. Three independent records to compare. |
| **AU region** | Bucket in `ap-southeast-2`. Default region is hardcoded; the env override is documented as "do not change without a legal basis". |
| **No PII in URLs / object keys** | Object key is `{reference}/{uuid}.{ext}` — reference is opaque, uuid is opaque. Signed URLs are short-TTL (default 15 min). |
| **Private-by-default** | Bucket has block-all-public-access. All reads via server-minted signed URLs after the consent/auth check. |
| **Image-only / size / count caps** | Magic-byte sniff rejects anything that isn't a real image (renamed `.exe` is caught). Per-file size cap + per-case count cap. Validated in the store AND in the DB trigger. |
| **Retention** | Lifecycle rule transitions to Glacier at 90 days, expires at the retention horizon. The `delete_for_retention()` adapter method exists for a future scheduled job (TODO: scheduler not built). |

---

## 7. Encryption posture

* **At rest:** SSE-KMS, always on. AWS-managed key by default; the runbook
  recommends a Customer Managed Key for production so you get CloudTrail on
  key use + independent rotation.
* **In transit:** all S3 API calls are TLS (HTTPS endpoint). The signed URLs
  minted for the browser are HTTPS.
* **Client-side:** the browser resize happens on the customer's device BEFORE
  upload. We never receive the original full-resolution bytes; we receive the
  resized-for-evidence JPEG. The customer's original is untouched on their
  device.

---

## 8. Hash chain

Each upload produces three records of the same SHA-256:

1. **`audit_log.inputs.sha256`** — written on upload (append-only)
2. **`case_evidence.content_hash_sha256`** — written on upload (immutable trigger)
3. **S3 object metadata `sha256`** — set on PUT (immutable unless versioned)

To verify integrity later: re-hash the object bytes (via signed GET), compare
to all three. Mismatch on (1) or (2) means the metadata was tampered with
(should be impossible given the triggers). Mismatch on (3) means the object
itself was replaced (impossible given the IAM scope + bucket policy).

---

## 9. S3 Object Lock (RECOMMENDATION, not enabled by default)

For full WORM (write-once-read-many) — i.e.legal-hold-grade immutability —
enable **S3 Object Lock** on the bucket at creation time in Compliance mode
with the retention period matching `{{RETENTION_PERIOD}}`. This would prevent
even the root account from deleting an object before retention expires.

This is **not enabled by default** because:
* It must be set at bucket creation (cannot be retrofitted to an existing bucket).
* It complicates the legitimate delete-on-RTBF (right-to-be-forgotten) path,
  which the retention purge needs to honour.

**Recommendation:** enable Object Lock on the production bucket at creation.
Document the RTBF override path (legal-hold release via break-glass IAM role)
before going live with real customer data.

---

## 10. Open items / TODOs

* **Retention scheduler** — `EvidenceStore.delete_for_retention()` exists but
  no scheduled job calls it yet. Recommended: an EventBridge cron that runs
  nightly, queries `case_evidence` for rows past the horizon, and calls the
  delete method. Documented as a stub in `evidence_store.py`.
* **S3 Object Lock** — see §9.
* **Antivirus scan** — out of scope for v1; S3 doesn't malware-scan by default.
  A ClamAV-based scan-on-upload Lambda is the standard pattern. Add before
  going live if Legal requires it.
* **HEIC support** — the magic-byte sniff accepts HEIC, but Safari is the only
  browser that can resize it client-side; other browsers send the original
  HEIC through unchanged (server validates + stores it). Acceptable for v1.

---

## 11. Test coverage

Four new acceptance tests in `stage-2.5/tests/run_acceptance.py`:

| ID | What it asserts |
|---|---|
| `T-25-020` | Upload before `/api/consent` → 403 with "consent" in the detail |
| `T-25-021` | Upload after consent → 200, returns sha256 + s3_key + signed_url, audit entry written with matching hash |
| `T-25-022` | `GET /evidence` returns the uploaded item; `GET /case/{ref}` agrees + binds the PDF URL |
| `T-25-023` | Non-image (text lying as PNG) → 400; 11 MB JPEG → 400 with size in the detail |

All four run against `InMemoryEvidenceStore` locally (storage-agnostic) and
against the configured S3 bucket over the weblink runner. Full suite was
19/19 → now 23/23 (+4). Stage 3 (50) and the injury extension (26) untouched.
