"""add odontograma_versiones (versionado del odontograma)

Snapshots del odontograma en el tiempo (B1 — versionado). Cada fila congela el
estado de las piezas con datos en JSON, permitiendo consultar la evolución dental
sin bloquear la edición del odontograma vivo. Aditiva e idempotente.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()

    if 'odontograma_versiones' not in _tables(conn):
        op.create_table(
            'odontograma_versiones',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'), nullable=False),
            sa.Column('titulo', sa.String(length=120), nullable=False),
            sa.Column('nota', sa.String(length=255), nullable=True),
            sa.Column('piezas', sa.Text(), nullable=False),
            sa.Column('con_datos', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        )
        op.create_index('ix_odontograma_versiones_clinica_id', 'odontograma_versiones', ['clinica_id'])
        op.create_index('ix_odontograma_versiones_paciente_id', 'odontograma_versiones', ['paciente_id'])
        op.create_index('ix_odontograma_versiones_sede_id', 'odontograma_versiones', ['sede_id'])
        op.create_index('ix_odontograma_versiones_is_active', 'odontograma_versiones', ['is_active'])
        op.create_index('ix_odontograma_versiones_created_at', 'odontograma_versiones', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()

    if 'odontograma_versiones' in _tables(conn):
        for ix in (
            'ix_odontograma_versiones_created_at', 'ix_odontograma_versiones_is_active',
            'ix_odontograma_versiones_sede_id', 'ix_odontograma_versiones_paciente_id',
            'ix_odontograma_versiones_clinica_id',
        ):
            op.drop_index(ix, table_name='odontograma_versiones')
        op.drop_table('odontograma_versiones')
