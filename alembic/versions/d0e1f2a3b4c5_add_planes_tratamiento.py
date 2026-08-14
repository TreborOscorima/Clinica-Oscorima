"""add planes_tratamiento + plan_tratamiento_items

Plan de tratamiento por fases + presupuesto (B2 del plan multi-especialidad).
Cabecera por paciente (planes_tratamiento) + líneas de tratamiento
(plan_tratamiento_items), cada línea opcionalmente sobre una pieza FDI y un
servicio, con precio y estado de avance. Tablas aditivas e idempotentes.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
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

    if 'planes_tratamiento' not in existentes:
        op.create_table(
            'planes_tratamiento',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'), nullable=False),
            sa.Column('titulo', sa.String(length=160), nullable=False),
            sa.Column('estado', sa.String(length=20), nullable=False, server_default='borrador'),
            sa.Column('notas', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        )
        op.create_index('ix_planes_tratamiento_clinica_id', 'planes_tratamiento', ['clinica_id'])
        op.create_index('ix_planes_tratamiento_paciente_id', 'planes_tratamiento', ['paciente_id'])
        op.create_index('ix_planes_tratamiento_sede_id', 'planes_tratamiento', ['sede_id'])
        op.create_index('ix_planes_tratamiento_is_active', 'planes_tratamiento', ['is_active'])
        op.create_index('ix_planes_tratamiento_created_at', 'planes_tratamiento', ['created_at'])

    if 'plan_tratamiento_items' not in existentes:
        op.create_table(
            'plan_tratamiento_items',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('plan_id', sa.Integer(), sa.ForeignKey('planes_tratamiento.id'), nullable=False),
            sa.Column('fase', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('orden', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('pieza_numero', sa.String(length=4), nullable=True),
            sa.Column('servicio_id', sa.Integer(), sa.ForeignKey('servicios.id'), nullable=True),
            sa.Column('descripcion', sa.String(length=200), nullable=False),
            sa.Column('precio', sa.Numeric(10, 2), nullable=False, server_default='0'),
            sa.Column('estado', sa.String(length=20), nullable=False, server_default='propuesto'),
            sa.Column('comprobante_id', sa.Integer(), sa.ForeignKey('comprobantes.id'), nullable=True),
        )
        op.create_index('ix_plan_tratamiento_items_clinica_id', 'plan_tratamiento_items', ['clinica_id'])
        op.create_index('ix_plan_tratamiento_items_plan_id', 'plan_tratamiento_items', ['plan_id'])
        op.create_index('ix_plan_tratamiento_items_servicio_id', 'plan_tratamiento_items', ['servicio_id'])
        op.create_index('ix_plan_tratamiento_items_is_active', 'plan_tratamiento_items', ['is_active'])
        op.create_index('ix_plan_tratamiento_items_created_at', 'plan_tratamiento_items', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    existentes = _tables(conn)

    if 'plan_tratamiento_items' in existentes:
        for ix in (
            'ix_plan_tratamiento_items_created_at', 'ix_plan_tratamiento_items_is_active',
            'ix_plan_tratamiento_items_servicio_id', 'ix_plan_tratamiento_items_plan_id',
            'ix_plan_tratamiento_items_clinica_id',
        ):
            op.drop_index(ix, table_name='plan_tratamiento_items')
        op.drop_table('plan_tratamiento_items')

    if 'planes_tratamiento' in existentes:
        for ix in (
            'ix_planes_tratamiento_created_at', 'ix_planes_tratamiento_is_active',
            'ix_planes_tratamiento_sede_id', 'ix_planes_tratamiento_paciente_id',
            'ix_planes_tratamiento_clinica_id',
        ):
            op.drop_index(ix, table_name='planes_tratamiento')
        op.drop_table('planes_tratamiento')
