from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

from sqlalchemy import Column, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class TipoNota(str, Enum):
    EVOLUCION   = "evolucion"
    ANAMNESIS   = "anamnesis"
    DIAGNOSTICO = "diagnostico"
    INDICACION  = "indicacion"
    OTRO        = "otro"


class NotaClinica(TenantSQLModel, table=True):
    __tablename__ = "notas_clinicas"

    paciente_id:    int       = Field(foreign_key="pacientes.id", nullable=False, index=True)
    turno_id:       int | None = Field(default=None, foreign_key="turnos.id", nullable=True, index=True)
    profesional_id: int | None = Field(default=None, foreign_key="profesionales.id", nullable=True)
    created_by_id:  int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )
    tipo: TipoNota = Field(
        sa_column=Column(SAEnum(TipoNota), nullable=False, default=TipoNota.EVOLUCION)
    )
    contenido: str = Field(sa_column=Column(Text, nullable=False))

    paciente:    ClassVar[Any] = relationship("Paciente",    lazy="select")
    profesional: ClassVar[Any] = relationship("Profesional", lazy="select")
    turno:       ClassVar[Any] = relationship("Turno",       lazy="select")
    created_by:  ClassVar[Any] = relationship("User",        lazy="select")
