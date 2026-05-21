from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, DateTime, Numeric, Text
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Servicio(SQLModel, table=True):
    __tablename__ = "servicios"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=120, nullable=False)
    descripcion: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    precio: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    duracion_min: int | None = Field(default=30, nullable=True)
    insumos: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    protocolo: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime | None = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime, default=_utcnow, nullable=True),
    )
    updated_at: datetime | None = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=True),
    )
