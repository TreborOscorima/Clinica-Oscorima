from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from sqlalchemy import Column, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlmodel import Field

from extensions import db
from models.base import TenantSQLModel
from models.paciente import Paciente
from models.profesional import Profesional
from models.servicio import Servicio
from models.user import User
from models.turno_servicio import TurnoServicio


class EstadoTurno(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    ATENDIDO = "atendido"


class Turno(TenantSQLModel, table=True):
    __tablename__ = "turnos"
    metadata = db.metadata

    paciente_id: int = Field(foreign_key="pacientes.id", nullable=False)
    profesional_id: int | None = Field(default=None, foreign_key="profesionales.id", nullable=True)
    # legacy: se mantiene para compat, la logica nueva usa items (TurnoServicio)
    servicio_id: int | None = Field(default=None, foreign_key="servicios.id", nullable=True)
    fecha_hora: datetime = Field(nullable=False)
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )
    estado: EstadoTurno | None = Field(
        sa_column=Column(SAEnum(EstadoTurno), nullable=True, default=EstadoTurno.PENDIENTE)
    )
    motivo_cancelacion: str | None = Field(default=None, max_length=240, nullable=True)

    paciente: ClassVar[Any] = relationship(Paciente, lazy="select")
    profesional: ClassVar[Any] = relationship(Profesional, lazy="select")
    servicio: ClassVar[Any] = relationship(Servicio, lazy="select")
    created_by: ClassVar[Any] = relationship(User, lazy="select")
    items: ClassVar[Any] = relationship("TurnoServicio", foreign_keys="[TurnoServicio.turno_id]", cascade="all, delete-orphan", lazy="select", uselist=True)
