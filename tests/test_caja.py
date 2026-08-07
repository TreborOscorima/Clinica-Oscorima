"""Tests del servicio de caja (movimientos, resumen y cierres diarios)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from clinica_app.services import caja as svc
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


async def test_registrar_ingreso(session, clinica):
    res = await svc.registrar_movimiento(
        session, clinica.id, {"tipo": "ingreso", "monto": "100", "metodo_pago": "efectivo"}
    )
    assert res["tipo"] == "ingreso"
    assert Decimal(res["monto"]) == Decimal("100")
    assert res["metodo_pago"] == "efectivo"


async def test_registrar_tipo_invalido(session, clinica):
    with pytest.raises(ServiceError):
        await svc.registrar_movimiento(session, clinica.id, {"tipo": "otro", "monto": "10"})


async def test_registrar_monto_no_positivo(session, clinica):
    with pytest.raises(ServiceError):
        await svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "0"})
    with pytest.raises(ServiceError):
        await svc.registrar_movimiento(session, clinica.id, {"tipo": "egreso", "monto": "-5"})


async def test_resumen_dia_calcula_saldo(session, clinica):
    await svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "100"})
    await svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "50"})
    await svc.registrar_movimiento(session, clinica.id, {"tipo": "egreso", "monto": "30"})

    resumen = await svc.resumen_dia(session, clinica.id)
    assert Decimal(resumen["ingresos"]) == Decimal("150.00")
    assert Decimal(resumen["egresos"]) == Decimal("30.00")
    assert Decimal(resumen["saldo"]) == Decimal("120.00")
    assert resumen["total_movimientos"] == 3


async def test_cierre_dia_y_duplicado(session, clinica):
    await svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "200"})
    cierre = await svc.realizar_cierre_dia(session, clinica.id)
    assert Decimal(cierre["saldo"]) == Decimal("200.00")

    # Un segundo cierre para el mismo día debe rechazarse.
    with pytest.raises(ConflictError):
        await svc.realizar_cierre_dia(session, clinica.id)


async def test_eliminar_movimiento_saca_del_resumen(session, clinica):
    mov = await svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "80"})
    await svc.eliminar_movimiento(session, clinica.id, mov["id"])

    resumen = await svc.resumen_dia(session, clinica.id)
    assert resumen["total_movimientos"] == 0
    assert Decimal(resumen["ingresos"]) == Decimal("0")


async def test_eliminar_movimiento_inexistente(session, clinica):
    with pytest.raises(NotFoundError):
        await svc.eliminar_movimiento(session, clinica.id, 99999)
