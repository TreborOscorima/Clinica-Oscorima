"""Tests del servicio de autenticación."""
from __future__ import annotations

import pytest

from clinica_app.services import auth as svc
from clinica_app.services.exceptions import ServiceError


async def test_autenticar_credenciales_correctas(session, admin_user):
    user = await svc.autenticar(session, "admin@test.com", "secret123")
    assert user.id == admin_user.id
    assert user.email == "admin@test.com"


async def test_autenticar_password_incorrecto(session, admin_user):
    with pytest.raises(ServiceError):
        await svc.autenticar(session, "admin@test.com", "wrong")


async def test_autenticar_email_inexistente(session):
    with pytest.raises(ServiceError):
        await svc.autenticar(session, "nobody@test.com", "any")


async def test_autenticar_usuario_inactivo(session, clinica):
    from clinica_app.models.user import RoleEnum, User
    u = User(clinica_id=clinica.id, nombre="Inactivo", email="off@test.com",
             rol=RoleEnum.RECEP, is_active=False)
    u.set_password("pass123")
    session.add(u)
    await session.flush()

    with pytest.raises(ServiceError):
        await svc.autenticar(session, "off@test.com", "pass123")


async def test_datos_usuario(admin_user):
    datos = svc.datos_usuario(admin_user)
    assert datos["email"] == "admin@test.com"
    assert datos["clinica_id"] == admin_user.clinica_id
    assert datos["rol"] == "administracion"


# ── Enforcement de licencia (integración panel Owner) ────────────────────────

async def test_login_bloqueado_clinica_suspendida(session, clinica, admin_user):
    """Credenciales OK pero clínica suspendida → login rechazado (403)."""
    clinica.licencia_activa = False
    session.add(clinica)
    await session.flush()
    with pytest.raises(ServiceError) as exc:
        await svc.autenticar(session, "admin@test.com", "secret123")
    assert exc.value.status_code == 403


async def test_login_bloqueado_trial_vencido(session, clinica, admin_user):
    from datetime import datetime, timedelta
    clinica.plan = "trial"
    clinica.trial_ends_at = datetime.utcnow() - timedelta(days=1)
    session.add(clinica)
    await session.flush()
    with pytest.raises(ServiceError) as exc:
        await svc.autenticar(session, "admin@test.com", "secret123")
    assert exc.value.status_code == 403


async def test_login_bloqueado_plan_vencido(session, clinica, admin_user):
    from datetime import datetime, timedelta
    clinica.plan = "standard"
    clinica.plan_expires_at = datetime.utcnow() - timedelta(days=1)
    session.add(clinica)
    await session.flush()
    with pytest.raises(ServiceError) as exc:
        await svc.autenticar(session, "admin@test.com", "secret123")
    assert exc.value.status_code == 403


async def test_login_permitido_plan_vigente(session, clinica, admin_user):
    from datetime import datetime, timedelta
    clinica.plan = "profesional"
    clinica.plan_expires_at = datetime.utcnow() + timedelta(days=30)
    session.add(clinica)
    await session.flush()
    user = await svc.autenticar(session, "admin@test.com", "secret123")
    assert user.id == admin_user.id


def test_clinica_acceso_permitido_helper():
    from types import SimpleNamespace
    from datetime import datetime, timedelta
    from clinica_app.services.planes import clinica_acceso_permitido

    activa = SimpleNamespace(licencia_activa=True, plan="trial", trial_ends_at=None, plan_expires_at=None)
    assert clinica_acceso_permitido(activa)[0] is True

    suspendida = SimpleNamespace(licencia_activa=False, plan="trial", trial_ends_at=None, plan_expires_at=None)
    assert clinica_acceso_permitido(suspendida)[0] is False

    vencida = SimpleNamespace(
        licencia_activa=True, plan="standard",
        trial_ends_at=None, plan_expires_at=datetime.utcnow() - timedelta(days=1),
    )
    assert clinica_acceso_permitido(vencida)[0] is False
