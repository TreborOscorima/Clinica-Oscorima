"""multi tenant pacientes

Revision ID: 20260506_01
Revises: 6cf17fdcc226
Create Date: 2026-05-06 00:00:00.000000
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "20260506_01"
down_revision = "6cf17fdcc226"
branch_labels = None
depends_on = None


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
    unique_constraints = {uc["name"] for uc in inspector.get_unique_constraints(table_name)}
    if index_name in indexes or index_name in unique_constraints:
        op.drop_index(index_name, table_name=table_name)


def upgrade():
    op.create_table(
        "clinicas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("razon_social", sa.String(length=180), nullable=True),
        sa.Column("documento_fiscal", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("telefono", sa.String(length=60), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinicas_created_at", "clinicas", ["created_at"])
    op.create_index("ix_clinicas_deleted_at", "clinicas", ["deleted_at"])
    op.create_index("ix_clinicas_documento_fiscal", "clinicas", ["documento_fiscal"])
    op.create_index("ix_clinicas_is_active", "clinicas", ["is_active"])
    op.create_index("ix_clinicas_nombre", "clinicas", ["nombre"])
    op.create_index("ix_clinicas_slug", "clinicas", ["slug"], unique=True)

    clinicas = sa.table(
        "clinicas",
        sa.column("id", sa.Integer),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("is_active", sa.Boolean),
        sa.column("nombre", sa.String),
        sa.column("slug", sa.String),
    )
    op.bulk_insert(
        clinicas,
        [
            {
                "id": 1,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "nombre": "Clinica Default",
                "slug": "clinica-default",
            }
        ],
    )

    with op.batch_alter_table("pacientes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("clinica_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))

    op.execute("UPDATE pacientes SET clinica_id = 1 WHERE clinica_id IS NULL")

    with op.batch_alter_table("pacientes", schema=None) as batch_op:
        batch_op.alter_column("clinica_id", existing_type=sa.Integer(), nullable=False)

    for idx in ("ix_pacientes_documento", "uq_pacientes_documento", "email", "uq_pacientes_email"):
        _drop_index_if_exists("pacientes", idx)

    with op.batch_alter_table("pacientes", schema=None) as batch_op:
        batch_op.create_index("ix_pacientes_clinica_id", ["clinica_id"])
        batch_op.create_index("ix_pacientes_created_at", ["created_at"])
        batch_op.create_index("ix_pacientes_deleted_at", ["deleted_at"])
        batch_op.create_index("ix_pacientes_documento", ["documento"])
        batch_op.create_index("ix_pacientes_email", ["email"])
        batch_op.create_index("ix_pacientes_is_active", ["is_active"])
        batch_op.create_index("ix_pacientes_nombre", ["nombre"])
        batch_op.create_unique_constraint(
            "uq_pacientes_clinica_documento",
            ["clinica_id", "documento"],
        )
        batch_op.create_unique_constraint(
            "uq_pacientes_clinica_email",
            ["clinica_id", "email"],
        )
        batch_op.create_foreign_key(
            "fk_pacientes_clinica",
            "clinicas",
            ["clinica_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("pacientes", schema=None) as batch_op:
        batch_op.drop_constraint("fk_pacientes_clinica", type_="foreignkey")
        batch_op.drop_constraint("uq_pacientes_clinica_email", type_="unique")
        batch_op.drop_constraint("uq_pacientes_clinica_documento", type_="unique")
        batch_op.drop_index("ix_pacientes_nombre")
        batch_op.drop_index("ix_pacientes_is_active")
        batch_op.drop_index("ix_pacientes_email")
        batch_op.drop_index("ix_pacientes_documento")
        batch_op.drop_index("ix_pacientes_deleted_at")
        batch_op.drop_index("ix_pacientes_created_at")
        batch_op.drop_index("ix_pacientes_clinica_id")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("clinica_id")
        batch_op.create_index("ix_pacientes_documento", ["documento"], unique=True)
        batch_op.create_unique_constraint("email", ["email"])

    op.drop_index("ix_clinicas_slug", table_name="clinicas")
    op.drop_index("ix_clinicas_nombre", table_name="clinicas")
    op.drop_index("ix_clinicas_is_active", table_name="clinicas")
    op.drop_index("ix_clinicas_documento_fiscal", table_name="clinicas")
    op.drop_index("ix_clinicas_deleted_at", table_name="clinicas")
    op.drop_index("ix_clinicas_created_at", table_name="clinicas")
    op.drop_table("clinicas")
