from __future__ import annotations

from datetime import date

from sqlalchemy import Column, Date, Text, UniqueConstraint
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class Paciente(TenantSQLModel, table=True):
    __tablename__ = "pacientes"
    __table_args__ = (
        UniqueConstraint("clinica_id", "documento", name="uq_pacientes_clinica_documento"),
        UniqueConstraint("clinica_id", "email", name="uq_pacientes_clinica_email"),
    )

    sede_id: int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    nombre: str = Field(max_length=180, nullable=False, index=True)
    documento: str | None = Field(default=None, max_length=40, nullable=True, index=True)
    direccion: str | None = Field(default=None, max_length=200, nullable=True)
    email: str | None = Field(default=None, max_length=120, nullable=True, index=True)
    telefono: str | None = Field(default=None, max_length=60, nullable=True)
    fecha_nacimiento: date | None = Field(
        default=None, sa_column=Column(Date(), nullable=True)
    )
    contacto_emergencia: str | None = Field(default=None, max_length=160, nullable=True)

    # ── Ficha médica (A1) — todo opcional; sirve a estética y odontología ──
    grupo_sanguineo: str | None = Field(default=None, max_length=8, nullable=True)
    alergias:        str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    antecedentes:    str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    medicacion:      str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    habitos:         str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    @property
    def edad(self) -> int | None:
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        return (
            hoy.year
            - self.fecha_nacimiento.year
            - ((hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
        )
