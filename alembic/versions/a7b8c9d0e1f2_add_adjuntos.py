"""add adjuntos table

Adjuntos clínicos del paciente (A2 del plan multi-especialidad): fotos, estudios,
radiografías y PDFs. El binario vive en disco; esta tabla guarda los metadatos.

Revision ID: a7b8c9d0e1f2
Revises: f6a1c2d3e4b5
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a1c2d3e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()

    if 'adjuntos' not in _tables(conn):
        op.create_table(
            'adjuntos',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'), nullable=False),
            sa.Column('nota_id', sa.Integer(), sa.ForeignKey('notas_clinicas.id'), nullable=True),
            sa.Column('nombre', sa.String(length=255), nullable=False),
            sa.Column('stored_name', sa.String(length=255), nullable=False),
            sa.Column('mime', sa.String(length=120), nullable=True),
            sa.Column('tamano', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('categoria', sa.String(length=40), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        )
        op.create_index('ix_adjuntos_clinica_id', 'adjuntos', ['clinica_id'])
        op.create_index('ix_adjuntos_paciente_id', 'adjuntos', ['paciente_id'])
        op.create_index('ix_adjuntos_nota_id', 'adjuntos', ['nota_id'])
        op.create_index('ix_adjuntos_sede_id', 'adjuntos', ['sede_id'])
        op.create_index('ix_adjuntos_categoria', 'adjuntos', ['categoria'])
        op.create_index('ix_adjuntos_is_active', 'adjuntos', ['is_active'])
        op.create_index('ix_adjuntos_created_at', 'adjuntos', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    if 'adjuntos' in _tables(conn):
        for ix in (
            'ix_adjuntos_created_at', 'ix_adjuntos_is_active', 'ix_adjuntos_categoria',
            'ix_adjuntos_sede_id', 'ix_adjuntos_nota_id', 'ix_adjuntos_paciente_id',
            'ix_adjuntos_clinica_id',
        ):
            op.drop_index(ix, table_name='adjuntos')
        op.drop_table('adjuntos')
