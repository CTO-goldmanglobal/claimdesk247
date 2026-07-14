# Evidence Storage — Setup Runbook

**Goal:** stand up the AWS S3 Sydney two-tier evidence bucket + IAM + lifecycle
rule, wire the env vars into Vercel, and verify the upload pipeline end-to-end.

**Audience:** deployer / ops.
**Related:** `stage-4/legal/EVIDENCE-UPLOAD-DESIGN-2026-07-14.md` (the why),
`stage-4/db/0004_evidence_metadata.sql` (the metadata schema),
`stage-4/app/evidence_store.py` (the code).

---

## 0. Prerequisites

* An AWS account.
* The Supabase project URL + service-role key (already used by the engine).
* `psql` access to the Supabase Postgres (or the SQL editor in the dashboard).
* Vercel project access (to set env vars on the engine deployment).

---

## 1. Create the S3 bucket (Sydney, private, encrypted)

**AWS console → S3 → Create bucket**

| Field | Value |
|---|---|
| **Bucket name** | `claimdesk247-evidence-prod` (or your environment-specific name). Must be globally unique. |
| **Region** | `Asia Pacific (Sydney) ap-southeast-2` ← **NON-NEGOTIABLE** (privacy notice promises Australia-only). |
| **Object Ownership** | Bucket owner enforced |
| **Block Public Access settings** | ☑ Block **all** public access ← **NON-NEGOTIABLE** |
| **Bucket Versioning** | Enable (recommended; lets the lifecycle rule's `NoncurrentVersionExpiration` work + gives you a rollback path) |
| **Default encryption** | Server-side encryption with AWS KMS keys (SSE-KMS). Use the AWS-managed key `aws/s3` for v1; create a CMK for production (§5 below). |
| **Advanced → Object Lock** | Optional but **recommended** for production (see design doc §9). Must be set at creation; cannot be retrofitted. |

Click **Create bucket**. Verify the bucket appears with **Access = Bucket and objects not public**.

### Equivalent AWS CLI

```bash
aws s3api create-bucket \
  --bucket claimdesk247-evidence-prod \
  --region ap-southeast-2 \
  --create-bucket-configuration LocationConstraint=ap-southeast-2

aws s3api put-public-access-block \
  --bucket claimdesk247-evidence-prod \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3api put-bucket-encryption \
  --bucket claimdesk247-evidence-prod \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'
```

---

## 2. Create the IAM user + least-privilege policy

The engine talks to S3 from a Vercel serverless function using an IAM user's
access key. Scope the policy to **this one bucket only**.

**AWS console → IAM → Users → Create user**

* Name: `claimdesk247-evidence-engine`
* Access type: **Programmatic access**
* Attach policy → Create policy → JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EvidenceBucketObjectOps",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload"
      ],
      "Resource": "arn:aws:s3:::claimdesk247-evidence-prod/*"
    },
    {
      "Sid": "EvidenceBucketList",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": "arn:aws:s3:::claimdesk247-evidence-prod"
    },
    {
      "Sid": "EvidenceBucketLifecycle",
      "Effect": "Allow",
      "Action": [
        "s3:GetLifecycleConfiguration",
        "s3:PutLifecycleConfiguration"
      ],
      "Resource": "arn:aws:s3:::claimdesk247-evidence-prod"
    }
  ]
}
```

(Replace `claimdesk247-evidence-prod` with your actual bucket name.)

Attach the policy to the user, then **create an access key**. Record the
`Access key ID` and `Secret access key` — you'll set them as Vercel env vars
next. **NEVER commit these to the repo.**

---

## 3. Set env vars (local + Vercel)

### Local dev (`.env` — copy from `.env.example`)

```bash
EVIDENCE_BUCKET_NAME=claimdesk247-evidence-prod
EVIDENCE_S3_REGION=ap-southeast-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-southeast-2
# Optional but recommended for prod:
# EVIDENCE_KMS_KEY_ID=arn:aws:kms:ap-southeast-2:ACCOUNT:key/KEY-ID
EVIDENCE_MAX_FILE_MB=10
EVIDENCE_MAX_FILES_PER_CASE=20
EVIDENCE_SIGNED_URL_TTL=900
```

### Vercel project env vars

Set the same vars in the engine's Vercel project (Project → Settings →
Environment Variables). Scope them to **Production + Preview** (the serverless
function reads them at runtime). Redeploy the engine after saving.

> **Note on `EVIDENCE_S3_REGION`:** keep it `ap-southeast-2`. The privacy
> notice promises Australia-only storage. Changing it without a legal basis
> is a compliance violation.

---

## 4. Apply the metadata table to Postgres

Run `stage-4/db/0004_evidence_metadata.sql` in the Supabase SQL editor.
Run order: `0002 → 0003 → 0004`. The migration creates:

* `public.case_evidence` (the metadata table)
* A trigger enforcing the 20-file-per-case cap
* A trigger blocking updates to the integrity columns (hash, key, size)
* RLS policy mirroring `intake_sessions` (staff read, anon/customer blocked)

Verify with:

```sql
-- Should return 0 (anon has no access; this is from a staff session):
SELECT count(*) FROM public.case_evidence;

