"""
SmartChoice AI — Reports Blueprint
Generates downloadable PDF decision reports using ReportLab.
"""
from __future__ import annotations

import io
from datetime import datetime

from flask import Blueprint, jsonify, make_response, session, current_app

from app.models import DecisionSession

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/<session_id>/pdf", methods=["GET"])
def generate_pdf(session_id: str):
    """GET /api/reports/<session_id>/pdf — Generate a print-ready PDF report."""
    token = session.get("user_token")
    ds = DecisionSession.query.filter_by(id=session_id, session_token=token).first()
    if not ds:
        return jsonify(error="Session not found."), 404

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        heading1 = ParagraphStyle(
            "heading1", parent=styles["Heading1"],
            fontSize=18, textColor=colors.HexColor("#1a3a6b"), spaceAfter=6
        )
        heading2 = ParagraphStyle(
            "heading2", parent=styles["Heading2"],
            fontSize=13, textColor=colors.HexColor("#2563eb"), spaceAfter=4
        )
        normal = ParagraphStyle(
            "normal_sc", parent=styles["Normal"],
            fontSize=10, leading=14
        )
        muted = ParagraphStyle(
            "muted_sc", parent=styles["Normal"],
            fontSize=9, textColor=colors.HexColor("#6b7280"), leading=12
        )

        story = []

        # ── Header ──────────────────────────────────────────────────────────
        story.append(Paragraph("SmartChoice AI — Decision Intelligence Report", heading1))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2563eb")))
        story.append(Spacer(1, 4 * mm))

        meta_data = [
            ["Decision Title:", ds.title],
            ["Domain:", ds.domain.replace("_", " ").title()],
            ["Status:", ds.status.capitalize()],
            ["Date:", ds.created_at.strftime("%d %B %Y, %I:%M %p")],
            ["Report Generated:", datetime.utcnow().strftime("%d %B %Y, %I:%M %p UTC")],
        ]
        meta_table = Table(meta_data, colWidths=[45 * mm, 130 * mm])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 6 * mm))

        # ── Scores ──────────────────────────────────────────────────────────
        if ds.result and ds.result.scores:
            story.append(Paragraph("Decision Scores", heading2))
            score_rows = [["Option", "Decision Score", "Confidence"]]
            for opt, score in ds.result.scores.items():
                conf = ds.result.confidence.get(opt, "N/A")
                score_rows.append([opt, f"{score}/100", f"{conf}%"])

            score_table = Table(score_rows, colWidths=[80 * mm, 50 * mm, 45 * mm])
            score_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(score_table)
            story.append(Spacer(1, 6 * mm))

        # ── Risk Summary ─────────────────────────────────────────────────────
        if ds.result and ds.result.risks:
            story.append(Paragraph("Risk Assessment Summary", heading2))
            risk_rows = [["Risk", "Severity"]]
            severity_colors = {"HIGH": "#fca5a5", "MEDIUM": "#fde68a", "LOW": "#bbf7d0"}
            for risk in ds.result.risks[:8]:
                risk_rows.append([risk.get("item", ""), risk.get("severity", "MEDIUM")])

            risk_table = Table(risk_rows, colWidths=[145 * mm, 30 * mm])
            risk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(risk_table)
            story.append(Spacer(1, 6 * mm))

        # ── Full Analysis ────────────────────────────────────────────────────
        if ds.result and ds.result.full_analysis:
            story.append(Paragraph("Full Analysis", heading2))
            # Strip markdown for PDF
            import re
            clean_text = re.sub(r"#{1,6}\s*", "", ds.result.full_analysis)
            clean_text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", clean_text)
            clean_text = re.sub(r"`([^`]+)`", r"\1", clean_text)

            for para in clean_text.split("\n\n"):
                para = para.strip()
                if para:
                    story.append(Paragraph(para[:800], normal))
                    story.append(Spacer(1, 2 * mm))

        # ── Footer disclaimer ────────────────────────────────────────────────
        story.append(Spacer(1, 8 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9ca3af")))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            "Disclaimer: This report is generated by SmartChoice AI for informational purposes "
            "only. It does not constitute professional financial, legal, or medical advice. "
            "Consult qualified professionals before making significant decisions.",
            muted
        ))

        doc.build(story)
        buffer.seek(0)

        filename = f"SmartChoice_Report_{ds.id[:8]}.pdf"
        response = make_response(buffer.read())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    except ImportError:
        return jsonify(error="ReportLab not installed. Run: pip install reportlab"), 500
    except Exception as exc:
        current_app.logger.exception("PDF generation failed: %s", exc)
        return jsonify(error="PDF generation failed."), 500
