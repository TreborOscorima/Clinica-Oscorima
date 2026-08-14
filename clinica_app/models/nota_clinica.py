from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Text
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

    sede_id:        int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
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

    # ── Firma / bloqueo (A3) — una nota firmada no se edita ni borra ──
    firmada:        bool = Field(
        default=False, sa_column=Column(Boolean, nullable=False, server_default="0")
    )
    firmada_en:     datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    firmada_por_id: int | None = Field(
        default=None, sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:    ClassVar[Any] = relationship("Paciente",    lazy="select")
    profesional: ClassVar[Any] = relationship("Profesional", lazy="select")
    turno:       ClassVar[Any] = relationship("Turno",       lazy="select")
    # Hay dos FKs a usuarios (created_by_id y firmada_por_id): SQLAlchemy exige
    # declarar foreign_keys en ambas relaciones para desambiguar.
    created_by:  ClassVar[Any] = relationship(
        "User", lazy="select", foreign_keys="[NotaClinica.created_by_id]"
    )
    firmada_por: ClassVar[Any] = relationship(
        "User", lazy="select", foreign_keys="[NotaClinica.firmada_por_id]"
    )
