"""Lotes / partidas de inventario con vencimiento y consumo FEFO.

El `Producto.stock_actual` es la fuente de verdad agregada del stock. Los lotes
son un desglose por partida que habilita el control de vencimientos y el consumo
FEFO (first-expired-first-out). El consumo de lotes es best-effort: si un producto
no tiene lotes registrados, las funciones de consumo son no-op y el producto se
comporta igual que antes.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.inventario import LoteProducto, Producto

DEC2 = Decimal("0.01")
DEC3 = Decimal("0.001")


def _dec(v, quant=DEC3) -> Decimal:
    n = Decimal(str(v)) if v not in (None, "") else Decimal("0")
    return n.quantize(quant, rounding=ROUND_HALF_UP)


def parse_fecha(v: Any) -> date | None:
    """Acepta 'YYYY-MM-DD', date o datetime; devuelve date o None."""
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def _lotes_query(clinica_id: int, sede_id: int = 0):
    stmt = select(LoteProducto).where(
        LoteProducto.clinica_id == clinica_id,
        LoteProducto.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(LoteProducto.sede_id == sede_id)
    return stmt


async def registrar_ingreso(
    session: AsyncSession,
    clinica_id: int,
    producto_id: int,
    *,
    lote: str,
    vencimiento: Any = None,
    cantidad: Any,
    costo_unitario: Any = None,
    sede_id: int = 0,
) -> LoteProducto | None:
    """Suma `cantidad` al lote (upsert por producto+lote). No-op si lote vacío."""
    codigo = (lote or "").strip()
    cant = _dec(cantidad, DEC3)
    if not codigo or cant <= 0:
        return None

    venc = parse_fecha(vencimiento)
    costo = _dec(costo_unitario, DEC2) if costo_unitario not in (None, "") else None

    existente = (
        await session.execute(
            _lotes_query(clinica_id, sede_id).where(
                LoteProducto.producto_id == producto_id,
                func.upper(LoteProducto.lote) == codigo.upper(),
            )
        )
    ).scalars().first()

    if existente is not None:
        existente.cantidad_inicial = _dec(existente.cantidad_inicial, DEC3) + cant
        existente.cantidad_actual = _dec(existente.cantidad_actual, DEC3) + cant
        if venc is not None:
            existente.vencimiento = venc
        if costo is not None:
            existente.costo_unitario = costo
        await session.flush()
        return existente

    nuevo = LoteProducto(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        producto_id=producto_id,
        lote=codigo,
        vencimiento=venc,
        cantidad_inicial=cant,
        cantidad_actual=cant,
        costo_unitario=costo,
    )
    session.add(nuevo)
    await session.flush()
    return nuevo


async def consumir_fefo(
    session: AsyncSession,
    clinica_id: int,
    producto_id: int,
    cantidad: Any,
    *,
    sede_id: int = 0,
) -> list[dict[str, Any]]:
    """Descuenta `cantidad` de los lotes del producto, el que vence primero.

    Best-effort: si el producto no tiene lotes, devuelve [] sin tocar nada.
    Los lotes sin vencimiento se consumen al final. Nunca levanta excepción por
    faltante — descuenta lo que haya (el stock agregado es la fuente de verdad).
    """
    restante = _dec(cantidad, DEC3)
    if restante <= 0:
        return []

    lotes = (
        await session.execute(
            _lotes_query(clinica_id, sede_id)
            .where(
                LoteProducto.producto_id == producto_id,
                LoteProducto.cantidad_actual > 0,
            )
            .order_by(
                LoteProducto.vencimiento.is_(None),  # con vencimiento primero
                LoteProducto.vencimiento.asc(),
                LoteProducto.created_at.asc(),
            )
        )
    ).scalars().all()

    consumido: list[dict[str, Any]] = []
    for lote in lotes:
        if restante <= 0:
            break
        disponible = _dec(lote.cantidad_actual, DEC3)
        toma = min(disponible, restante)
        lote.cantidad_actual = disponible - toma
        restante -= toma
        consumido.append({"lote": lote.lote, "cantidad": str(toma)})
    await session.flush()
    return consumido


def _dump_lote(l: LoteProducto, hoy: date, nombre: str = "") -> dict[str, Any]:
    dias = (l.vencimiento - hoy).days if l.vencimiento else None
    if l.vencimiento is None:
        estado = "sin_venc"
    elif dias < 0:
        estado = "vencido"
    elif dias <= 30:
        estado = "por_vencer"
    else:
        estado = "ok"
    return {
        "id":              l.id,
        "producto_id":     l.producto_id,
        "producto_nombre": nombre,
        "lote":            l.lote,
        "vencimiento":     l.vencimiento.isoformat() if l.vencimiento else "",
        "dias_restantes":  dias,
        "estado":          estado,
        "cantidad":        str(_dec(l.cantidad_actual, DEC3)),
    }


async def listar_por_producto(
    session: AsyncSession,
    clinica_id: int,
    producto_id: int,
    *,
    sede_id: int = 0,
    hoy: date | None = None,
    incluir_agotados: bool = False,
) -> list[dict[str, Any]]:
    hoy = hoy or date.today()
    stmt = _lotes_query(clinica_id, sede_id).where(LoteProducto.producto_id == producto_id)
    if not incluir_agotados:
        stmt = stmt.where(LoteProducto.cantidad_actual > 0)
    stmt = stmt.order_by(
        LoteProducto.vencimiento.is_(None),
        LoteProducto.vencimiento.asc(),
        LoteProducto.created_at.asc(),
    )
    lotes = (await session.execute(stmt)).scalars().all()
    return [_dump_lote(l, hoy) for l in lotes]


async def alertas_vencimiento(
    session: AsyncSession,
    clinica_id: int,
    *,
    sede_id: int = 0,
    dias: int = 30,
    hoy: date | None = None,
) -> dict[str, Any]:
    """Lotes con stock vencidos o por vencer dentro de `dias`, con su producto."""
    hoy = hoy or date.today()
    stmt = (
        select(LoteProducto, Producto.nombre)
        .join(Producto, Producto.id == LoteProducto.producto_id)
        .where(
            LoteProducto.clinica_id == clinica_id,
            LoteProducto.is_active.is_(True),
            LoteProducto.cantidad_actual > 0,
            LoteProducto.vencimiento.is_not(None),
        )
    )
    if sede_id:
        stmt = stmt.where(LoteProducto.sede_id == sede_id)
    stmt = stmt.order_by(LoteProducto.vencimiento.asc())

    filas = (await session.execute(stmt)).all()

    vencidos: list[dict[str, Any]] = []
    por_vencer: list[dict[str, Any]] = []
    for lote, nombre in filas:
        d = _dump_lote(lote, hoy, nombre)
        if d["estado"] == "vencido":
            vencidos.append(d)
        elif lote.vencimiento is not None and 0 <= (lote.vencimiento - hoy).days <= dias:
            por_vencer.append(d)

    return {
        "vencidos":         vencidos,
        "por_vencer":       por_vencer,
        "total_vencidos":   len(vencidos),
        "total_por_vencer": len(por_vencer),
        "dias":             dias,
    }
