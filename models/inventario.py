from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


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
class Producto(SQLModel, table=True):
    __tablename__ = "inv_productos"
    __table_args__ = (
        UniqueConstraint("clinica_id", "sku", name="uq_inv_productos_clinica_sku"),
    )
    metadata = db.metadata

    id: int | None = Field(default=None, primary_key=True)
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    sku: str | None = Field(default=None, max_length=60, index=True, nullable=True)
    nombre: str = Field(max_length=180, nullable=False, index=True)
    precio_costo: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 2), nullable=True))
    precio_venta: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 2), nullable=True))
    stock_actual: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 3), nullable=True))
    stock_minimo: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 3), nullable=True))
    activo: bool | None = Field(default=True, nullable=True)
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True, index=True))
    created_at: datetime | None = Field(default_factory=_utcnow, sa_column=Column(DateTime, default=_utcnow, nullable=True, index=True))

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()
        self.activo = False


class MovimientoStock(SQLModel, table=True):
    __tablename__ = "inv_movimientos"
    metadata = db.metadata

    id: int | None = Field(default=None, primary_key=True)
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    fecha: datetime | None = Field(default_factory=_utcnow, sa_column=Column(DateTime, default=_utcnow, nullable=True, index=True))
    producto_id: int = Field(foreign_key="inv_productos.id", nullable=False, index=True)
    tipo: str = Field(max_length=12, nullable=False)
    cantidad: Decimal = Field(sa_column=Column(Numeric(12, 3), nullable=False))
    costo_unitario: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 2), nullable=True))
    saldo: Decimal = Field(sa_column=Column(Numeric(12, 3), nullable=False))
    motivo: str | None = Field(default=None, max_length=120, nullable=True)
    referencia: str | None = Field(default=None, max_length=120, nullable=True)
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True, index=True))

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()


# ========= Proveedores / Compras =========
class Proveedor(SQLModel, table=True):
    __tablename__ = "inv_proveedores"
    __table_args__ = (
        UniqueConstraint("clinica_id", "nombre", name="uq_inv_proveedores_clinica_nombre"),
    )
    metadata = db.metadata

    id: int | None = Field(default=None, primary_key=True)
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    nombre: str = Field(max_length=180, nullable=False, index=True)
    documento: str | None = Field(default=None, max_length=30, nullable=True)
    email: str | None = Field(default=None, max_length=120, nullable=True)
    telefono: str | None = Field(default=None, max_length=60, nullable=True)
    direccion: str | None = Field(default=None, max_length=240, nullable=True)
    activo: bool | None = Field(default=True, nullable=True)
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True, index=True))
    created_at: datetime | None = Field(default_factory=_utcnow, sa_column=Column(DateTime, default=_utcnow, nullable=True, index=True))

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()
        self.activo = False


class Compra(SQLModel, table=True):
    __tablename__ = "inv_compras"
    __table_args__ = (
        UniqueConstraint("clinica_id", "tipo_doc", "numero", name="uq_inv_compras_clinica_doc_numero"),
    )
    metadata = db.metadata

    id: int | None = Field(default=None, primary_key=True)
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    fecha: datetime | None = Field(default_factory=_utcnow, sa_column=Column(DateTime, default=_utcnow, nullable=True, index=True))
    proveedor_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("inv_proveedores.id"), nullable=True, index=True))
    tipo_doc: str | None = Field(default=None, max_length=20, nullable=True)
    numero: str | None = Field(default=None, max_length=60, nullable=True)
    nro_registro: str | None = Field(default=None, max_length=60, nullable=True)
    total: Decimal | None = Field(default=None, sa_column=Column(Numeric(12, 2), nullable=True))
    observacion: str | None = Field(default=None, max_length=240, nullable=True)
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True, index=True))

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()


class CompraItem(SQLModel, table=True):
    __tablename__ = "inv_compra_items"
    metadata = db.metadata

    id: int | None = Field(default=None, primary_key=True)
    compra_id: int = Field(sa_column=Column(Integer, ForeignKey("inv_compras.id"), nullable=False, index=True))
    producto_id: int = Field(foreign_key="inv_productos.id", nullable=False, index=True)
    cantidad: Decimal = Field(sa_column=Column(Numeric(12, 3), nullable=False))
    costo_unitario: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    subtotal: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))


# ========= Historial de precios/costos =========
class ProductoPrecioHist(SQLModel, table=True):
    __tablename__ = "inv_producto_precios_hist"
    metadata = db.metadata

    id: int | None = Field(default=None, sa_column=Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True))
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    producto_id: int = Field(foreign_key="inv_productos.id", nullable=False, index=True)
    tipo: str = Field(sa_column=Column(SAEnum("costo", "venta"), nullable=False))
    valor: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    vigente_desde: datetime | None = Field(default_factory=_utcnow, sa_column=Column(DateTime, default=_utcnow, nullable=False))
    vigente_hasta: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    motivo: str | None = Field(default=None, max_length=255, nullable=True)
    usuario_id: int | None = Field(default=None, nullable=True)
    creado_en: datetime | None = Field(default_factory=_utcnow, sa_column=Column(DateTime, default=_utcnow, nullable=False))


# ========= Operaciones =========
def aplicar_movimiento(producto: Producto, tipo: str, cantidad, motivo="", ref=""):
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
        clinica_id=producto.clinica_id, producto_id=producto.id, tipo=tipo, cantidad=delta,
        saldo=nuevo_saldo, motivo=motivo, referencia=ref,
        costo_unitario=to_dec2(producto.precio_costo) if tipo != TipoMov.AJUSTE.value else None,
    )
    db.session.add(mov)
    return mov
