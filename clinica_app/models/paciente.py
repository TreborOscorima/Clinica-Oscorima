from __future__ import annotations

from datetime import date

from sqlalchemy import Column, Date, UniqueConstraint
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class Paciente(TenantSQLModel, table=True):
    __tablename__ = "pacientes"
    __table_args__ = (
        UniqueConstraint("clinica_id", "documento", name="uq_pacientes_clinica_documento"),
        UniqueConstraint("clinica_id", "email", name="uq_pacientes_clinica_email"),
    )

    nombre: str = Field(max_length=180, nullable=False, index=True)
    documento: str | None = Field(default=None, max_length=40, nullable=True, index=True)
    direccion: str | None = Field(default=None, max_length=200, nullable=True)
    email: str | None = Field(default=None, max_length=120, nullable=True, index=True)
    telefono: str | None = Field(default=None, max_length=60, nullable=True)
    fecha_nacimiento: date | None = Field(
        default=None, sa_column=Column(Date(), nullable=True)
    )
    contacto_emergencia: str | None = Field(default=None, max_length=160, nullable=True)

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
