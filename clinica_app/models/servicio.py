from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Column, Numeric, Text
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class Servicio(TenantSQLModel, table=True):
    __tablename__ = "servicios"

    nombre:       str           = Field(max_length=120, nullable=False, index=True)
    categoria:    str | None    = Field(default=None, max_length=80, nullable=True, index=True)
    descripcion:  str | None    = Field(default=None, sa_column=Column(Text, nullable=True))
    precio:       Decimal       = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), default=0, nullable=False),
    )
    duracion_min: int           = Field(default=30, nullable=False)
    protocolo:    str | None    = Field(default=None, sa_column=Column(Text, nullable=True))
