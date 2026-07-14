"""PDF customer summary generator.

Renders the customer PDF per stage-2/spec/pdf-summary.v1.md. Server-side,
deterministic for testing. Uses reportlab.

Brand: ClaimDesk 247 (CR-6-01). Operated by ClaimDesk 247; smash-repair
services by {{PANEL_SHOP_NAME}} (Petersham Prestige Smash Repairs by default).
All tokens resolve from app.config before render; unresolved tokens raise
UnresolvedTokenError (G-18, T-2-024).
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether,
    Image, Table, TableStyle, HRFlowable,
)

from app.config import resolve_strict, get_disclaimer, UnresolvedTokenError


# ----- Brand palette (matches lovable-ui: navy + slate + accent blue) -----
BRAND_NAVY = colors.HexColor("#1a365d")       # primary headings
BRAND_ACCENT = colors.HexColor("#2563eb")     # links / highlights
BRAND_SLATE = colors.HexColor("#475569")      # secondary text
BRAND_LIGHT = colors.HexColor("#f1f5f9")      # subtle backgrounds
BRAND_RULE = colors.HexColor("#cbd5e1")       # rules / dividers

LOGO_PATH = Path(__file__).parent / "data" / "claimdesk-logo.png"


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
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=20, leading=24,
            textColor=BRAND_NAVY, spaceAfter=4, alignment=0,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["BodyText"], fontSize=10, leading=13,
            textColor=BRAND_SLATE, spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=12, leading=15,
            spaceBefore=14, spaceAfter=6, textColor=BRAND_NAVY,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontSize=10, leading=14, spaceAfter=6,
        ),
        "body_muted": ParagraphStyle(
            "body_muted", parent=base["BodyText"], fontSize=9, leading=12,
            textColor=BRAND_SLATE, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontSize=8, leading=11,
            textColor=colors.HexColor("#444444"),
        ),
        "mono": ParagraphStyle(
            "mono", parent=base["Code"], fontSize=9, leading=12,
            textColor=colors.HexColor("#222222"),
        ),
        "ref_label": ParagraphStyle(
            "ref_label", parent=base["BodyText"], fontSize=8, leading=10,
            textColor=BRAND_SLATE, spaceAfter=0,
        ),
        "ref_value": ParagraphStyle(
            "ref_value", parent=base["BodyText"], fontSize=14, leading=18,
            textColor=BRAND_NAVY, fontName="Helvetica-Bold", spaceAfter=0,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["BodyText"], fontSize=8, leading=10,
            textColor=BRAND_SLATE, alignment=TA_CENTER,
        ),
    }


def _evidence_checklist_for(intake: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return (collected, outstanding) lists for the evidence section."""
    collected: list[str] = []
    outstanding: list[str] = []
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
    outstanding.extend([EVIDENCE_CHECKLIST[6], EVIDENCE_CHECKLIST[7]])
    return collected, outstanding


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    """Two-column key/value table with subtle striping — for accident details."""
    data = [[Paragraph(f"<b>{k}</b>", ParagraphStyle(
                "kv_k", fontName="Helvetica-Bold", fontSize=10, leading=13,
                textColor=BRAND_NAVY)),
             Paragraph(v or "—", ParagraphStyle(
                "kv_v", fontSize=10, leading=13))] for k, v in rows]
    t = Table(data, colWidths=[5 * cm, 11 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, BRAND_RULE),
        ("BOX", (0, 0), (-1, -1), 0.25, BRAND_RULE),
    ]))
    return t


def _evidence_table(collected: list[str], outstanding: list[str]) -> Table:
    """Two-column collected/outstanding evidence layout."""
    col_cell = ParagraphStyle(
        "ev_col", fontName="Helvetica-Bold", fontSize=9, leading=12,
        textColor=colors.white, alignment=TA_CENTER,
    )
    item_style = ParagraphStyle(
        "ev_item", fontSize=9, leading=12,
    )
    item_style_done = ParagraphStyle(
        "ev_item_done", fontSize=9, leading=12, textColor=BRAND_SLATE,
    )
    rows: list[list[Any]] = [[Paragraph("Collected", col_cell),
                              Paragraph("Outstanding", col_cell)]]
    n = max(len(collected), len(outstanding), 1)
    for i in range(n):
        left = Paragraph(f"✓ {collected[i]}", item_style_done) if i < len(collected) else ""
        right = Paragraph(f"• {outstanding[i]}", item_style) if i < len(outstanding) else ""
        rows.append([left, right])
    t = Table(rows, colWidths=[8 * cm, 8 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#16a34a")),  # green header
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#d97706")),  # amber header
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.25, BRAND_RULE),
        ("LINEAFTER", (0, 0), (0, -1), 0.25, BRAND_RULE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRAND_NAVY),
    ]))
    return t


def _header_logo_and_title(flow: list[Any], styles: dict[str, ParagraphStyle],
                            reference: str) -> None:
    """Branded header: logo on the left, document title on the right."""
    # Logo: scale to ~4cm wide. Original 800x225 → aspect ratio preserved.
    if LOGO_PATH.exists():
        img = Image(str(LOGO_PATH), width=5 * cm, height=5 * cm * (225 / 800))
        # Title block on the right side, logo on the left.
        title_block = [
            Paragraph("Accident Summary", styles["title"]),
            Paragraph(f"Reference <font color='#1a365d'><b>{reference}</b></font> "
                      f"· generated by ClaimDesk 247", styles["subtitle"]),
        ]
        header = Table([[img, title_block]], colWidths=[5.5 * cm, 10.5 * cm])
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        flow.append(header)
    else:
        # Fallback if the logo file is missing (CI / minimal deploy)
        flow.append(Paragraph("ClaimDesk 247", styles["title"]))
        flow.append(Paragraph(f"Reference {reference}", styles["subtitle"]))
    flow.append(Spacer(1, 4))
    flow.append(HRFlowable(width="100%", thickness=1, color=BRAND_NAVY,
                            spaceBefore=2, spaceAfter=10))


