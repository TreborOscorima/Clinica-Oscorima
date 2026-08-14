"""Generación del PDF de consentimiento informado (A4).

A diferencia de `pdf_recibo` (que escribe a REPORT_EXPORT_DIR y devuelve un
nombre de archivo), acá devolvemos los **bytes** del PDF para que la capa que
llama los archive como adjunto vía `services/storage.py`. Formato A4 vertical,
apto para imprimir y firmar a mano.

Requisito: pip install reportlab
"""
from __future__ import annotations

import io
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    _REPORTLAB_OK = True
except ImportError:
    _REPORTLAB_OK = False


def _linea_dato(label: str, valor: str, style) -> "Table":
    tbl = Table([[label, valor or "—"]], colWidths=[35 * mm, 120 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, 0), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#6b7280")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl


def generar_consentimiento_pdf(
    *,
    clinica_nombre: str = "TUWAYKILIFE",
    titulo: str = "Consentimiento informado",
    cuerpo: str = "",
    paciente_nombre: str = "",
    paciente_documento: str = "",
    procedimiento: str = "",
    profesional_nombre: str = "",
    observaciones: str = "",
    fecha: str = "",
) -> bytes:
    """Construye el PDF del consentimiento y devuelve sus bytes.

    Lanza RuntimeError si reportlab no está instalado.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError(
            "ReportLab no está instalado. Ejecutá: pip install reportlab"
        )

    fecha = fecha or datetime.now().strftime("%d/%m/%Y")

    sky  = colors.HexColor("#0284c7")
    gray = colors.HexColor("#6b7280")
    dark = colors.HexColor("#1f2937")

    title_style = ParagraphStyle(
        "Title", fontSize=15, fontName="Helvetica-Bold",
        textColor=sky, alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    clinica_style = ParagraphStyle(
        "Clinica", fontSize=10, fontName="Helvetica",
        textColor=gray, alignment=TA_CENTER, spaceAfter=6 * mm,
    )
    section_style = ParagraphStyle(
        "Section", fontSize=9, fontName="Helvetica-Bold",
        textColor=gray, spaceBefore=4 * mm, spaceAfter=2 * mm,
    )
    body_style = ParagraphStyle(
        "Body", fontSize=10, fontName="Helvetica", textColor=dark,
        alignment=TA_JUSTIFY, leading=15, spaceAfter=3 * mm,
    )
    small_style = ParagraphStyle(
        "Small", fontSize=8, fontName="Helvetica", textColor=gray,
        alignment=TA_CENTER,
    )

    story: list = []
    story.append(Paragraph(clinica_nombre, clinica_style))
    story.append(Paragraph(titulo, title_style))
    story.append(Spacer(1, 4 * mm))

    # Datos del paciente
    story.append(_linea_dato("Paciente:", paciente_nombre, body_style))
    story.append(_linea_dato("Documento:", paciente_documento, body_style))
    story.append(_linea_dato("Fecha:", fecha, body_style))
    if procedimiento.strip():
        story.append(_linea_dato("Procedimiento:", procedimiento, body_style))
    story.append(Spacer(1, 4 * mm))

    # Cuerpo del consentimiento (párrafos separados por línea en blanco)
    for parrafo in (cuerpo or "").split("\n\n"):
        parrafo = parrafo.strip()
        if parrafo:
            story.append(Paragraph(parrafo.replace("\n", "<br/>"), body_style))

    if observaciones.strip():
        story.append(Paragraph("Observaciones", section_style))
        story.append(Paragraph(observaciones.replace("\n", "<br/>"), body_style))

    # Firmas
    story.append(Spacer(1, 16 * mm))
    firmas = Table(
        [
            ["_______________________________", "_______________________________"],
            ["Firma del paciente", "Firma del profesional"],
            ["Aclaración y documento", profesional_nombre or "Aclaración y matrícula"],
        ],
        colWidths=[80 * mm, 80 * mm],
    )
    firmas.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, 0), 10),
        ("FONTSIZE",  (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, 1), dark),
        ("TEXTCOLOR", (0, 2), (-1, 2), gray),
        ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
    ]))
    story.append(firmas)

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} — {clinica_nombre}",
        small_style,
    ))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=titulo,
    )
    doc.build(story)
    return buffer.getvalue()
