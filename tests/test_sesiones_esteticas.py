"""Tests de la galería antes/después estética (C1)."""
from __future__ import annotations

import pytest
from sqlmodel import select

from clinica_app.models.adjunto import Adjunto
from clinica_app.models.audit_log import AuditLog
from clinica_app.services import sesiones_esteticas as svc
from clinica_app.services.exceptions import NotFoundError, ValidationError


async def _sesion(session, clinica, paciente, admin_user, fecha="2026-08-10", titulo="Ácido hialurónico"):
    return await svc.crear_sesion(
        session, clinica.id, paciente.id,
        fecha=fecha, titulo=titulo, zona="Labios", usuario_id=admin_user.id,
    )


async def _foto(session, clinica, paciente, admin_user, sesion_id, momento, nombre="f.jpg", stored="abc.jpg"):
    return await svc.registrar_foto(
        session, clinica.id, paciente.id, sesion_id,
        momento=momento, nombre=nombre, stored_name=stored,
        mime="image/jpeg", tamano=1000, usuario_id=admin_user.id,
    )


# ── Catálogo ──────────────────────────────────────────────────────────────────

def test_momentos_catalogo():
    claves = {m["clave"] for m in svc.momentos_catalogo()}
    assert claves == {"antes", "durante", "despues"}


# ── crear_sesion ──────────────────────────────────────────────────────────────

async def test_crear_sesion(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    assert s["id"] > 0
    assert s["titulo"] == "Ácido hialurónico"
    assert s["fecha"] == "2026-08-10"
    assert s["zona"] == "Labios"
    assert s["n_fotos"] == 0


async def test_crear_sesion_titulo_obligatorio(session, clinica, paciente, admin_user):
    with pytest.raises(ValidationError):
        await svc.crear_sesion(session, clinica.id, paciente.id, fecha="2026-08-10", titulo="  ", usuario_id=admin_user.id)


async def test_crear_sesion_fecha_invalida(session, clinica, paciente, admin_user):
    with pytest.raises(ValidationError):
        await svc.crear_sesion(session, clinica.id, paciente.id, fecha="10-08-2026", titulo="X", usuario_id=admin_user.id)


async def test_crear_sesion_paciente_inexistente(session, clinica, admin_user):
    with pytest.raises(NotFoundError):
        await svc.crear_sesion(session, clinica.id, 999999, fecha="2026-08-10", titulo="X", usuario_id=admin_user.id)


# ── fotos ─────────────────────────────────────────────────────────────────────

async def test_registrar_foto_y_agrupar_por_momento(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    await _foto(session, clinica, paciente, admin_user, s["id"], "antes", stored="a1.jpg")
    await _foto(session, clinica, paciente, admin_user, s["id"], "antes", stored="a2.jpg")
    await _foto(session, clinica, paciente, admin_user, s["id"], "despues", stored="d1.jpg")

    full = await svc.obtener_sesion(session, clinica.id, s["id"])
    assert len(full["antes"]) == 2
    assert len(full["despues"]) == 1
    assert full["n_fotos"] == 3
    # La foto queda registrada como Adjunto categoría "foto" con sesion+momento.
    filas = (await session.execute(
        select(Adjunto).where(Adjunto.sesion_id == s["id"], Adjunto.is_active.is_(True))
    )).scalars().all()
    assert len(filas) == 3
    assert all(f.categoria == "foto" for f in filas)


async def test_registrar_foto_momento_invalido(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    with pytest.raises(ValidationError):
        await _foto(session, clinica, paciente, admin_user, s["id"], "medio")


async def test_registrar_foto_sesion_inexistente(session, clinica, paciente, admin_user):
    with pytest.raises(NotFoundError):
        await _foto(session, clinica, paciente, admin_user, 999999, "antes")


async def test_eliminar_foto_devuelve_stored_name(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    f = await _foto(session, clinica, paciente, admin_user, s["id"], "antes", stored="borrar.jpg")
    stored = await svc.eliminar_foto(session, clinica.id, f["id"], usuario_id=admin_user.id)
    assert stored == "borrar.jpg"
    full = await svc.obtener_sesion(session, clinica.id, s["id"])
    assert full["n_fotos"] == 0


# ── listar_sesiones (timeline) ────────────────────────────────────────────────

async def test_listar_sesiones_timeline_orden_y_conteos(session, clinica, paciente, admin_user):
    s1 = await _sesion(session, clinica, paciente, admin_user, fecha="2026-08-01", titulo="Sesión 1")
    s2 = await _sesion(session, clinica, paciente, admin_user, fecha="2026-08-20", titulo="Sesión 2")
    await _foto(session, clinica, paciente, admin_user, s1["id"], "antes", stored="s1a.jpg")
    await _foto(session, clinica, paciente, admin_user, s2["id"], "antes", stored="s2a.jpg")
    await _foto(session, clinica, paciente, admin_user, s2["id"], "despues", stored="s2d.jpg")

    tl = await svc.listar_sesiones(session, clinica.id, paciente.id)
    # Más reciente primero.
    assert [s["titulo"] for s in tl] == ["Sesión 2", "Sesión 1"]
    s2_row = tl[0]
    assert s2_row["n_fotos"] == 2
    assert s2_row["n_antes"] == 1
    assert s2_row["n_despues"] == 1


# ── actualizar / eliminar ─────────────────────────────────────────────────────

async def test_actualizar_sesion(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    upd = await svc.actualizar_sesion(session, clinica.id, s["id"], titulo="Nuevo título", zona="Frente", usuario_id=admin_user.id)
    assert upd["titulo"] == "Nuevo título"
    assert upd["zona"] == "Frente"


async def test_eliminar_sesion_cascada_devuelve_stored_names(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    await _foto(session, clinica, paciente, admin_user, s["id"], "antes", stored="x1.jpg")
    await _foto(session, clinica, paciente, admin_user, s["id"], "despues", stored="x2.jpg")

    stored = await svc.eliminar_sesion(session, clinica.id, s["id"], usuario_id=admin_user.id)
    assert set(stored) == {"x1.jpg", "x2.jpg"}
    # Ya no aparece en el timeline y sus fotos quedaron inactivas.
    assert await svc.listar_sesiones(session, clinica.id, paciente.id) == []
    activas = (await session.execute(
        select(Adjunto).where(Adjunto.sesion_id == s["id"], Adjunto.is_active.is_(True))
    )).scalars().all()
    assert activas == []
    with pytest.raises(NotFoundError):
        await svc.obtener_sesion(session, clinica.id, s["id"])


# ── auditoría / aislamiento ───────────────────────────────────────────────────

async def test_auditoria_registrada(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    await _foto(session, clinica, paciente, admin_user, s["id"], "antes")
    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "sesion_estetica")
    )).scalars().all()
    acciones = {log.accion for log in logs}
    assert "crear" in acciones
    assert "agregar_foto" in acciones


async def test_sesiones_aisladas_por_paciente(session, clinica, paciente, admin_user):
    await _sesion(session, clinica, paciente, admin_user)
    otras = await svc.listar_sesiones(session, clinica.id, paciente.id + 9999)
    assert otras == []
