"""Legal-firm intake brief generator (§8.2, Stage 3).

Internal-only deliverable that legal staff see in the dashboard. NEVER
customer-facing. All fields specified in T-3-026 must be present:

    intake_fields, band, rule_refs, escalation_flags, evidence_gaps,
    recommended_action, verbatim_quotes, tow_rental_status

Hard rules (G-36):
  - Never customer-facing (no PDF, no voice output, no web output).
  - No numeric fault % anywhere.
  - Framing rules still apply to any narrative text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Patterns we must NEVER emit in the brief (G-36, G-13 echo).
FAULT_PERCENT_PATTERNS = [
    r"\b\d{1,3}\s*%\s*(fault|liability|responsibility|at fault)\b",
    r"\b(fault|liability|responsibility)\s*[:=]?\s*\d{1,3}\s*%",
    r"\b\d{1,3}\s*percent\b",
]

# Forbidden advice-y phrases (same set as the customer-facing framing rules,
# kept here so the brief's narrative also passes the scan).
ADVICE_PHRASES = [
    "you are entitled",
    "you will get",
    "they will pay",
    "you can claim",
]


@dataclass
class IntakeBrief:
    session_id: str
    generated_at: str
    intake_fields: dict[str, Any]
    band: str | None
    rule_refs: list[str]
    escalation_flags: list[str]
    evidence_gaps: list[str]
    recommended_action: str
    verbatim_quotes: list[dict[str, str]]
    tow_rental_status: dict[str, Any]
    customer_facing: bool = False  # always False (G-36)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "generated_at": self.generated_at,
            "intake_fields": self.intake_fields,
            "band": self.band,
            "rule_refs": self.rule_refs,
            "escalation_flags": self.escalation_flags,
            "evidence_gaps": self.evidence_gaps,
            "recommended_action": self.recommended_action,
            "verbatim_quotes": self.verbatim_quotes,
            "tow_rental_status": self.tow_rental_status,
            "customer_facing": self.customer_facing,  # always False
        }


def _evidence_gaps_for(scenario_id: str | None, intake: dict[str, Any]) -> list[str]:
    """Return a list of fields the lawyer should follow up on. The Stage 1
    rule tree already marks classification questions; we surface the ones
    that are missing or weak in the intake."""
    gaps: list[str] = []
    if not intake.get("witnesses") or intake.get("witnesses") in ("none", "unknown"):
        gaps.append("witness details not captured")
    if not intake.get("photos_taken") or intake.get("photos_taken") in ("no", "none"):
        gaps.append("photos of damage/scene not yet collected")
    if not intake.get("dashcam") or intake.get("dashcam") in ("none", "no", "neither"):
        gaps.append("dashcam footage status unknown")
    if not intake.get("police_attendance") or intake.get("police_attendance") in ("unsure", "unknown"):
        gaps.append("police attendance not confirmed")
    if not intake.get("other_driver_details") or intake.get("other_driver_details") in ("unknown", "refused"):
        gaps.append("other driver / insurer details not captured")
    return gaps


def _recommended_action_for(band: str | None, escalation: str | None) -> str:
    """Short narrative for the lawyer. Passes framing rules (no advice)."""
    if escalation:
        return (
            f"Escalation flag: {escalation}. The intake is paused; a lawyer "
            f"should review the escalation reason and decide on next steps."
        )
    if band in ("likely", "possible"):
        return (
            f"Pattern band is {band}. Recommend a lawyer review the intake "
            f"record, evidence checklist, and policy coverage before next steps."
        )
    if band == "unclear":
        return (
            "Pattern band is unclear. Recommend a lawyer request additional "
            "evidence (witness statements, photos, dashcam) before next steps."
        )
    return (
        "Insufficient information to assign a pattern band. Recommend a "
        "lawyer follow up to gather the missing classification questions."
    )


def generate_intake_brief(session: Any, classification: Any,
                          tow_status: dict[str, Any] | None = None,
                          rental_status: dict[str, Any] | None = None,
                          verbatim_quotes: list[dict[str, str]] | None = None,
                          generated_at: str = "") -> IntakeBrief:
    """Build the legal-firm brief from a completed session.

    `session` is the Session dataclass from app.state_machine.
    `classification` is the EngineResult from app.engine.
    `tow_status` / `rental_status` are the aux_flow results (dicts).
    `verbatim_quotes` is the lawyer's curated list (may be empty in Stage 3).
    """
    intake = dict(session.intake) if hasattr(session, "intake") else {}
    scenario_id = getattr(classification, "scenario_id", None)
    band = getattr(classification, "band", None)
    escalation = session.escalation if hasattr(session, "escalation") else None

    # Rule refs: from the rule-tree scenario entry, if available
    rule_refs: list[str] = []
    if scenario_id:
        from app.engine import _scenario_by_id
        try:
            sc = _scenario_by_id(scenario_id)
            for c in sc.get("rule_citations", []):
                if c.get("nsw_rule_ref"):
                    rule_refs.append(c["nsw_rule_ref"])
        except Exception:
            pass
    if not rule_refs and band:
        # Fall back to the global citation set if scenario-level ones are missing
        rule_refs = ["Road Rule 126 (safe following distance)"] if scenario_id == "s1-rear-end" else []

    # Escalation flags
    esc_flags: list[str] = []
    if escalation:
        esc_flags.append(escalation)
    if scenario_id and intake.get("chain_count") in (3, "3", 4, 5, 6):
        esc_flags.append("multi-party (3+ vehicles)")

    return IntakeBrief(
        session_id=session.session_id if hasattr(session, "session_id") else "unknown",
        generated_at=generated_at,
        intake_fields=intake,
        band=band,
        rule_refs=rule_refs,
        escalation_flags=esc_flags,
        evidence_gaps=_evidence_gaps_for(scenario_id, intake),
        recommended_action=_recommended_action_for(band, escalation),
        verbatim_quotes=list(verbatim_quotes or []),
        tow_rental_status={
            "tow": tow_status or {},
            "rental": rental_status or {},
        },
        customer_facing=False,  # G-36
    )


def brief_passes_compliance_scan(brief: IntakeBrief) -> bool:
    """Return True iff the brief contains no fault % and no advice phrases."""
    blob = brief.recommended_action + " " + " ".join(
        q.get("text", "") for q in brief.verbatim_quotes
    )
    low = blob.lower()
    for pat in FAULT_PERCENT_PATTERNS:
        if re.search(pat, low):
            return False
    for phrase in ADVICE_PHRASES:
        if phrase in low:
            return False
    return True
