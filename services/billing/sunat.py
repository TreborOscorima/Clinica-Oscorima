from __future__ import annotations

from .base import BillingStrategy


class SunatBillingStrategy(BillingStrategy):
    """
    Estrategia de facturación electrónica con SUNAT (Perú).
    Pendiente de implementación — requiere credenciales OSE/SUNAT
    y la librería de firma XML (signxml o similar).
    """

    def generate_pdf(self, comprobante, paciente=None) -> bytes:
        raise NotImplementedError(
            "Integración SUNAT pendiente. "
            "Implemente la generación de PDF con CDR/XML firmado."
        )

    def register_fiscal(self, comprobante) -> dict:
        raise NotImplementedError(
            "Integración SUNAT pendiente. "
            "Implemente el envío del XML al OSE/SUNAT y retorne "
            "{'status': ..., 'numero_fiscal': ..., 'cdr_hash': ...}."
        )
