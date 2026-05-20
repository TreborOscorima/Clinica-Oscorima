from __future__ import annotations

from .base import BillingStrategy
from .internal import InternalBillingStrategy


# Registro de estrategias disponibles.
# Cuando se active una integración fiscal, añadir la clave aquí:
#   "sunat": SunatBillingStrategy,
#   "afip":  AfipBillingStrategy,
_STRATEGIES: dict[str, type[BillingStrategy]] = {
    "interno": InternalBillingStrategy,
    "internal": InternalBillingStrategy,
}


def get_billing_strategy(tipo: str | None = None) -> BillingStrategy:
    """
    Retorna la estrategia de facturación según el tipo de comprobante o proveedor.
    Mientras no haya integración fiscal activa, siempre devuelve InternalBillingStrategy.
    """
    key = (tipo or "interno").lower()
    strategy_cls = _STRATEGIES.get(key, InternalBillingStrategy)
    return strategy_cls()
