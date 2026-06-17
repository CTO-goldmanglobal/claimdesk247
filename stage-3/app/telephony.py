"""Telephony transport interface.

The voice dialog manager is transport-agnostic. This module defines the
interface a real telephony provider (Twilio, etc.) would implement, plus
a stub used in tests. The voice dialog manager never imports this module
directly — Stage 5 deployment wires a real provider by implementing the
interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class TelephonyTransport(Protocol):
    """Interface for telephony providers. The voice dialog manager consumes
    this; Stage 5 chooses a concrete impl (Twilio, Aircall, etc.)."""

    def start_call(self, to_number: str, from_number: str) -> str:
        """Initiate an outbound call. Returns the provider's call id."""
        ...

    def accept_inbound(self, request: Any) -> "CallContext":
        """Wrap an inbound webhook request as a CallContext."""
        ...

    def end_call(self, call_id: str) -> None:
        ...

    def transfer(self, call_id: str, target: str) -> None:
        """Warm transfer to a nominated human (during business hours)."""
        ...

    def play(self, call_id: str, text: str) -> None:
        """TTS play."""
        ...


@dataclass
class CallContext:
    """A live call. Used by the dialog manager when integrating with a
    real telephony provider."""
    call_id: str
    from_number: str
    to_number: str
    audio_input: bytes = b""
    audio_output: bytes = b""
