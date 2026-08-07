"""Tests del servicio de compras (recepción → stock y anulación → repone stock)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from clinica_app.services import compras as svc
from clinica_app.services import inventario as inv
from clinica_app.services.exceptions import NotFoundError, ServiceError


async def _producto(session, clinica_id, stock="0"):
    return await inv.crear_producto(
        session, clinica_id, {"nombre": "Insumo", "sku": "INS-1", "stock_actual": stock}
    )


async def test_crear_proveedor(session, clinica):
    prov = await svc.crear_proveedor(session, clinica.id, {"nombre": "Distribuidora X"})
    assert prov["id"] > 0
    assert prov["nombre"] == "Distribuidora X"


async def test_crear_proveedor_sin_nombre(session, clinica):
    with pytest.raises(ServiceError):
        await svc.crear_proveedor(session, clinica.id, {"nombre": ""})


async def test_compra_ingresa_stock_y_calcula_venta(session, clinica):
    p = await _producto(session, clinica.id, stock="0")
    items = [{"producto_id": p["id"], "cantidad": "10", "costo_unitario": "5"}]
    compra = await svc.crear(session, clinica.id, {"numero": "F-001"}, items, margen_global=50.0)

    assert Decimal(compra["total"]) == Decimal("50.00")
    prod = await inv.obtener_producto(session, clinica.id, p["id"])
    assert Decimal(prod.stock_actual) == Decimal("10")
    assert Decimal(prod.precio_costo) == Decimal("5.00")
    assert Decimal(prod.precio_venta) == Decimal("7.50")  # 5 * (1 + 50%)


async def test_compra_sin_items(session, clinica):
    with pytest.raises(ServiceError):
        await svc.crear(session, clinica.id, {"numero": "F-002"}, [])


async def test_compra_cantidad_invalida(session, clinica):
    p = await _producto(session, clinica.id)
    items = [{"producto_id": p["id"], "cantidad": "0", "costo_unitario": "5"}]
    with pytest.raises(ServiceError):
        await svc.crear(session, clinica.id, {"numero": "F-003"}, items)


async def test_compra_producto_inexistente(session, clinica):
    items = [{"producto_id": 99999, "cantidad": "1", "costo_unitario": "5"}]
    with pytest.raises(NotFoundError):
        await svc.crear(session, clinica.id, {"numero": "F-004"}, items)


async def test_anular_repone_stock(session, clinica):
    p = await _producto(session, clinica.id, stock="0")
    items = [{"producto_id": p["id"], "cantidad": "10", "costo_unitario": "5"}]
    compra = await svc.crear(session, clinica.id, {"numero": "F-005"}, items)

    prod = await inv.obtener_producto(session, clinica.id, p["id"])
    assert Decimal(prod.stock_actual) == Decimal("10")

    await svc.anular(session, clinica.id, compra["id"])
    prod = await inv.obtener_producto(session, clinica.id, p["id"])
    assert Decimal(prod.stock_actual) == Decimal("0")

    # La compra anulada ya no aparece en el listado.
    listado = await svc.listar(session, clinica.id)
    assert listado["total"] == 0


async def test_anular_compra_inexistente(session, clinica):
    with pytest.raises(NotFoundError):
        await svc.anular(session, clinica.id, 99999)
