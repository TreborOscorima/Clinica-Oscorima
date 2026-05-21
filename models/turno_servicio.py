from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlmodel import Field, SQLModel

from extensions import db
from models.servicio import Servicio


class TurnoServicio(SQLModel, table=True):
    __tablename__ = "turno_servicios"
    metadata = db.metadata

    id: int | None = Field(default=None, primary_key=True)
    turno_id: int = Field(
        sa_column=Column(Integer, ForeignKey("turnos.id", ondelete="CASCADE"), nullable=False)
    )
    servicio_id: int = Field(foreign_key="servicios.id", nullable=False)
    precio: Decimal | None = Field(default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    cantidad: Decimal | None = Field(default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    descuento: Decimal | None = Field(default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    nota: str | None = Field(default=None, sa_column=Column(String(240), nullable=True))

    servicio: ClassVar[Any] = relationship(Servicio, lazy="select")
