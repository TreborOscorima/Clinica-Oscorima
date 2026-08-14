from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class Adjunto(TenantSQLModel, table=True):
    """Archivo clínico de un paciente (A2): foto, estudio, radiografía, PDF.

    El binario vive en disco (ver services/storage.py); acá solo van los
    metadatos. `nota_id` es opcional para poder colgar un adjunto de una nota
    clínica concreta más adelante; hoy se usa a nivel paciente.
    """

    __tablename__ = "adjuntos"

    sede_id:      int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id:  int        = Field(foreign_key="pacientes.id", nullable=False, index=True)
    nota_id:      int | None = Field(default=None, foreign_key="notas_clinicas.id", nullable=True, index=True)
    # C1 — galería estética: una foto puede pertenecer a una sesión y a un momento
    # (antes/durante/después). Nullable: los adjuntos genéricos de A2 no los usan.
    sesion_id:    int | None = Field(default=None, foreign_key="sesiones_esteticas.id", nullable=True, index=True)
    momento:      str | None = Field(default=None, max_length=12, nullable=True)
    nombre:       str        = Field(max_length=255, nullable=False)   # nombre original visible
    stored_name:  str        = Field(max_length=255, nullable=False)   # uuid.ext en disco
    mime:         str | None = Field(default=None, max_length=120, nullable=True)
    tamano:       int        = Field(default=0, nullable=False)        # bytes
    categoria:    str | None = Field(default=None, max_length=40, nullable=True, index=True)
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:   ClassVar[Any] = relationship("Paciente",   lazy="select")
    created_by: ClassVar[Any] = relationship("User",       lazy="select")
