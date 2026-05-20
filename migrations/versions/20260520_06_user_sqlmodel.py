"""User: migrar a TenantSQLModel — renombrar activo→is_active, agregar deleted_at

Revision ID: 20260520_06
Revises: 20260506_05
Create Date: 2026-05-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260520_06"
down_revision = "20260506_05"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        # Renombrar 'activo' → 'is_active' (SoftDeleteMixin)
        batch_op.alter_column(
            "activo",
            new_column_name="is_active",
            existing_type=sa.Boolean(),
            existing_nullable=False,
        )
        batch_op.create_index("ix_usuarios_is_active", ["is_active"])
        # Agregar campo de soft-delete timestamp
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_usuarios_deleted_at", ["deleted_at"])
        # Agregar índice en created_at (TimestampMixin lo define con index=True)
        batch_op.create_index("ix_usuarios_created_at", ["created_at"])


def downgrade():
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.drop_index("ix_usuarios_created_at")
        batch_op.drop_index("ix_usuarios_deleted_at")
        batch_op.drop_column("deleted_at")
        batch_op.drop_index("ix_usuarios_is_active")
        batch_op.alter_column(
            "is_active",
            new_column_name="activo",
            existing_type=sa.Boolean(),
            existing_nullable=False,
        )
