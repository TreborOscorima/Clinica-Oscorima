"""add anulación de comprobante (anulado / anulado_en / anulado_motivo)

Habilita anular una venta dejando rastro: el comprobante no desaparece, queda
marcado ANULADO con fecha y motivo. La reversión de caja/stock/deuda la hace el
servicio (`cobro.anular`), no la migración.

Aditiva e idempotente: solo agrega columnas que no existan; no toca datos. El
default anulado=0 preserva todos los comprobantes existentes como vigentes.

Revision ID: a1b2c3d4e5f7
Revises: f7a8b9c0d1e2
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, tabla: str) -> set[str]:
    return {
        r[0] for r in conn.execute(sa.text(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
        ), {"t": tabla}).fetchall()
    }


def upgrade() -> None:
    conn = op.get_bind()
    cols = _cols(conn, "comprobantes")
    if "anulado" not in cols:
        op.add_column("comprobantes", sa.Column(
            "anulado", sa.Boolean(), nullable=False, server_default="0",
        ))
    if "anulado_en" not in cols:
        op.add_column("comprobantes", sa.Column(
            "anulado_en", sa.DateTime(), nullable=True,
        ))
    if "anulado_motivo" not in cols:
        op.add_column("comprobantes", sa.Column(
            "anulado_motivo", sa.String(length=240), nullable=True,
        ))


def downgrade() -> None:
    conn = op.get_bind()
    cols = _cols(conn, "comprobantes")
    if "anulado_motivo" in cols:
        op.drop_column("comprobantes", "anulado_motivo")
    if "anulado_en" in cols:
        op.drop_column("comprobantes", "anulado_en")
    if "anulado" in cols:
        op.drop_column("comprobantes", "anulado")
