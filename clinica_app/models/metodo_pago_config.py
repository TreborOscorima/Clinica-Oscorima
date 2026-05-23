from __future__ import annotations

from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class MetodoPagoConfig(TenantSQLModel, table=True):
    """
    Métodos de pago configurables por clínica (distinto del enum MetodoPago
    usado en comprobantes históricos).
    """
    __tablename__ = "metodos_pago_config"

    nombre:           str       = Field(max_length=80,  nullable=False)
    descripcion:      str | None = Field(default=None, max_length=200, nullable=True)
    tipo:             str       = Field(default="otro", max_length=30, nullable=False)
    visible_en_venta: bool      = Field(default=True,  nullable=False)
