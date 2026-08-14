from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class SesionEstetica(TenantSQLModel, table=True):
    """Sesión de tratamiento estético (C1 galería + C2 ficha).

    Cabecera que agrupa las fotos de una visita/tratamiento por fecha y zona
    (C1). Las fotos se guardan como `Adjunto` (categoría "foto") con `sesion_id`
    + `momento`. C2 agrega la ficha clínica: nº de sesión, zonas tratadas
    (`zona`), parámetros del equipo, próxima sesión recomendada e insumos
    aplicados (`SesionInsumo`). La lista ordenada por fecha es la línea de
    tiempo de evolución del paciente.
    """

    __tablename__ = "sesiones_esteticas"

    sede_id:     int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id: int        = Field(foreign_key="pacientes.id", nullable=False, index=True)
    fecha:       date       = Field(sa_column=Column(Date, nullable=False, index=True))
    titulo:      str        = Field(max_length=160, nullable=False)
    zona:        str | None = Field(default=None, max_length=120, nullable=True)
    notas:       str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # ── Ficha clínica (C2) ──────────────────────────────────────────────────────
    numero_sesion:       int | None  = Field(default=None, nullable=True)
    parametros:          str | None  = Field(default=None, sa_column=Column(Text, nullable=True))
    proxima_recomendada: date | None = Field(default=None, sa_column=Column(Date, nullable=True, index=True))
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:   ClassVar[Any] = relationship("Paciente", lazy="select")
    created_by: ClassVar[Any] = relationship("User", lazy="select")


class SesionInsumo(TenantSQLModel, table=True):
    """Insumo/producto aplicado en una sesión estética (C2).

    Registro descriptivo de lo aplicado (no mueve stock): opcionalmente referido
    a un producto de inventario (`producto_id`), con cantidad y unidad
    (ml, UI, disparos, J/cm²…).
    """

    __tablename__ = "sesion_insumos"

    sesion_id:   int        = Field(foreign_key="sesiones_esteticas.id", nullable=False, index=True)
    producto_id: int | None = Field(default=None, foreign_key="inv_productos.id", nullable=True, index=True)
    descripcion: str        = Field(max_length=200, nullable=False)
    cantidad:    Decimal    = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(12, 3), default=0, nullable=False),
    )
    unidad:      str | None = Field(default=None, max_length=20, nullable=True)

    sesion:   ClassVar[Any] = relationship("SesionEstetica", lazy="select")
    producto: ClassVar[Any] = relationship("Producto", lazy="select")
