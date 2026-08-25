"""Tests del servicio de turnos."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from clinica_app.services import turnos as svc
from clinica_app.services.exceptions import ConflictError, ServiceError


def _dt(offset_hours: int = 2) -> str:
    """Fecha/hora futura (naive) para no chocar con el bloqueo de fecha pasada."""
    return ((datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=offset_hours))
            .replace(second=0, microsecond=0).isoformat())


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


_PASADO = "2020-01-01T10:00:00"


# ── Bloqueo de fecha pasada ──────────────────────────────────────────────────

async def test_crear_turno_fecha_pasada_falla(session, clinica, paciente):
    with pytest.raises(ServiceError):
        await svc.crear(session, clinica.id, {
            "paciente_id": paciente.id, "fecha_hora": _PASADO,
        })


async def test_reprogramar_fecha_pasada_falla(session, clinica, paciente):
    t = await svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": _dt()})
    with pytest.raises(ServiceError):
        await svc.reprogramar(session, clinica.id, t["id"], {"fecha_hora": _PASADO})


# ── Máquina de estados ───────────────────────────────────────────────────────

async def _turno(session, clinica, paciente):
    return await svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": _dt()})


async def test_estado_pendiente_a_atendido_ok(session, clinica, paciente):
    t = await _turno(session, clinica, paciente)
    r = await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "atendido"})
    assert r["estado"] == "atendido"


async def test_estado_atendido_es_terminal(session, clinica, paciente):
    t = await _turno(session, clinica, paciente)
    await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "atendido"})
    with pytest.raises(ConflictError):
        await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "confirmado"})


async def test_estado_cancelado_no_va_a_atendido(session, clinica, paciente):
    t = await _turno(session, clinica, paciente)
    await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "cancelado"})
    with pytest.raises(ConflictError):
        await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "atendido"})


async def test_estado_cancelado_se_reactiva_a_pendiente(session, clinica, paciente):
    t = await _turno(session, clinica, paciente)
    await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "cancelado"})
    r = await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "pendiente"})
    assert r["estado"] == "pendiente"


async def test_estado_mismo_estado_falla(session, clinica, paciente):
    t = await _turno(session, clinica, paciente)  # nace pendiente
    with pytest.raises(ConflictError):
        await svc.cambiar_estado(session, clinica.id, t["id"], {"estado": "pendiente"})


def test_transiciones_validas():
    assert set(svc.transiciones_validas("pendiente")) == {"confirmado", "cancelado", "atendido"}
    assert svc.transiciones_validas("atendido") == []
    assert svc.transiciones_validas("cancelado") == ["pendiente"]
    assert svc.transiciones_validas("inexistente") == []


async def test_turno_con_varios_servicios_se_serializa(session, clinica, paciente):
    """Regresión: la relación Turno.items debe ser una colección (uselist=True).

    Con `uselist=False` (bug del upgrade a SQLAlchemy 2.0/SQLModel), `t.items`
    devolvía un único objeto que al iterarse en `_dump` producía tuplas
    ('turno_id', N) → AttributeError y la lista de /turnos quedaba vacía.
    """
    creado = await svc.crear(session, clinica.id, {
        "paciente_id": paciente.id,
        "fecha_hora":  _dt(),
        "items": [
            {"servicio_id": 1, "precio": "100", "cantidad": "1"},
            {"servicio_id": 2, "precio": "50",  "cantidad": "2"},
            {"servicio_id": 3, "precio": "30",  "cantidad": "1"},
        ],
    })
    # crear() ya serializa vía _dump: los 3 items deben venir como lista
    assert isinstance(creado["items"], list)
    assert len(creado["items"]) == 3
    assert all("id" in it for it in creado["items"])

    # y listar() (que también pasa por _dump) no debe crashear
    res = await svc.listar(session, clinica.id)
    fila = next(t for t in res["data"] if t["id"] == creado["id"])
    assert len(fila["items"]) == 3
