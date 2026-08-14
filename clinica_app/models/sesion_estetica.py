from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

from sqlalchemy import Column, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class SesionEstetica(TenantSQLModel, table=True):
    """Sesión de tratamiento estético (C1 — galería antes/después).

    Cabecera que agrupa las fotos de una visita/tratamiento por fecha y zona.
    Las fotos se guardan como `Adjunto` (categoría "foto") con `sesion_id` +
    `momento` (antes/durante/después), reutilizando el almacenamiento y el
    endpoint de descarga de A2. La lista de sesiones ordenada por fecha es la
    línea de tiempo de evolución del paciente.
    """

    __tablename__ = "sesiones_esteticas"

    sede_id:     int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id: int        = Field(foreign_key="pacientes.id", nullable=False, index=True)
    fecha:       date       = Field(sa_column=Column(Date, nullable=False, index=True))
    titulo:      str        = Field(max_length=160, nullable=False)
    zona:        str | None = Field(default=None, max_length=120, nullable=True)
    notas:       str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:   ClassVar[Any] = relationship("Paciente", lazy="select")
    created_by: ClassVar[Any] = relationship("User", lazy="select")
