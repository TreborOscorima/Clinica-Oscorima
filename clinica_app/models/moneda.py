from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class Moneda(TenantSQLModel, table=True):
    __tablename__ = "monedas"
    __table_args__ = (
        UniqueConstraint("clinica_id", "codigo", name="uq_monedas_clinica_codigo"),
    )

    codigo:    str  = Field(max_length=10,  nullable=False)
    nombre:    str  = Field(max_length=80,  nullable=False)
    simbolo:   str  = Field(max_length=10,  nullable=False)
    es_activa: bool = Field(default=False,  nullable=False)
