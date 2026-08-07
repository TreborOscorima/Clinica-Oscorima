"""Tests del servicio de promociones (validaciones y vigencia por fechas)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from clinica_app.services import promociones as svc
from clinica_app.services.exceptions import NotFoundError, ServiceError


async def test_crear_porcentaje(session, clinica):
    p = await svc.crear(session, clinica.id, {"nombre": "2x1", "tipo": "porcentaje", "valor": "20"})
    assert Decimal(p["valor"]) == Decimal("20.00")
    assert p["activo"] is True
    assert p["vigente"] is True  # sin fechas → siempre vigente mientras esté activa


async def test_crear_sin_nombre(session, clinica):
    with pytest.raises(ServiceError):
        await svc.crear(session, clinica.id, {"nombre": "", "valor": "10"})


async def test_porcentaje_fuera_de_rango(session, clinica):
    with pytest.raises(ServiceError):
        await svc.crear(session, clinica.id, {"nombre": "Mal", "tipo": "porcentaje", "valor": "150"})


async def test_tipo_invalido(session, clinica):
    with pytest.raises(ServiceError):
        await svc.crear(session, clinica.id, {"nombre": "Mal", "tipo": "xyz", "valor": "10"})


async def test_aplica_a_invalido(session, clinica):
    with pytest.raises(ServiceError):
        await svc.crear(
            session, clinica.id,
            {"nombre": "Mal", "tipo": "monto_fijo", "valor": "10", "aplica_a": "algo"},
        )


async def test_toggle_activo_afecta_vigencia(session, clinica):
    p = await svc.crear(session, clinica.id, {"nombre": "Flash", "valor": "10"})
    assert p["vigente"] is True
    off = await svc.toggle_activo(session, clinica.id, p["id"])
    assert off["activo"] is False
    assert off["vigente"] is False  # inactiva no es vigente


async def test_vigencia_fecha_fin_pasada(session, clinica):
    p = await svc.crear(
        session, clinica.id,
        {"nombre": "Vencida", "valor": "10", "fecha_inicio": "2000-01-01", "fecha_fin": "2000-12-31"},
    )
    assert p["vigente"] is False


async def test_vigencia_fecha_inicio_futura(session, clinica):
    p = await svc.crear(
        session, clinica.id,
        {"nombre": "Futura", "valor": "10", "fecha_inicio": "2999-01-01"},
    )
    assert p["vigente"] is False


async def test_vigencia_dentro_de_rango(session, clinica):
    p = await svc.crear(
        session, clinica.id,
        {"nombre": "Actual", "valor": "10", "fecha_inicio": "2000-01-01", "fecha_fin": "2999-12-31"},
    )
    assert p["vigente"] is True


async def test_eliminar_promocion(session, clinica):
    p = await svc.crear(session, clinica.id, {"nombre": "Borrar", "valor": "10"})
    await svc.eliminar(session, clinica.id, p["id"])
    with pytest.raises(NotFoundError):
        await svc.actualizar(session, clinica.id, p["id"], {"nombre": "X", "valor": "5"})
