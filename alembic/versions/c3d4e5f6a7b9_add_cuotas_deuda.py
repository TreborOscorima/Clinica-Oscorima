"""add cuotas_deuda (cronograma de cuotas de una deuda financiada)

Cada fila es una cuota del plan de pago de una DeudaPaciente: número, monto y
vencimiento. El estado de pago no se persiste: se deriva del `pagado` de la
deuda en cascada (ver services/cuotas.py).

Aditiva e idempotente: solo crea la tabla si no existe; no toca datos existentes.

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b9'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a8'
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
    if "cuotas_deuda" in _tablas(conn):
        return
    op.create_table(
        "cuotas_deuda",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("clinica_id", sa.Integer(), sa.ForeignKey("clinicas.id"), nullable=False, index=True),
        sa.Column("deuda_id", sa.Integer(), sa.ForeignKey("deudas_paciente.id"), nullable=False, index=True),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("vencimiento", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    conn = op.get_bind()
    if "cuotas_deuda" in _tablas(conn):
        op.drop_table("cuotas_deuda")
