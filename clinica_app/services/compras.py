from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func
from sqlmodel import select
from sqlmodel import Session

from clinica_app.models.inventario import (
    Compra, CompraItem, Producto, Proveedor, TipoMov,
)
from clinica_app.services.exceptions import NotFoundError, ServiceError
from clinica_app.services.inventario import _aplicar_movimiento

D2 = Decimal("0.01")
D3 = Decimal("0.001")


def _dec2(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _dec3(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    return Decimal(str(v)).quantize(D3, rounding=ROUND_HALF_UP)


def _dump_compra(c: Compra, prov_nombre: str = "") -> dict[str, Any]:
    return {
        "id":           c.id or 0,
        "fecha":        c.fecha.strftime("%d/%m/%Y") if c.fecha else "",
        "proveedor_id": c.proveedor_id or 0,
        "proveedor":    prov_nombre,
        "tipo_doc":     c.tipo_doc or "",
        "numero":       c.numero or "",
        "nro_registro": c.nro_registro or "",
        "total":        str(_dec2(c.total)),
        "observacion":  c.observacion or "",
    }


def _dump_item(i: CompraItem, prod_nombre: str = "") -> dict[str, Any]:
    return {
        "id":             i.id or 0,
        "compra_id":      i.compra_id,
        "producto_id":    i.producto_id,
        "producto_nombre": prod_nombre,
        "cantidad":       str(_dec3(i.cantidad)),
        "costo_unitario": str(_dec2(i.costo_unitario)),
        "subtotal":       str(_dec2(i.subtotal)),
    }


# ── Proveedores ───────────────────────────────────────────────────────────────

def listar_proveedores(session: Session, clinica_id: int) -> list[dict[str, Any]]:
    rows = session.exec(
        select(Proveedor)
        .where(Proveedor.clinica_id == clinica_id, Proveedor.is_active.is_(True))
        .order_by(Proveedor.nombre)
    ).all()
    return [{"id": p.id, "nombre": p.nombre} for p in rows]


def crear_proveedor(session: Session, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre del proveedor es requerido")
    p = Proveedor(
        clinica_id=clinica_id,
        nombre=nombre,
        documento=(payload.get("documento") or "").strip() or None,
        email=(payload.get("email") or "").strip() or None,
        telefono=(payload.get("telefono") or "").strip() or None,
        direccion=(payload.get("direccion") or "").strip() or None,
    )
    session.add(p)
    session.flush()
    return {"id": p.id, "nombre": p.nombre}


# ── Compras ───────────────────────────────────────────────────────────────────

def listar(
    session: Session,
    clinica_id: int,
    q: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    base = (
        select(Compra, Proveedor)
        .outerjoin(Proveedor, Proveedor.id == Compra.proveedor_id)
        .where(Compra.clinica_id == clinica_id, Compra.is_active.is_(True))
    )

    if q:
        like = f"%{q}%"
        base = base.where(
            (Compra.numero.ilike(like)) | (Proveedor.nombre.ilike(like))
        )

    base = base.order_by(Compra.fecha.desc())

    total_sub = base.subquery()
    total = session.execute(select(func.count()).select_from(total_sub)).scalar_one()

    rows = session.execute(base.offset((page - 1) * per_page).limit(per_page)).all()
    data = [_dump_compra(c, p.nombre if p else "") for c, p in rows]

    kpi = session.execute(
        select(func.count(Compra.id), func.coalesce(func.sum(Compra.total), 0))
        .where(Compra.clinica_id == clinica_id, Compra.is_active.is_(True))
    ).one()

    return {
        "data":          data,
        "total":         total,
        "pages":         max(1, -(-total // per_page)),
        "total_compras": kpi[0] or 0,
        "total_gastado": str(_dec2(kpi[1])),
    }


def obtener_items(session: Session, compra_id: int) -> list[dict[str, Any]]:
    rows = session.execute(
        select(CompraItem, Producto)
        .join(Producto, Producto.id == CompraItem.producto_id)
        .where(CompraItem.compra_id == compra_id)
        .order_by(CompraItem.id)
    ).all()
    return [_dump_item(i, p.nombre) for i, p in rows]


def crear(
    session: Session,
    clinica_id: int,
    payload: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    if not items:
        raise ServiceError("Debe agregar al menos un producto")

    proveedor_id = payload.get("proveedor_id") or None
    if proveedor_id:
        prov = session.get(Proveedor, int(proveedor_id))
        if not prov or prov.clinica_id != clinica_id:
            raise NotFoundError("Proveedor no encontrado")
    else:
        prov = None

    compra = Compra(
        clinica_id=clinica_id,
        proveedor_id=int(proveedor_id) if proveedor_id else None,
        tipo_doc=(payload.get("tipo_doc") or "").strip() or None,
        numero=(payload.get("numero") or "").strip() or None,
        nro_registro=(payload.get("nro_registro") or "").strip() or None,
        observacion=(payload.get("observacion") or "").strip() or None,
    )
    session.add(compra)
    session.flush()

    total_compra = Decimal("0")
    for it in items:
        prod = session.get(Producto, int(it["producto_id"]))
        if not prod or prod.clinica_id != clinica_id or not prod.is_active:
            raise NotFoundError(f"Producto {it.get('producto_id')} no encontrado")

        cantidad = _dec3(it.get("cantidad", 0))
        costo    = _dec2(it.get("costo_unitario", 0))
        if cantidad <= Decimal("0"):
            raise ServiceError(f"Cantidad inválida para '{prod.nombre}'")
        if costo < Decimal("0"):
            raise ServiceError(f"Costo inválido para '{prod.nombre}'")

        subtotal = (cantidad * costo).quantize(D2)
        total_compra += subtotal

        item = CompraItem(
            compra_id=compra.id,
            producto_id=prod.id,
            cantidad=cantidad,
            costo_unitario=costo,
            subtotal=subtotal,
        )
        session.add(item)

        prod.precio_costo = costo
        _aplicar_movimiento(
            session, prod,
            TipoMov.INGRESO.value,
            cantidad,
            motivo="Compra",
            referencia=f"compra#{compra.id}",
        )

    compra.total = total_compra
    session.flush()

    return _dump_compra(compra, prov.nombre if prov else "")


def anular(session: Session, clinica_id: int, compra_id: int) -> None:
    compra = session.get(Compra, compra_id)
    if not compra or compra.clinica_id != clinica_id or not compra.is_active:
        raise NotFoundError("Compra no encontrada")

    items = session.execute(
        select(CompraItem, Producto)
        .join(Producto, Producto.id == CompraItem.producto_id)
        .where(CompraItem.compra_id == compra_id)
    ).all()

    for ci, prod in items:
        try:
            _aplicar_movimiento(
                session, prod,
                TipoMov.EGRESO.value,
                ci.cantidad,
                motivo="Anulación compra",
                referencia=f"compra#{compra_id}",
            )
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc

    compra.soft_delete()
    session.flush()
