from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlmodel import Session

from clinica_app.models.inventario import (
    Producto, MovimientoStock, Proveedor, TipoMov,
)
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError

DEC2 = Decimal("0.01")
DEC3 = Decimal("0.001")
_DEC4 = Decimal("0.0001")  # tolerancia mínima para stock negativo


def dec(v, quant=None) -> Decimal:
    n = Decimal(str(v)) if v not in (None, "") else Decimal("0")
    return n.quantize(quant, rounding=ROUND_HALF_UP) if quant else n


def _dump_producto(p: Producto) -> dict[str, Any]:
    return {
        "id":           p.id,
        "sku":          p.sku,
        "nombre":       p.nombre,
        "precio_costo": str(p.precio_costo) if p.precio_costo is not None else None,
        "precio_venta": str(p.precio_venta) if p.precio_venta is not None else None,
        "stock_actual": str(p.stock_actual) if p.stock_actual is not None else "0",
        "stock_minimo": str(p.stock_minimo) if p.stock_minimo is not None else None,
        "bajo_minimo":  p.bajo_minimo,
        "activo":       p.activo,
    }


def _productos_query(clinica_id: int):
    return select(Producto).where(
        Producto.clinica_id == clinica_id,
        Producto.is_active.is_(True),
    )


def listar_productos(
    session: Session,
    clinica_id: int,
    q: str = "",
    bajo_minimo: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = _productos_query(clinica_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Producto.nombre.ilike(like)) | (Producto.sku.ilike(like)))
    if bajo_minimo:
        stmt = stmt.where(Producto.stock_actual < Producto.stock_minimo)

    total: int = session.exec(
        select(func.count()).select_from(stmt.subquery())
    ).one()
    items = session.exec(
        stmt.order_by(Producto.nombre.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    return {
        "data":     [_dump_producto(p) for p in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, -(-total // per_page)),
    }


def obtener_producto(session: Session, clinica_id: int, producto_id: int) -> Producto:
    p = session.exec(
        _productos_query(clinica_id).where(Producto.id == producto_id)
    ).first()
    if p is None:
        raise NotFoundError("Producto no encontrado")
    return p


def crear_producto(session: Session, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("nombre requerido")
    sku = (payload.get("sku") or "").strip() or None

    if sku:
        existing = session.exec(
            _productos_query(clinica_id).where(func.upper(Producto.sku) == sku.upper())
        ).first()
        if existing:
            raise ConflictError("SKU ya registrado en esta clínica")

    p = Producto(
        clinica_id=clinica_id,
        nombre=nombre,
        sku=sku,
        precio_costo=dec(payload.get("precio_costo"), DEC2) or None,
        precio_venta=dec(payload.get("precio_venta"), DEC2) or None,
        stock_actual=dec(payload.get("stock_actual", 0), DEC3),
        stock_minimo=dec(payload.get("stock_minimo", 0), DEC3),
    )
    session.add(p)
    session.flush()
    return _dump_producto(p)


def actualizar_producto(session: Session, clinica_id: int, producto_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    p = obtener_producto(session, clinica_id, producto_id)
    fields_map = {
        "nombre": str, "sku": str,
        "precio_costo": lambda v: dec(v, DEC2),
        "precio_venta": lambda v: dec(v, DEC2),
        "stock_minimo": lambda v: dec(v, DEC3),
    }
    for field, cast_fn in fields_map.items():
        if field in payload and payload[field] is not None:
            setattr(p, field, cast_fn(payload[field]))
    session.flush()
    return _dump_producto(p)


def _aplicar_movimiento(
    session: Session,
    producto: Producto,
    tipo: str,
    cantidad: Any,
    motivo: str = "",
    referencia: str = "",
) -> MovimientoStock:
    cant = dec(cantidad, DEC3)

    if tipo == TipoMov.INGRESO.value:
        delta = cant
    elif tipo == TipoMov.EGRESO.value:
        delta = -cant
        if dec(producto.stock_actual, DEC3) + delta < -_DEC4:
            raise ValueError("Stock insuficiente para egreso")
    elif tipo == TipoMov.AJUSTE.value:
        delta = cant
    else:
        raise ValueError("Tipo de movimiento inválido")

    nuevo_saldo = dec(producto.stock_actual, DEC3) + delta
    producto.stock_actual = nuevo_saldo

    mov = MovimientoStock(
        clinica_id=producto.clinica_id,
        producto_id=producto.id,
        tipo=tipo,
        cantidad=delta,
        saldo=nuevo_saldo,
        motivo=motivo,
        referencia=referencia,
        costo_unitario=dec(producto.precio_costo, DEC2) if tipo != TipoMov.AJUSTE.value else None,
    )
    session.add(mov)
    return mov


def registrar_movimiento_stock(
    session: Session,
    clinica_id: int,
    producto_id: int,
    tipo: str,
    cantidad: Any,
    motivo: str = "",
    referencia: str = "",
) -> dict[str, Any]:
    p = obtener_producto(session, clinica_id, producto_id)
    try:
        mov = _aplicar_movimiento(session, p, tipo, cantidad, motivo=motivo, referencia=referencia)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    session.flush()
    return {
        "producto_id":  p.id,
        "nombre":       p.nombre,
        "tipo":         mov.tipo,
        "cantidad":     str(mov.cantidad),
        "nuevo_saldo":  str(p.stock_actual),
    }


def eliminar_producto(session: Session, clinica_id: int, producto_id: int) -> None:
    p = obtener_producto(session, clinica_id, producto_id)
    p.soft_delete()
    session.flush()
