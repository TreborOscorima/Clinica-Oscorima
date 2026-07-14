"""Tests del servicio de turnos."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from clinica_app.services import turnos as svc
from clinica_app.services.exceptions import ServiceError


def _dt(offset_hours: int = 2) -> str:
    return (datetime.now(timezone.utc).replace(tzinfo=None).replace(second=0, microsecond=0)
            .isoformat())


async def test_crear_turno(session, clinica, paciente):
    t = await svc.crear(session, clinica.id, {
        "paciente_id": paciente.id,
        "fecha_hora":  _dt(),
    })
    assert t["paciente_id"] == paciente.id
    assert t["estado"] == "pendiente"


async def test_crear_turno_sin_paciente_id(session, clinica):
    with pytest.raises(ServiceError):
        await svc.crear(session, clinica.id, {"fecha_hora": _dt()})


async def test_crear_turno_paciente_inexistente(session, clinica):
    with pytest.raises(Exception):
        await svc.crear(session, clinica.id, {"paciente_id": 99999, "fecha_hora": _dt()})


async def test_cambiar_estado(session, clinica, paciente):
    t = await svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": _dt()})
    actualizado = await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "confirmado"})
    assert actualizado["estado"] == "confirmado"


async def test_reprogramar(session, clinica, paciente):
    t = await svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": _dt()})
    nueva = "2030-01-15T14:30:00"
    rep = await svc.reprogramar(session, clinica.id, t["id"], {"fecha_hora": nueva})
    assert "2030-01-15" in rep["fecha_hora"]


async def test_listar_por_estado(session, clinica, paciente):
    await svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": _dt()})
    res = await svc.listar(session, clinica.id, estado="pendiente")
    assert res["total"] >= 1
    assert all(t["estado"] == "pendiente" for t in res["data"])


async def test_listar_estado_invalido(session, clinica):
    with pytest.raises(ServiceError):
        await svc.listar(session, clinica.id, estado="invalido")
