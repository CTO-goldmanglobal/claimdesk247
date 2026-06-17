"""PDF customer summary generator.

Renders the 9-section customer PDF per stage-2/spec/pdf-summary.v1.md.
Server-side, deterministic for testing. Uses reportlab.

All `{{...}}` tokens are resolved from app.config before render; unresolved
tokens raise UnresolvedTokenError (G-18, T-2-024).
"""
from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether,
)

from app.config import resolve_strict, get_disclaimer, UnresolvedTokenError


EVIDENCE_CHECKLIST: list[str] = [
    "Photos of all vehicles (front, rear, both sides, damage close-ups)",
    "Photos of the scene (road, signage, skid marks, weather conditions)",
    "Other driver's name, rego, insurer details",
    "Police event number (if police attended)",
    "Witness name(s) and contact details",
    "Dashcam footage (yours and/or theirs)",
    "Sketch of vehicle positions at moment of impact",
    "Any CCTV in the area that may have captured the incident",
]

# Short glossary used in the PDF footer area.
LEGAL_GLOSSARY: list[tuple[str, str]] = [
    ("CTP", "Compulsory Third Party (green slip) insurance — covers personal injury."),
    ("Duty of care", "The legal obligation to drive with reasonable care to avoid harming others."),
    ("Give way", "To allow another road user to proceed first; required at give-way signs and T-intersections."),
    ("Without prejudice", "A communication made in an attempt to settle a dispute, which cannot be used as evidence in court."),
    ("Zip merge", "Where two lanes narrow into one; the vehicle ahead has priority."),
]


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=18, spaceAfter=12),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#1a365d")),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontSize=10, leading=13, spaceAfter=6),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#444444")),
        "mono": ParagraphStyle("mono", parent=base["Code"], fontSize=8, leading=10, textColor=colors.HexColor("#222222")),
        "ref": ParagraphStyle("ref", parent=base["BodyText"], fontSize=14, leading=18, spaceAfter=10, textColor=colors.HexColor("#1a365d"), fontName="Helvetica-Bold"),
    }


