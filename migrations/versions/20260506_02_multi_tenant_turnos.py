"""multi tenant turnos

Revision ID: 20260506_02
Revises: 20260506_01
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260506_02"
down_revision = "20260506_01"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("turnos", schema=None) as batch_op:
        batch_op.add_column(sa.Column("clinica_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))

    op.execute(
        """
        UPDATE turnos t
        JOIN pacientes p ON p.id = t.paciente_id
        SET t.clinica_id = p.clinica_id
        WHERE t.clinica_id IS NULL
        """
    )
    op.execute("UPDATE turnos SET clinica_id = 1 WHERE clinica_id IS NULL")

    with op.batch_alter_table("turnos", schema=None) as batch_op:
        batch_op.alter_column("clinica_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index("ix_turnos_clinica_id", ["clinica_id"])
        batch_op.create_index("ix_turnos_created_at", ["created_at"])
        batch_op.create_index("ix_turnos_deleted_at", ["deleted_at"])
        batch_op.create_index("ix_turnos_is_active", ["is_active"])
        batch_op.create_foreign_key(
            "fk_turnos_clinica",
            "clinicas",
            ["clinica_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("turnos", schema=None) as batch_op:
        batch_op.drop_constraint("fk_turnos_clinica", type_="foreignkey")
        batch_op.drop_index("ix_turnos_is_active")
        batch_op.drop_index("ix_turnos_deleted_at")
        batch_op.drop_index("ix_turnos_created_at")
        batch_op.drop_index("ix_turnos_clinica_id")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("clinica_id")
