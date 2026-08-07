from __future__ import annotations

from decimal import Decimal

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ServicioInsumo(SQLModel, table=True):
    __tablename__ = "servicio_insumos"

    id: int | None = Field(default=None, primary_key=True)
    servicio_id: int = Field(
        sa_column_kwargs={"nullable": False, "index": True},
        foreign_key="servicios.id",
    )
    producto_id: int = Field(
        sa_column_kwargs={"nullable": False, "index": True},
        foreign_key="inv_productos.id",
    )
    cantidad_por_sesion: Decimal = Field(default=Decimal("0"), decimal_places=3)

    __table_args__ = (
        UniqueConstraint("servicio_id", "producto_id", name="uq_servicio_producto"),
    )
