"""Generación del PDF del odontograma (exportación imprimible).

Devuelve los **bytes** del PDF (igual que `pdf_receta`/`pdf_consentimiento`).
Dibuja la arcada FDI completa (superior + inferior) con cada pieza coloreada
según su estado, más el detalle de hallazgos, la leyenda de estados y los datos
del paciente. Sirve tanto para el odontograma vivo como para una versión
histórica (se pasa `version_titulo`/`version_fecha`).

Requisito: pip install reportlab
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
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


_CARA_LABEL = {
    "vestibular": "Vestibular", "palatina": "Palatina/Lingual",
    "mesial": "Mesial", "distal": "Distal", "oclusal": "Oclusal/Incisal",
}


def _caras_texto(caras: dict, label_estado: dict) -> str:
    """Detalle por cara legible: 'Oclusal/Incisal: Caries; Mesial: Obturado'.
    Cadena vacía si no hay caras. `label_estado` mapea clave→label del estado."""
    if not caras:
        return ""
    partes = [
        f"{_CARA_LABEL.get(c, c)}: {label_estado.get(e, e)}"
        for c, e in caras.items()
    ]
    return "; ".join(partes)


def _hex(valor: str, defecto: str):
    """HexColor tolerante: cae a `defecto` si el string no es válido."""
    try:
        return colors.HexColor(valor)
    except (ValueError, AttributeError):
        return colors.HexColor(defecto)


def _arcada_table(piezas: list[dict[str, Any]]) -> "Table":
    """Una fila de celdas coloreadas (una por pieza) con su número FDI.

    Las piezas con nota llevan un punto (•) para señalarlo. El color de fondo es
    el del estado; el texto usa el color de contraste calculado en el servicio.
    """
    n = len(piezas) or 1
    etiquetas = [
        (p.get("numero", "") + (" •" if (p.get("nota") or "") else ""))
        for p in piezas
    ]
    tbl = Table([etiquetas], colWidths=[(260 / n) * mm] * n, rowHeights=[13 * mm])
    estilo = [
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
        ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",      (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]
    for i, p in enumerate(piezas):
        estilo.append(("BACKGROUND", (i, 0), (i, 0), _hex(p.get("color", "#e5e7eb"), "#e5e7eb")))
        estilo.append(("TEXTCOLOR",  (i, 0), (i, 0), _hex(p.get("text_color", "#374151"), "#374151")))
    tbl.setStyle(TableStyle(estilo))
    return tbl


def _chip(color_hex: str, texto: str, gray) -> "Table":
    """Cuadradito de color + etiqueta, para leyenda/hallazgos."""
    tbl = Table([["", texto]], colWidths=[5 * mm, 42 * mm], rowHeights=[5 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), _hex(color_hex, "#e5e7eb")),
        ("BOX",        (0, 0), (0, 0), 0.5, colors.HexColor("#d1d5db")),
        ("FONTNAME",   (1, 0), (1, 0), "Helvetica"),
        ("FONTSIZE",   (1, 0), (1, 0), 8),
        ("TEXTCOLOR",  (1, 0), (1, 0), gray),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0), 3),
    ]))
    return tbl


def _dato(label: str, valor: str, gray) -> "Table":
    tbl = Table([[label, valor or "—"]], colWidths=[26 * mm, 110 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, 0), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, 0), gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
    ]))
    return tbl


def generar_odontograma_pdf(
    *,
    clinica_nombre: str = "TUWAYKILIFE",
    paciente_nombre: str = "",
    paciente_documento: str = "",
    fecha: str = "",
    superior: list[dict[str, Any]] | None = None,
    inferior: list[dict[str, Any]] | None = None,
    leyenda: list[dict[str, Any]] | None = None,
    version_titulo: str = "",
    version_fecha: str = "",
) -> bytes:
    """Construye el PDF del odontograma y devuelve sus bytes.

    `superior`/`inferior` son las arcadas (dicts con numero/estado/color/
    text_color/estado_label/nota). `leyenda` es el catálogo de estados
    (clave/label/color/text). Lanza RuntimeError si reportlab no está instalado.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError("ReportLab no está instalado. Ejecutá: pip install reportlab")

    superior = superior or []
    inferior = inferior or []
    leyenda = leyenda or []
    fecha = fecha or datetime.now().strftime("%d/%m/%Y")

    sky  = colors.HexColor("#0284c7")
    gray = colors.HexColor("#6b7280")
    dark = colors.HexColor("#1f2937")

    title_style = ParagraphStyle(
        "Title", fontSize=16, fontName="Helvetica-Bold",
        textColor=sky, alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    clinica_style = ParagraphStyle(
        "Clinica", fontSize=10, fontName="Helvetica",
        textColor=gray, alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    sub_style = ParagraphStyle(
        "Sub", fontSize=9, fontName="Helvetica-Oblique",
        textColor=gray, alignment=TA_CENTER, spaceAfter=4 * mm,
    )
    arch_style = ParagraphStyle(
        "Arch", fontSize=9, fontName="Helvetica-Bold", textColor=gray,
        spaceBefore=3 * mm, spaceAfter=1.5 * mm,
    )
    section_style = ParagraphStyle(
        "Section", fontSize=10, fontName="Helvetica-Bold", textColor=dark,
        spaceBefore=4 * mm, spaceAfter=2 * mm,
    )
    small_style = ParagraphStyle(
        "Small", fontSize=8, fontName="Helvetica", textColor=gray,
        alignment=TA_CENTER,
    )
    item_style = ParagraphStyle(
        "Item", fontSize=9, fontName="Helvetica", textColor=dark, leading=13,
    )

    story: list = []
    story.append(Paragraph(clinica_nombre, clinica_style))
    story.append(Paragraph("Odontograma", title_style))
    if version_titulo:
        etiqueta_ver = f"Versión: {version_titulo}"
        if version_fecha:
            etiqueta_ver += f" — {version_fecha}"
        story.append(Paragraph(etiqueta_ver, sub_style))
    else:
        story.append(Spacer(1, 3 * mm))

    # Datos del paciente
    story.append(_dato("Paciente:", paciente_nombre, gray))
    if (paciente_documento or "").strip():
        story.append(_dato("Documento:", paciente_documento, gray))
    story.append(_dato("Fecha:", fecha, gray))

    # Arcadas
    story.append(Paragraph("Arcada superior (maxilar)", arch_style))
    story.append(_arcada_table(superior))
    story.append(Paragraph("Arcada inferior (mandíbula)", arch_style))
    story.append(_arcada_table(inferior))

    # Detalle de hallazgos (piezas != sano o con detalle por cara)
    hallazgos = [
        p for p in (superior + inferior)
        if (p.get("estado") or "sano") != "sano" or (p.get("caras") or {})
    ]
    # Labels legibles de estado (para las caras).
    label_estado = {e.get("clave"): e.get("label", e.get("clave")) for e in leyenda}
    story.append(Paragraph("Detalle de hallazgos", section_style))
    if hallazgos:
        filas = []
        for p in hallazgos:
            nota = (p.get("nota") or "").strip()
            texto = f"<b>Pieza {p.get('numero','')}</b> — {p.get('estado_label','')}"
            caras_txt = _caras_texto(p.get("caras") or {}, label_estado)
            if caras_txt:
                texto += "  ·  Caras — " + caras_txt
            if nota:
                texto += f" · <i>{nota}</i>"
            filas.append([Paragraph(texto, item_style)])
        det = Table(filas, colWidths=[260 * mm])
        det.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#e5e7eb")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(det)
    else:
        story.append(Paragraph(
            "Sin hallazgos cargados — todas las piezas figuran como sanas.",
            ParagraphStyle("Empty", fontSize=9, fontName="Helvetica-Oblique", textColor=gray),
        ))

    # Leyenda de estados (en filas de 6 chips)
    if leyenda:
        story.append(Paragraph("Referencias", section_style))
        chips = [_chip(e.get("color", "#e5e7eb"), e.get("label", ""), gray) for e in leyenda]
        por_fila = 6
        filas_leyenda = [chips[i:i + por_fila] for i in range(0, len(chips), por_fila)]
        for fila in filas_leyenda:
            while len(fila) < por_fila:
                fila.append("")
        leg = Table(filas_leyenda, colWidths=[47 * mm] * por_fila)
        leg.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        story.append(leg)

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        f"Emitido el {datetime.now().strftime('%d/%m/%Y %H:%M')} — {clinica_nombre}",
        small_style,
    ))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=12 * mm, leftMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=10 * mm,
        title="Odontograma",
    )
    doc.build(story)
    return buffer.getvalue()
