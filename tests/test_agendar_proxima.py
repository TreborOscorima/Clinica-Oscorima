"""Tests de la creación automática del turno de la próxima sesión (C2)."""
from __future__ import annotations

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.services import sesiones_esteticas as svc
from clinica_app.services.exceptions import ValidationError


async def _sesion(session, clinica, paciente, admin_user, proxima=None):
    s = await svc.crear_sesion(
        session, clinica.id, paciente.id,
        fecha="2026-08-10", titulo="Botox", usuario_id=admin_user.id,
    )
    if proxima:
        await svc.actualizar_sesion(session, clinica.id, s["id"], proxima=proxima, usuario_id=admin_user.id)
    return s


async def test_agendar_usa_proxima_y_hora_default(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user, proxima="2026-09-10")
    turno = await svc.agendar_proxima_sesion(session, clinica.id, s["id"], usuario_id=admin_user.id)
    assert turno["paciente_id"] == paciente.id
    assert turno["fecha_hora"] == "2026-09-10 09:00"
    assert turno["estado"] == EstadoTurno.PENDIENTE.value

    # El turno existe en la BD.
    filas = (await session.execute(
        select(Turno).where(Turno.clinica_id == clinica.id, Turno.is_active.is_(True))
    )).scalars().all()
    assert len(filas) == 1
    assert filas[0].paciente_id == paciente.id


async def test_agendar_con_fecha_y_hora_explicitas(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user, proxima="2026-09-10")
    turno = await svc.agendar_proxima_sesion(
        session, clinica.id, s["id"], fecha="2026-10-01", hora="15:30", usuario_id=admin_user.id,
    )
    assert turno["fecha_hora"] == "2026-10-01 15:30"


async def test_agendar_sin_proxima_falla(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)  # sin proxima
    with pytest.raises(ValidationError):
        await svc.agendar_proxima_sesion(session, clinica.id, s["id"], usuario_id=admin_user.id)


async def test_agendar_hora_invalida(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user, proxima="2026-09-10")
    with pytest.raises(ValidationError):
        await svc.agendar_proxima_sesion(session, clinica.id, s["id"], hora="25:99", usuario_id=admin_user.id)


async def test_agendar_con_profesional(session, clinica, paciente, admin_user):
    from clinica_app.models.profesional import Profesional
    prof = Profesional(clinica_id=clinica.id, nombres="Ana", apellidos="Pérez")
    session.add(prof)
    await session.flush()
    s = await _sesion(session, clinica, paciente, admin_user, proxima="2026-09-10")
    turno = await svc.agendar_proxima_sesion(
        session, clinica.id, s["id"], profesional_id=prof.id, usuario_id=admin_user.id,
    )
    assert turno["profesional_id"] == prof.id


async def test_agendar_registra_auditoria(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user, proxima="2026-09-10")
    await svc.agendar_proxima_sesion(session, clinica.id, s["id"], usuario_id=admin_user.id)
    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "sesion_estetica", AuditLog.accion == "agendar_turno")
    )).scalars().all()
    assert len(logs) == 1