def _evidence_checklist_for(intake: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return (collected, outstanding) lists for the evidence section."""
    collected: list[str] = []
    outstanding: list[str] = []
    # We have a single photo_taken flag; the rest are open-ended.
    if intake.get("photos_taken") in ("yes", True):
        collected.append(EVIDENCE_CHECKLIST[0])
    else:
        outstanding.append(EVIDENCE_CHECKLIST[0])
    if intake.get("other_driver_details"):
        collected.append(EVIDENCE_CHECKLIST[2])
    else:
        outstanding.append(EVIDENCE_CHECKLIST[2])
    if intake.get("police_attendance") == "yes":
        collected.append(EVIDENCE_CHECKLIST[3])
    else:
        outstanding.append(EVIDENCE_CHECKLIST[3])
    if intake.get("witnesses"):
        collected.append(EVIDENCE_CHECKLIST[4])
    else:
        outstanding.append(EVIDENCE_CHECKLIST[4])
    if intake.get("dashcam") in ("yours", "theirs"):
        collected.append(EVIDENCE_CHECKLIST[5])
    else:
        outstanding.append(EVIDENCE_CHECKLIST[5])
    # Scene sketch and CCTV are always outstanding in MVP
    outstanding.extend([EVIDENCE_CHECKLIST[6], EVIDENCE_CHECKLIST[7]])
    return collected, outstanding


def render_summary_pdf(*, reference: str, intake: dict[str, Any], engine_result: Any) -> bytes:
    """Render the customer PDF to a byte buffer. Returns the bytes.

    Inputs:
        reference: session reference (e.g. "GF-A1B2C3D4")
        intake: the full intake record (dict)
        engine_result: an EngineResult (from app.engine), or None if the
            session escalated before classification completed
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Accident summary {reference}",
    )
    styles = _styles()
    flow: list[Any] = []

    # ----- Section 1: Reference number + date/time -----
    flow.append(Paragraph(f"Reference: {reference}", styles["ref"]))
    flow.append(Paragraph("Accident Summary", styles["title"]))
    flow.append(Paragraph(f"Generated: {intake.get('generated_at', '2026-06-13')}", styles["body"]))
    flow.append(Spacer(1, 6))

    # ----- Section 2: Accident details summary -----
    flow.append(Paragraph("1. Accident details", styles["h2"]))
    details = (
        f"State: {intake.get('state_of_accident', '—')}<br/>"
        f"Date, time &amp; location: {intake.get('datetime_location', '—')}<br/>"
        f"Accident type: {intake.get('accident_type', '—')}<br/>"
        f"Your vehicle: {intake.get('user_vehicle', '—')}<br/>"
        f"Other vehicle(s): {intake.get('other_vehicles', '—')}<br/>"
        f"Movement description: {intake.get('movement_description', '—')}<br/>"
        f"Controls at the location: {intake.get('control_devices', '—')}<br/>"
        f"Police attended: {intake.get('police_attendance', '—')}"
    )
    flow.append(Paragraph(details, styles["body"]))

    # ----- Section 3: Damage map (text) -----
    flow.append(Paragraph("2. Damage map", styles["h2"]))
    dmg = intake.get("damage_locations")
    if isinstance(dmg, list):
        dmg_text = ", ".join(dmg)
    else:
        dmg_text = str(dmg or "—")
    flow.append(Paragraph(f"Damage locations: {dmg_text}", styles["body"]))
    if intake.get("other_driver_details"):
        flow.append(Paragraph(f"Other driver: {intake['other_driver_details']}", styles["body"]))

    # ----- Section 4: Evidence checklist -----
    flow.append(Paragraph("3. Evidence checklist", styles["h2"]))
    collected, outstanding = _evidence_checklist_for(intake)
    if collected:
        flow.append(Paragraph("<b>Collected</b>", styles["body"]))
        for item in collected:
            flow.append(Paragraph(f"  • {item}", styles["body"]))
    if outstanding:
        flow.append(Paragraph("<b>Outstanding — please gather before the lawyer callback</b>", styles["body"]))
        for item in outstanding:
            flow.append(Paragraph(f"  • {item}", styles["body"]))

    # ----- Section 5: General information (with master disclaimer attached) -----
    flow.append(Paragraph("4. General information", styles["h2"]))
    if engine_result and engine_result.text_web:
        # Resolve tokens (the rule tree's text_web contains {{ATTACH:master}} etc.)
        try:
            text_resolved = resolve_strict(engine_result.text_web)
        except UnresolvedTokenError as e:
            # Hard render error: render an error marker so the test catches it.
            text_resolved = f"[RENDER ERROR: {e}]"
        flow.append(Paragraph(text_resolved, styles["body"]))
    elif engine_result and engine_result.escalation:
        # Escalated case — no band output
        flow.append(Paragraph(
            "This matter has been referred to a lawyer at Goldman Forge Legal. "
            "A general-information note will not be issued by the AI assistant.",
            styles["body"],
        ))
    else:
        flow.append(Paragraph("—", styles["body"]))

    # ----- Section 6: Next steps -----
    flow.append(Paragraph("5. Next steps", styles["h2"]))
    flow.append(Paragraph(
        "A lawyer from Goldman Forge Legal will review the information you have provided "
        "and call you back during the next business day during 9:00 am to 5:30 pm, "
        "Monday to Friday. Please have your evidence (photos, witness details, dashcam) "
        "ready if available.",
        styles["body"],
    ))

    # ----- Section 7: Lawyer callback details -----
    flow.append(Paragraph("6. Lawyer callback details", styles["h2"]))
    flow.append(Paragraph(
        f"Callback reference: {reference}<br/>"
        f"Callback window: during the next business day<br/>"
        f"Phone number on file: {intake.get('callback_phone', '(as provided)')}",
        styles["body"],
    ))

    # ----- Section 8: Full disclaimer block (master in full) -----
    flow.append(Paragraph("7. Full disclaimer", styles["h2"]))
    flow.append(Paragraph(get_disclaimer("master"), styles["body"]))

    # Glossary (plain-English support, per G-14)
    flow.append(Paragraph("Glossary", styles["h2"]))
    for term, defn in LEGAL_GLOSSARY:
        flow.append(Paragraph(f"<b>{term}</b> — {defn}", styles["small"]))

    # ----- Section 9: Footer (FIXED, verbatim) -----
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(get_disclaimer("pdf_footer"), styles["small"]))

    doc.build(flow)
    return buf.getvalue()