-- Should ERROR (integrity columns are immutable):
UPDATE public.case_evidence SET content_hash_sha256 = 'x' WHERE false;
-- → ERROR: case_evidence integrity fields are immutable
```

---

## 5. Apply the lifecycle rule

The two-tier lifecycle (Standard → Glacier Deep Archive at 90 days, expire at
retention horizon) is the cost + retention mechanism.

### Option A — opt-in script (recommended)

```bash
EVIDENCE_BUCKET_NAME=claimdesk247-evidence-prod \
AWS_ACCESS_KEY_ID=AKIA... \
AWS_SECRET_ACCESS_KEY=... \
AWS_REGION=ap-southeast-2 \
python3 stage-4/scripts/apply_evidence_lifecycle.py

# Dry-run first to see the rule:
python3 stage-4/scripts/apply_evidence_lifecycle.py --dry-run

# Override retention (MUST match {{RETENTION_PERIOD}}):
EVIDENCE_RETENTION_DAYS=2555 python3 stage-4/scripts/apply_evidence_lifecycle.py
```

The script is idempotent — re-running replaces the lifecycle config. It
warns loudly if the region is not `ap-southeast-2`.

### Option B — AWS console

S3 → bucket → Management → Lifecycle configuration → Add rule:

* Apply to **whole bucket** (prefix `*`)
* Transition: `Standard → Glacier Deep Archive` after **90 days**
* Expire current version: after **2555 days** (= 7 years; must match `{{RETENTION_PERIOD}}`)
* Expire noncurrent versions: after **2555 days**
* Rule name: `claimdesk247-evidence-two-tier`

Save. Re-apply if the retention period ever changes (rare; legal-driven).

---

## 6. (Recommended for prod) Create a Customer Managed Key

The default AWS-managed key (`aws/s3`) is fine for staging. For production:

1. KMS → Customer managed keys → Create key → Symmetric → Encrypt/Decrypt → Region: `ap-southeast-2`.
2. Give the engine IAM user `kms:GenerateDataKey` + `kms:Decrypt` on the key.
3. Set `EVIDENCE_KMS_KEY_ID` to the key ARN in Vercel.

This gives you CloudTrail on every key use + independent rotation.

---

## 7. Verify end-to-end

After deploy, smoke-test the full pipeline:

```bash
# 1. Health check (engine is up)
curl https://<your-engine>/healthz

# 2. Create a session + grant consent
REF=$(curl -s -X POST https://<your-engine>/api/session \
  -H 'content-type: application/json' -d '{"channel":"web"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["reference"])')
curl -X POST https://<your-engine>/api/consent \
  -H 'content-type: application/json' \
  -d "{\"reference\":\"$REF\",\"accept\":true}"

# 3. Upload a test image (the smallest valid 1x1 PNG works for smoke)
curl -X POST "https://<your-engine>/api/intake/$REF/evidence" \
  -F 'file=@test.png;type=image/png'
# Expect: 200, JSON with sha256, s3_key, signed_url

