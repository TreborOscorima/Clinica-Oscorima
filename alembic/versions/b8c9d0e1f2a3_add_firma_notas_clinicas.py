"""add firma columns to notas_clinicas

Firma / bloqueo de nota clínica (A3): una nota firmada queda inmutable
(no se edita ni se borra) — requisito de trazabilidad legal en salud.
Columnas: firmada (bool), firmada_en (datetime), firmada_por_id (FK usuarios).
Todo con default seguro → migración aditiva.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(conn, table: str) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {"t": table}).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn, 'notas_clinicas')

    if 'firmada' not in cols:
        op.add_column('notas_clinicas', sa.Column(
            'firmada', sa.Boolean(), nullable=False, server_default=sa.text('0')
        ))
    if 'firmada_en' not in cols:
        op.add_column('notas_clinicas', sa.Column('firmada_en', sa.DateTime(), nullable=True))
    if 'firmada_por_id' not in cols:
        op.add_column('notas_clinicas', sa.Column(
            'firmada_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True
        ))


def downgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn, 'notas_clinicas')
    for col in ('firmada_por_id', 'firmada_en', 'firmada'):
        if col in cols:
            op.drop_column('notas_clinicas', col)
