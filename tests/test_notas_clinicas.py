"""Tests de notas clínicas: firma/bloqueo (A3) y plantillas."""
from __future__ import annotations

import pytest

from clinica_app.services import notas_clinicas as svc
from clinica_app.services import plantillas_nota
from clinica_app.services.exceptions import ConflictError


async def _crear_nota(session, clinica, paciente, contenido="Evolución inicial"):
    return await svc.crear(
        session, clinica.id,
        {"paciente_id": paciente.id, "tipo": "evolucion", "contenido": contenido},
    )


# ── Firma / bloqueo ──────────────────────────────────────────────────────────

async def test_nota_nace_sin_firmar(session, clinica, paciente):
    n = await _crear_nota(session, clinica, paciente)
    assert n["firmada"] is False
    assert n["firmada_en"] == ""


async def test_firmar_nota(session, clinica, paciente, admin_user):
    n = await _crear_nota(session, clinica, paciente)
    firmada = await svc.firmar(session, clinica.id, n["id"], usuario_id=admin_user.id)
    assert firmada["firmada"] is True
    assert firmada["firmada_en"] != ""
    assert firmada["firmada_por_nombre"] == "Admin"


async def test_no_se_puede_refirmar(session, clinica, paciente, admin_user):
    n = await _crear_nota(session, clinica, paciente)
    await svc.firmar(session, clinica.id, n["id"], usuario_id=admin_user.id)
    with pytest.raises(ConflictError):
        await svc.firmar(session, clinica.id, n["id"], usuario_id=admin_user.id)


async def test_nota_firmada_no_se_edita(session, clinica, paciente, admin_user):
    n = await _crear_nota(session, clinica, paciente)
    await svc.firmar(session, clinica.id, n["id"], usuario_id=admin_user.id)
    with pytest.raises(ConflictError):
        await svc.actualizar(session, clinica.id, n["id"], {"contenido": "Cambio prohibido"})


async def test_nota_firmada_no_se_elimina(session, clinica, paciente, admin_user):
    n = await _crear_nota(session, clinica, paciente)
    await svc.firmar(session, clinica.id, n["id"], usuario_id=admin_user.id)
    with pytest.raises(ConflictError):
        await svc.eliminar(session, clinica.id, n["id"])


async def test_nota_sin_firmar_si_se_edita(session, clinica, paciente):
    n = await _crear_nota(session, clinica, paciente)
    actualizada = await svc.actualizar(session, clinica.id, n["id"], {"contenido": "Editada OK"})
    assert actualizada["contenido"] == "Editada OK"


async def test_firmar_registra_auditoria(session, clinica, paciente, admin_user):
    from sqlmodel import select

    from clinica_app.models.audit_log import AuditLog

    n = await _crear_nota(session, clinica, paciente)
    await svc.firmar(session, clinica.id, n["id"], usuario_id=admin_user.id)

    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "nota_clinica", AuditLog.accion == "firmar")
    )).scalars().all()
    assert len(logs) == 1
    assert logs[0].entidad_id == n["id"]


# ── Plantillas ───────────────────────────────────────────────────────────────

def test_plantillas_opciones_no_vacio():
    ops = plantillas_nota.opciones()
    claves = {o["clave"] for o in ops}
    assert {"anamnesis", "evolucion", "odontologia", "estetica"} <= claves


def test_plantilla_contenido_conocida():
    assert "Pieza(s)" in plantillas_nota.contenido("odontologia")
    assert plantillas_nota.contenido("inexistente") == ""
