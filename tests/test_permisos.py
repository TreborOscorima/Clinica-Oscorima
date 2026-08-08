"""Tests del servicio de permisos (seed por rol + backfill + enforcement de defaults)."""
from __future__ import annotations

from sqlalchemy import func
from sqlmodel import select

from clinica_app.models.user import PermisoRol, RoleEnum
from clinica_app.services import permisos as svc


async def _count(session, clinica_id, role=None):
    stmt = select(func.count()).select_from(PermisoRol).where(PermisoRol.clinica_id == clinica_id)
    if role is not None:
        stmt = stmt.where(PermisoRol.role == RoleEnum(role))
    return (await session.execute(stmt)).scalar_one()


async def test_autoseed_administracion_todo_permitido(session, clinica):
    perms = await svc.cargar_permisos(session, clinica.id, "administracion")
    assert len(perms) == len(svc.MODULOS)
    # El administrador tiene lectura y escritura en todos los módulos.
    assert all(p["read"] and p["write"] for p in perms.values())


async def test_autoseed_recepcionista_aplica_defaults(session, clinica):
    perms = await svc.cargar_permisos(session, clinica.id, "recepcionista")
    assert perms["pacientes"] == {"read": True, "write": True}
    assert perms["caja"] == {"read": True, "write": False}      # solo lectura
    assert perms["compras"] == {"read": False, "write": False}   # sin acceso


async def test_cargar_es_idempotente(session, clinica):
    await svc.cargar_permisos(session, clinica.id, "administracion")
    await svc.cargar_permisos(session, clinica.id, "administracion")
    # No se duplican registros: exactamente un PermisoRol por módulo.
    assert await _count(session, clinica.id, "administracion") == len(svc.MODULOS)


async def test_backfill_de_modulos_faltantes(session, clinica):
    # Simula una clínica vieja con un solo módulo sembrado para el rol.
    session.add(PermisoRol(
        clinica_id=clinica.id, role=RoleEnum.ADMIN,
        module="dashboard", can_read=True, can_write=False,
    ))
    await session.flush()

    perms = await svc.cargar_permisos(session, clinica.id, "administracion")
    assert len(perms) == len(svc.MODULOS)
    # El módulo preexistente se respeta (no se pisa con el default).
    assert perms["dashboard"] == {"read": True, "write": False}
    # Los faltantes se completan con el default del rol.
    assert perms["pacientes"] == {"read": True, "write": True}


async def test_seedear_todos_cubre_los_cuatro_roles(session, clinica):
    await svc.seedear_todos(session, clinica.id)
    esperado = len(svc.MODULOS) * 4  # administracion, recepcionista, profesional, contador
    assert await _count(session, clinica.id) == esperado
    # Idempotente: una segunda pasada no agrega nada.
    await svc.seedear_todos(session, clinica.id)
    assert await _count(session, clinica.id) == esperado
