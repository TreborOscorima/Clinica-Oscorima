"""Tests del servicio de cobro (POS)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from clinica_app.services import cobro as svc
from clinica_app.services.exceptions import ServiceError


def _payload_minimo(paciente_id: int) -> dict:
    return {
        "paciente_id": paciente_id,
        "items": [
            {
                "tipo":        "servicio",
                "ref_id":      1,
                "nombre":      "Limpieza facial",
                "cantidad":    "1",
                "precio_unit": "100.00",
            }
        ],
        "forma_pago":       "efectivo",
        "descuento_global": "0",
        "es_cuotas":        False,
        "num_cuotas":       1,
        "cuota_inicial":    "0",
    }


async def test_crear_comprobante_basico(session, clinica, paciente):
    res = await svc.crear(session, clinica.id, _payload_minimo(paciente.id))
    assert res["total"] == "100.00"
    assert res["numero"].startswith("REC-")
    assert len(res["items"]) == 1


async def test_crear_sin_paciente(session, clinica):
    payload = _payload_minimo(999)
    with pytest.raises(Exception):
        await svc.crear(session, clinica.id, payload)


async def test_crear_sin_items(session, clinica, paciente):
    payload = _payload_minimo(paciente.id)
    payload["items"] = []
    with pytest.raises(ServiceError):
        await svc.crear(session, clinica.id, payload)


async def test_descuento_reduce_total(session, clinica, paciente):
    payload = _payload_minimo(paciente.id)
    payload["descuento_global"] = "20"
    res = await svc.crear(session, clinica.id, payload)
    assert Decimal(res["total"]) == Decimal("80.00")
    assert Decimal(res["descuento_global"]) == Decimal("20.00")


async def test_multiples_items(session, clinica, paciente):
    payload = {
        "paciente_id": paciente.id,
        "items": [
            {"tipo": "servicio", "ref_id": 1, "nombre": "Svc A",
             "cantidad": "2", "precio_unit": "50.00"},
            {"tipo": "producto", "ref_id": 2, "nombre": "Prod B",
             "cantidad": "1", "precio_unit": "30.00"},
        ],
        "forma_pago": "tarjeta",
        "descuento_global": "0",
        "es_cuotas": False,
        "num_cuotas": 1,
        "cuota_inicial": "0",
    }
    res = await svc.crear(session, clinica.id, payload)
    assert Decimal(res["total"]) == Decimal("130.00")


async def test_pago_en_cuotas_genera_deuda(session, clinica, paciente):
    from clinica_app.models.caja import DeudaPaciente
    from sqlmodel import select

    payload = _payload_minimo(paciente.id)
    payload["es_cuotas"]     = True
    payload["num_cuotas"]    = 3
    payload["cuota_inicial"] = "30"

    await svc.crear(session, clinica.id, payload)

    result = await session.execute(
        select(DeudaPaciente).where(DeudaPaciente.paciente_id == paciente.id)
    )
    deuda = result.scalars().first()
    assert deuda is not None
    assert deuda.saldo == Decimal("70.00")
