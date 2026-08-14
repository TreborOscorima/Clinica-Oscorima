from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import Column, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class PlanTratamiento(TenantSQLModel, table=True):
    """Plan de tratamiento de un paciente (B2 — odontología/estética).

    Cabecera: agrupa una serie de tratamientos propuestos (`PlanTratamientoItem`)
    organizados por fases, con presupuesto y seguimiento de avance. Se apoya en
    el odontograma (B1): cada item puede referir una pieza FDI. El `estado` global
    resume el ciclo de vida del plan; el avance real se calcula desde los items.
    """

    __tablename__ = "planes_tratamiento"

    sede_id:     int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id: int        = Field(foreign_key="pacientes.id", nullable=False, index=True)
    titulo:      str        = Field(max_length=160, nullable=False)
    estado:      str        = Field(default="borrador", max_length=20, nullable=False)
    notas:       str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:   ClassVar[Any] = relationship("Paciente", lazy="select")
    created_by: ClassVar[Any] = relationship("User", lazy="select")


class PlanTratamientoItem(TenantSQLModel, table=True):
    """Línea de un plan de tratamiento: un tratamiento propuesto.

    Puede vincularse a una pieza del odontograma (`pieza_numero`, FDI) y a un
    servicio del catálogo (`servicio_id`, para heredar precio). `fase` agrupa los
    items en etapas; `estado` sigue el avance (propuesto → aprobado → en_curso →
    terminado). Al cobrarse, `comprobante_id` enlaza con Caja.
    """

    __tablename__ = "plan_tratamiento_items"

    plan_id:      int        = Field(foreign_key="planes_tratamiento.id", nullable=False, index=True)
    fase:         int        = Field(default=1, nullable=False)
    orden:        int        = Field(default=0, nullable=False)
    pieza_numero: str | None = Field(default=None, max_length=4, nullable=True)
    servicio_id:  int | None = Field(default=None, foreign_key="servicios.id", nullable=True, index=True)
    descripcion:  str        = Field(max_length=200, nullable=False)
    precio:       Decimal    = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), default=0, nullable=False),
    )
    estado:       str        = Field(default="propuesto", max_length=20, nullable=False)
    comprobante_id: int | None = Field(
        default=None, sa_column=Column(Integer, ForeignKey("comprobantes.id"), nullable=True)
    )

    plan:     ClassVar[Any] = relationship("PlanTratamiento", lazy="select")
    servicio: ClassVar[Any] = relationship("Servicio", lazy="select")
