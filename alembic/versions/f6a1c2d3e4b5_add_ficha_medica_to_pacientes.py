"""add ficha medica columns to pacientes

Ficha médica del paciente (A1 del plan multi-especialidad): grupo sanguíneo,
alergias, antecedentes, medicación habitual y hábitos. Todo opcional (nullable),
así que es una migración puramente aditiva: no toca ni exige datos existentes.

Revision ID: f6a1c2d3e4b5
Revises: e5h3i4j5k6l7
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a1c2d3e4b5'
down_revision: Union[str, Sequence[str], None] = 'e5h3i4j5k6l7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(conn, table: str) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {"t": table}).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn, 'pacientes')

    if 'grupo_sanguineo' not in cols:
        op.add_column('pacientes', sa.Column('grupo_sanguineo', sa.String(length=8), nullable=True))
    if 'alergias' not in cols:
        op.add_column('pacientes', sa.Column('alergias', sa.Text(), nullable=True))
    if 'antecedentes' not in cols:
        op.add_column('pacientes', sa.Column('antecedentes', sa.Text(), nullable=True))
    if 'medicacion' not in cols:
        op.add_column('pacientes', sa.Column('medicacion', sa.Text(), nullable=True))
    if 'habitos' not in cols:
        op.add_column('pacientes', sa.Column('habitos', sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn, 'pacientes')

    for col in ('habitos', 'medicacion', 'antecedentes', 'alergias', 'grupo_sanguineo'):
        if col in cols:
            op.drop_column('pacientes', col)
