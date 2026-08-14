from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class DisponibilidadProfesional(TenantSQLModel, table=True):
    """Horario semanal de atención de un profesional (agenda real).

    Una fila por franja: (día de la semana, hora_inicio, hora_fin). Un profesional
    puede tener varias franjas por día (p. ej. mañana y tarde). Si un profesional
    no tiene ninguna franja cargada, se considera *siempre disponible* (no se
    valida horario). Las horas se guardan como texto "HH:MM".
    """

    __tablename__ = "disponibilidad_profesional"

    sede_id:        int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    profesional_id: int        = Field(foreign_key="profesionales.id", nullable=False, index=True)
    dia_semana:     int        = Field(nullable=False)              # 0=lunes … 6=domingo
    hora_inicio:    str        = Field(sa_column=Column(String(5), nullable=False))   # "HH:MM"
    hora_fin:       str        = Field(sa_column=Column(String(5), nullable=False))   # "HH:MM"

    profesional: ClassVar[Any] = relationship("Profesional", lazy="select")


class BloqueoAgenda(TenantSQLModel, table=True):
    """Bloqueo de agenda de un profesional (vacaciones, ausencia, licencia).

    Rango [inicio, fin) en el que el profesional NO está disponible; cualquier
    turno que se solape con el rango se rechaza.
    """

    __tablename__ = "bloqueos_agenda"

    sede_id:        int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    profesional_id: int        = Field(foreign_key="profesionales.id", nullable=False, index=True)
    inicio:         datetime   = Field(sa_column=Column(DateTime, nullable=False, index=True))
    fin:            datetime   = Field(sa_column=Column(DateTime, nullable=False, index=True))
    motivo:         str | None = Field(default=None, max_length=200, nullable=True)

    profesional: ClassVar[Any] = relationship("Profesional", lazy="select")
