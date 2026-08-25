"""add inv_lotes (lotes/partidas de producto con vencimiento)

Habilita el control de vencimientos (fármacos e insumos estéticos) y el consumo
FEFO. El `inv_productos.stock_actual` sigue siendo la fuente de verdad agregada;
esta tabla es un desglose por partida que se mantiene best-effort en cada consumo.

Aditiva e idempotente: solo crea la tabla si no existe; no toca datos existentes.

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tablas(conn) -> set[str]:
    return {
        r[0] for r in conn.execute(sa.text(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE()"
        )).fetchall()
    }


def upgrade() -> None:
    conn = op.get_bind()
    if "inv_lotes" in _tablas(conn):
        return
    op.create_table(
        "inv_lotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("clinica_id", sa.Integer(), sa.ForeignKey("clinicas.id"), nullable=False, index=True),
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id"), nullable=True, index=True),
        sa.Column("producto_id", sa.Integer(), sa.ForeignKey("inv_productos.id"), nullable=False, index=True),
        sa.Column("lote", sa.String(length=80), nullable=False),
        sa.Column("vencimiento", sa.Date(), nullable=True, index=True),
        sa.Column("cantidad_inicial", sa.Numeric(12, 3), nullable=False),
        sa.Column("cantidad_actual", sa.Numeric(12, 3), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1", index=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, index=True),
        sa.UniqueConstraint(
            "clinica_id", "sede_id", "producto_id", "lote",
            name="uq_inv_lotes_clinica_sede_prod_lote",
        ),
    )


def downgrade() -> None:
    conn = op.get_bind()
    if "inv_lotes" in _tablas(conn):
        op.drop_table("inv_lotes")
