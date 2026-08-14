"""add sesiones_esteticas + adjuntos.sesion_id/momento

Galería antes/después estética (C1 del plan multi-especialidad). Cabecera
`sesiones_esteticas` (agrupa fotos por fecha/zona) + dos columnas en `adjuntos`
para colgar cada foto de una sesión y un momento (antes/durante/después).
Aditiva e idempotente.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
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

    if 'sesiones_esteticas' not in _tables(conn):
        op.create_table(
            'sesiones_esteticas',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'), nullable=False),
            sa.Column('fecha', sa.Date(), nullable=False),
            sa.Column('titulo', sa.String(length=160), nullable=False),
            sa.Column('zona', sa.String(length=120), nullable=True),
            sa.Column('notas', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        )
        op.create_index('ix_sesiones_esteticas_clinica_id', 'sesiones_esteticas', ['clinica_id'])
        op.create_index('ix_sesiones_esteticas_paciente_id', 'sesiones_esteticas', ['paciente_id'])
        op.create_index('ix_sesiones_esteticas_sede_id', 'sesiones_esteticas', ['sede_id'])
        op.create_index('ix_sesiones_esteticas_fecha', 'sesiones_esteticas', ['fecha'])
        op.create_index('ix_sesiones_esteticas_is_active', 'sesiones_esteticas', ['is_active'])
        op.create_index('ix_sesiones_esteticas_created_at', 'sesiones_esteticas', ['created_at'])

    cols = _columns(conn, 'adjuntos')
    if 'sesion_id' not in cols:
        op.add_column('adjuntos', sa.Column('sesion_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_adjuntos_sesion_id', 'adjuntos', 'sesiones_esteticas', ['sesion_id'], ['id']
        )
        op.create_index('ix_adjuntos_sesion_id', 'adjuntos', ['sesion_id'])
    if 'momento' not in cols:
        op.add_column('adjuntos', sa.Column('momento', sa.String(length=12), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()

    cols = _columns(conn, 'adjuntos')
    if 'momento' in cols:
        op.drop_column('adjuntos', 'momento')
    if 'sesion_id' in cols:
        op.drop_index('ix_adjuntos_sesion_id', table_name='adjuntos')
        op.drop_constraint('fk_adjuntos_sesion_id', 'adjuntos', type_='foreignkey')
        op.drop_column('adjuntos', 'sesion_id')

    if 'sesiones_esteticas' in _tables(conn):
        for ix in (
            'ix_sesiones_esteticas_created_at', 'ix_sesiones_esteticas_is_active',
            'ix_sesiones_esteticas_fecha', 'ix_sesiones_esteticas_sede_id',
            'ix_sesiones_esteticas_paciente_id', 'ix_sesiones_esteticas_clinica_id',
        ):
            op.drop_index(ix, table_name='sesiones_esteticas')
        op.drop_table('sesiones_esteticas')
