"""add agenda profesional: disponibilidad + bloqueos

Agenda profesional real (P2): franjas horarias semanales por profesional
(`disponibilidad_profesional`) y bloqueos/vacaciones (`bloqueos_agenda`). La
detección de solapamientos al crear turno se resuelve en el servicio, sin
columnas nuevas en `turnos`. Aditiva e idempotente.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()]


def upgrade() -> None:
    conn = op.get_bind()
    existentes = _tables(conn)

    if 'disponibilidad_profesional' not in existentes:
        op.create_table(
            'disponibilidad_profesional',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('profesional_id', sa.Integer(), sa.ForeignKey('profesionales.id'), nullable=False),
            sa.Column('dia_semana', sa.Integer(), nullable=False),
            sa.Column('hora_inicio', sa.String(length=5), nullable=False),
            sa.Column('hora_fin', sa.String(length=5), nullable=False),
        )
        op.create_index('ix_disponibilidad_profesional_clinica_id', 'disponibilidad_profesional', ['clinica_id'])
        op.create_index('ix_disponibilidad_profesional_profesional_id', 'disponibilidad_profesional', ['profesional_id'])
        op.create_index('ix_disponibilidad_profesional_sede_id', 'disponibilidad_profesional', ['sede_id'])
        op.create_index('ix_disponibilidad_profesional_is_active', 'disponibilidad_profesional', ['is_active'])
        op.create_index('ix_disponibilidad_profesional_created_at', 'disponibilidad_profesional', ['created_at'])

    if 'bloqueos_agenda' not in existentes:
        op.create_table(
            'bloqueos_agenda',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('profesional_id', sa.Integer(), sa.ForeignKey('profesionales.id'), nullable=False),
            sa.Column('inicio', sa.DateTime(), nullable=False),
            sa.Column('fin', sa.DateTime(), nullable=False),
            sa.Column('motivo', sa.String(length=200), nullable=True),
        )
        op.create_index('ix_bloqueos_agenda_clinica_id', 'bloqueos_agenda', ['clinica_id'])
        op.create_index('ix_bloqueos_agenda_profesional_id', 'bloqueos_agenda', ['profesional_id'])
        op.create_index('ix_bloqueos_agenda_sede_id', 'bloqueos_agenda', ['sede_id'])
        op.create_index('ix_bloqueos_agenda_is_active', 'bloqueos_agenda', ['is_active'])
        op.create_index('ix_bloqueos_agenda_inicio', 'bloqueos_agenda', ['inicio'])
        op.create_index('ix_bloqueos_agenda_fin', 'bloqueos_agenda', ['fin'])
        op.create_index('ix_bloqueos_agenda_created_at', 'bloqueos_agenda', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    existentes = _tables(conn)

    if 'bloqueos_agenda' in existentes:
        for ix in (
            'ix_bloqueos_agenda_created_at', 'ix_bloqueos_agenda_fin', 'ix_bloqueos_agenda_inicio',
            'ix_bloqueos_agenda_is_active', 'ix_bloqueos_agenda_sede_id',
            'ix_bloqueos_agenda_profesional_id', 'ix_bloqueos_agenda_clinica_id',
        ):
            op.drop_index(ix, table_name='bloqueos_agenda')
        op.drop_table('bloqueos_agenda')

    if 'disponibilidad_profesional' in existentes:
        for ix in (
            'ix_disponibilidad_profesional_created_at', 'ix_disponibilidad_profesional_is_active',
            'ix_disponibilidad_profesional_sede_id', 'ix_disponibilidad_profesional_profesional_id',
            'ix_disponibilidad_profesional_clinica_id',
        ):
            op.drop_index(ix, table_name='disponibilidad_profesional')
        op.drop_table('disponibilidad_profesional')
