"""Generación del PDF de receta / indicaciones médicas (A5).

Devuelve los **bytes** del PDF (igual que `pdf_consentimiento`) para que la capa
que llama lo archive como adjunto vía `services/storage.py`. Formato A5 vertical,
apto para imprimir. Cubre dos modos:

  - "receta":     encabezado "Rp/" con cada renglón del cuerpo como ítem.
  - "indicacion": indicaciones médicas en texto corrido.

Requisito: pip install reportlab
"""
from __future__ import annotations

import io
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A5
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

_TITULOS = {
    "receta":     "Receta",
    "indicacion": "Indicaciones médicas",
}


def _dato(label: str, valor: str, gray) -> "Table":
    tbl = Table([[label, valor or "—"]], colWidths=[28 * mm, 90 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, 0), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, 0), gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl


def generar_receta_pdf(
    *,
    clinica_nombre: str = "TUWAYKILIFE",
    tipo: str = "receta",
    paciente_nombre: str = "",
    paciente_documento: str = "",
    profesional_nombre: str = "",
    diagnostico: str = "",
    cuerpo: str = "",
    fecha: str = "",
) -> bytes:
    """Construye el PDF de la receta/indicación y devuelve sus bytes.

    Lanza RuntimeError si reportlab no está instalado.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError(
            "ReportLab no está instalado. Ejecutá: pip install reportlab"
        )

    fecha = fecha or datetime.now().strftime("%d/%m/%Y")
    es_receta = tipo == "receta"
    titulo = _TITULOS.get(tipo, _TITULOS["receta"])

    sky  = colors.HexColor("#0284c7")
    gray = colors.HexColor("#6b7280")
    dark = colors.HexColor("#1f2937")

    title_style = ParagraphStyle(
        "Title", fontSize=15, fontName="Helvetica-Bold",
        textColor=sky, alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    clinica_style = ParagraphStyle(
        "Clinica", fontSize=10, fontName="Helvetica",
        textColor=gray, alignment=TA_CENTER, spaceAfter=5 * mm,
    )
    rp_style = ParagraphStyle(
        "Rp", fontSize=13, fontName="Helvetica-Bold", textColor=dark,
        spaceBefore=3 * mm, spaceAfter=2 * mm,
    )
    item_style = ParagraphStyle(
        "Item", fontSize=10, fontName="Helvetica", textColor=dark,
        leading=15, leftIndent=6 * mm, spaceAfter=1.5 * mm,
    )
    body_style = ParagraphStyle(
        "Body", fontSize=10, fontName="Helvetica", textColor=dark,
        leading=15, spaceAfter=2 * mm,
    )
    small_style = ParagraphStyle(
        "Small", fontSize=8, fontName="Helvetica", textColor=gray,
        alignment=TA_CENTER,
    )

    story: list = []
    story.append(Paragraph(clinica_nombre, clinica_style))
    story.append(Paragraph(titulo, title_style))
    story.append(Spacer(1, 3 * mm))

    story.append(_dato("Paciente:", paciente_nombre, gray))
    if paciente_documento.strip():
        story.append(_dato("Documento:", paciente_documento, gray))
    story.append(_dato("Fecha:", fecha, gray))
    if diagnostico.strip():
        story.append(_dato("Diagnóstico:", diagnostico, gray))
    story.append(Spacer(1, 3 * mm))

    lineas = [ln.strip() for ln in (cuerpo or "").splitlines() if ln.strip()]
    if es_receta:
        story.append(Paragraph("Rp/", rp_style))
        for i, ln in enumerate(lineas, start=1):
            story.append(Paragraph(f"{i}. {ln}", item_style))
    else:
        for ln in lineas:
            story.append(Paragraph(ln, body_style))

    # Firma del profesional
    story.append(Spacer(1, 18 * mm))
    firma = Table(
        [
            ["_______________________________"],
            [profesional_nombre or "Firma y sello del profesional"],
        ],
        colWidths=[90 * mm],
    )
    firma.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (0, 0), 10),
        ("FONTSIZE",  (0, 1), (0, 1), 8),
        ("TEXTCOLOR", (0, 1), (0, 1), gray),
        ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 1), (0, 1), 2),
    ]))
    story.append(firma)

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"Emitido el {datetime.now().strftime('%d/%m/%Y %H:%M')} — {clinica_nombre}",
        small_style,
    ))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A5,
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=titulo,
    )
    doc.build(story)
    return buffer.getvalue()
