"""Tests de consentimiento informado (A4).

Cubren las plantillas, la generación de bytes del PDF y la orquestación completa
(genera → archiva como adjunto → auditoría). El almacenamiento se redirige a un
directorio temporal para no ensuciar ./uploads.
"""
from __future__ import annotations

import os

import pytest
from sqlmodel import select

from clinica_app.models.adjunto import Adjunto
from clinica_app.models.audit_log import AuditLog
from clinica_app.services import consentimientos as svc
from clinica_app.services import plantillas_consentimiento as plantillas
from clinica_app.services import storage
from clinica_app.services.exceptions import NotFoundError
from clinica_app.services.pdf_consentimiento import generar_consentimiento_pdf


# ── Plantillas ───────────────────────────────────────────────────────────────

def test_plantillas_opciones_cubren_rubros():
    claves = {o["clave"] for o in plantillas.opciones()}
    assert {"general", "estetica", "odontologia"} <= claves


def test_cuerpo_reemplaza_procedimiento():
    txt = plantillas.cuerpo("estetica", "limpieza facial profunda")
    assert "limpieza facial profunda" in txt
    assert "{procedimiento}" not in txt


def test_cuerpo_tipo_desconocido_cae_en_general():
    # No debe romper: cae en la plantilla por defecto.
    assert plantillas.cuerpo("no-existe", "algo") != ""
    assert plantillas.titulo("no-existe") == plantillas.titulo("general")


# ── PDF (bytes, sin disco) ───────────────────────────────────────────────────

def test_pdf_devuelve_bytes_validos():
    data = generar_consentimiento_pdf(
        clinica_nombre="Clínica Test",
        titulo="Consentimiento informado",
        cuerpo="Párrafo uno.\n\nPárrafo dos.",
        paciente_nombre="Juan Pérez",
        paciente_documento="12345678",
        procedimiento="Extracción simple",
        profesional_nombre="Dra. Gómez",
    )
    assert isinstance(data, bytes)
    assert data[:5] == b"%PDF-"
    assert len(data) > 1000


# ── Orquestación completa ────────────────────────────────────────────────────

async def test_generar_crea_adjunto_consentimiento(session, clinica, paciente, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))

    dump = await svc.generar(
        session, clinica.id, paciente.id,
        tipo="odontologia",
        procedimiento="Endodoncia pieza 26",
        profesional_nombre="Dr. Ruiz M.P. 1234",
        usuario_id=admin_user.id,
    )

    assert dump["categoria"] == "consentimiento"
    assert dump["nombre"].endswith(".pdf")
    assert dump["tamano"] > 0

    # La fila quedó en adjuntos, ligada al paciente.
    adj = (await session.execute(
        select(Adjunto).where(Adjunto.id == dump["id"])
    )).scalars().first()
    assert adj is not None
    assert adj.paciente_id == paciente.id
    assert adj.mime == "application/pdf"

    # El archivo físico existe en el directorio temporal.
    path = storage.ruta_absoluta(clinica.id, adj.stored_name)
    assert os.path.isfile(path)


async def test_generar_registra_auditoria(session, clinica, paciente, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))

    dump = await svc.generar(
        session, clinica.id, paciente.id,
        tipo="general", procedimiento="Procedimiento X",
        usuario_id=admin_user.id,
    )

    logs = (await session.execute(
        select(AuditLog).where(
            AuditLog.entidad == "consentimiento",
            AuditLog.accion == "generar",
        )
    )).scalars().all()
    assert len(logs) == 1
    assert logs[0].entidad_id == dump["id"]


async def test_generar_paciente_inexistente(session, clinica, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))
    with pytest.raises(NotFoundError):
        await svc.generar(
            session, clinica.id, 999999,
            tipo="general", procedimiento="X",
            usuario_id=admin_user.id,
        )
