"""Tests del servicio de inventario (productos y movimientos de stock)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from clinica_app.services import inventario as svc
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


async def _crear(session, clinica_id, **kw):
    payload = {"nombre": "Guantes", "sku": "SKU-1", "stock_actual": "5", "stock_minimo": "2"}
    payload.update(kw)
    return await svc.crear_producto(session, clinica_id, payload)


async def test_crear_producto(session, clinica):
    p = await _crear(session, clinica.id)
    assert p["nombre"] == "Guantes"
    assert Decimal(p["stock_actual"]) == Decimal("5")
    assert p["bajo_minimo"] is False


async def test_crear_sin_nombre(session, clinica):
    with pytest.raises(ServiceError):
        await svc.crear_producto(session, clinica.id, {"nombre": "  "})


async def test_sku_duplicado(session, clinica):
    await _crear(session, clinica.id)
    with pytest.raises(ConflictError):
        await _crear(session, clinica.id, nombre="Otro")


async def test_ingreso_suma_stock(session, clinica):
    p = await _crear(session, clinica.id)
    res = await svc.registrar_movimiento_stock(session, clinica.id, p["id"], "ingreso", "10")
    assert Decimal(res["nuevo_saldo"]) == Decimal("15")


async def test_egreso_descuenta_stock(session, clinica):
    p = await _crear(session, clinica.id)
    res = await svc.registrar_movimiento_stock(session, clinica.id, p["id"], "egreso", "3")
    assert Decimal(res["nuevo_saldo"]) == Decimal("2")


async def test_egreso_insuficiente_falla(session, clinica):
    p = await _crear(session, clinica.id)
    with pytest.raises(ServiceError):
        await svc.registrar_movimiento_stock(session, clinica.id, p["id"], "egreso", "10")


async def test_bajo_minimo_tras_egreso(session, clinica):
    p = await _crear(session, clinica.id)  # stock 5, minimo 2
    await svc.registrar_movimiento_stock(session, clinica.id, p["id"], "egreso", "4")
    prod = await svc.obtener_producto(session, clinica.id, p["id"])
    assert prod.bajo_minimo is True


async def test_eliminar_producto(session, clinica):
    p = await _crear(session, clinica.id)
    await svc.eliminar_producto(session, clinica.id, p["id"])
    with pytest.raises(NotFoundError):
        await svc.obtener_producto(session, clinica.id, p["id"])
