"""Token and disclaimer config.

All `{{...}}` tokens resolve from this single config map (per build request §3.2).
Stubbed dev values for Stage 2; real values resolved at Stage 5 deployment.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"


# Dev stub values for tokens. Real values injected at Stage 5 deployment.
#
# CR-6-01 (2026-07-14): Operating entity for claimdesk247.com.au is
# "ClaimDesk 247". Smash-repair services are provided by an accredited panel
# shop; the launch-case partner is Petersham Prestige Smash Repairs, set via
# the {{PANEL_SHOP_NAME}} token so partners can be swapped per case without
# code edits. Goldman Forge Legal remains the upstream legal/firmware brand
# (ForgeWright) and must not appear to customers as the operator of this site.
STAGE2_TOKENS: dict[str, str] = {
    "{{PERSONA_NAME}}": "Alex",
    "{{FIRM_NAME}}": "ClaimDesk 247",
    "{{OPERATOR_NAME}}": "ClaimDesk 247",
    "{{PANEL_SHOP_NAME}}": "Petersham Prestige Smash Repairs",
    "{{FIRM_PHONE}}": "(02) 9000 0000",
    "{{CALLBACK_SLA}}": "during the next business day",
    "{{RETENTION_PERIOD}}": "7 years",
    "{{TOW_PROVIDER_REF}}": "TOW-GF-001",
    "{{RENTAL_PARTNER_REF}}": "RENT-GF-001",
    "{{BUSINESS_HOURS}}": "9:00 am to 5:30 pm, Monday to Friday",
}

# Disclaimer attachment tokens. These resolve to the FIXED/binder-draft strings
# in the disclaimer data, not to free text.
ATTACH_TOKENS: dict[str, str] = {
    "{{ATTACH:master}}": "__DISCLAIMER_MASTER__",
    "{{ATTACH:master_voice_short}}": "__DISCLAIMER_MASTER_VOICE_SHORT__",
}

# All token keys we expect to resolve.
ALL_TOKEN_KEYS = set(STAGE2_TOKENS) | set(ATTACH_TOKENS)

TOKEN_PATTERN = re.compile(r"\{\{[A-Za-z_][A-Za-z0-9_:]*\}\}")


@lru_cache(maxsize=1)
def _load_disclaimers() -> dict[str, Any]:
    with (DATA_DIR / "disclaimers.v1.complete.json").open() as f:
        return json.load(f)


def get_disclaimer(key: str) -> str:
    """Return the resolved text of a disclaimer by key. Attachment keys are
    returned as their fully-resolved string (master string in full, etc.)."""
    disclaimers = _load_disclaimers()
    strings = disclaimers["strings"]

    if key == "master":
        return strings["master"]["text"]
    if key == "master_voice_short":
        return strings["master_voice_short"]["text"]
    if key == "pdf_footer":
        return strings["pdf_footer"]["text"]
    if key == "state_scope_guard":
        return strings["state_scope_guard"]["text"]
    if key == "recording_consent":
        return strings["recording_consent"]["text"]
    if key == "privacy_notice":
        pn = strings["privacy_notice"]
        if isinstance(pn, dict) and "text" in pn and isinstance(pn["text"], dict):
            return pn["text"]["web"]
        return pn.get("text", "")
    if key == "pd_recovery_disclosure":
        return strings["pd_recovery_disclosure"]["text"]
    if key.startswith("escalation_handoff."):
        variant = key.split(".", 1)[1]
        variants = strings["escalation_handoff"].get("variants", {})
        if variant in variants:
            return variants[variant]["web"]
        raise KeyError(f"unknown escalation_handoff variant: {variant}")
    if key.startswith("session_close."):
        variant = key.split(".", 1)[1]
        return strings["session_close"]["variants"].get(variant, "")
    raise KeyError(f"unknown disclaimer key: {key}")


def resolve_tokens(text: str) -> str:
    """Resolve all `{{...}}` tokens in a string to their configured values.

    Attachment tokens (`{{ATTACH:...}}`) are resolved to the full disclaimer text.
    An unrecognised token raises ValueError (fail-closed at render — G-18).
    """
    def replace(match: re.Match) -> str:
        tok = match.group(0)
        if tok in STAGE2_TOKENS:
            return STAGE2_TOKENS[tok]
        if tok in ATTACH_TOKENS:
            return get_disclaimer(tok.removeprefix("{{ATTACH:").removesuffix("}}"))
        raise ValueError(f"unresolved token at render: {tok!r}")

    return TOKEN_PATTERN.sub(replace, text)


def find_unresolved_tokens(text: str) -> list[str]:
    """Return the list of `{{...}}` tokens that would NOT resolve.
    Used by tests and the render-time guard (G-18)."""
    found = TOKEN_PATTERN.findall(text)
    return [t for t in found if t not in ALL_TOKEN_KEYS]


# Convenience: framework-level guard used by the render path.
class UnresolvedTokenError(RuntimeError):
    pass


def resolve_strict(text: str) -> str:
    """Like resolve_tokens, but raises UnresolvedTokenError on any token that
    isn't in the configured set. Use this in the render path; tests use
    resolve_tokens() so they can assert behaviour with input fixtures."""
    try:
        return resolve_tokens(text)
    except ValueError as exc:
        raise UnresolvedTokenError(str(exc)) from exc
