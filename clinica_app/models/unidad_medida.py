from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class UnidadMedida(TenantSQLModel, table=True):
    __tablename__ = "unidades_medida"
    __table_args__ = (
        UniqueConstraint("clinica_id", "nombre", name="uq_unidades_clinica_nombre"),
    )

    nombre:            str  = Field(max_length=60, nullable=False)
    permite_decimales: bool = Field(default=False,  nullable=False)
