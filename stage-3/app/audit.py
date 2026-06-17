"""Append-only audit log (G-34).

Every intake session already records: timestamp, session id, inputs,
rule-tree path, output (Stage 2 store). This module adds the append-only
log used by the legal-firm dashboard view.

Invariants:
  - Entries are never mutated or deleted (G-34).
  - The dashboard view is read-only.
  - The export (admin role only) returns the full log as a list of dicts.
  - Mutations raise AuditMutationError.

Storage: a simple list of dicts. Stage 4 swaps the in-memory list for a
real append-only log (S3 object-lock, WORM, etc.). The interface is
the same.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


class AuditMutationError(Exception):
    """Raised if anyone attempts to mutate the audit log."""


@dataclass
class AuditEntry:
    """One audit-log record. Once written, never mutated (G-34)."""
    timestamp: str
    session_id: str
    user: str
    action: str
    inputs: dict[str, Any]
    rule_path: list[str]
    output: dict[str, Any]
    entry_id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuditLog:
    """Append-only log. Thread-unsafe by design (Stage 3 is single-process);
    the interface is unchanged in Stage 4 when this becomes a real WORM store."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._next_id: int = 1

    def append(self, *, session_id: str, user: str, action: str,
               inputs: dict[str, Any], rule_path: list[str],
               output: dict[str, Any]) -> AuditEntry:
        """Append a new entry. The only mutating operation allowed."""
        e = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            user=user,
            action=action,
            inputs=dict(inputs),  # snapshot
            rule_path=list(rule_path),
            output=dict(output),
            entry_id=self._next_id,
        )
        self._next_id += 1
        self._entries.append(e)
        return e

    def all(self) -> list[AuditEntry]:
        """Read-only view. Returns a shallow copy of the entries list."""
        return list(self._entries)

    def filter(self, **kwargs: Any) -> list[AuditEntry]:
        """Read-only filter. Returns a new list (no in-place mutation)."""
        out: list[AuditEntry] = []
        for e in self._entries:
            if all(getattr(e, k, None) == v for k, v in kwargs.items()):
                out.append(e)
        return out

    def export(self) -> list[dict[str, Any]]:
        """Admin-only export (G-34). Returns a JSON-serialisable list."""
        return [e.to_dict() for e in self._entries]

    def __len__(self) -> int:
        return len(self._entries)

    # ----- Mutators that are explicitly rejected -----

    def pop(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        raise AuditMutationError("audit log is append-only; pop is forbidden (G-34)")

    def remove(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        raise AuditMutationError("audit log is append-only; remove is forbidden (G-34)")

    def clear(self) -> None:  # type: ignore[override]
        raise AuditMutationError("audit log is append-only; clear is forbidden (G-34)")

    def __setitem__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        raise AuditMutationError("audit log is append-only; __setitem__ is forbidden (G-34)")

    def __delitem__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        raise AuditMutationError("audit log is append-only; __delitem__ is forbidden (G-34)")


# Module-level singleton (Stage 3 in-memory; Stage 4 swaps for persistent)
DEFAULT_AUDIT_LOG = AuditLog()
