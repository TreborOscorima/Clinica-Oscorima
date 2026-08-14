"""add piezas_dentales table

Odontograma (B1 del plan multi-especialidad): estado por pieza dental del
paciente, numeración FDI. Una fila por pieza con datos; el detalle por cara va
en JSON. Tabla aditiva e idempotente.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()

    if 'piezas_dentales' not in _tables(conn):
        op.create_table(
            'piezas_dentales',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'), nullable=False),
            sa.Column('numero', sa.String(length=4), nullable=False),
            sa.Column('estado', sa.String(length=30), nullable=False, server_default='sano'),
            sa.Column('caras', sa.Text(), nullable=True),
            sa.Column('nota', sa.String(length=255), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
            sa.UniqueConstraint('clinica_id', 'paciente_id', 'numero', name='uq_pieza_clinica_paciente_numero'),
        )
        op.create_index('ix_piezas_dentales_clinica_id', 'piezas_dentales', ['clinica_id'])
        op.create_index('ix_piezas_dentales_paciente_id', 'piezas_dentales', ['paciente_id'])
        op.create_index('ix_piezas_dentales_sede_id', 'piezas_dentales', ['sede_id'])
        op.create_index('ix_piezas_dentales_is_active', 'piezas_dentales', ['is_active'])
        op.create_index('ix_piezas_dentales_created_at', 'piezas_dentales', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    if 'piezas_dentales' in _tables(conn):
        for ix in (
            'ix_piezas_dentales_created_at', 'ix_piezas_dentales_is_active',
            'ix_piezas_dentales_sede_id', 'ix_piezas_dentales_paciente_id',
            'ix_piezas_dentales_clinica_id',
        ):
            op.drop_index(ix, table_name='piezas_dentales')
        op.drop_table('piezas_dentales')
