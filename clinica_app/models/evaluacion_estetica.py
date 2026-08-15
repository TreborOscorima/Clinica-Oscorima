from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class EvaluacionEstetica(TenantSQLModel, table=True):
    """Evaluación estética por zona anatómica (E5 — mapa estético).

    Registra la valoración de una zona facial/corporal (del catálogo en
    `services/anatomia.py`) en una categoría (simetría, volumen, arrugas,
    flacidez, pigmentación, textura, hidratación…) con una severidad 0–4 y una
    observación libre. Opcionalmente ligada a una `SesionEstetica`. No mueve
    stock ni toca el resto del sistema; reutiliza tenant + auditoría.
    """

    __tablename__ = "evaluaciones_esteticas"

    sede_id:     int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id: int        = Field(foreign_key="pacientes.id", nullable=False, index=True)
    sesion_id:   int | None = Field(default=None, foreign_key="sesiones_esteticas.id", nullable=True, index=True)
    zona_codigo: str        = Field(max_length=40, nullable=False, index=True)
    categoria:   str        = Field(max_length=40, nullable=False)
    severidad:   int | None = Field(default=None, nullable=True)
    observacion: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_by_id: int | None = Field(
        sa_column=Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    )

    paciente:   ClassVar[Any] = relationship("Paciente", lazy="select")
    sesion:     ClassVar[Any] = relationship("SesionEstetica", lazy="select")
    created_by: ClassVar[Any] = relationship("User", lazy="select")
