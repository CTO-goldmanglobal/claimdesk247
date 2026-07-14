"""Evidence Storage Layer (Stage 4 — Feature 2).

Customer-uploaded photo evidence bound to an intake session reference.

**Storage decision (2026-07-14, user-confirmed):** AWS S3, Sydney region
``ap-southeast-2``, two-tier with a lifecycle rule (Standard → Glacier Deep
Archive at 90 days; expire at the retention horizon). See
``EVIDENCE-STORAGE-SETUP.md`` for the bucket + IAM + lifecycle runbook, and
``stage-4/legal/EVIDENCE-UPLOAD-DESIGN-2026-07-14.md`` for the rationale
(S3 Sydney two-tier vs Supabase Storage vs Google Drive vs Mac Studio).

This module ships two adapters behind one ``EvidenceStore`` Protocol:
  * ``S3EvidenceStore``        — production path (boto3, lazy-imported).
  * ``InMemoryEvidenceStore``  — local dev / CI / acceptance tests (no AWS).

The HTTP layer (``stage-2.5/app/wrap.py``) never branches on the backend —
the factory picks based on env vars. Both adapters enforce the same consent
contract via the HTTP layer and the same per-file validation here.

Object key layout: ``{reference}/{uuid}.{ext}`` — no PII in keys.
Encryption: SSE-KMS always (AWS-managed key by default; CMK if
``EVIDENCE_KMS_KEY_ID`` is set). Bucket is private, block-all-public-access.

The metadata pointer for each file lives in Postgres ``case_evidence`` (see
``db/0004_evidence_metadata.sql``) so the case-file view can enumerate
evidence without LISTing S3. The immutable audit chain (existing
``audit_log``) records every upload/list/delete with the SHA-256.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Protocol


# ----- Compliance constants (shared by every adapter) -----

# Images only for v1. We accept these MIME types and sniff them from magic
# bytes; the client's declared Content-Type is never trusted on its own.
ALLOWED_IMAGE_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
})

# Magic-byte sniff for the allowlist. Anything not matching is rejected even
# if the client lied about Content-Type (defense against renamed binaries).
_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),       # JPEG
    (b"\x89PNG\r\n\x1a\n", "image/png"),   # PNG
    (b"RIFF", "image/webp"),               # WebP (RIFF....WEBP)
]

# Per-file size cap. The frontend resizes to ~1600px / JPEG q80 (~300KB
# typical) before upload, so this cap is the safety net for raw originals.
MAX_FILE_BYTES: int = int(os.environ.get("EVIDENCE_MAX_FILE_MB", "10")) * 1024 * 1024

# Per-case count cap. Stops a runaway client from exhausting the bucket.
MAX_FILES_PER_CASE: int = int(os.environ.get("EVIDENCE_MAX_FILES_PER_CASE", "20"))

# Signed-URL TTL — short by design (G-44: no PII in URLs, short exposure).
SIGNED_URL_TTL_SECONDS: int = int(os.environ.get("EVIDENCE_SIGNED_URL_TTL", "900"))  # 15 min

# Default region. The privacy notice promises Australia-only storage; do NOT
# override unless you have a separate legal basis.
DEFAULT_S3_REGION = "ap-southeast-2"

# Extension → canonical MIME for object naming (we always persist a real ext).
_EXT_BY_MIME: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
}


class EvidenceValidationError(ValueError):
    """File failed validation (wrong type / too large / per-case cap hit).

    Carries a short, customer-facing ``reason`` the HTTP layer surfaces as 400.
    """


@dataclass
class EvidenceRecord:
    """One uploaded evidence file, bound to a case reference."""
    file_id: str             # uuid (also the S3 key stem)
    reference: str           # intake session reference (GF-XXXXXXXX, opaque)
    s3_key: str              # {reference}/{file_id}.{ext}  — never PII
    s3_bucket: str           # bucket name ( informational; helps the audit row)
    filename: str            # original customer filename (audit only)
    content_type: str        # canonical image MIME
    size_bytes: int
    sha256: str              # content hash — tamper-evidence
    uploaded_by: str         # actor (client IP for customer, email for staff)
    uploaded_at: str         # ISO-8601 UTC
    storage_class: str = "STANDARD"   # STANDARD | GLACIER_DEEP_ARCHIVE (post-lifecycle)
    signed_url: Optional[str] = None  # short-TTL read URL; None if mint failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "reference": self.reference,
            "s3_key": self.s3_key,
            "s3_bucket": self.s3_bucket,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at,
            "storage_class": self.storage_class,
            "signed_url": self.signed_url,
        }


class EvidenceStore(Protocol):
    """Storage-agnostic evidence interface used by the HTTP layer."""

    def upload(self, *, reference: str, content: bytes, content_type: str,
               filename: str, actor: str) -> EvidenceRecord: ...

    def list(self, *, reference: str) -> list[EvidenceRecord]: ...

    def signed_url(self, *, reference: str, file_id: str) -> Optional[str]: ...

    def delete_for_retention(self, *, reference: str,
                             older_than: datetime) -> list[str]: ...


# ----- Validation helpers (shared by every adapter) -----

def detect_content_type(content: bytes, declared: str) -> str:
    """Sniff the canonical image MIME from leading bytes.

    Returns the canonical type if it's in the allowlist. Raises
    ``EvidenceValidationError`` for anything else — a renamed executable or a
    non-image file is rejected even if the client lied about Content-Type.
    """
    if not content:
        raise EvidenceValidationError("Empty file.")
    # HEIC/HEIF needs a deeper check (the ftyp box prefix is generic).
    if len(content) >= 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        if brand in (b"heic", b"heix", b"hevc", b"heim", b"mif1"):
            # Treat mif1 with heif-derived brands as HEIF-family; we accept both.
            return "image/heic" if brand != b"mif1" else "image/heif"
    for magic, mime in _MAGIC_BYTES:
        if content.startswith(magic):
            if mime == "image/webp" and content[8:12] != b"WEBP":
                continue
            return mime
    raise EvidenceValidationError(
        f"File does not match any allowed image type (declared {declared!r})."
    )


def ext_for(content_type: str) -> str:
    return _EXT_BY_MIME.get(content_type, "bin")


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_file(*, content: bytes, declared_type: str,
                  current_count: int) -> str:
    """Run all per-file validations. Returns the canonical content type.

    Raises ``EvidenceValidationError`` with a customer-facing reason.
    """
    if current_count >= MAX_FILES_PER_CASE:
        raise EvidenceValidationError(
            f"You can attach up to {MAX_FILES_PER_CASE} photos per case."
        )
    if len(content) > MAX_FILE_BYTES:
        mb = MAX_FILE_BYTES / (1024 * 1024)
        raise EvidenceValidationError(
            f"Each photo must be under {mb:.0f} MB."
        )
    return detect_content_type(content, declared_type)


# =====================================================================
# Production adapter — AWS S3 (Sydney / ap-southeast-2), two-tier
# =====================================================================

class S3EvidenceStore:
    """Stores evidence files in a private S3 bucket in Sydney.

    Bucket (``EVIDENCE_BUCKET_NAME``) MUST be private with block-all-public-
    access enabled and SSE-KMS default encryption. Lifecycle rule transitions
    objects to Glacier Deep Archive at 90 days and expires them at the
    retention horizon — see ``apply_evidence_lifecycle.py`` and the runbook.

    boto3 is lazy-imported so this module loads cleanly in environments where
    boto3 isn't installed (CI, the weblink test runner); the factory only
    picks this adapter when AWS credentials + bucket are configured.
    """

    def __init__(self, *, bucket_name: str, region: str = DEFAULT_S3_REGION,
                 kms_key_id: Optional[str] = None) -> None:
        import boto3  # lazy: keep the test runner off the boto3 dep
        self._bucket = bucket_name
        self._region = region
        self._kms_key_id = kms_key_id
        self._s3 = boto3.client("s3", region_name=region)

    def upload(self, *, reference: str, content: bytes, content_type: str,
               filename: str, actor: str) -> EvidenceRecord:
        current = self.list(reference=reference)
        canonical = validate_file(
            content=content, declared_type=content_type,
            current_count=len(current),
        )
        ext = ext_for(canonical)
        file_id = str(uuid.uuid4())
        key = f"{reference}/{file_id}.{ext}"
        digest = sha256_hex(content)
        # SSE-KMS, always on. AWS-managed key by default; CMK if provided.
        # P2-1 fix (2026-07-14 review): also persist sha256, original
        # filename, and actor as object metadata so the S3-source-of-truth
        # read (DR / list-from-S3) returns complete records.
        put_args: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": key,
            "Body": content,
            "ContentType": canonical,
            "ServerSideEncryption": "aws:kms",
            "Metadata": {
                "sha256": digest,
                "original-filename": filename[:200],  # S3 metadata value cap
                "uploaded-by": (actor or "")[:200],
                "reference": reference,
            },
        }
        if self._kms_key_id:
            put_args["SSEKMSKeyId"] = self._kms_key_id
        self._s3.put_object(**put_args)
        uploaded_at = datetime.now(timezone.utc).isoformat()
        return EvidenceRecord(
            file_id=file_id, reference=reference, s3_key=key,
            s3_bucket=self._bucket, filename=filename, content_type=canonical,
            size_bytes=len(content), sha256=digest, uploaded_by=actor,
            uploaded_at=uploaded_at, storage_class="STANDARD",
            signed_url=self._mint_signed_url(key),
        )

    def list(self, *, reference: str) -> list[EvidenceRecord]:
        """LIST the prefix and HEAD each object for metadata.

        The Postgres ``case_evidence`` row is the authoritative index for the
        case-file view; this method is the S3-source-of-truth read used by the
        retention purge and by disaster recovery. Reads are scoped to the
        reference prefix — no cross-case enumeration.
        """
        out: list[EvidenceRecord] = []
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=f"{reference}/"):
            for obj in page.get("Contents", []) or []:
                head = self._s3.head_object(Bucket=self._bucket, Key=obj["Key"])
                # Recompute file_id from the key: {reference}/{uuid}.{ext}
                stem = obj["Key"].rsplit("/", 1)[-1]
                file_id = stem.rsplit(".", 1)[0] if "." in stem else stem
                meta = head.get("Metadata", {}) or {}
                out.append(EvidenceRecord(
                    file_id=file_id, reference=reference, s3_key=obj["Key"],
                    s3_bucket=self._bucket,
                    filename=meta.get("original-filename", ""),
                    content_type=head.get("ContentType", "application/octet-stream"),
                    size_bytes=obj.get("Size", head.get("ContentLength", 0)),
                    sha256=meta.get("sha256", ""),
                    uploaded_by=meta.get("uploaded-by", ""),
                    uploaded_at=obj["LastModified"].isoformat()
                                if obj.get("LastModified") else "",
                    storage_class=head.get("StorageClass",
                                           obj.get("StorageClass", "STANDARD")),
                    signed_url=self._mint_signed_url(obj["Key"]),
                ))
        # Oldest first (matches the audit-log ordering everywhere else).
        out.sort(key=lambda r: r.uploaded_at)
        return out

    def signed_url(self, *, reference: str, file_id: str) -> Optional[str]:
        # We don't know the extension from file_id alone; look it up.
        items = self.list(reference=reference)
        for it in items:
            if it.file_id == file_id:
                return self._mint_signed_url(it.s3_key)
        return None

    def delete_for_retention(self, *, reference: str,
                             older_than: datetime) -> list[str]:
        """Retention purge: delete the S3 objects. Soft-deletes the metadata
        row via the HTTP caller (which owns the DB adapter). The audit log
        entry is append-only and is NEVER removed.

        Returns the list of file_ids that were deleted so the caller can
        soft-delete the matching DB rows. Glacier-archived objects need a
        restore before delete; this implementation issues the delete and lets
        S3 handle it (Glacier Deep Archive supports direct DELETE without restore).
        """
        items = self.list(reference=reference)
        to_delete: list[dict[str, str]] = []
        deleted_file_ids: list[str] = []
        id_by_key: dict[str, str] = {}
        for it in items:
            try:
                ts = datetime.fromisoformat(it.uploaded_at)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if ts > older_than:
                continue
            to_delete.append({"Key": it.s3_key})
            id_by_key[it.s3_key] = it.file_id
        if not to_delete:
            return []
        self._s3.delete_objects(
            Bucket=self._bucket,
            Delete={"Objects": to_delete, "Quiet": True},
        )
        # Only count as deleted the keys we submitted; Quiet response omits
        # successful ones, so we trust the request unless the API ever returns
        # per-key Errors (would surface via exception).
        for d in to_delete:
            fid = id_by_key.get(d["Key"])
            if fid:
                deleted_file_ids.append(fid)
        return deleted_file_ids

    # ----- internal -----

    def _mint_signed_url(self, key: str) -> str:
        url = self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=SIGNED_URL_TTL_SECONDS,
        )
        return url


# =====================================================================
# Dev / test adapter — in-process (no AWS, no network)
# =====================================================================

class InMemoryEvidenceStore:
    """Drop-in ``EvidenceStore`` for local dev + the acceptance test runner.

    Mirrors ``S3EvidenceStore``'s public surface byte-for-byte so the tests
    exercise the same validation, hashing, and audit hooks as production.
    NOT for deployment: buffers are lost on process exit.
    """

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}                 # s3_key -> bytes
        self._rows: dict[str, EvidenceRecord] = {}           # file_id -> record
        self._bucket = "memory-evidence"

    def upload(self, *, reference: str, content: bytes, content_type: str,
               filename: str, actor: str) -> EvidenceRecord:
        current = self.list(reference=reference)
        canonical = validate_file(
            content=content, declared_type=content_type,
            current_count=len(current),
        )
        ext = ext_for(canonical)
        file_id = str(uuid.uuid4())
        key = f"{reference}/{file_id}.{ext}"
        digest = sha256_hex(content)
        self._objects[key] = content
        uploaded_at = datetime.now(timezone.utc).isoformat()
        rec = EvidenceRecord(
            file_id=file_id, reference=reference, s3_key=key,
            s3_bucket=self._bucket, filename=filename, content_type=canonical,
            size_bytes=len(content), sha256=digest, uploaded_by=actor,
            uploaded_at=uploaded_at, storage_class="STANDARD",
            signed_url=f"memory://signed/{key}?ttl={SIGNED_URL_TTL_SECONDS}",
        )
        self._rows[file_id] = rec
        return rec

    def list(self, *, reference: str) -> list[EvidenceRecord]:
        rows = [r for r in self._rows.values() if r.reference == reference]
        rows.sort(key=lambda r: r.uploaded_at)
        return rows

    def signed_url(self, *, reference: str, file_id: str) -> Optional[str]:
        rec = self._rows.get(file_id)
        if rec is None or rec.reference != reference:
            return None
        return f"memory://signed/{rec.s3_key}?ttl={SIGNED_URL_TTL_SECONDS}"

    def delete_for_retention(self, *, reference: str,
                             older_than: datetime) -> list[str]:
        removed_ids: list[str] = []
        for fid, rec in list(self._rows.items()):
            if rec.reference != reference:
                continue
            try:
                ts = datetime.fromisoformat(rec.uploaded_at)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if ts > older_than:
                continue
            self._objects.pop(rec.s3_key, None)
            self._rows.pop(fid, None)
            removed_ids.append(fid)
        return removed_ids


# =====================================================================
# Factory — picks S3 vs InMemory based on env vars
# =====================================================================

def build_evidence_store() -> EvidenceStore:
    """Pick the right adapter at import time.

    Production / staging: ``AWS_ACCESS_KEY_ID`` + ``EVIDENCE_BUCKET_NAME`` →
        ``S3EvidenceStore``. (We key on AWS creds rather than just the bucket
        name so a stale bucket name alone doesn't crash local dev.)
    Local dev / CI / tests: ``InMemoryEvidenceStore`` (lost on process exit;
        fine for tests, never for deploy).

    Fail-closed policy (P1-4 fix, 2026-07-14 review): if S3 was *configured*
    (creds + bucket present) but initialization failed, RAISE. The previous
    behavior fell back to InMemory silently, which made evidence uploads
    appear to succeed while vanishing on serverless cold-start. The only
    time InMemory is acceptable is when S3 is genuinely unconfigured (local
    dev / CI / tests). The ``EVIDENCE_ALLOW_IN_MEMORY_FALLBACK=1`` env var
    overrides for unusual staging setups that intentionally run memory-only.
    """
    bucket = os.environ.get("EVIDENCE_BUCKET_NAME")
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    allow_fallback = os.environ.get("EVIDENCE_ALLOW_IN_MEMORY_FALLBACK") == "1"
    if bucket and aws_key:
        try:
            return S3EvidenceStore(
                bucket_name=bucket,
                region=os.environ.get("EVIDENCE_S3_REGION", DEFAULT_S3_REGION),
                kms_key_id=os.environ.get("EVIDENCE_KMS_KEY_ID"),
            )
        except Exception as exc:
            if allow_fallback:
                return InMemoryEvidenceStore()
            raise RuntimeError(
                f"Evidence S3 store configured but init failed: {exc}. "
                f"Refusing to fall back to InMemory in a configured environment "
                f"(set EVIDENCE_ALLOW_IN_MEMORY_FALLBACK=1 to override)."
            ) from exc
    return InMemoryEvidenceStore()
