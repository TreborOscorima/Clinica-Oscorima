"""multi tenant inventario

Revision ID: 20260506_04
Revises: 20260506_03
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260506_04"
down_revision = "20260506_03"
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
    _add_tenant_soft_delete("inv_productos")
    _add_tenant_soft_delete("inv_movimientos")
    _add_tenant_soft_delete("inv_proveedores")
    _add_tenant_soft_delete("inv_compras")

    with op.batch_alter_table("inv_producto_precios_hist", schema=None) as batch_op:
        batch_op.add_column(sa.Column("clinica_id", sa.Integer(), nullable=True))

    op.execute("UPDATE inv_productos SET clinica_id = 1 WHERE clinica_id IS NULL")
    op.execute("UPDATE inv_proveedores SET clinica_id = 1 WHERE clinica_id IS NULL")
    op.execute("UPDATE inv_compras SET clinica_id = 1 WHERE clinica_id IS NULL")
    op.execute(
        """
        UPDATE inv_movimientos m
        JOIN inv_productos p ON p.id = m.producto_id
        SET m.clinica_id = p.clinica_id
        WHERE m.clinica_id IS NULL
        """
    )
    op.execute("UPDATE inv_movimientos SET clinica_id = 1 WHERE clinica_id IS NULL")
    op.execute(
        """
        UPDATE inv_producto_precios_hist h
        JOIN inv_productos p ON p.id = h.producto_id
        SET h.clinica_id = p.clinica_id
        WHERE h.clinica_id IS NULL
        """
    )
    op.execute("UPDATE inv_producto_precios_hist SET clinica_id = 1 WHERE clinica_id IS NULL")

    for idx in ("ix_inv_productos_sku", "uq_inv_productos_sku", "uq_inv_productos_sku_norm"):
        _drop_index_if_exists("inv_productos", idx)
    for idx in ("ix_inv_proveedores_nombre", "nombre"):
        _drop_index_if_exists("inv_proveedores", idx)
    for idx in ("ux_inv_compras_factura_numero",):
        _drop_index_if_exists("inv_compras", idx)

    op.execute("UPDATE inv_compras SET numero = NULL WHERE numero = ''")

    _finalize_tenant_soft_delete("inv_productos", "fk_inv_productos_clinica")
    _finalize_tenant_soft_delete("inv_movimientos", "fk_inv_movimientos_clinica")
    _finalize_tenant_soft_delete("inv_proveedores", "fk_inv_proveedores_clinica")
    _finalize_tenant_soft_delete("inv_compras", "fk_inv_compras_clinica")

    with op.batch_alter_table("inv_producto_precios_hist", schema=None) as batch_op:
        batch_op.alter_column("clinica_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index("ix_inv_producto_precios_hist_clinica_id", ["clinica_id"])
        batch_op.create_foreign_key(
            "fk_inv_producto_precios_hist_clinica",
            "clinicas",
            ["clinica_id"],
            ["id"],
        )

    with op.batch_alter_table("inv_productos", schema=None) as batch_op:
        batch_op.create_index("ix_inv_productos_sku", ["sku"])
        batch_op.create_unique_constraint("uq_inv_productos_clinica_sku", ["clinica_id", "sku"])

    with op.batch_alter_table("inv_proveedores", schema=None) as batch_op:
        batch_op.create_index("ix_inv_proveedores_nombre", ["nombre"])
        batch_op.create_unique_constraint("uq_inv_proveedores_clinica_nombre", ["clinica_id", "nombre"])

    with op.batch_alter_table("inv_compras", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_inv_compras_clinica_doc_numero", ["clinica_id", "tipo_doc", "numero"])


def downgrade():
    with op.batch_alter_table("inv_compras", schema=None) as batch_op:
        batch_op.drop_constraint("uq_inv_compras_clinica_doc_numero", type_="unique")

    with op.batch_alter_table("inv_proveedores", schema=None) as batch_op:
        batch_op.drop_constraint("uq_inv_proveedores_clinica_nombre", type_="unique")
        batch_op.drop_index("ix_inv_proveedores_nombre")

    with op.batch_alter_table("inv_productos", schema=None) as batch_op:
        batch_op.drop_constraint("uq_inv_productos_clinica_sku", type_="unique")
        batch_op.drop_index("ix_inv_productos_sku")

    with op.batch_alter_table("inv_producto_precios_hist", schema=None) as batch_op:
        batch_op.drop_constraint("fk_inv_producto_precios_hist_clinica", type_="foreignkey")
        batch_op.drop_index("ix_inv_producto_precios_hist_clinica_id")
        batch_op.drop_column("clinica_id")

    for table_name, fk_name in (
        ("inv_compras", "fk_inv_compras_clinica"),
        ("inv_proveedores", "fk_inv_proveedores_clinica"),
        ("inv_movimientos", "fk_inv_movimientos_clinica"),
        ("inv_productos", "fk_inv_productos_clinica"),
    ):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
            batch_op.drop_index(f"ix_{table_name}_is_active")
            batch_op.drop_index(f"ix_{table_name}_deleted_at")
            batch_op.drop_index(f"ix_{table_name}_clinica_id")
            batch_op.drop_column("deleted_at")
            batch_op.drop_column("is_active")
            batch_op.drop_column("clinica_id")

    with op.batch_alter_table("inv_productos", schema=None) as batch_op:
        batch_op.create_index("ix_inv_productos_sku", ["sku"], unique=True)
    with op.batch_alter_table("inv_proveedores", schema=None) as batch_op:
        batch_op.create_index("ix_inv_proveedores_nombre", ["nombre"], unique=True)
