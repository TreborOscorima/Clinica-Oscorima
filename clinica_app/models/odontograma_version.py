from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class OdontogramaVersion(TenantSQLModel, table=True):
    """Snapshot del odontograma de un paciente en un momento dado (B1 — versionado).

    Permite guardar la evolución dental en el tiempo: cada versión congela el
    estado completo de las piezas *con datos* en JSON (`piezas`), de modo que el
    odontograma vivo (una fila por pieza en `piezas_dentales`) puede seguir
    editándose sin perder los estados históricos. `con_datos` cachea la cantidad
    de piezas intervenidas para listar el historial sin re-parsear el JSON.
    """

    __tablename__ = "odontograma_versiones"

    sede_id:     int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id: int        = Field(foreign_key="pacientes.id", nullable=False, index=True)
    titulo:      str        = Field(max_length=120, nullable=False)
    nota:        str | None = Field(default=None, max_length=255, nullable=True)
    piezas:      str        = Field(sa_column=Column(Text, nullable=False))  # JSON [{numero, estado, caras, nota}]
    con_datos:   int        = Field(default=0, nullable=False)
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:   ClassVar[Any] = relationship("Paciente", lazy="select")
    created_by: ClassVar[Any] = relationship("User",     lazy="select")
