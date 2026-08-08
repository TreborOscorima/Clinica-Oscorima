"""add audit_log table

Bitácora append-only de acciones sensibles (cobros, anulaciones, cierres de
caja, cambios de permisos, borrados). Requisito de trazabilidad en salud.

Revision ID: e5h3i4j5k6l7
Revises: d4g2h3i4j5k6
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5h3i4j5k6l7'
down_revision: Union[str, Sequence[str], None] = 'd4g2h3i4j5k6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()

    if 'audit_log' not in _tables(conn):
        op.create_table(
            'audit_log',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
            sa.Column('sede_id', sa.Integer(), nullable=True),
            sa.Column('accion', sa.String(length=40), nullable=False),
            sa.Column('entidad', sa.String(length=40), nullable=False),
            sa.Column('entidad_id', sa.Integer(), nullable=True),
            sa.Column('detalle', sa.Text(), nullable=True),
            sa.Column('creado_en', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_audit_log_clinica_id', 'audit_log', ['clinica_id'])
        op.create_index('ix_audit_log_usuario_id', 'audit_log', ['usuario_id'])
        op.create_index('ix_audit_log_accion', 'audit_log', ['accion'])
        op.create_index('ix_audit_log_entidad', 'audit_log', ['entidad'])
        op.create_index('ix_audit_log_creado_en', 'audit_log', ['creado_en'])


def downgrade() -> None:
    conn = op.get_bind()
    if 'audit_log' in _tables(conn):
        for ix in (
            'ix_audit_log_creado_en', 'ix_audit_log_entidad', 'ix_audit_log_accion',
            'ix_audit_log_usuario_id', 'ix_audit_log_clinica_id',
        ):
            op.drop_index(ix, table_name='audit_log')
        op.drop_table('audit_log')
