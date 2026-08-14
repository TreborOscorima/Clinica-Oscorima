"""Tests de la agenda profesional (disponibilidad, bloqueos, solapamientos)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from clinica_app.models.profesional import Profesional
from clinica_app.models.servicio import Servicio
from clinica_app.services import agenda as svc
from clinica_app.services import turnos as turnos_svc
from clinica_app.services.exceptions import ConflictError, ValidationError


async def _prof(session, clinica, nombres="Ana", apellidos="García"):
    p = Profesional(clinica_id=clinica.id, nombres=nombres, apellidos=apellidos)
    session.add(p)
    await session.flush()
    return p


async def _servicio(session, clinica, dur=30, nombre="Consulta"):
    s = Servicio(clinica_id=clinica.id, nombre=nombre, duracion_min=dur)
    session.add(s)
    await session.flush()
    return s


# Lunes 2030-01-07 10:00  (weekday()==0)
_LUNES = datetime(2030, 1, 7, 10, 0)


# ── Disponibilidad ────────────────────────────────────────────────────────────

async def test_agregar_y_listar_disponibilidad(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    await svc.agregar_disponibilidad(
        session, clinica.id, prof.id,
        dia_semana=0, hora_inicio="09:00", hora_fin="13:00", usuario_id=admin_user.id,
    )
    disp = await svc.listar_disponibilidad(session, clinica.id, prof.id)
    assert len(disp) == 1
    assert disp[0]["dia_label"] == "Lunes"
    assert disp[0]["hora_inicio"] == "09:00"


async def test_disponibilidad_hora_invertida(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    with pytest.raises(ValidationError):
        await svc.agregar_disponibilidad(
            session, clinica.id, prof.id,
            dia_semana=0, hora_inicio="18:00", hora_fin="09:00", usuario_id=admin_user.id,
        )


async def test_disponibilidad_dia_invalido(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    with pytest.raises(ValidationError):
        await svc.agregar_disponibilidad(
            session, clinica.id, prof.id,
            dia_semana=9, hora_inicio="09:00", hora_fin="13:00", usuario_id=admin_user.id,
        )


async def test_eliminar_disponibilidad(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    d = await svc.agregar_disponibilidad(
        session, clinica.id, prof.id,
        dia_semana=0, hora_inicio="09:00", hora_fin="13:00", usuario_id=admin_user.id,
    )
    await svc.eliminar_disponibilidad(session, clinica.id, d["id"], usuario_id=admin_user.id)
    assert await svc.listar_disponibilidad(session, clinica.id, prof.id) == []


# ── Bloqueos ──────────────────────────────────────────────────────────────────

async def test_agregar_y_listar_bloqueo(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    await svc.agregar_bloqueo(
        session, clinica.id, prof.id,
        inicio="2030-01-07T00:00", fin="2030-01-10T23:59",
        motivo="Vacaciones", usuario_id=admin_user.id,
    )
    bloqs = await svc.listar_bloqueos(session, clinica.id, prof.id)
    assert len(bloqs) == 1
    assert bloqs[0]["motivo"] == "Vacaciones"


async def test_bloqueo_rango_invertido(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    with pytest.raises(ValidationError):
        await svc.agregar_bloqueo(
            session, clinica.id, prof.id,
            inicio="2030-01-10T00:00", fin="2030-01-07T00:00", usuario_id=admin_user.id,
        )


# ── verificar ─────────────────────────────────────────────────────────────────

async def test_verificar_sin_profesional_no_valida(session, clinica):
    res = await svc.verificar(session, clinica.id, None, _LUNES)
    assert res["conflictos"] == []


async def test_verificar_solapamiento_con_turno(session, clinica, paciente):
    prof = await _prof(session, clinica)
    serv = await _servicio(session, clinica, dur=30)
    # Turno existente a las 10:00 (30 min).
    await turnos_svc.crear(session, clinica.id, {
        "paciente_id": paciente.id, "profesional_id": prof.id,
        "servicio_id": serv.id, "fecha_hora": _LUNES.isoformat(),
    })
    # Nuevo turno a las 10:15 → se superpone.
    res = await svc.verificar(
        session, clinica.id, prof.id, _LUNES + timedelta(minutes=15), duracion_min=30,
    )
    assert any("superpone" in c for c in res["conflictos"])


async def test_verificar_sin_solapamiento_contiguo(session, clinica, paciente):
    prof = await _prof(session, clinica)
    serv = await _servicio(session, clinica, dur=30)
    await turnos_svc.crear(session, clinica.id, {
        "paciente_id": paciente.id, "profesional_id": prof.id,
        "servicio_id": serv.id, "fecha_hora": _LUNES.isoformat(),
    })
    # Turno contiguo a las 10:30 → no se superpone.
    res = await svc.verificar(
        session, clinica.id, prof.id, _LUNES + timedelta(minutes=30), duracion_min=30,
    )
    assert not any("superpone" in c for c in res["conflictos"])


async def test_verificar_bloqueo(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    await svc.agregar_bloqueo(
        session, clinica.id, prof.id,
        inicio="2030-01-07T00:00", fin="2030-01-08T00:00",
        motivo="Congreso", usuario_id=admin_user.id,
    )
    res = await svc.verificar(session, clinica.id, prof.id, _LUNES, duracion_min=30)
    assert any("Congreso" in c for c in res["conflictos"])


async def test_verificar_fuera_de_horario(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    # Atiende los lunes de 09:00 a 11:00.
    await svc.agregar_disponibilidad(
        session, clinica.id, prof.id,
        dia_semana=0, hora_inicio="09:00", hora_fin="11:00", usuario_id=admin_user.id,
    )
    # Turno lunes a las 16:00 → fuera de horario.
    res = await svc.verificar(session, clinica.id, prof.id, _LUNES.replace(hour=16), duracion_min=30)
    assert any("Fuera del horario" in c for c in res["conflictos"])


async def test_verificar_dentro_de_horario(session, clinica, admin_user):
    prof = await _prof(session, clinica)
    await svc.agregar_disponibilidad(
        session, clinica.id, prof.id,
        dia_semana=0, hora_inicio="09:00", hora_fin="13:00", usuario_id=admin_user.id,
    )
    res = await svc.verificar(session, clinica.id, prof.id, _LUNES, duracion_min=30)
    assert res["conflictos"] == []


async def test_verificar_sin_horario_no_bloquea_por_hora(session, clinica):
    prof = await _prof(session, clinica)
    # Sin disponibilidad cargada → no se valida horario.
    res = await svc.verificar(session, clinica.id, prof.id, _LUNES.replace(hour=23), duracion_min=30)
    assert res["conflictos"] == []


async def test_verificar_excluye_turno_propio(session, clinica, paciente):
    prof = await _prof(session, clinica)
    serv = await _servicio(session, clinica, dur=30)
    t = await turnos_svc.crear(session, clinica.id, {
        "paciente_id": paciente.id, "profesional_id": prof.id,
        "servicio_id": serv.id, "fecha_hora": _LUNES.isoformat(),
    })
    # Reprogramar al mismo horario, excluyéndose a sí mismo → sin conflicto.
    res = await svc.verificar(
        session, clinica.id, prof.id, _LUNES, duracion_min=30, excluir_turno_id=t["id"],
    )
    assert not any("superpone" in c for c in res["conflictos"])


# ── Integración con turnos.crear ──────────────────────────────────────────────

async def test_crear_turno_con_validacion_bloquea_solapamiento(session, clinica, paciente):
    prof = await _prof(session, clinica)
    serv = await _servicio(session, clinica, dur=30)
    await turnos_svc.crear(session, clinica.id, {
        "paciente_id": paciente.id, "profesional_id": prof.id,
        "servicio_id": serv.id, "fecha_hora": _LUNES.isoformat(),
    })
    with pytest.raises(ConflictError):
        await turnos_svc.crear(session, clinica.id, {
            "paciente_id": paciente.id, "profesional_id": prof.id,
            "servicio_id": serv.id, "fecha_hora": _LUNES.isoformat(),
        }, validar_agenda=True)


async def test_crear_turno_sin_validacion_permite_solapamiento(session, clinica, paciente):
    prof = await _prof(session, clinica)
    serv = await _servicio(session, clinica, dur=30)
    await turnos_svc.crear(session, clinica.id, {
        "paciente_id": paciente.id, "profesional_id": prof.id,
        "servicio_id": serv.id, "fecha_hora": _LUNES.isoformat(),
    })
    # Sin validar_agenda (default) NO bloquea — protege el flujo de estética.
    t = await turnos_svc.crear(session, clinica.id, {
        "paciente_id": paciente.id, "profesional_id": prof.id,
        "servicio_id": serv.id, "fecha_hora": _LUNES.isoformat(),
    })
    assert t["id"] is not None
