"""initial_schema — baseline (DB pre-existente)

Revision ID: b4288f6adaf9
Revises:
Create Date: 2026-04-07 18:39:44.221785

NOTA: Esta migración es un punto de partida (baseline) para una base de datos
que ya existía antes de integrar Flask-Migrate. No realiza ningún cambio en
el esquema — simplemente registra el estado actual como "versión 0".

A partir de aquí, cualquier cambio a los modelos generará migraciones
incrementales correctas con `flask --app app:create_app db migrate`.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b4288f6adaf9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Baseline — la base de datos ya existe con el esquema correcto.
    # No se realizan cambios. Las migraciones futuras se aplican
    # de forma incremental a partir de esta revisión.
    pass


def downgrade():
    # No hay nada que revertir en el baseline.
    pass

    with op.batch_alter_table('comprobantes_backup', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('numero'))

    op.drop_table('comprobantes_backup')
    with op.batch_alter_table('pacientes_full_backup', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pacientes_documento'))

    op.drop_table('pacientes_full_backup')
    op.drop_table('turnos_backup')
    with op.batch_alter_table('pacientes_duplicados_backup', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pacientes_documento'))

    op.drop_table('pacientes_duplicados_backup')
    with op.batch_alter_table('caja_movimientos_backup', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_caja_movimientos_fecha'))

    op.drop_table('caja_movimientos_backup')
    with op.batch_alter_table('caja_movimientos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_caja_movimientos_turno_id'))
        batch_op.create_foreign_key(None, 'turnos', ['turno_id'], ['id'])

    with op.batch_alter_table('comprobantes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ux_comprobantes_idemkey'))
        batch_op.create_index(batch_op.f('ix_comprobantes_idempotency_key'), ['idempotency_key'], unique=True)

    with op.batch_alter_table('inv_compra_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_inv_compra_items_compra_id'), ['compra_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_inv_compra_items_producto_id'), ['producto_id'], unique=False)
        batch_op.drop_constraint(batch_op.f('fk_inv_compra_items_p'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_inv_compra_items_c'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'inv_productos', ['producto_id'], ['id'])
        batch_op.create_foreign_key(None, 'inv_compras', ['compra_id'], ['id'])

    with op.batch_alter_table('inv_compras', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ux_inv_compras_factura_numero'))
        batch_op.create_index(batch_op.f('ix_inv_compras_fecha'), ['fecha'], unique=False)
        batch_op.create_index(batch_op.f('ix_inv_compras_proveedor_id'), ['proveedor_id'], unique=False)
        batch_op.drop_constraint(batch_op.f('fk_inv_compras_prov'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'inv_proveedores', ['proveedor_id'], ['id'])
        batch_op.drop_column('numero_factura_unq')

    with op.batch_alter_table('inv_movimientos', schema=None) as batch_op:
        batch_op.alter_column('tipo',
               existing_type=mysql.ENUM('INGRESO', 'EGRESO', 'AJUSTE', collation='utf8mb4_unicode_ci'),
               type_=sa.String(length=12),
               existing_nullable=False)
        batch_op.alter_column('motivo',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=240),
               type_=sa.String(length=120),
               existing_nullable=True)

    with op.batch_alter_table('inv_producto_precios_hist', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=mysql.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False,
               autoincrement=True)
        batch_op.drop_index(batch_op.f('idx_pph_fecha'))
        batch_op.drop_index(batch_op.f('idx_pph_prod_tipo_fecha'))
        batch_op.create_index(batch_op.f('ix_inv_producto_precios_hist_producto_id'), ['producto_id'], unique=False)
        batch_op.drop_constraint(batch_op.f('fk_pph_producto'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'inv_productos', ['producto_id'], ['id'])

    with op.batch_alter_table('inv_productos', schema=None) as batch_op:
        batch_op.alter_column('sku',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=64),
               type_=sa.String(length=60),
               nullable=True)
        batch_op.alter_column('precio_costo',
               existing_type=mysql.DECIMAL(precision=10, scale=2),
               type_=sa.Numeric(precision=12, scale=2),
               existing_nullable=True)
        batch_op.alter_column('precio_venta',
               existing_type=mysql.DECIMAL(precision=12, scale=2),
               nullable=True,
               existing_server_default=sa.text("'0.00'"))
        batch_op.drop_index(batch_op.f('uq_inv_productos_sku'))
        batch_op.drop_index(batch_op.f('uq_inv_productos_sku_norm'))
        batch_op.create_index(batch_op.f('ix_inv_productos_sku'), ['sku'], unique=True)
        batch_op.drop_column('stock')
        batch_op.drop_column('ubicacion')
        batch_op.drop_column('sku_norm')
        batch_op.drop_column('categoria')
        batch_op.drop_column('unidad')
        batch_op.drop_column('precio')
        batch_op.drop_column('updated_at')

    with op.batch_alter_table('inv_proveedores', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('nombre'))
        batch_op.create_index(batch_op.f('ix_inv_proveedores_nombre'), ['nombre'], unique=True)

    with op.batch_alter_table('pacientes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('uq_pacientes_documento'))
        batch_op.drop_index(batch_op.f('uq_pacientes_documento_norm'))
        batch_op.drop_index(batch_op.f('ix_pacientes_documento'))
        batch_op.create_index(batch_op.f('ix_pacientes_documento'), ['documento'], unique=True)
        batch_op.create_unique_constraint(None, ['email'])
        batch_op.drop_column('documento_norm')

    with op.batch_alter_table('profesionales', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('dni'))
        batch_op.create_index(batch_op.f('ix_profesionales_dni'), ['dni'], unique=True)
        batch_op.create_index(batch_op.f('ix_profesionales_matricula'), ['matricula'], unique=True)

    with op.batch_alter_table('turno_servicios', schema=None) as batch_op:
        batch_op.alter_column('cantidad',
               existing_type=mysql.DECIMAL(precision=10, scale=2),
               nullable=True,
               existing_server_default=sa.text("'1.00'"))
        batch_op.alter_column('descuento',
               existing_type=mysql.DECIMAL(precision=10, scale=2),
               nullable=True,
               existing_server_default=sa.text("'0.00'"))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('turno_servicios', schema=None) as batch_op:
        batch_op.alter_column('descuento',
               existing_type=mysql.DECIMAL(precision=10, scale=2),
               nullable=False,
               existing_server_default=sa.text("'0.00'"))
        batch_op.alter_column('cantidad',
               existing_type=mysql.DECIMAL(precision=10, scale=2),
               nullable=False,
               existing_server_default=sa.text("'1.00'"))

    with op.batch_alter_table('profesionales', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_profesionales_matricula'))
        batch_op.drop_index(batch_op.f('ix_profesionales_dni'))
        batch_op.create_index(batch_op.f('dni'), ['dni'], unique=True)

    with op.batch_alter_table('pacientes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('documento_norm', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=32), sa.Computed("(replace(replace(trim(`documento`),_utf8mb4'.',_utf8mb4''),_utf8mb4' ',_utf8mb4''))", persisted=True), nullable=True))
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_index(batch_op.f('ix_pacientes_documento'))
        batch_op.create_index(batch_op.f('ix_pacientes_documento'), ['documento'], unique=False)
        batch_op.create_index(batch_op.f('uq_pacientes_documento_norm'), ['documento_norm'], unique=True)
        batch_op.create_index(batch_op.f('uq_pacientes_documento'), ['documento'], unique=True)

    with op.batch_alter_table('inv_proveedores', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_inv_proveedores_nombre'))
        batch_op.create_index(batch_op.f('nombre'), ['nombre'], unique=True)

    with op.batch_alter_table('inv_productos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated_at', mysql.DATETIME(), nullable=True))
        batch_op.add_column(sa.Column('precio', mysql.DECIMAL(precision=12, scale=2), server_default=sa.text("'0.00'"), nullable=False))
        batch_op.add_column(sa.Column('unidad', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=30), nullable=True))
        batch_op.add_column(sa.Column('categoria', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=120), nullable=True))
        batch_op.add_column(sa.Column('sku_norm', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=64), sa.Computed("(replace(replace(replace(lower(trim(`sku`)),_utf8mb4'-',_utf8mb4''),_utf8mb4' ',_utf8mb4''),_utf8mb4'_',_utf8mb4''))", persisted=True), nullable=True))
        batch_op.add_column(sa.Column('ubicacion', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=120), nullable=True))
        batch_op.add_column(sa.Column('stock', mysql.INTEGER(), server_default=sa.text("'0'"), autoincrement=False, nullable=False))
        batch_op.drop_index(batch_op.f('ix_inv_productos_sku'))
        batch_op.create_index(batch_op.f('uq_inv_productos_sku_norm'), ['sku_norm'], unique=True)
        batch_op.create_index(batch_op.f('uq_inv_productos_sku'), ['sku'], unique=True)
        batch_op.alter_column('precio_venta',
               existing_type=mysql.DECIMAL(precision=12, scale=2),
               nullable=False,
               existing_server_default=sa.text("'0.00'"))
        batch_op.alter_column('precio_costo',
               existing_type=sa.Numeric(precision=12, scale=2),
               type_=mysql.DECIMAL(precision=10, scale=2),
               existing_nullable=True)
        batch_op.alter_column('sku',
               existing_type=sa.String(length=60),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=64),
               nullable=False)

    with op.batch_alter_table('inv_producto_precios_hist', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_pph_producto'), 'inv_productos', ['producto_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_index(batch_op.f('ix_inv_producto_precios_hist_producto_id'))
        batch_op.create_index(batch_op.f('idx_pph_prod_tipo_fecha'), ['producto_id', 'tipo', 'vigente_desde'], unique=False)
        batch_op.create_index(batch_op.f('idx_pph_fecha'), ['vigente_desde'], unique=False)
        batch_op.alter_column('id',
               existing_type=sa.BigInteger(),
               type_=mysql.INTEGER(),
               existing_nullable=False,
               autoincrement=True)

    with op.batch_alter_table('inv_movimientos', schema=None) as batch_op:
        batch_op.alter_column('motivo',
               existing_type=sa.String(length=120),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=240),
               existing_nullable=True)
        batch_op.alter_column('tipo',
               existing_type=sa.String(length=12),
               type_=mysql.ENUM('INGRESO', 'EGRESO', 'AJUSTE', collation='utf8mb4_unicode_ci'),
               existing_nullable=False)

    with op.batch_alter_table('inv_compras', schema=None) as batch_op:
        batch_op.add_column(sa.Column('numero_factura_unq', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=64), sa.Computed("((case when (lower(coalesce(`tipo_doc`,_utf8mb4'')) = _utf8mb4'factura') then lower(coalesce(`numero`,_utf8mb4'')) else NULL end))", persisted=True), nullable=True))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_inv_compras_prov'), 'inv_proveedores', ['proveedor_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')
        batch_op.drop_index(batch_op.f('ix_inv_compras_proveedor_id'))
        batch_op.drop_index(batch_op.f('ix_inv_compras_fecha'))
        batch_op.create_index(batch_op.f('ux_inv_compras_factura_numero'), ['numero_factura_unq'], unique=True)

    with op.batch_alter_table('inv_compra_items', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_inv_compra_items_c'), 'inv_compras', ['compra_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_inv_compra_items_p'), 'inv_productos', ['producto_id'], ['id'], onupdate='CASCADE')
        batch_op.drop_index(batch_op.f('ix_inv_compra_items_producto_id'))
        batch_op.drop_index(batch_op.f('ix_inv_compra_items_compra_id'))

    with op.batch_alter_table('comprobantes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_comprobantes_idempotency_key'))
        batch_op.create_index(batch_op.f('ux_comprobantes_idemkey'), ['idempotency_key'], unique=True)

    with op.batch_alter_table('caja_movimientos', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_index(batch_op.f('ix_caja_movimientos_turno_id'), ['turno_id'], unique=False)

    op.create_table('caja_movimientos_backup',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('fecha', mysql.DATETIME(), nullable=True),
    sa.Column('tipo', mysql.ENUM('INGRESO', 'EGRESO'), nullable=False),
    sa.Column('monto', mysql.DECIMAL(precision=10, scale=2), nullable=False),
    sa.Column('metodo_pago', mysql.ENUM('EFECTIVO', 'TARJETA', 'TRANSFERENCIA', 'OTRO'), nullable=True),
    sa.Column('paciente_id', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('profesional_id', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('servicio_id', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('comprobante_id', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('observacion', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=240), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('caja_movimientos_backup', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_caja_movimientos_fecha'), ['fecha'], unique=False)

    op.create_table('pacientes_duplicados_backup',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('nombre', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=180), nullable=False),
    sa.Column('documento', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=40), nullable=True),
    sa.Column('direccion', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=200), nullable=True),
    sa.Column('email', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=120), nullable=True),
    sa.Column('telefono', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=60), nullable=True),
    sa.Column('fecha_nacimiento', sa.DATE(), nullable=True),
    sa.Column('contacto_emergencia', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=160), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.Column('updated_at', mysql.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('pacientes_duplicados_backup', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pacientes_documento'), ['documento'], unique=False)

    op.create_table('turnos_backup',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('paciente_id', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('profesional_id', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('servicio_id', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('fecha_hora', mysql.DATETIME(), nullable=False),
    sa.Column('estado', mysql.ENUM('PENDIENTE', 'CONFIRMADO', 'CANCELADO', 'ATENDIDO'), nullable=True),
    sa.Column('motivo_cancelacion', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=240), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.Column('updated_at', mysql.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('pacientes_full_backup',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('nombre', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=180), nullable=False),
    sa.Column('documento', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=40), nullable=True),
    sa.Column('direccion', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=200), nullable=True),
    sa.Column('email', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=120), nullable=True),
    sa.Column('telefono', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=60), nullable=True),
    sa.Column('fecha_nacimiento', sa.DATE(), nullable=True),
    sa.Column('contacto_emergencia', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=160), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.Column('updated_at', mysql.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('pacientes_full_backup', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pacientes_documento'), ['documento'], unique=False)

    op.create_table('comprobantes_backup',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('tipo', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=20), nullable=True),
    sa.Column('numero', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=40), nullable=True),
    sa.Column('fecha', mysql.DATETIME(), nullable=True),
    sa.Column('paciente_id', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('total', mysql.DECIMAL(precision=10, scale=2), nullable=True),
    sa.Column('forma_pago', mysql.ENUM('EFECTIVO', 'TARJETA', 'TRANSFERENCIA', 'OTRO'), nullable=True),
    sa.Column('observacion', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=240), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('comprobantes_backup', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('numero'), ['numero'], unique=True)

    # ### end Alembic commands ###
