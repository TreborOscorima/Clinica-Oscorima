"""multi tenant caja

Revision ID: 20260506_03
Revises: 20260506_02
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260506_03"
down_revision = "20260506_02"
branch_labels = None
depends_on = None


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
    unique_constraints = {uc["name"] for uc in inspector.get_unique_constraints(table_name)}
    if index_name in indexes or index_name in unique_constraints:
        op.drop_index(index_name, table_name=table_name)


def _add_tenant_soft_delete(table_name: str) -> None:
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.add_column(sa.Column("clinica_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))


def _finalize_tenant_soft_delete(table_name: str, fk_name: str) -> None:
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.alter_column("clinica_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index(f"ix_{table_name}_clinica_id", ["clinica_id"])
        batch_op.create_index(f"ix_{table_name}_deleted_at", ["deleted_at"])
        batch_op.create_index(f"ix_{table_name}_is_active", ["is_active"])
        batch_op.create_foreign_key(fk_name, "clinicas", ["clinica_id"], ["id"])


def upgrade():
    _add_tenant_soft_delete("comprobantes")
    _add_tenant_soft_delete("caja_movimientos")
    _add_tenant_soft_delete("cierres_caja")
    _add_tenant_soft_delete("deudas_paciente")

    op.execute(
        """
        UPDATE comprobantes c
        JOIN pacientes p ON p.id = c.paciente_id
        SET c.clinica_id = p.clinica_id
        WHERE c.clinica_id IS NULL
        """
    )
    op.execute("UPDATE comprobantes SET clinica_id = 1 WHERE clinica_id IS NULL")

    op.execute(
        """
        UPDATE caja_movimientos m
        JOIN comprobantes c ON c.id = m.comprobante_id
        SET m.clinica_id = c.clinica_id
        WHERE m.clinica_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE caja_movimientos m
        JOIN turnos t ON t.id = m.turno_id
        SET m.clinica_id = t.clinica_id
        WHERE m.clinica_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE caja_movimientos m
        JOIN pacientes p ON p.id = m.paciente_id
        SET m.clinica_id = p.clinica_id
        WHERE m.clinica_id IS NULL
        """
    )
    op.execute("UPDATE caja_movimientos SET clinica_id = 1 WHERE clinica_id IS NULL")

    op.execute(
        """
        UPDATE deudas_paciente d
        JOIN comprobantes c ON c.id = d.comprobante_id
        SET d.clinica_id = c.clinica_id
        WHERE d.clinica_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE deudas_paciente d
        JOIN pacientes p ON p.id = d.paciente_id
        SET d.clinica_id = p.clinica_id
        WHERE d.clinica_id IS NULL
        """
    )
    op.execute("UPDATE deudas_paciente SET clinica_id = 1 WHERE clinica_id IS NULL")
    op.execute("UPDATE cierres_caja SET clinica_id = 1 WHERE clinica_id IS NULL")

    _finalize_tenant_soft_delete("comprobantes", "fk_comprobantes_clinica")
    _finalize_tenant_soft_delete("caja_movimientos", "fk_caja_movimientos_clinica")
    _finalize_tenant_soft_delete("deudas_paciente", "fk_deudas_paciente_clinica")

    _drop_index_if_exists("cierres_caja", "fecha")
    with op.batch_alter_table("cierres_caja", schema=None) as batch_op:
        batch_op.alter_column("clinica_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index("ix_cierres_caja_clinica_id", ["clinica_id"])
        batch_op.create_index("ix_cierres_caja_deleted_at", ["deleted_at"])
        batch_op.create_index("ix_cierres_caja_is_active", ["is_active"])
        batch_op.create_unique_constraint("uq_cierres_caja_clinica_fecha", ["clinica_id", "fecha"])
        batch_op.create_foreign_key("fk_cierres_caja_clinica", "clinicas", ["clinica_id"], ["id"])


def downgrade():
    with op.batch_alter_table("cierres_caja", schema=None) as batch_op:
        batch_op.drop_constraint("fk_cierres_caja_clinica", type_="foreignkey")
        batch_op.drop_constraint("uq_cierres_caja_clinica_fecha", type_="unique")
        batch_op.drop_index("ix_cierres_caja_is_active")
        batch_op.drop_index("ix_cierres_caja_deleted_at")
        batch_op.drop_index("ix_cierres_caja_clinica_id")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("clinica_id")
        batch_op.create_unique_constraint("fecha", ["fecha"])

    for table_name, fk_name in (
        ("deudas_paciente", "fk_deudas_paciente_clinica"),
        ("caja_movimientos", "fk_caja_movimientos_clinica"),
        ("comprobantes", "fk_comprobantes_clinica"),
    ):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
            batch_op.drop_index(f"ix_{table_name}_is_active")
            batch_op.drop_index(f"ix_{table_name}_deleted_at")
            batch_op.drop_index(f"ix_{table_name}_clinica_id")
            batch_op.drop_column("deleted_at")
            batch_op.drop_column("is_active")
            batch_op.drop_column("clinica_id")
