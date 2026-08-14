"""Tests del versionado del odontograma (B1 — evolución en el tiempo)."""
from __future__ import annotations

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.services import odontograma as svc
from clinica_app.services.exceptions import NotFoundError


async def _marcar(session, clinica, paciente, admin_user, numero, estado, nota=None):
    return await svc.guardar_pieza(
        session, clinica.id, paciente.id, numero,
        estado=estado, nota=nota, usuario_id=admin_user.id,
    )


# ── crear_version ─────────────────────────────────────────────────────────────

async def test_crear_version_congela_estado(session, clinica, paciente, admin_user):
    await _marcar(session, clinica, paciente, admin_user, "16", "caries", nota="oclusal")
    await _marcar(session, clinica, paciente, admin_user, "26", "obturado")

    v = await svc.crear_version(
        session, clinica.id, paciente.id,
        titulo="Estado inicial", usuario_id=admin_user.id,
    )
    assert v["titulo"] == "Estado inicial"
    assert v["con_datos"] == 2
    # El resumen refleja las dos piezas intervenidas.
    claves = {r["estado"]: r["count"] for r in v["resumen"]}
    assert claves == {"caries": 1, "obturado": 1}


async def test_crear_version_titulo_por_defecto(session, clinica, paciente, admin_user):
    v = await svc.crear_version(session, clinica.id, paciente.id, usuario_id=admin_user.id)
    assert v["titulo"].startswith("Versión ")
    assert v["con_datos"] == 0


async def test_crear_version_solo_piezas_con_datos(session, clinica, paciente, admin_user):
    await _marcar(session, clinica, paciente, admin_user, "16", "caries")
    v = await svc.crear_version(session, clinica.id, paciente.id, usuario_id=admin_user.id)
    # Solo 1 pieza con datos, no las 32 sanas.
    assert v["con_datos"] == 1


async def test_crear_version_registra_auditoria(session, clinica, paciente, admin_user):
    await svc.crear_version(session, clinica.id, paciente.id, usuario_id=admin_user.id)
    logs = (await session.execute(
        select(AuditLog).where(
            AuditLog.entidad == "odontograma_version", AuditLog.accion == "versionar",
        )
    )).scalars().all()
    assert len(logs) == 1


# ── inmutabilidad: la versión no cambia al editar el odontograma vivo ─────────

async def test_version_es_inmutable(session, clinica, paciente, admin_user):
    await _marcar(session, clinica, paciente, admin_user, "16", "caries")
    v = await svc.crear_version(session, clinica.id, paciente.id, titulo="Antes", usuario_id=admin_user.id)

    # Se trata la caries → ahora está obturada.
    await _marcar(session, clinica, paciente, admin_user, "16", "obturado")

    # La versión histórica sigue mostrando caries.
    arcada = await svc.obtener_version(session, clinica.id, paciente.id, v["id"])
    pieza16 = next(p for p in arcada["superior"] if p["numero"] == "16")
    assert pieza16["estado"] == "caries"
    # Mientras el odontograma vivo muestra obturado.
    actual = await svc.listar(session, clinica.id, paciente.id)
    pieza16_vivo = next(p for p in actual["superior"] if p["numero"] == "16")
    assert pieza16_vivo["estado"] == "obturado"


# ── obtener_version ───────────────────────────────────────────────────────────

async def test_obtener_version_reconstruye_arcada_completa(session, clinica, paciente, admin_user):
    await _marcar(session, clinica, paciente, admin_user, "16", "caries")
    v = await svc.crear_version(session, clinica.id, paciente.id, usuario_id=admin_user.id)
    arcada = await svc.obtener_version(session, clinica.id, paciente.id, v["id"])
    assert len(arcada["superior"]) == 16
    assert len(arcada["inferior"]) == 16
    assert arcada["resumen"].get("caries") == 1
    assert arcada["con_datos"] == 1


async def test_obtener_version_inexistente(session, clinica, paciente, admin_user):
    with pytest.raises(NotFoundError):
        await svc.obtener_version(session, clinica.id, paciente.id, 99999)


# ── listar_versiones ──────────────────────────────────────────────────────────

async def test_listar_versiones_orden_reciente_primero(session, clinica, paciente, admin_user):
    v1 = await svc.crear_version(session, clinica.id, paciente.id, titulo="Primera", usuario_id=admin_user.id)
    v2 = await svc.crear_version(session, clinica.id, paciente.id, titulo="Segunda", usuario_id=admin_user.id)
    vs = await svc.listar_versiones(session, clinica.id, paciente.id)
    assert len(vs) == 2
    ids = [x["id"] for x in vs]
    # La segunda (id mayor) aparece primero.
    assert ids[0] == v2["id"] and ids[1] == v1["id"]


async def test_listar_versiones_aislado_por_paciente(session, clinica, paciente, admin_user):
    await svc.crear_version(session, clinica.id, paciente.id, usuario_id=admin_user.id)
    otras = await svc.listar_versiones(session, clinica.id, paciente.id + 9999)
    assert otras == []


# ── eliminar_version ──────────────────────────────────────────────────────────

async def test_eliminar_version(session, clinica, paciente, admin_user):
    v = await svc.crear_version(session, clinica.id, paciente.id, usuario_id=admin_user.id)
    await svc.eliminar_version(session, clinica.id, paciente.id, v["id"], usuario_id=admin_user.id)
    vs = await svc.listar_versiones(session, clinica.id, paciente.id)
    assert vs == []
    with pytest.raises(NotFoundError):
        await svc.obtener_version(session, clinica.id, paciente.id, v["id"])


async def test_eliminar_version_inexistente(session, clinica, paciente, admin_user):
    with pytest.raises(NotFoundError):
        await svc.eliminar_version(session, clinica.id, paciente.id, 99999, usuario_id=admin_user.id)
