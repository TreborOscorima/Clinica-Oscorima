"""
Generación de recibos en PDF usando ReportLab.

Requisito: pip install reportlab

El PDF generado es A5 (148x210mm), apto para imprimir y enviar por email.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from clinica_app.config import REPORT_EXPORT_DIR

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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


def _ensure_dir() -> Path:
    path = Path(REPORT_EXPORT_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generar_recibo_pdf(
    comprobante: dict[str, Any],
    paciente_nombre: str = "",
    clinica_nombre: str = "WaykiSAC",
) -> str:
    """
    Genera un PDF del comprobante y lo guarda en REPORT_EXPORT_DIR.
    Devuelve el nombre del archivo generado.
    Lanza RuntimeError si reportlab no está instalado.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError(
            "ReportLab no está instalado. Ejecutá: pip install reportlab"
        )

    numero   = comprobante.get("numero", "SIN-NUM")
    fecha    = comprobante.get("fecha", "")
    total    = comprobante.get("total", "0.00")
    descuento = comprobante.get("descuento_global", "0.00")
    total_bruto = comprobante.get("total_bruto", "0.00")
    forma_pago  = comprobante.get("forma_pago", "efectivo").capitalize()
    observacion = comprobante.get("observacion", "")
    items    = comprobante.get("items", [])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename  = f"recibo_{numero.replace('/', '-')}_{timestamp}.pdf"
    filepath  = _ensure_dir() / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A5,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    sky    = colors.HexColor("#0284c7")
    gray   = colors.HexColor("#6b7280")
    light  = colors.HexColor("#f0f9ff")

    title_style = ParagraphStyle(
        "Title", fontSize=16, fontName="Helvetica-Bold",
        textColor=sky, alignment=TA_CENTER, spaceAfter=2 * mm,
    )
    sub_style = ParagraphStyle(
        "Sub", fontSize=9, fontName="Helvetica",
        textColor=gray, alignment=TA_CENTER, spaceAfter=6 * mm,
    )
    label_style = ParagraphStyle(
        "Label", fontSize=8, fontName="Helvetica-Bold",
        textColor=gray,
    )
    value_style = ParagraphStyle(
        "Value", fontSize=9, fontName="Helvetica",
    )
    footer_style = ParagraphStyle(
        "Footer", fontSize=7, fontName="Helvetica",
        textColor=gray, alignment=TA_CENTER,
    )

    story: list[Any] = []

    # Encabezado
    story.append(Paragraph(clinica_nombre, title_style))
    story.append(Paragraph(f"Recibo N° {numero}", sub_style))

    # Info del comprobante
    info_data = [
        ["Fecha:", fecha, "Paciente:", paciente_nombre],
        ["Forma de pago:", forma_pago, "", ""],
    ]
    info_table = Table(info_data, colWidths=[25 * mm, 40 * mm, 22 * mm, 40 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), gray),
        ("TEXTCOLOR", (2, 0), (2, -1), gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    # Tabla de ítems
    item_headers = ["Descripción", "Cant.", "P. Unit.", "Subtotal"]
    item_rows = [item_headers]
    for it in items:
        item_rows.append([
            it.get("nombre", ""),
            str(it.get("cantidad", "1")),
            f"$ {it.get('precio_unit', '0')}",
            f"$ {it.get('subtotal', '0')}",
        ])

    item_table = Table(
        item_rows,
        colWidths=[60 * mm, 18 * mm, 25 * mm, 25 * mm],
    )
    item_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), sky),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 4 * mm))

    # Totales
    totales_data = []
    if Decimal(str(descuento)) > 0:
        totales_data.append(["Subtotal:", f"$ {total_bruto}"])
        totales_data.append(["Descuento:", f"- $ {descuento}"])
    totales_data.append(["TOTAL:", f"$ {total}"])

    tot_table = Table(totales_data, colWidths=[80 * mm, 48 * mm], hAlign="RIGHT")
    tot_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME",  (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -2), 9),
        ("FONTSIZE",  (0, -1), (-1, -1), 11),
        ("ALIGN",     (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, sky),
        ("TEXTCOLOR", (0, -1), (-1, -1), sky),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tot_table)

    if observacion:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"Obs: {observacion}", ParagraphStyle(
            "Obs", fontSize=8, textColor=gray
        )))

    # Pie
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} — {clinica_nombre}",
        footer_style,
    ))

    doc.build(story)
    return filename


def obtener_datos_comprobante(session, clinica_id: int, comprobante_id: int) -> tuple[dict, str]:
    """Devuelve (comprobante_dict, paciente_nombre)."""
    from clinica_app.models.caja import Comprobante, ComprobanteItem
    from clinica_app.models.paciente import Paciente
    from sqlmodel import select

    comp = session.exec(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.clinica_id == clinica_id,
        )
    ).first()
    if comp is None:
        raise ValueError(f"Comprobante {comprobante_id} no encontrado")

    items = session.exec(
        select(ComprobanteItem).where(ComprobanteItem.comprobante_id == comprobante_id)
    ).all()
    paciente_nombre = ""
    if comp.paciente_id:
        pac = session.exec(select(Paciente).where(Paciente.id == comp.paciente_id)).first()
        if pac:
            paciente_nombre = pac.nombre

    comp_dict = {
        "id":               comp.id,
        "numero":           comp.numero or "",
        "tipo":             comp.tipo or "recibo",
        "fecha":            comp.fecha.strftime("%d/%m/%Y %H:%M") if comp.fecha else "",
        "paciente_id":      comp.paciente_id,
        "total_bruto":      str(comp.total_bruto or 0),
        "descuento_global": str(comp.descuento_global or 0),
        "total":            str(comp.total or 0),
        "forma_pago":       comp.forma_pago.value if comp.forma_pago else "efectivo",
        "observacion":      comp.observacion or "",
        "items": [
            {
                "nombre":      i.nombre,
                "cantidad":    str(i.cantidad or 1),
                "precio_unit": str(i.precio_unit or 0),
                "subtotal":    str(i.subtotal or 0),
            }
            for i in items
        ],
    }
    return comp_dict, paciente_nombre
