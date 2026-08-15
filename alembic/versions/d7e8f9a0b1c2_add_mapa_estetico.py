"""add mapa estético: evaluaciones + procedimientos + puntos de aplicación

Modelo espacial estético (E5 del motor anatómico). Tres tablas nuevas:
- evaluaciones_esteticas: valoración por zona/categoría/severidad.
- procedimientos_esteticos: procedimiento (toxina/relleno/…) por zona.
- puntos_aplicacion: coordenada normalizada + producto + lote + cantidad
  (corazón del pedido estético; NO mueve stock).

Aditiva e idempotente. No toca tablas existentes.

Revision ID: d7e8f9a0b1c2
Revises: b4c5d6e7f8a9
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(conn) -> list[str]:
    return [r[0] for r in conn.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE()"
    )).fetchall()]


def _tenant_cols() -> list[sa.Column]:
    """Columnas comunes de TenantSQLModel (id + timestamps + tenant + soft-delete)."""
    return [
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('clinica_id', sa.Integer(), sa.ForeignKey('clinicas.id'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    ]


def upgrade() -> None:
    conn = op.get_bind()
    existentes = _tables(conn)

    if 'evaluaciones_esteticas' not in existentes:
        op.create_table(
            'evaluaciones_esteticas',
            *_tenant_cols(),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'), nullable=False),
            sa.Column('sesion_id', sa.Integer(), sa.ForeignKey('sesiones_esteticas.id'), nullable=True),
            sa.Column('zona_codigo', sa.String(length=40), nullable=False),
            sa.Column('categoria', sa.String(length=40), nullable=False),
            sa.Column('severidad', sa.Integer(), nullable=True),
            sa.Column('observacion', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        )
        op.create_index('ix_evaluaciones_esteticas_clinica_id', 'evaluaciones_esteticas', ['clinica_id'])
        op.create_index('ix_evaluaciones_esteticas_is_active', 'evaluaciones_esteticas', ['is_active'])
        op.create_index('ix_evaluaciones_esteticas_created_at', 'evaluaciones_esteticas', ['created_at'])
        op.create_index('ix_evaluaciones_esteticas_sede_id', 'evaluaciones_esteticas', ['sede_id'])
        op.create_index('ix_evaluaciones_esteticas_paciente_id', 'evaluaciones_esteticas', ['paciente_id'])
        op.create_index('ix_evaluaciones_esteticas_sesion_id', 'evaluaciones_esteticas', ['sesion_id'])
        op.create_index('ix_evaluaciones_esteticas_zona_codigo', 'evaluaciones_esteticas', ['zona_codigo'])

    if 'procedimientos_esteticos' not in existentes:
        op.create_table(
            'procedimientos_esteticos',
            *_tenant_cols(),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('paciente_id', sa.Integer(), sa.ForeignKey('pacientes.id'), nullable=False),
            sa.Column('sesion_id', sa.Integer(), sa.ForeignKey('sesiones_esteticas.id'), nullable=True),
            sa.Column('zona_codigo', sa.String(length=40), nullable=False),
            sa.Column('tipo', sa.String(length=40), nullable=False),
            sa.Column('observacion', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        )
        op.create_index('ix_procedimientos_esteticos_clinica_id', 'procedimientos_esteticos', ['clinica_id'])
        op.create_index('ix_procedimientos_esteticos_is_active', 'procedimientos_esteticos', ['is_active'])
        op.create_index('ix_procedimientos_esteticos_created_at', 'procedimientos_esteticos', ['created_at'])
        op.create_index('ix_procedimientos_esteticos_sede_id', 'procedimientos_esteticos', ['sede_id'])
        op.create_index('ix_procedimientos_esteticos_paciente_id', 'procedimientos_esteticos', ['paciente_id'])
        op.create_index('ix_procedimientos_esteticos_sesion_id', 'procedimientos_esteticos', ['sesion_id'])
        op.create_index('ix_procedimientos_esteticos_zona_codigo', 'procedimientos_esteticos', ['zona_codigo'])

    if 'puntos_aplicacion' not in existentes:
        op.create_table(
            'puntos_aplicacion',
            *_tenant_cols(),
            sa.Column('sede_id', sa.Integer(), sa.ForeignKey('sedes.id'), nullable=True),
            sa.Column('procedimiento_id', sa.Integer(), sa.ForeignKey('procedimientos_esteticos.id'), nullable=False),
            sa.Column('zona_codigo', sa.String(length=40), nullable=False),
            sa.Column('coord_x', sa.Float(), nullable=False, server_default='0'),
            sa.Column('coord_y', sa.Float(), nullable=False, server_default='0'),
            sa.Column('producto_id', sa.Integer(), sa.ForeignKey('inv_productos.id'), nullable=True),
            sa.Column('lote', sa.String(length=60), nullable=True),
            sa.Column('cantidad', sa.Numeric(12, 3), nullable=False, server_default='0'),
            sa.Column('unidad', sa.String(length=20), nullable=True),
            sa.Column('observacion', sa.String(length=200), nullable=True),
        )
        op.create_index('ix_puntos_aplicacion_clinica_id', 'puntos_aplicacion', ['clinica_id'])
        op.create_index('ix_puntos_aplicacion_is_active', 'puntos_aplicacion', ['is_active'])
        op.create_index('ix_puntos_aplicacion_created_at', 'puntos_aplicacion', ['created_at'])
        op.create_index('ix_puntos_aplicacion_sede_id', 'puntos_aplicacion', ['sede_id'])
        op.create_index('ix_puntos_aplicacion_procedimiento_id', 'puntos_aplicacion', ['procedimiento_id'])
        op.create_index('ix_puntos_aplicacion_producto_id', 'puntos_aplicacion', ['producto_id'])
        op.create_index('ix_puntos_aplicacion_zona_codigo', 'puntos_aplicacion', ['zona_codigo'])


def downgrade() -> None:
    conn = op.get_bind()
    existentes = _tables(conn)

    if 'puntos_aplicacion' in existentes:
        op.drop_table('puntos_aplicacion')
    if 'procedimientos_esteticos' in existentes:
        op.drop_table('procedimientos_esteticos')
    if 'evaluaciones_esteticas' in existentes:
        op.drop_table('evaluaciones_esteticas')
