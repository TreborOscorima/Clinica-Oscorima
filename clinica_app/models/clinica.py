from __future__ import annotations

from sqlmodel import Field

from clinica_app.models.base import BaseSQLModel, SoftDeleteMixin


class Clinica(BaseSQLModel, SoftDeleteMixin, table=True):
    __tablename__ = "clinicas"

    nombre:           str       = Field(max_length=180, nullable=False, index=True)
    slug:             str       = Field(max_length=80,  nullable=False, unique=True, index=True)
    razon_social:     str | None = Field(default=None, max_length=180)
    documento_fiscal: str | None = Field(default=None, max_length=40, index=True)
    email:            str | None = Field(default=None, max_length=120)
    telefono:         str | None = Field(default=None, max_length=60)

    # Campos adicionales de empresa
    direccion_fiscal:        str | None = Field(default=None, max_length=240)
    zona_horaria:            str | None = Field(default=None, max_length=80)
    rubro:                   str | None = Field(default=None, max_length=80)
    mensaje_recibo:          str | None = Field(default=None, max_length=240)
    papel_impresion:         str | None = Field(default="80mm", max_length=20)
    ancho_recibo:            int | None = Field(default=None)
    margen_global:           float      = Field(default=50.0,  sa_column_kwargs={"server_default": "50.00"})
    mostrar_impuesto_recibo: bool       = Field(default=False, sa_column_kwargs={"server_default": "0"})
