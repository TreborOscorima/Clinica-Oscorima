from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import Column, Float, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class ProcedimientoEstetico(TenantSQLModel, table=True):
    """Procedimiento estético aplicado en una zona (E5 — mapa estético).

    Cabecera de un procedimiento (toxina botulínica, ácido hialurónico,
    bioestimulador, mesoterapia…) sobre una zona anatómica del catálogo, para
    un paciente y opcionalmente ligado a una `SesionEstetica`. Agrupa los
    `PuntoAplicacion` (coordenadas + producto + lote + cantidad).
    """

    __tablename__ = "procedimientos_esteticos"

    sede_id:     int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id: int        = Field(foreign_key="pacientes.id", nullable=False, index=True)
    sesion_id:   int | None = Field(default=None, foreign_key="sesiones_esteticas.id", nullable=True, index=True)
    zona_codigo: str        = Field(max_length=40, nullable=False, index=True)
    tipo:        str        = Field(max_length=40, nullable=False)
    observacion: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:   ClassVar[Any] = relationship("Paciente", lazy="select")
    sesion:     ClassVar[Any] = relationship("SesionEstetica", lazy="select")
    created_by: ClassVar[Any] = relationship("User", lazy="select")


class PuntoAplicacion(TenantSQLModel, table=True):
    """Punto de aplicación de un procedimiento estético (E5 — CORAZÓN del pedido).

    Cada punto lleva coordenada normalizada (0..1) sobre el modelo/vista, la
    zona anatómica, el producto de inventario aplicado (trazabilidad + lote),
    cantidad y unidad (UI, ml, disparos…). Es descriptivo: NO mueve stock por sí
    mismo (la baja de inventario sigue por la ficha de sesión). Cuelga de un
    `ProcedimientoEstetico`.
    """

    __tablename__ = "puntos_aplicacion"

    sede_id:          int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    procedimiento_id: int        = Field(foreign_key="procedimientos_esteticos.id", nullable=False, index=True)
    zona_codigo:      str        = Field(max_length=40, nullable=False, index=True)
    coord_x:          float      = Field(sa_column=Column(Float, nullable=False, default=0.0))
    coord_y:          float      = Field(sa_column=Column(Float, nullable=False, default=0.0))
    producto_id:      int | None = Field(default=None, foreign_key="inv_productos.id", nullable=True, index=True)
    lote:             str | None = Field(default=None, max_length=60, nullable=True)
    cantidad:         Decimal    = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(12, 3), default=0, nullable=False),
    )
    unidad:           str | None = Field(default=None, max_length=20, nullable=True)
    observacion:      str | None = Field(default=None, max_length=200, nullable=True)

    procedimiento: ClassVar[Any] = relationship("ProcedimientoEstetico", lazy="select")
    producto:      ClassVar[Any] = relationship("Producto", lazy="select")
