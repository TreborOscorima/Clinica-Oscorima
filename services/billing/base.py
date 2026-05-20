from __future__ import annotations

from abc import ABC, abstractmethod


class BillingStrategy(ABC):
    """
    Interfaz para estrategias de generación y registro de comprobantes.

    Permite intercambiar la implementación entre comprobantes internos,
    SUNAT (Perú), AFIP (Argentina) u otros proveedores fiscales sin
    modificar la capa de negocio ni las rutas HTTP.
    """

    @abstractmethod
    def generate_pdf(self, comprobante, paciente=None) -> bytes:
        """Genera el PDF del comprobante y retorna los bytes listos para enviar."""
        ...

    @abstractmethod
    def register_fiscal(self, comprobante) -> dict:
        """
        Registra el comprobante ante el ente fiscal correspondiente.
        Retorna un dict con al menos las claves: status, numero_fiscal.
        """
        ...
