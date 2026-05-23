from __future__ import annotations

from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class Sede(TenantSQLModel, table=True):
    """
    Sucursal / sede de una clínica.
    Una Clinica puede tener N Sedes. Los recursos (profesionales, turnos, caja)
    pueden filtrarse opcionalmente por sede_id.
    """
    __tablename__ = "sedes"

    nombre:       str       = Field(max_length=120, nullable=False, index=True)
    direccion:    str | None = Field(default=None, max_length=240, nullable=True)
    telefono:     str | None = Field(default=None, max_length=60,  nullable=True)
    email:        str | None = Field(default=None, max_length=120, nullable=True)
    es_principal: bool       = Field(default=False, nullable=False)
    margen_local: float | None = Field(default=None, nullable=True)
