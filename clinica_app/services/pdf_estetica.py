"""Generación del PDF del mapa estético (reporte imprimible) — E9.

Devuelve los **bytes** del PDF (igual que `pdf_odontograma`/`pdf_receta`).
Resume, por paciente, las evaluaciones estéticas, los procedimientos con sus
puntos de aplicación (producto/lote/cantidad/zona/coordenadas) y el conteo de
fotos antes/durante/después por zona. Los datos vienen de
`estetica_mapa.datos_export`; acá solo se maqueta.

Requisito: pip install reportlab
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
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


_SKY   = "#0284c7"
_GRAY  = "#6b7280"
_DARK  = "#1f2937"
_LINE  = "#e5e7eb"
_VIOL  = "#7c3aed"


def _dato(label: str, valor: str, gray) -> "Table":
    tbl = Table([[label, valor or "—"]], colWidths=[26 * mm, 150 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, 0), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, 0), gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
    ]))
    return tbl


def _chip(texto: str, color_hex: str) -> "Table":
    """Píldora de total (número + etiqueta) para la fila de resumen."""
    tbl = Table([[texto]], colWidths=[42 * mm], rowHeights=[8 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(color_hex)),
        ("TEXTCOLOR",  (0, 0), (0, 0), colors.white),
        ("FONTNAME",   (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (0, 0), 8),
        ("ALIGN",      (0, 0), (0, 0), "CENTER"),
        ("VALIGN",     (0, 0), (0, 0), "MIDDLE"),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return tbl


def generar_estetica_pdf(
    *,
    clinica_nombre: str = "TUWAYKILIFE",
    paciente_nombre: str = "",
    paciente_documento: str = "",
    fecha: str = "",
    evaluaciones: list[dict[str, Any]] | None = None,
    procedimientos: list[dict[str, Any]] | None = None,
    fotos_por_zona: dict[str, dict[str, int]] | None = None,
    n_evaluaciones: int = 0,
    n_procedimientos: int = 0,
    n_puntos: int = 0,
    n_fotos: int = 0,
) -> bytes:
    """Construye el PDF del reporte estético y devuelve sus bytes.

    Lanza RuntimeError si reportlab no está instalado.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError("ReportLab no está instalado. Ejecutá: pip install reportlab")

    evaluaciones = evaluaciones or []
    procedimientos = procedimientos or []
    fotos_por_zona = fotos_por_zona or {}
    fecha = fecha or datetime.now().strftime("%d/%m/%Y")

    sky  = colors.HexColor(_SKY)
    gray = colors.HexColor(_GRAY)
    dark = colors.HexColor(_DARK)
    line = colors.HexColor(_LINE)

    title_style = ParagraphStyle(
        "Title", fontSize=16, fontName="Helvetica-Bold",
        textColor=sky, alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    clinica_style = ParagraphStyle(
        "Clinica", fontSize=10, fontName="Helvetica",
        textColor=gray, alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    section_style = ParagraphStyle(
        "Section", fontSize=11, fontName="Helvetica-Bold", textColor=dark,
        spaceBefore=5 * mm, spaceAfter=2 * mm,
    )
    sub_style = ParagraphStyle(
        "Sub", fontSize=9.5, fontName="Helvetica-Bold", textColor=colors.HexColor(_VIOL),
        spaceBefore=2.5 * mm, spaceAfter=1 * mm,
    )
    cell_style = ParagraphStyle(
        "Cell", fontSize=8.5, fontName="Helvetica", textColor=dark, leading=11,
    )
    cellh_style = ParagraphStyle(
        "CellH", fontSize=8.5, fontName="Helvetica-Bold", textColor=colors.white, leading=11,
    )
    empty_style = ParagraphStyle(
        "Empty", fontSize=9, fontName="Helvetica-Oblique", textColor=gray,
    )
    small_style = ParagraphStyle(
        "Small", fontSize=8, fontName="Helvetica", textColor=gray, alignment=TA_CENTER,
    )

    def _header_row(labels: list[str]) -> list:
        return [Paragraph(t, cellh_style) for t in labels]

    story: list = []
    story.append(Paragraph(clinica_nombre, clinica_style))
    story.append(Paragraph("Reporte del mapa estético", title_style))
    story.append(Spacer(1, 3 * mm))

    # Datos del paciente
    story.append(_dato("Paciente:", paciente_nombre, gray))
    if (paciente_documento or "").strip():
        story.append(_dato("Documento:", paciente_documento, gray))
    story.append(_dato("Fecha:", fecha, gray))

    # Resumen (totales en píldoras)
    story.append(Paragraph("Resumen", section_style))
    resumen = Table([[
        _chip(f"{n_evaluaciones}  Evaluaciones", _VIOL),
        _chip(f"{n_procedimientos}  Procedimientos", _SKY),
        _chip(f"{n_puntos}  Puntos", "#0d9488"),
        _chip(f"{n_fotos}  Fotos", "#d97706"),
    ]], colWidths=[44 * mm] * 4)
    resumen.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(resumen)

    # Evaluaciones
    story.append(Paragraph("Evaluaciones por zona", section_style))
    if evaluaciones:
        filas = [_header_row(["Zona", "Categoría", "Severidad", "Observación"])]
        for e in evaluaciones:
            sev = e.get("severidad_label") or (
                str(e.get("severidad")) if e.get("severidad") not in ("", None) else "—"
            )
            filas.append([
                Paragraph(e.get("zona_label", ""), cell_style),
                Paragraph(e.get("categoria_label", ""), cell_style),
                Paragraph(sev, cell_style),
                Paragraph(e.get("observacion") or "—", cell_style),
            ])
        tbl = Table(filas, colWidths=[38 * mm, 40 * mm, 30 * mm, 68 * mm], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_VIOL)),
            ("GRID", (0, 0), (-1, -1), 0.4, line),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf5ff")]),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("Sin evaluaciones registradas.", empty_style))

    # Procedimientos (cada uno con su tabla de puntos)
    story.append(Paragraph("Procedimientos y puntos de aplicación", section_style))
    if procedimientos:
        for pr in procedimientos:
            titulo = f"{pr.get('zona_label', '')} — {pr.get('tipo_label', '')}"
            obs = (pr.get("observacion") or "").strip()
            if obs:
                titulo += f"  ·  {obs}"
            story.append(Paragraph(titulo, sub_style))
            puntos = pr.get("puntos", []) or []
            if puntos:
                filas = [_header_row(["Producto", "Lote", "Cantidad", "Coord (x, y)", "Nota"])]
                for p in puntos:
                    cant = p.get("cantidad", "")
                    unidad = p.get("unidad", "")
                    cant_txt = f"{cant} {unidad}".strip() or "—"
                    coord = f"{p.get('coord_x', 0)}, {p.get('coord_y', 0)}"
                    filas.append([
                        Paragraph(p.get("producto_nombre") or "—", cell_style),
                        Paragraph(p.get("lote") or "—", cell_style),
                        Paragraph(cant_txt, cell_style),
                        Paragraph(coord, cell_style),
                        Paragraph(p.get("observacion") or "—", cell_style),
                    ])
                tbl = Table(filas, colWidths=[46 * mm, 30 * mm, 28 * mm, 30 * mm, 42 * mm], repeatRows=1)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_SKY)),
                    ("GRID", (0, 0), (-1, -1), 0.4, line),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
                ]))
                story.append(tbl)
            else:
                story.append(Paragraph("Sin puntos de aplicación.", empty_style))
    else:
        story.append(Paragraph("Sin procedimientos registrados.", empty_style))

    # Fotos por zona
    story.append(Paragraph("Fotos antes / después por zona", section_style))
    if fotos_por_zona:
        filas = [_header_row(["Zona", "Antes", "Durante", "Después"])]
        for zona_label, cont in fotos_por_zona.items():
            filas.append([
                Paragraph(zona_label, cell_style),
                Paragraph(str(cont.get("antes", 0)), cell_style),
                Paragraph(str(cont.get("durante", 0)), cell_style),
                Paragraph(str(cont.get("despues", 0)), cell_style),
            ])
        tbl = Table(filas, colWidths=[66 * mm, 36 * mm, 36 * mm, 38 * mm], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d97706")),
            ("GRID", (0, 0), (-1, -1), 0.4, line),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fffbeb")]),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("Sin fotos cargadas.", empty_style))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"Emitido el {datetime.now().strftime('%d/%m/%Y %H:%M')} — {clinica_nombre}",
        small_style,
    ))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=12 * mm,
        title="Reporte estético",
    )
    doc.build(story)
    return buffer.getvalue()
