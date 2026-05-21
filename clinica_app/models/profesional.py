from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profesional(SQLModel, table=True):
    __tablename__ = "profesionales"

    id: int | None = Field(default=None, primary_key=True)
    dni: str | None = Field(default=None, max_length=40, nullable=True, unique=True, index=True)
    matricula: str | None = Field(default=None, max_length=60, nullable=True, unique=True, index=True)
    nombres: str = Field(max_length=120, nullable=False)
    apellidos: str = Field(max_length=120, nullable=False)
    especialidad: str | None = Field(default=None, max_length=120, nullable=True)
    created_at: datetime | None = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime, default=_utcnow, nullable=True),
    )
    updated_at: datetime | None = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=True),
    )

    @property
    def nombre_completo(self) -> str:
        return f"{(self.nombres or '').strip()} {(self.apellidos or '').strip()}".strip()
