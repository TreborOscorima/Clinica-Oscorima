from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow import EXCLUDE
from extensions import db
from models.inventario import (
    Producto, MovimientoStock,
    Proveedor, Compra, CompraItem
)

class ProductoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Producto
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
        ordered = True
    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    sku = auto_field()
    nombre = auto_field(required=True)
    precio_costo = auto_field()
    precio_venta = auto_field()     # <-- NUEVO
    stock_actual = auto_field()
    stock_minimo = auto_field()
    activo = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)

class MovimientoStockSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = MovimientoStock
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
        ordered = True
    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    fecha = auto_field(dump_only=True)
    producto_id = auto_field(required=True)
    tipo = auto_field(required=True)
    cantidad = auto_field()
    saldo = auto_field()
    motivo = auto_field()
    referencia = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)

class ProveedorSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Proveedor
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
        ordered = True
    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    nombre = auto_field(required=True)
    documento = auto_field()
    email = auto_field()
    telefono = auto_field()
    direccion = auto_field()
    activo = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)

class CompraItemSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = CompraItem
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
        ordered = True
    id = auto_field(dump_only=True)
    compra_id = auto_field(dump_only=True)
    producto_id = auto_field(required=True)
    cantidad = auto_field(required=True)
    costo_unitario = auto_field(required=True)
    subtotal = auto_field(dump_only=True)

class CompraSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Compra
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
        ordered = True
    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    fecha = auto_field(dump_only=True)
    proveedor_id = auto_field()
    tipo_doc = auto_field()
    numero = auto_field()
    nro_registro = auto_field()
    total = auto_field(dump_only=True)
    observacion = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)
    
