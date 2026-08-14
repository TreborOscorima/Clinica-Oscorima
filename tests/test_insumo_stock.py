"""Tests del descuento de stock al registrar un insumo estético (C2)."""
from __future__ import annotations

from decimal import Decimal

from sqlmodel import select

from clinica_app.models.inventario import MovimientoStock, Producto
from clinica_app.services import sesiones_esteticas as svc


async def _sesion(session, clinica, paciente, admin_user):
    return await svc.crear_sesion(
        session, clinica.id, paciente.id,
        fecha="2026-08-10", titulo="Botox", usuario_id=admin_user.id,
    )


async def _producto(session, clinica, nombre="Toxina", stock="50"):
    p = Producto(clinica_id=clinica.id, nombre=nombre, stock_actual=Decimal(stock))
    session.add(p)
    await session.flush()
    return p


async def test_insumo_con_producto_descuenta_stock(session, clinica, paciente, admin_user):
    prod = await _producto(session, clinica, stock="50")
    s = await _sesion(session, clinica, paciente, admin_user)
    res = await svc.agregar_insumo(
        session, clinica.id, s["id"],
        descripcion="", producto_id=prod.id, cantidad="8", unidad="UI",
        usuario_id=admin_user.id,
    )
    assert "stock_warning" not in res
    # Stock descontado: 50 - 8 = 42.
    await session.refresh(prod)
    assert prod.stock_actual == Decimal("42.000")
    # Se registró un movimiento de egreso referenciado a la sesión.
    movs = (await session.execute(
        select(MovimientoStock).where(MovimientoStock.producto_id == prod.id)
    )).scalars().all()
    assert len(movs) == 1
    assert movs[0].tipo == "egreso"
    assert movs[0].referencia == f"sesion:{s['id']}"


async def test_insumo_sin_producto_no_mueve_stock(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    res = await svc.agregar_insumo(
        session, clinica.id, s["id"], descripcion="Gasa", cantidad="3", usuario_id=admin_user.id,
    )
    assert "stock_warning" not in res
    movs = (await session.execute(select(MovimientoStock))).scalars().all()
    assert movs == []


async def test_insumo_stock_insuficiente_no_bloquea(session, clinica, paciente, admin_user):
    prod = await _producto(session, clinica, stock="5")
    s = await _sesion(session, clinica, paciente, admin_user)
    res = await svc.agregar_insumo(
        session, clinica.id, s["id"],
        descripcion="", producto_id=prod.id, cantidad="10", usuario_id=admin_user.id,
    )
    # El insumo se registró igual, con aviso; el stock NO cambió.
    assert "stock_warning" in res
    full = await svc.obtener_sesion(session, clinica.id, s["id"])
    assert len(full["insumos"]) == 1
    await session.refresh(prod)
    assert prod.stock_actual == Decimal("5.000")


async def test_insumo_cantidad_cero_no_mueve_stock(session, clinica, paciente, admin_user):
    prod = await _producto(session, clinica, stock="50")
    s = await _sesion(session, clinica, paciente, admin_user)
    await svc.agregar_insumo(
        session, clinica.id, s["id"],
        descripcion="Muestra", producto_id=prod.id, cantidad="0", usuario_id=admin_user.id,
    )
    await session.refresh(prod)
    assert prod.stock_actual == Decimal("50.000")
    movs = (await session.execute(select(MovimientoStock))).scalars().all()
    assert movs == []
