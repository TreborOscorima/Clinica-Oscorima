from __future__ import annotations

from sqlmodel import Field

from clinica_app.models.base import BaseSQLModel, SoftDeleteMixin


class Clinica(BaseSQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "clinicas"

    nombre: str = Field(max_length=180, nullable=False, index=True)
    slug: str = Field(max_length=80, nullable=False, unique=True, index=True)
    razon_social: str | None = Field(default=None, max_length=180)
    documento_fiscal: str | None = Field(default=None, max_length=40, index=True)
    email: str | None = Field(default=None, max_length=120)
    telefono: str | None = Field(default=None, max_length=60)
