from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Integer, Text
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(SQLModel, table=True):
    """Bitácora append-only de acciones sensibles (cobros, anulaciones, cierres
    de caja, cambios de permisos, borrados). Nunca se edita ni se borra:
    trazabilidad legal, requisito en salud.
    """
    __tablename__ = "audit_log"

    id: int | None = Field(
        default=None,
        # BigInteger en MySQL (volumen); Integer en SQLite para que autoincremente
        # como rowid en la suite de tests.
        sa_column=Column(
            BigInteger().with_variant(Integer, "sqlite"),
            primary_key=True, autoincrement=True,
        ),
    )
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    usuario_id: int | None = Field(
        default=None, foreign_key="usuarios.id", nullable=True, index=True
    )
    sede_id: int | None = Field(default=None, nullable=True)
    # Verbo de la acción: crear, anular, cerrar_caja, eliminar, cambiar_permisos, ...
    accion: str = Field(max_length=40, nullable=False, index=True)
    # Entidad afectada: comprobante, compra, cierre_caja, caja_movimiento, permiso_rol, ...
    entidad: str = Field(max_length=40, nullable=False, index=True)
    entidad_id: int | None = Field(default=None, nullable=True)
    # Contexto extra (JSON serializado o texto libre).
    detalle: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    creado_en: datetime | None = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime, default=_utcnow, nullable=False, index=True),
    )
