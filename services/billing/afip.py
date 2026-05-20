from __future__ import annotations

from .base import BillingStrategy


class AfipBillingStrategy(BillingStrategy):
    """
    Estrategia de facturación electrónica con AFIP (Argentina).
    Pendiente de implementación — requiere CUIT, certificado digital
    y comunicación con los Web Services wsfe/wsfex de AFIP.
    """

    def generate_pdf(self, comprobante, paciente=None) -> bytes:
        raise NotImplementedError(
            "Integración AFIP pendiente. "
            "Implemente la generación de PDF con CAE/CAI."
        )

    def register_fiscal(self, comprobante) -> dict:
        raise NotImplementedError(
            "Integración AFIP pendiente. "
            "Implemente la autorización vía wsfe y retorne "
            "{'status': ..., 'numero_fiscal': ..., 'cae': ..., 'cae_vto': ...}."
        )
