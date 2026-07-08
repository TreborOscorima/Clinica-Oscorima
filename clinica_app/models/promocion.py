from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, DateTime, Numeric
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Promocion(SQLModel, table=True):
    __tablename__ = "promo_promociones"

    id:          int | None = Field(default=None, primary_key=True)
    clinica_id:  int        = Field(foreign_key="clinicas.id", nullable=False, index=True)
    sede_id:     int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    nombre:      str        = Field(max_length=180, nullable=False, index=True)
    descripcion: str | None = Field(default=None, max_length=500, nullable=True)
    # "porcentaje" | "monto_fijo"
    tipo:        str        = Field(max_length=20, nullable=False, default="porcentaje")
    valor:       Decimal    = Field(sa_column=Column(Numeric(10, 2), nullable=False, default=0))
    # "todo" | "servicios" | "productos"
    aplica_a:    str        = Field(max_length=20, nullable=False, default="todo")
    fecha_inicio: datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    fecha_fin:    datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True)
    )
    activo:      bool       = Field(default=True, nullable=False)
    is_active:   bool       = Field(default=True, nullable=False, index=True)
    deleted_at:  datetime | None = Field(
        default=None, sa_column=Column(DateTime, nullable=True, index=True)
    )
    created_at:  datetime | None = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime, default=_utcnow, nullable=True, index=True),
    )

    def soft_delete(self) -> None:
        self.is_active  = False
        self.deleted_at = _utcnow()
        self.activo     = False

    @property
    def vigente(self) -> bool:
        if not self.activo:
            return False
        now = _utcnow().replace(tzinfo=None)
        if self.fecha_inicio and now < self.fecha_inicio.replace(tzinfo=None):
            return False
        if self.fecha_fin and now > self.fecha_fin.replace(tzinfo=None):
            return False
        return True
