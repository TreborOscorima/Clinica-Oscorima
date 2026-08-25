"""Lotes de inventario: upsert de ingreso, consumo FEFO y alertas de vencimiento.

El stock agregado del producto es la fuente de verdad; los lotes son un desglose
por partida best-effort que habilita control de vencimientos y consumo del que
vence primero (first-expired-first-out).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import select

from clinica_app.models.inventario import LoteProducto, Producto, TipoMov
from clinica_app.services import inventario as inv_svc
from clinica_app.services import lotes as svc

HOY = date(2026, 8, 25)


async def _producto(session, clinica, nombre="Bótox", stock="0"):
    p = Producto(
        clinica_id=clinica.id, nombre=nombre,
        stock_actual=Decimal(stock), precio_costo=Decimal("10.00"),
    )
    session.add(p)
    await session.flush()
    return p


async def _saldo_lote(session, lote_id):
    l = (await session.execute(
        select(LoteProducto).where(LoteProducto.id == lote_id)
    )).scalars().first()
    return l.cantidad_actual


# ── registrar_ingreso ─────────────────────────────────────────────────────────

async def test_registrar_ingreso_crea_lote(session, clinica):
    p = await _producto(session, clinica)
    l = await svc.registrar_ingreso(
        session, clinica.id, p.id,
        lote="L-001", vencimiento="2027-01-31", cantidad="5",
    )
    assert l is not None
    assert l.lote == "L-001"
    assert l.vencimiento == date(2027, 1, 31)
    assert l.cantidad_actual == Decimal("5.000")
    assert l.cantidad_inicial == Decimal("5.000")


async def test_registrar_ingreso_upsert_suma(session, clinica):
    p = await _producto(session, clinica)
    await svc.registrar_ingreso(session, clinica.id, p.id, lote="L-001", cantidad="5")
    l = await svc.registrar_ingreso(session, clinica.id, p.id, lote="l-001", cantidad="3")
    # Mismo lote (case-insensitive) → suma, no duplica.
    assert l.cantidad_actual == Decimal("8.000")
    total = (await session.execute(
        select(LoteProducto).where(LoteProducto.producto_id == p.id)
    )).scalars().all()
    assert len(total) == 1


async def test_registrar_ingreso_lote_vacio_noop(session, clinica):
    p = await _producto(session, clinica)
    assert await svc.registrar_ingreso(session, clinica.id, p.id, lote="", cantidad="5") is None
    assert await svc.registrar_ingreso(session, clinica.id, p.id, lote="X", cantidad="0") is None


# ── consumir_fefo ─────────────────────────────────────────────────────────────

async def test_consumir_fefo_orden_vencimiento(session, clinica):
    p = await _producto(session, clinica)
    tarde = await svc.registrar_ingreso(session, clinica.id, p.id, lote="TARDE", vencimiento="2027-12-31", cantidad="10")
    pronto = await svc.registrar_ingreso(session, clinica.id, p.id, lote="PRONTO", vencimiento="2026-09-30", cantidad="4")

    detalle = await svc.consumir_fefo(session, clinica.id, p.id, "6")
    # Consume primero el que vence antes (PRONTO: 4), luego TARDE: 2.
    assert detalle == [{"lote": "PRONTO", "cantidad": "4.000"}, {"lote": "TARDE", "cantidad": "2.000"}]
    assert await _saldo_lote(session, pronto.id) == Decimal("0.000")
    assert await _saldo_lote(session, tarde.id) == Decimal("8.000")


async def test_consumir_fefo_sin_lotes_noop(session, clinica):
    p = await _producto(session, clinica)
    assert await svc.consumir_fefo(session, clinica.id, p.id, "5") == []


async def test_consumir_fefo_parcial_no_levanta(session, clinica):
    p = await _producto(session, clinica)
    l = await svc.registrar_ingreso(session, clinica.id, p.id, lote="L", vencimiento="2027-01-01", cantidad="2")
    # Pide más de lo que hay: descuenta lo disponible sin error.
    detalle = await svc.consumir_fefo(session, clinica.id, p.id, "5")
    assert detalle == [{"lote": "L", "cantidad": "2.000"}]
    assert await _saldo_lote(session, l.id) == Decimal("0.000")


async def test_consumir_fefo_sin_venc_al_final(session, clinica):
    p = await _producto(session, clinica)
    sin = await svc.registrar_ingreso(session, clinica.id, p.id, lote="SINVENC", cantidad="10")
    con = await svc.registrar_ingreso(session, clinica.id, p.id, lote="CONVENC", vencimiento="2027-01-01", cantidad="10")
    await svc.consumir_fefo(session, clinica.id, p.id, "5")
    # El que tiene vencimiento se consume antes que el que no tiene.
    assert await _saldo_lote(session, con.id) == Decimal("5.000")
    assert await _saldo_lote(session, sin.id) == Decimal("10.000")


# ── alertas_vencimiento ───────────────────────────────────────────────────────

async def test_alertas_clasifica(session, clinica):
    p = await _producto(session, clinica)
    await svc.registrar_ingreso(session, clinica.id, p.id, lote="VENCIDO",
                                vencimiento=(HOY - timedelta(days=3)).isoformat(), cantidad="2")
    await svc.registrar_ingreso(session, clinica.id, p.id, lote="PRONTO",
                                vencimiento=(HOY + timedelta(days=10)).isoformat(), cantidad="2")
    await svc.registrar_ingreso(session, clinica.id, p.id, lote="LEJOS",
                                vencimiento=(HOY + timedelta(days=200)).isoformat(), cantidad="2")

    al = await svc.alertas_vencimiento(session, clinica.id, dias=30, hoy=HOY)
    assert al["total_vencidos"] == 1
    assert al["total_por_vencer"] == 1
    assert al["vencidos"][0]["lote"] == "VENCIDO"
    assert al["por_vencer"][0]["lote"] == "PRONTO"


async def test_alertas_ignora_agotados(session, clinica):
    p = await _producto(session, clinica)
    await svc.registrar_ingreso(session, clinica.id, p.id, lote="VENCIDO_SIN_STOCK",
                                vencimiento=(HOY - timedelta(days=3)).isoformat(), cantidad="2")
    await svc.consumir_fefo(session, clinica.id, p.id, "2")  # lo agota
    al = await svc.alertas_vencimiento(session, clinica.id, dias=30, hoy=HOY)
    assert al["total_vencidos"] == 0


async def test_listar_por_producto_excluye_agotados(session, clinica):
    p = await _producto(session, clinica)
    await svc.registrar_ingreso(session, clinica.id, p.id, lote="A", vencimiento="2027-01-01", cantidad="3")
    await svc.registrar_ingreso(session, clinica.id, p.id, lote="B", vencimiento="2026-09-01", cantidad="1")
    await svc.consumir_fefo(session, clinica.id, p.id, "1")  # agota B (vence antes)
    activos = await svc.listar_por_producto(session, clinica.id, p.id, hoy=HOY)
    assert [x["lote"] for x in activos] == ["A"]
    todos = await svc.listar_por_producto(session, clinica.id, p.id, hoy=HOY, incluir_agotados=True)
    assert len(todos) == 2


# ── Integración con el movimiento de stock ──────────────────────────────────────

async def test_movimiento_ingreso_crea_lote(session, clinica):
    p = await _producto(session, clinica, stock="0")
    await inv_svc.registrar_movimiento_stock(
        session, clinica.id, p.id, TipoMov.INGRESO.value, "7",
        lote="L-XYZ", vencimiento="2027-03-15",
    )
    lotes = await svc.listar_por_producto(session, clinica.id, p.id, hoy=HOY)
    assert len(lotes) == 1
    assert lotes[0]["lote"] == "L-XYZ"
    assert lotes[0]["cantidad"] == "7.000"
    await session.refresh(p)
    assert p.stock_actual == Decimal("7.000")


async def test_movimiento_egreso_consume_fefo(session, clinica):
    p = await _producto(session, clinica, stock="0")
    await inv_svc.registrar_movimiento_stock(
        session, clinica.id, p.id, TipoMov.INGRESO.value, "10", lote="L1", vencimiento="2027-01-01",
    )
    await inv_svc.registrar_movimiento_stock(
        session, clinica.id, p.id, TipoMov.EGRESO.value, "4",
    )
    lotes = await svc.listar_por_producto(session, clinica.id, p.id, hoy=HOY)
    assert lotes[0]["cantidad"] == "6.000"   # 10 - 4 por FEFO
    await session.refresh(p)
    assert p.stock_actual == Decimal("6.000")
