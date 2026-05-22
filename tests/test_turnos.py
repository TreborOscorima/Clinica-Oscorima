"""Tests del servicio de turnos."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from clinica_app.services import turnos as svc
from clinica_app.services.exceptions import ServiceError


def _dt(offset_hours: int = 2) -> str:
    return (datetime.now(timezone.utc).replace(tzinfo=None).replace(second=0, microsecond=0)
            .isoformat())


def test_crear_turno(session, clinica, paciente):
    t = svc.crear(session, clinica.id, {
        "paciente_id": paciente.id,
        "fecha_hora":  _dt(),
    })
    assert t["paciente_id"] == paciente.id
    assert t["estado"] == "pendiente"


def test_crear_turno_sin_paciente_id(session, clinica):
    with pytest.raises(ServiceError):
        svc.crear(session, clinica.id, {"fecha_hora": _dt()})


def test_crear_turno_paciente_inexistente(session, clinica):
    with pytest.raises(Exception):
        svc.crear(session, clinica.id, {"paciente_id": 99999, "fecha_hora": _dt()})


def test_cambiar_estado(session, clinica, paciente):
    t = svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": _dt()})
    actualizado = svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "confirmado"})
    assert actualizado["estado"] == "confirmado"


def test_reprogramar(session, clinica, paciente):
    t = svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": _dt()})
    nueva = "2030-01-15T14:30:00"
    rep = svc.reprogramar(session, clinica.id, t["id"], {"fecha_hora": nueva})
    assert "2030-01-15" in rep["fecha_hora"]


def test_listar_por_estado(session, clinica, paciente):
    svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": _dt()})
    res = svc.listar(session, clinica.id, estado="pendiente")
    assert res["total"] >= 1
    assert all(t["estado"] == "pendiente" for t in res["data"])


def test_listar_estado_invalido(session, clinica):
    with pytest.raises(ServiceError):
        svc.listar(session, clinica.id, estado="invalido")
