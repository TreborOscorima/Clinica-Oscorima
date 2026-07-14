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
