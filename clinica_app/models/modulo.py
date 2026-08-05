from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from clinica_app.models.base import BaseSQLModel


class ClinicaModulo(BaseSQLModel, table=True):
    """Override por clínica de qué módulos están habilitados (Fase 3 Owner Panel).

    LIFE no gatea módulos por plan: por defecto TODOS están disponibles. Esta
    tabla guarda solo los overrides del owner (habilitar/deshabilitar por clínica).
    Si no hay fila para un módulo, se considera habilitado. El módulo se ve en la
    app si (el rol lo permite) AND (el owner no lo deshabilitó).
    """

    __tablename__ = "clinica_modulos"
    __table_args__ = (
        UniqueConstraint("clinica_id", "modulo", name="uq_clinica_modulos"),
    )

    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    modulo: str = Field(max_length=40, nullable=False)
    habilitado: bool = Field(default=True, nullable=False)
