from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Numeric, Text
from sqlmodel import Field, SQLModel

from clinica_app.models.base import TenantSQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


class ServicioPrecioHist(SQLModel, table=True):
    """Historial de cambios de precio de un servicio."""
    __tablename__ = "servicios_precio_hist"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    clinica_id:  int            = Field(foreign_key="clinicas.id", nullable=False, index=True)
    servicio_id: int            = Field(foreign_key="servicios.id", nullable=False, index=True)
    precio_anterior: Decimal    = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    precio_nuevo:    Decimal    = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    motivo:      str | None     = Field(default=None, max_length=200, nullable=True)
    usuario_id:  int | None     = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )
    registrado_en: datetime     = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime, default=_utcnow, nullable=False),
    )