# 4. Confirm the object landed in S3
aws s3 ls s3://claimdesk247-evidence-prod/$REF/ --region ap-southeast-2

# 5. Confirm the metadata row exists
psql $DATABASE_URL -c \
  "SELECT evidence_id, reference, s3_key, content_hash_sha256 FROM public.case_evidence WHERE reference = '$REF';"

# 6. Confirm the audit log entry
psql $DATABASE_URL -c \
  "SELECT entry_id, action, inputs->>'sha256' AS sha FROM audit_log WHERE session_id IN (SELECT session_id FROM intake_sessions WHERE reference = '$REF') AND action = 'evidence_uploaded';"

# 7. Confirm the signed URL works (should return the bytes)
curl -I "$(curl -s 'https://<your-engine>/api/intake/'$REF'/evidence' | python3 -c 'import sys,json;print(json.load(sys.stdin)["items"][0]["signed_url"])')"
# Expect: HTTP/1.1 200 OK, Content-Type: image/png

# 8. Confirm the case view binds everything
curl "https://<your-engine>/api/case/$REF"
# Expect: {"reference":"...","evidence_count":1,"pdf_url":"/api/pdf/...","intake_completed":...}
```

---

## 8. Runbook maintenance

* **Retention period change** (rare, legal-driven): update `{{RETENTION_PERIOD}}`,
  re-run `apply_evidence_lifecycle.py --retention-days N`. Existing objects
  keep their old expiration; only future uploads pick up the new rule. If you
  need to shorten retroactively, do it via a one-off S3 batch operation with
  legal sign-off.
* **Adding a new file type** (e.g. PDF evidence): update `ALLOWED_IMAGE_TYPES`
  + magic-byte sniff in `evidence_store.py`, the multipart `allowed_mime_types`
  on the bucket (if you set it), and the SQL migration's `content_type` CHECK
  if you add one. Add an acceptance test.
* **Disaster recovery**: S3 cross-region replication to a second Sydney
  bucket is the standard DR pattern. Out of scope for v1.

## 9. Retention scheduler (EventBridge → Lambda → run_evidence_retention.py)

The S3 lifecycle rule (§5) handles tiered storage (Standard → Glacier Deep Archive
@ 90d) and final expiration at the retention horizon. The **scheduler script**
`stage-4/scripts/run_evidence_retention.py` is the per-case complement: it
soft-deletes the `case_evidence` metadata rows for cases past retention so
signed URLs stop resolving, while preserving the append-only audit log entries.

Wire it as an EventBridge-scheduled Lambda:

1. **Build the Lambda zip:**
   ```bash
   cd stage-4/scripts
   python3 -m pip install --target ./lambda-deps supabase boto3
   zip -r claimdesk247-evidence-retention.zip \
       run_evidence_retention.py ../app/evidence_store.py lambda-deps/
   ```
2. **Create the Lambda** (Python 3.12, handler `run_evidence_retention.main`,
   timeout 5 min, memory 512 MB). Env vars: `EVIDENCE_BUCKET_NAME`,
   `AWS_REGION=ap-southeast-2`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   (store the key in Secrets Manager, not inline, for prod),
   `EVIDENCE_RETENTION_DAYS=2555`.
3. **IAM role** — least-privilege: `s3:ListBucket`, `s3:DeleteObject`,
   `s3:GetObject` (for list/delete only) on `arn:aws:s3:::claimdesk247-evidence-prod/*`,
   plus the Lambda basic execution role.
4. **EventBridge rule**: schedule `rate(1 day)` (or `cron(0 2 * * ? *)` for
   02:00 UTC). Target the Lambda. Enable logging on the rule.
5. **Verify after first run**: check CloudWatch Logs for the script's stdout
   (`Total purged: N object(s)`). The audit log should show no entries from
   this script (audit entries are preserved — the script only deletes S3 +
   soft-deletes metadata).

**One-off local run** (manual purge, e.g. before a retention-period change):
```bash
EVIDENCE_BUCKET_NAME=claimdesk247-evidence-prod \
AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_REGION=ap-southeast-2 \
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
python3 stage-4/scripts/run_evidence_retention.py --dry-run
```