def _footer_canvas(canvas_obj: Any, doc: Any) -> None:
    """Page footer drawn on every page: brand line + page number."""
    canvas_obj.saveState()
    # Top rule
    canvas_obj.setStrokeColor(BRAND_RULE)
    canvas_obj.setLineWidth(0.25)
    canvas_obj.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    # Footer text — centred
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(BRAND_SLATE)
    footer_text = ("ClaimDesk 247 · Operated by ClaimDesk 247 · "
                   "Data hosted in Australia · Not legal advice")
    canvas_obj.drawCentredString(A4[0] / 2, 1.1 * cm, footer_text)
    canvas_obj.drawRightString(A4[0] - 2 * cm, 1.1 * cm,
                                f"Page {canvas_obj.getPageNumber()}")
    canvas_obj.restoreState()


def render_summary_pdf(*, reference: str, intake: dict[str, Any],
                       engine_result: Any) -> bytes:
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
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title=f"ClaimDesk 247 — Accident summary {reference}",
        author="ClaimDesk 247",
        subject="Accident summary",
    )
    styles = _styles()
    flow: list[Any] = []

    # ----- Branded header -----
    _header_logo_and_title(flow, styles, reference)

    # ----- Section 1: Accident details -----
    flow.append(Paragraph("1. Accident details", styles["h2"]))
    details_rows = [
        ("State", str(intake.get("state_of_accident", "—"))),
        ("Date, time & location", str(intake.get("datetime_location", "—"))),
        ("Accident type", str(intake.get("accident_type", intake.get("collision_type", "—")))),
        ("Your vehicle", str(intake.get("user_vehicle", "—"))),
        ("Other vehicle(s)", str(intake.get("other_vehicles", "—"))),
        ("Movement description", str(intake.get("movement_description", "—"))),
        ("Controls at the location", str(intake.get("control_devices", "—"))),
        ("Police attended", str(intake.get("police_attendance", "—"))),
    ]
    flow.append(_kv_table(details_rows))

    # ----- Section 2: Damage map -----
    flow.append(Paragraph("2. Damage map", styles["h2"]))
    dmg = intake.get("damage_locations")
    if isinstance(dmg, list):
        dmg_text = ", ".join(dmg)
    else:
        dmg_text = str(dmg or "—")
    flow.append(Paragraph(f"<b>Damage locations:</b> {dmg_text}", styles["body"]))
    if intake.get("other_driver_details"):
        flow.append(Paragraph(
            f"<b>Other driver:</b> {intake['other_driver_details']}",
            styles["body"]))

    # ----- Section 3: Evidence checklist -----
    flow.append(Paragraph("3. Evidence checklist", styles["h2"]))
    collected, outstanding = _evidence_checklist_for(intake)
    flow.append(_evidence_table(collected, outstanding))

    # ----- Section 4: General information -----
    flow.append(Paragraph("4. General information", styles["h2"]))
    if engine_result and engine_result.text_web:
        try:
            text_resolved = resolve_strict(engine_result.text_web)
        except UnresolvedTokenError as e:
            text_resolved = f"[RENDER ERROR: {e}]"
        flow.append(Paragraph(text_resolved, styles["body"]))
    elif engine_result and engine_result.escalation:
        # Escalated case — no band output
        flow.append(Paragraph(
            "This matter has been referred for human review by the ClaimDesk 247 "
            "team. A general-information note will not be issued by the AI assistant.",
            styles["body"],
        ))
    else:
        flow.append(Paragraph("—", styles["body"]))

    # ----- Section 5: Next steps -----
    flow.append(Paragraph("5. Next steps", styles["h2"]))
    flow.append(Paragraph(
        "The ClaimDesk 247 team will review the information you have provided "
        "and be in touch during the next business day (9:00 am to 5:30 pm, "
        "Monday to Friday). Please have your evidence (photos, witness details, "
        "dashcam) ready if available.",
        styles["body"],
    ))

    # ----- Section 6: Callback details -----
    flow.append(Paragraph("6. Callback details", styles["h2"]))
    cb_rows = [
        ("Callback reference", reference),
        ("Callback window", "during the next business day"),
        ("Phone number on file", str(intake.get("callback_phone", "(as provided)"))),
    ]
    flow.append(_kv_table(cb_rows))

    # ----- Section 7: Full disclaimer -----
    flow.append(Paragraph("7. Full disclaimer", styles["h2"]))
    flow.append(Paragraph(get_disclaimer("master"), styles["body"]))

    # Glossary (plain-English support, per G-14)
    flow.append(Paragraph("Glossary", styles["h2"]))
    for term, defn in LEGAL_GLOSSARY:
        flow.append(Paragraph(f"<b>{term}</b> — {defn}", styles["small"]))

    # Final FIXED footer text (the PDF footer disclaimer itself)
    flow.append(Spacer(1, 12))
    flow.append(HRFlowable(width="100%", thickness=0.25, color=BRAND_RULE,
                            spaceBefore=2, spaceAfter=6))
    flow.append(Paragraph(get_disclaimer("pdf_footer"), styles["footer"]))

    doc.build(flow, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    return buf.getvalue()
