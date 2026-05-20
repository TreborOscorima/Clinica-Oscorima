"""user clinica jwt

Revision ID: 20260506_05
Revises: 20260506_04
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260506_05"
down_revision = "20260506_04"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.add_column(sa.Column("clinica_id", sa.Integer(), nullable=True))

    op.execute("UPDATE usuarios SET clinica_id = 1 WHERE clinica_id IS NULL")

    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.alter_column("clinica_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index("ix_usuarios_clinica_id", ["clinica_id"])
        batch_op.create_foreign_key("fk_usuarios_clinica", "clinicas", ["clinica_id"], ["id"])


def downgrade():
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.drop_constraint("fk_usuarios_clinica", type_="foreignkey")
        batch_op.drop_index("ix_usuarios_clinica_id")
        batch_op.drop_column("clinica_id")
