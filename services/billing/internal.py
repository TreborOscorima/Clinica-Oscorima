from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from .base import BillingStrategy

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    _REPORTLAB_OK = True
except ModuleNotFoundError:
    A4 = None
    rl_canvas = None
    _REPORTLAB_OK = False

D2 = Decimal("0.01")


def _dec2(value) -> Decimal:
    if value is None:
        value = 0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(D2, rounding=ROUND_HALF_UP)


class InternalBillingStrategy(BillingStrategy):
    """
    Comprobantes internos en PDF generados con ReportLab.
    No requiere conexión con ningún ente fiscal externo.
    """

    def generate_pdf(self, comprobante, paciente=None) -> bytes:
        if not _REPORTLAB_OK:
            raise RuntimeError(
                "ReportLab no está instalado. "
                "Ejecuta: pip install reportlab"
            )

        # Importar constantes de empresa en tiempo de ejecución
        # para evitar dependencias circulares al cargar el módulo.
        from utils.exporter import (
            COMPANY_ADDRESS, COMPANY_NAME, COMPANY_PHONE,
            COMPANY_RUC, COMPANY_SERIE, COMPANY_VOUCHER,
        )
        from utils.numeros import numero_a_letras

        subtotal = _dec2(
            getattr(comprobante, "total_bruto", None)
            or sum((it.subtotal or 0) for it in (comprobante.items or []))
        )
        descuento = _dec2(getattr(comprobante, "descuento_global", None) or 0)
        total = _dec2(getattr(comprobante, "total", 0) or (subtotal - descuento))

        paciente_nombre = "-"
        paciente_doc = ""
        if paciente:
            paciente_nombre = (getattr(paciente, "nombre", "") or "").strip() or "-"
            paciente_doc = (getattr(paciente, "documento", "") or "").strip()

        buffer = BytesIO()
        lienzo = rl_canvas.Canvas(buffer, pagesize=A4)
        _, height = A4
        cursor_y = height - 50

        lienzo.setFont("Helvetica-Bold", 14)
        lienzo.drawString(50, cursor_y, "WaykiSAC - Sistema de Gestion Clinica")
        cursor_y -= 24

        lienzo.setFont("Helvetica", 10.5)
        for label, value in [
            ("Empresa", COMPANY_NAME),
            ("RUC", COMPANY_RUC or "-"),
            ("Direccion", COMPANY_ADDRESS),
            ("Telefono", COMPANY_PHONE or "-"),
            ("Tipo comprobante", COMPANY_VOUCHER),
            ("Serie y Numero", comprobante.numero or COMPANY_SERIE),
        ]:
            lienzo.drawString(50, cursor_y, f"{label}: {value}")
            cursor_y -= 16

        cursor_y -= 4
        fecha_segura = getattr(comprobante, "fecha", None) or datetime.utcnow()
        lienzo.drawString(50, cursor_y, f"Fecha: {fecha_segura.strftime('%Y-%m-%d %H:%M')}")
        cursor_y -= 16
        lienzo.drawString(50, cursor_y, f"Paciente: {paciente_nombre}")
        cursor_y -= 16
        if paciente_doc:
            lienzo.drawString(50, cursor_y, f"Documento: {paciente_doc}")
            cursor_y -= 16
        forma_pago = getattr(comprobante.forma_pago, "value", str(comprobante.forma_pago))
        lienzo.drawString(50, cursor_y, f"Forma de pago: {forma_pago}")
        cursor_y -= 16
        if comprobante.observacion:
            lienzo.drawString(50, cursor_y, f"Obs: {comprobante.observacion}")
            cursor_y -= 16

        if getattr(comprobante, "items", None):
            cursor_y -= 12
            lienzo.setFont("Helvetica-Bold", 11)
            lienzo.drawString(50, cursor_y, "Detalle de items")
            cursor_y -= 18
            lienzo.setFont("Helvetica-Bold", 10)
            lienzo.drawString(50, cursor_y, "Descripcion")
            lienzo.drawRightString(320, cursor_y, "Cant.")
            lienzo.drawRightString(390, cursor_y, "Precio unit.")
            lienzo.drawRightString(470, cursor_y, "Importe")
            cursor_y -= 14
            lienzo.setFont("Helvetica", 10)

            for item in comprobante.items:
                if cursor_y < 120:
                    lienzo.showPage()
                    cursor_y = height - 60
                    lienzo.setFont("Helvetica-Bold", 10)
                    lienzo.drawString(50, cursor_y, "Descripcion")
                    lienzo.drawRightString(320, cursor_y, "Cant.")
                    lienzo.drawRightString(390, cursor_y, "Precio unit.")
                    lienzo.drawRightString(470, cursor_y, "Importe")
                    cursor_y -= 14
                    lienzo.setFont("Helvetica", 10)

                descripcion = (item.nombre or "").strip()
                tipo_linea = (item.tipo or "").strip()
                if tipo_linea:
                    descripcion = (
                        f"{tipo_linea.capitalize()} - {descripcion}"
                        if descripcion
                        else tipo_linea.capitalize()
                    )
                cantidad = float(item.cantidad or 0)
                precio_unit = float(item.precio_unit or 0)
                subtotal_item = float(item.subtotal or (cantidad * precio_unit))

                lienzo.drawString(50, cursor_y, descripcion[:70])
                lienzo.drawRightString(320, cursor_y, f"{cantidad:.2f}")
                lienzo.drawRightString(400, cursor_y, f"S/ {precio_unit:.2f}")
                lienzo.drawRightString(470, cursor_y, f"S/ {subtotal_item:.2f}")
                cursor_y -= 14

        cursor_y -= 8
        lienzo.setFont("Helvetica", 10)
        lienzo.drawRightString(470, cursor_y, f"Subtotal: S/ {float(subtotal):.2f}")
        cursor_y -= 16
        lienzo.drawRightString(470, cursor_y, f"Descuento aplicado: S/ {float(descuento):.2f}")
        cursor_y -= 16
        lienzo.setFont("Helvetica-Bold", 11)
        lienzo.drawRightString(470, cursor_y, f"Total: S/ {float(total):.2f}")
        cursor_y -= 22

        try:
            total_letras = numero_a_letras(float(total), moneda="soles")
        except Exception:
            total_letras = f"{float(total):.2f}"
        lienzo.setFont("Helvetica-Bold", 10)
        lienzo.drawString(50, cursor_y, f"Total en letras: {total_letras}")
        cursor_y -= 20

        lienzo.setFont("Helvetica", 9.5)
        lienzo.drawString(
            50, cursor_y,
            "Documento generado automaticamente por el sistema de gestion.",
        )
        lienzo.showPage()
        lienzo.save()

        pdf = buffer.getvalue()
        buffer.close()
        return pdf

    def register_fiscal(self, comprobante) -> dict:
        return {"status": "internal", "numero_fiscal": comprobante.numero}
