"""Impuesto (IGV/IVA) en el punto de cobro.

Cubre el cálculo puro (`calcular_impuesto`) en ambos modos y la integración con
`cobro.crear`: el comprobante congela tasa/monto, el desglose cuadra y el
ingreso a caja refleja el total efectivamente pagado.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from clinica_app.services import cobro as svc
from clinica_app.services import configuracion as cfg
from clinica_app.services.exceptions import ServiceError


def _payload(paciente_id: int, precio: str = "100.00", descuento: str = "0") -> dict:
    return {
        "paciente_id": paciente_id,
        "items": [
            {"tipo": "servicio", "ref_id": 1, "nombre": "Consulta",
             "cantidad": "1", "precio_unit": precio},
        ],
        "forma_pago":       "efectivo",
        "descuento_global": descuento,
        "es_cuotas":        False,
        "num_cuotas":       1,
        "cuota_inicial":    "0",
    }


async def _activar_impuesto(session, clinica, tasa: float = 18.0, modo: str = "incluido"):
    from clinica_app.models.impuesto_tasa import ImpuestoTasa
    clinica.mostrar_impuesto_recibo = True
    clinica.impuesto_modo = modo
    session.add(ImpuestoTasa(
        clinica_id=clinica.id, tipo_impuesto="IGV", nombre="Estándar",
        porcentaje=tasa, is_default=True,
    ))
    await session.flush()


async def _ingreso_caja(session, comp_id: int) -> Decimal:
    from clinica_app.models.caja import CajaMovimiento, TipoMovimiento
    from sqlmodel import select
    movs = (await session.execute(
        select(CajaMovimiento).where(
            CajaMovimiento.comprobante_id == comp_id,
            CajaMovimiento.tipo == TipoMovimiento.INGRESO,
        )
    )).scalars().all()
    return sum((m.monto for m in movs), Decimal("0"))


# ── Cálculo puro ──────────────────────────────────────────────────────────────

def test_calcular_impuesto_incluido():
    base, imp, total = svc.calcular_impuesto(Decimal("100"), Decimal("18"), "incluido")
    assert base == Decimal("84.75")
    assert imp == Decimal("15.25")
    assert total == Decimal("100.00")


def test_calcular_impuesto_agregado():
    base, imp, total = svc.calcular_impuesto(Decimal("100"), Decimal("18"), "agregado")
    assert base == Decimal("100.00")
    assert imp == Decimal("18.00")
    assert total == Decimal("118.00")


def test_calcular_impuesto_tasa_cero():
    for modo in ("incluido", "agregado"):
        base, imp, total = svc.calcular_impuesto(Decimal("100"), Decimal("0"), modo)
        assert (base, imp, total) == (Decimal("100.00"), Decimal("0.00"), Decimal("100.00"))


def test_calcular_impuesto_suma_exacta():
    # base + impuesto == total siempre, incluso con redondeo feo.
    for modo in ("incluido", "agregado"):
        base, imp, total = svc.calcular_impuesto(Decimal("99.99"), Decimal("18"), modo)
        assert base + imp == total


# ── Integración con cobro.crear ───────────────────────────────────────────────

async def test_crear_sin_impuesto_no_cambia(session, clinica, paciente):
    res = await svc.crear(session, clinica.id, _payload(paciente.id))
    assert Decimal(res["total"]) == Decimal("100.00")
    assert Decimal(res["impuesto_monto"]) == Decimal("0")
    assert Decimal(res["base_imponible"]) == Decimal("100.00")


async def test_crear_impuesto_incluido(session, clinica, paciente):
    await _activar_impuesto(session, clinica, 18.0, "incluido")
    res = await svc.crear(session, clinica.id, _payload(paciente.id))
    assert Decimal(res["total"]) == Decimal("100.00")          # el total no cambia
    assert Decimal(res["impuesto_monto"]) == Decimal("15.25")
    assert Decimal(res["base_imponible"]) == Decimal("84.75")
    assert Decimal(res["impuesto_tasa"]) == Decimal("18.00")
    # El ingreso a caja es el total pagado (100).
    assert await _ingreso_caja(session, res["id"]) == Decimal("100.00")


async def test_crear_impuesto_agregado(session, clinica, paciente):
    await _activar_impuesto(session, clinica, 18.0, "agregado")
    res = await svc.crear(session, clinica.id, _payload(paciente.id))
    assert Decimal(res["total"]) == Decimal("118.00")          # sube el total
    assert Decimal(res["impuesto_monto"]) == Decimal("18.00")
    assert Decimal(res["base_imponible"]) == Decimal("100.00")
    # El ingreso a caja refleja el total con impuesto (118).
    assert await _ingreso_caja(session, res["id"]) == Decimal("118.00")


async def test_impuesto_incluido_con_descuento(session, clinica, paciente):
    await _activar_impuesto(session, clinica, 18.0, "incluido")
    res = await svc.crear(session, clinica.id, _payload(paciente.id, descuento="20"))
    # neto = 80; incluido → total 80, base+igv == 80
    assert Decimal(res["total"]) == Decimal("80.00")
    assert Decimal(res["base_imponible"]) + Decimal(res["impuesto_monto"]) == Decimal("80.00")


# ── Config: modo de impuesto ──────────────────────────────────────────────────

async def test_set_impuesto_modo(session, clinica):
    data = await cfg.obtener_clinica(session, clinica.id)
    assert data["impuesto_modo"] == "incluido"          # default
    await cfg.set_impuesto_modo(session, clinica.id, "agregado")
    data = await cfg.obtener_clinica(session, clinica.id)
    assert data["impuesto_modo"] == "agregado"


async def test_set_impuesto_modo_invalido(session, clinica):
    with pytest.raises(ServiceError):
        await cfg.set_impuesto_modo(session, clinica.id, "otro")
