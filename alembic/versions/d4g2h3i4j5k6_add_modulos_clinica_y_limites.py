"""add clinica modulos override table + limit columns

Fase 3 Owner Panel: capa de módulos habilitados por clínica (override del owner)
+ límites por clínica (usuarios, sedes). NULL en las columnas de límite = sin
límite (ilimitado).

Revision ID: d4g2h3i4j5k6
Revises: c3f1a2b4d5e6
Create Date: 2026-08-05 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4g2h3i4j5k6'
down_revision: Union[str, Sequence[str], None] = 'c3f1a2b4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()]


def _columns(conn, table: str) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {"t": table}).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()

    if 'clinica_modulos' not in _tables(conn):
        op.create_table(
            'clinica_modulos',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('modulo', sa.String(length=40), nullable=False),
            sa.Column('habilitado', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('clinica_id', 'modulo', name='uq_clinica_modulos'),
        )
        op.create_index('ix_clinica_modulos_clinica_id', 'clinica_modulos', ['clinica_id'])

    cols = _columns(conn, 'clinicas')
    if 'max_usuarios' not in cols:
        op.add_column('clinicas', sa.Column('max_usuarios', sa.Integer(), nullable=True))
    if 'max_sedes' not in cols:
        op.add_column('clinicas', sa.Column('max_sedes', sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn, 'clinicas')
    if 'max_sedes' in cols:
        op.drop_column('clinicas', 'max_sedes')
    if 'max_usuarios' in cols:
        op.drop_column('clinicas', 'max_usuarios')
    if 'clinica_modulos' in _tables(conn):
        op.drop_index('ix_clinica_modulos_clinica_id', table_name='clinica_modulos')
        op.drop_table('clinica_modulos')
