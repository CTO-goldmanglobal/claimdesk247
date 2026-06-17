"""Swappable session store interface.

For Stage 2, an in-memory dict is the dev store. The interface is
defined here so a Stage 4 Australian-region persistent store can be
substituted without changing the web layer or the engine.
"""
from __future__ import annotations

from typing import Protocol

from app.state_machine import Session


class SessionStore(Protocol):
    def create(self) -> Session: ...
    def get(self, session_id: str) -> Session | None: ...
    def save(self, session: Session) -> None: ...
    def by_reference(self, reference: str) -> Session | None: ...


class InMemoryStore:
    """Dev store. Process-local. Replace at Stage 4."""

    def __init__(self) -> None:
        self._by_id: dict[str, Session] = {}
        self._by_ref: dict[str, Session] = {}

    def create(self) -> Session:
        s = Session(session_id=__import__("secrets").token_urlsafe(16))
        self._by_id[s.session_id] = s
        return s

    def get(self, session_id: str) -> Session | None:
        return self._by_id.get(session_id)

    def save(self, session: Session) -> None:
        self._by_id[session.session_id] = session
        if session.reference:
            self._by_ref[session.reference] = session

    def by_reference(self, reference: str) -> Session | None:
        return self._by_ref.get(reference)

    def put(self, session: Session) -> None:
        """Stage 3 dashboard convenience. Same semantics as save()."""
        self.save(session)

    def list(self) -> list[Session]:
        """Stage 3 dashboard. Return a snapshot list (no live view)."""
        return list(self._by_id.values())
