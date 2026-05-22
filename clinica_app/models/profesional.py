from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class Profesional(TenantSQLModel, table=True):
    __tablename__ = "profesionales"
    __table_args__ = (
        UniqueConstraint("clinica_id", "dni",      name="uq_prof_clinica_dni"),
        UniqueConstraint("clinica_id", "matricula", name="uq_prof_clinica_matricula"),
    )

    nombres:     str           = Field(max_length=120, nullable=False)
    apellidos:   str           = Field(max_length=120, nullable=False)
    dni:         str | None    = Field(default=None, max_length=40,  nullable=True, index=True)
    matricula:   str | None    = Field(default=None, max_length=60,  nullable=True, index=True)
    especialidad: str | None   = Field(default=None, max_length=120, nullable=True)
    telefono:    str | None    = Field(default=None, max_length=60,  nullable=True)
    email:       str | None    = Field(default=None, max_length=120, nullable=True)

    @property
    def nombre_completo(self) -> str:
        return f"{(self.nombres or '').strip()} {(self.apellidos or '').strip()}".strip()
