"""Tests de adjuntos clínicos (A2): storage + servicio."""
from __future__ import annotations

import os

import pytest

from clinica_app.services import adjuntos as svc
from clinica_app.services import storage
from clinica_app.services.exceptions import NotFoundError, ValidationError


# ── storage ──────────────────────────────────────────────────────────────────

def test_storage_valida_extension_no_permitida():
    with pytest.raises(ValidationError):
        storage.validar("virus.exe", 100)


def test_storage_valida_sin_extension():
    with pytest.raises(ValidationError):
        storage.validar("archivo_sin_ext", 100)


def test_storage_valida_tamano_cero():
    with pytest.raises(ValidationError):
        storage.validar("foto.jpg", 0)


def test_storage_valida_tamano_maximo(monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_MAX_MB", 1)
    with pytest.raises(ValidationError):
        storage.validar("foto.jpg", 2 * 1024 * 1024)


def test_storage_guardar_y_eliminar(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))
    stored = storage.guardar(7, "radiografia.png", b"\x89PNG datos")
    assert stored.endswith(".png")
    path = storage.ruta_absoluta(7, stored)
    assert os.path.isfile(path)
    # aislamiento por clínica
    assert f"clinica_7{os.sep}" in path

    storage.eliminar(7, stored)
    assert not os.path.isfile(path)
    # idempotente: borrar de nuevo no rompe
    storage.eliminar(7, stored)


def test_storage_ruta_bloquea_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))
    # basename() neutraliza el traversal → queda dentro del dir de la clínica
    path = storage.ruta_absoluta(3, "../../etc/passwd")
    base = os.path.abspath(os.path.join(str(tmp_path), "clinica_3"))
    assert path.startswith(base + os.sep)


# ── servicio ─────────────────────────────────────────────────────────────────

async def test_crear_y_listar_adjunto(session, clinica, paciente):
    creado = await svc.crear(
        session, clinica.id, paciente.id,
        nombre="foto.jpg", stored_name="abc123.jpg",
        mime="image/jpeg", tamano=2048, categoria="foto",
    )
    assert creado["id"] > 0
    assert creado["categoria"] == "foto"
    assert creado["tamano_fmt"] == "2 KB"

    lista = await svc.listar_por_paciente(session, clinica.id, paciente.id)
    assert len(lista) == 1
    assert lista[0]["nombre"] == "foto.jpg"


async def test_categoria_invalida_cae_en_otro(session, clinica, paciente):
    creado = await svc.crear(
        session, clinica.id, paciente.id,
        nombre="x.pdf", stored_name="x.pdf", categoria="inventada",
    )
    assert creado["categoria"] == "otro"


async def test_eliminar_adjunto_soft_delete_y_devuelve_stored(session, clinica, paciente, admin_user):
    creado = await svc.crear(
        session, clinica.id, paciente.id,
        nombre="estudio.pdf", stored_name="uuid999.pdf", categoria="estudio",
    )
    stored = await svc.eliminar(
        session, clinica.id, creado["id"], usuario_id=admin_user.id
    )
    assert stored == "uuid999.pdf"

    # ya no aparece en el listado
    lista = await svc.listar_por_paciente(session, clinica.id, paciente.id)
    assert lista == []

    # y no se puede obtener
    with pytest.raises(NotFoundError):
        await svc.obtener(session, clinica.id, creado["id"])


async def test_eliminar_adjunto_registra_auditoria(session, clinica, paciente, admin_user):
    from sqlmodel import select

    from clinica_app.models.audit_log import AuditLog

    creado = await svc.crear(
        session, clinica.id, paciente.id,
        nombre="consent.pdf", stored_name="c1.pdf", categoria="consentimiento",
    )
    await svc.eliminar(session, clinica.id, creado["id"], usuario_id=admin_user.id)

    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "adjunto", AuditLog.accion == "eliminar")
    )).scalars().all()
    assert len(logs) == 1
    assert logs[0].entidad_id == creado["id"]
