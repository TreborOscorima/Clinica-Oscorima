from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class ImpuestoTasa(TenantSQLModel, table=True):
    __tablename__ = "impuesto_tasas"
    __table_args__ = (
        UniqueConstraint("clinica_id", "tipo_impuesto", "nombre", name="uq_impuesto_tasas"),
    )

    tipo_impuesto: str   = Field(default="IVA", max_length=20, nullable=False)
    nombre:        str   = Field(max_length=80,  nullable=False)
    porcentaje:    float = Field(nullable=False)
    is_default:    bool  = Field(default=False,  nullable=False)
