from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy import Column, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class PiezaDental(TenantSQLModel, table=True):
    """Estado de una pieza dental de un paciente (B1 — odontograma).

    Se guarda **una fila por pieza con datos** (numeración FDI): las piezas sin
    intervención no ocupan fila y el servicio las presenta como "sano". El estado
    a nivel diente vive en `estado`; el detalle por cara (vestibular, lingual,
    mesial, distal, oclusal) va en `caras` como JSON. `UniqueConstraint`
    (clinica, paciente, numero) permite hacer upsert por pieza.
    """

    __tablename__ = "piezas_dentales"
    __table_args__ = (
        UniqueConstraint("clinica_id", "paciente_id", "numero", name="uq_pieza_clinica_paciente_numero"),
    )

    sede_id:     int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id: int        = Field(foreign_key="pacientes.id", nullable=False, index=True)
    numero:      str        = Field(max_length=4, nullable=False)          # FDI: "18", "55", …
    estado:      str        = Field(default="sano", max_length=30, nullable=False)
    caras:       str | None = Field(default=None, sa_column=Column(Text, nullable=True))  # JSON {cara: estado}
    nota:        str | None = Field(default=None, max_length=255, nullable=True)
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:   ClassVar[Any] = relationship("Paciente", lazy="select")
    created_by: ClassVar[Any] = relationship("User",     lazy="select")
