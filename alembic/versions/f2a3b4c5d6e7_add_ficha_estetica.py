"""add ficha estética: sesiones_esteticas cols + sesion_insumos

Ficha de tratamiento estético (C2 del plan multi-especialidad). Extiende la
sesión estética (C1) con nº de sesión, parámetros del equipo y próxima sesión
recomendada, más una tabla de insumos/productos aplicados por sesión. Aditiva
e idempotente.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()]


def _columns(conn, tabla: str) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {"t": tabla}).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()

    cols = _columns(conn, 'sesiones_esteticas')
    if 'numero_sesion' not in cols:
        op.add_column('sesiones_esteticas', sa.Column('numero_sesion', sa.Integer(), nullable=True))
    if 'parametros' not in cols:
        op.add_column('sesiones_esteticas', sa.Column('parametros', sa.Text(), nullable=True))
    if 'proxima_recomendada' not in cols:
        op.add_column('sesiones_esteticas', sa.Column('proxima_recomendada', sa.Date(), nullable=True))
        op.create_index('ix_sesiones_esteticas_proxima_recomendada', 'sesiones_esteticas', ['proxima_recomendada'])

    if 'sesion_insumos' not in _tables(conn):
        op.create_table(
            'sesion_insumos',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('sesion_id', sa.Integer(), sa.ForeignKey('sesiones_esteticas.id'), nullable=False),
            sa.Column('producto_id', sa.Integer(), sa.ForeignKey('inv_productos.id'), nullable=True),
            sa.Column('descripcion', sa.String(length=200), nullable=False),
            sa.Column('cantidad', sa.Numeric(12, 3), nullable=False, server_default='0'),
            sa.Column('unidad', sa.String(length=20), nullable=True),
        )
        op.create_index('ix_sesion_insumos_clinica_id', 'sesion_insumos', ['clinica_id'])
        op.create_index('ix_sesion_insumos_sesion_id', 'sesion_insumos', ['sesion_id'])
        op.create_index('ix_sesion_insumos_producto_id', 'sesion_insumos', ['producto_id'])
        op.create_index('ix_sesion_insumos_is_active', 'sesion_insumos', ['is_active'])
        op.create_index('ix_sesion_insumos_created_at', 'sesion_insumos', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()

    if 'sesion_insumos' in _tables(conn):
        for ix in (
            'ix_sesion_insumos_created_at', 'ix_sesion_insumos_is_active',
            'ix_sesion_insumos_producto_id', 'ix_sesion_insumos_sesion_id',
            'ix_sesion_insumos_clinica_id',
        ):
            op.drop_index(ix, table_name='sesion_insumos')
        op.drop_table('sesion_insumos')

    cols = _columns(conn, 'sesiones_esteticas')
    if 'proxima_recomendada' in cols:
        op.drop_index('ix_sesiones_esteticas_proxima_recomendada', table_name='sesiones_esteticas')
        op.drop_column('sesiones_esteticas', 'proxima_recomendada')
    if 'parametros' in cols:
        op.drop_column('sesiones_esteticas', 'parametros')
    if 'numero_sesion' in cols:
        op.drop_column('sesiones_esteticas', 'numero_sesion')
