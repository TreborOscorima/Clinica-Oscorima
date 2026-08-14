"""Tests de recetas / indicaciones imprimibles (A5).

Cubren los tipos, la generación de bytes del PDF (receta e indicación) y la
orquestación completa (genera → archiva como adjunto categoría "receta" →
auditoría). El almacenamiento se redirige a un directorio temporal.
"""
from __future__ import annotations

import os

import pytest
from sqlmodel import select

from clinica_app.models.adjunto import Adjunto
from clinica_app.models.audit_log import AuditLog
from clinica_app.services import recetas as svc
from clinica_app.services import storage
from clinica_app.services.exceptions import NotFoundError, ServiceError
from clinica_app.services.pdf_receta import generar_receta_pdf


# ── Tipos ────────────────────────────────────────────────────────────────────

def test_tipos_incluye_receta_e_indicacion():
    claves = {t["clave"] for t in svc.tipos()}
    assert claves == {"receta", "indicacion"}


# ── PDF (bytes, sin disco) ───────────────────────────────────────────────────

def test_pdf_receta_devuelve_bytes_validos():
    data = generar_receta_pdf(
        clinica_nombre="Clínica Test",
        tipo="receta",
        paciente_nombre="Juan Pérez",
        paciente_documento="12345678",
        profesional_nombre="Dr. Ruiz",
        diagnostico="Faringitis",
        cuerpo="Amoxicilina 500mg — 1 comp c/8h\nIbuprofeno 400mg — si dolor",
    )
    assert isinstance(data, bytes)
    assert data[:5] == b"%PDF-"
    assert len(data) > 800


def test_pdf_indicacion_devuelve_bytes_validos():
    data = generar_receta_pdf(
        tipo="indicacion",
        paciente_nombre="Ana",
        cuerpo="Reposo 48h\nHidratación abundante",
    )
    assert data[:5] == b"%PDF-"


# ── Orquestación completa ────────────────────────────────────────────────────

async def test_generar_crea_adjunto_receta(session, clinica, paciente, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))

    dump = await svc.generar(
        session, clinica.id, paciente.id,
        tipo="receta",
        cuerpo="Amoxicilina 500mg — 1 comp c/8h por 7 días",
        diagnostico="Faringitis aguda",
        profesional_nombre="Dr. Ruiz M.P. 1234",
        usuario_id=admin_user.id,
    )

    assert dump["categoria"] == "receta"
    assert dump["nombre"].endswith(".pdf")
    assert dump["tamano"] > 0

    adj = (await session.execute(
        select(Adjunto).where(Adjunto.id == dump["id"])
    )).scalars().first()
    assert adj is not None
    assert adj.paciente_id == paciente.id
    assert adj.mime == "application/pdf"

    path = storage.ruta_absoluta(clinica.id, adj.stored_name)
    assert os.path.isfile(path)


async def test_generar_registra_auditoria(session, clinica, paciente, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))

    dump = await svc.generar(
        session, clinica.id, paciente.id,
        tipo="indicacion", cuerpo="Reposo 48h",
        usuario_id=admin_user.id,
    )

    logs = (await session.execute(
        select(AuditLog).where(
            AuditLog.entidad == "receta",
            AuditLog.accion == "generar",
        )
    )).scalars().all()
    assert len(logs) == 1
    assert logs[0].entidad_id == dump["id"]


async def test_generar_cuerpo_vacio(session, clinica, paciente, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))
    with pytest.raises(ServiceError):
        await svc.generar(
            session, clinica.id, paciente.id,
            tipo="receta", cuerpo="   ",
            usuario_id=admin_user.id,
        )


async def test_generar_paciente_inexistente(session, clinica, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))
    with pytest.raises(NotFoundError):
        await svc.generar(
            session, clinica.id, 999999,
            tipo="receta", cuerpo="Algo",
            usuario_id=admin_user.id,
        )
