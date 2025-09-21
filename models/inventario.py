from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from extensions import db

# ========= Helpers =========
DEC4 = Decimal("0.0001")

def to_dec(v, q="0.000"):
    if v is None or v == "":
        v = "0"
    d = Decimal(str(v))
    return d.quantize(Decimal(q), rounding=ROUND_HALF_UP)

def to_dec2(v):
    d = Decimal(str(v or "0"))
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# ========= Enums =========
class TipoMov(str, Enum):
    INGRESO = "ingreso"
    EGRESO  = "egreso"
    AJUSTE  = "ajuste"

# ========= Producto / Movimientos =========
class Producto(db.Model):
    __tablename__ = "inv_productos"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(60), unique=True, index=True)
    nombre = db.Column(db.String(180), nullable=False, index=True)
    precio_costo = db.Column(db.Numeric(12,2), default=0)    # costo promedio
    precio_venta = db.Column(db.Numeric(12,2), default=0)    # <-- NUEVO
    stock_actual = db.Column(db.Numeric(12,3), default=0)
    stock_minimo = db.Column(db.Numeric(12,3), default=0)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MovimientoStock(db.Model):
    __tablename__ = "inv_movimientos"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("inv_productos.id"), nullable=False, index=True)
    tipo = db.Column(db.String(12), nullable=False)                  # ingreso/egreso/ajuste
    cantidad = db.Column(db.Numeric(12,3), nullable=False)           # (+/-)
    costo_unitario = db.Column(db.Numeric(12,2))
    saldo = db.Column(db.Numeric(12,3), nullable=False)              # stock luego del mov
    motivo = db.Column(db.String(120))
    referencia = db.Column(db.String(120))

# ========= Proveedores / Compras =========
class Proveedor(db.Model):
    __tablename__ = "inv_proveedores"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(180), nullable=False, unique=True, index=True)
    documento = db.Column(db.String(30))
    email = db.Column(db.String(120))
    telefono = db.Column(db.String(60))
    direccion = db.Column(db.String(240))
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Compra(db.Model):
    __tablename__ = "inv_compras"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey("inv_proveedores.id"), nullable=True, index=True)
    tipo_doc = db.Column(db.String(20))                              # boleta/factura/otro
    numero = db.Column(db.String(60))                                # serie-numero
    nro_registro = db.Column(db.String(60))                          # nro de registro (si aplica)
    total = db.Column(db.Numeric(12,2), default=0)
    observacion = db.Column(db.String(240))

class CompraItem(db.Model):
    __tablename__ = "inv_compra_items"
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("inv_compras.id"), nullable=False, index=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("inv_productos.id"), nullable=False, index=True)
    cantidad = db.Column(db.Numeric(12,3), nullable=False)
    costo_unitario = db.Column(db.Numeric(12,2), nullable=False)
    subtotal = db.Column(db.Numeric(12,2), nullable=False)
    
# ========= Historial de precios/costos =========
class ProductoPrecioHist(db.Model):
    __tablename__ = "inv_producto_precios_hist"
    id = db.Column(db.BigInteger, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("inv_productos.id"), nullable=False, index=True)
    tipo = db.Column(db.Enum("costo", "venta"), nullable=False)
    valor = db.Column(db.Numeric(12,2), nullable=False)
    vigente_desde = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    vigente_hasta = db.Column(db.DateTime, nullable=True)
    motivo = db.Column(db.String(255))
    usuario_id = db.Column(db.Integer)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# ========= Operaciones =========
def aplicar_movimiento(producto: Producto, tipo: str, cantidad, motivo="", ref=""):
    """
    Aplica un movimiento (sin commit).
    - EGRESO valida stock suficiente.
    - AJUSTE aplica la cantidad como viene (puede ser +/-).
    """
    cant = to_dec(cantidad)
    if tipo == TipoMov.INGRESO.value:
        delta = cant
    elif tipo == TipoMov.EGRESO.value:
        delta = -cant
        if to_dec(producto.stock_actual) + delta < -DEC4:
            raise ValueError("Stock insuficiente para egreso")
    elif tipo == TipoMov.AJUSTE.value:
        delta = cant
    else:
        raise ValueError("Tipo de movimiento inválido")

    nuevo_saldo = to_dec(producto.stock_actual) + delta
    producto.stock_actual = nuevo_saldo

    mov = MovimientoStock(
        producto_id=producto.id, tipo=tipo, cantidad=delta,
        saldo=nuevo_saldo, motivo=motivo, referencia=ref,
        costo_unitario=to_dec2(producto.precio_costo) if tipo != TipoMov.AJUSTE.value else None
    )
    db.session.add(mov)
    return mov
