"""Tests del odontograma (B1)."""
from __future__ import annotations

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.services import odontograma as svc
from clinica_app.services.exceptions import NotFoundError, ValidationError


# ── Catálogos / layout ───────────────────────────────────────────────────────

def test_layout_tiene_32_piezas():
    lay = svc.layout()
    assert len(lay["superior"]) == 16
    assert len(lay["inferior"]) == 16
    assert len(svc.PIEZAS_VALIDAS) == 32
    # No hay solapamiento entre arcadas.
    assert set(lay["superior"]).isdisjoint(set(lay["inferior"]))


def test_estados_catalogo_incluye_claves_clinicas():
    claves = {e["clave"] for e in svc.estados_catalogo()}
    assert {"sano", "caries", "obturado", "corona", "ausente", "implante"} <= claves


# ── listar ───────────────────────────────────────────────────────────────────

async def test_listar_arcada_completa_sana(session, clinica, paciente):
    data = await svc.listar(session, clinica.id, paciente.id)
    assert len(data["superior"]) == 16
    assert len(data["inferior"]) == 16
    assert all(p["estado"] == "sano" for p in data["superior"] + data["inferior"])
    assert data["resumen"] == {}
    assert data["con_datos"] == 0


# ── guardar_pieza (upsert) ───────────────────────────────────────────────────

async def test_guardar_pieza_crea(session, clinica, paciente, admin_user):
    r = await svc.guardar_pieza(
        session, clinica.id, paciente.id, "16",
        estado="caries", nota="Cara oclusal", usuario_id=admin_user.id,
    )
    assert r["numero"] == "16"
    assert r["estado"] == "caries"
    assert r["estado_label"] == "Caries"

    data = await svc.listar(session, clinica.id, paciente.id)
    pieza16 = next(p for p in data["superior"] if p["numero"] == "16")
    assert pieza16["estado"] == "caries"
    assert data["resumen"].get("caries") == 1
    assert data["con_datos"] == 1


async def test_guardar_pieza_actualiza_no_duplica(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="obturado", usuario_id=admin_user.id)

    from clinica_app.models.pieza_dental import PiezaDental
    filas = (await session.execute(
        select(PiezaDental).where(
            PiezaDental.paciente_id == paciente.id,
            PiezaDental.numero == "16",
            PiezaDental.is_active.is_(True),
        )
    )).scalars().all()
    assert len(filas) == 1
    assert filas[0].estado == "obturado"


async def test_guardar_pieza_con_caras(session, clinica, paciente, admin_user):
    r = await svc.guardar_pieza(
        session, clinica.id, paciente.id, "26",
        estado="obturado",
        caras={"oclusal": "obturado", "mesial": "caries", "zzz": "caries", "vestibular": "inexistente"},
        usuario_id=admin_user.id,
    )
    # Solo caras y estados válidos sobreviven.
    assert r["caras"] == {"oclusal": "obturado", "mesial": "caries"}


async def test_guardar_pieza_revive_tras_resetear(session, clinica, paciente, admin_user):
    """Regresión: resetear una pieza (soft-delete) y volver a marcarla no debe
    chocar con el UniqueConstraint (clinica, paciente, numero); la fila muerta se
    revive en lugar de insertar una nueva."""
    from clinica_app.models.pieza_dental import PiezaDental

    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    await svc.resetear_pieza(session, clinica.id, paciente.id, "16", usuario_id=admin_user.id)
    # Volver a marcarla NO lanza IntegrityError y queda con el nuevo estado.
    r = await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="obturado", usuario_id=admin_user.id)
    assert r["estado"] == "obturado"

    data = await svc.listar(session, clinica.id, paciente.id)
    pieza16 = next(p for p in data["superior"] if p["numero"] == "16")
    assert pieza16["estado"] == "obturado"

    # No quedan filas duplicadas para esa pieza.
    filas = (await session.execute(
        select(PiezaDental).where(
            PiezaDental.paciente_id == paciente.id,
            PiezaDental.numero == "16",
        )
    )).scalars().all()
    assert len(filas) == 1
    assert filas[0].is_active is True


async def test_listar_incluye_superficies(session, clinica, paciente, admin_user):
    """Cada pieza trae las 5 superficies ya resueltas (color/estado) para la grilla 2D."""
    await svc.guardar_pieza(
        session, clinica.id, paciente.id, "26",
        estado="obturado",
        caras={"oclusal": "obturado", "mesial": "caries"},
        usuario_id=admin_user.id,
    )
    data = await svc.listar(session, clinica.id, paciente.id)
    p26 = next(p for p in data["superior"] if p["numero"] == "26")
    assert len(p26["superficies"]) == 5
    by = {s["cara"]: s for s in p26["superficies"]}
    assert by["oclusal"]["tiene"] is True
    assert by["oclusal"]["color"] == svc.ESTADOS["obturado"]["color"]
    assert by["mesial"]["color"] == svc.ESTADOS["caries"]["color"]
    assert by["vestibular"]["tiene"] is False
    assert by["vestibular"]["color"] == "#ffffff"


async def test_guardar_pieza_estado_invalido(session, clinica, paciente, admin_user):
    with pytest.raises(ValidationError):
        await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="marciano", usuario_id=admin_user.id)


async def test_guardar_pieza_numero_invalido(session, clinica, paciente, admin_user):
    with pytest.raises(ValidationError):
        await svc.guardar_pieza(session, clinica.id, paciente.id, "99", estado="caries", usuario_id=admin_user.id)


async def test_guardar_pieza_registra_auditoria(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "pieza_dental", AuditLog.accion == "editar")
    )).scalars().all()
    assert len(logs) == 1


# ── resetear_pieza ───────────────────────────────────────────────────────────

async def test_resetear_pieza(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    r = await svc.resetear_pieza(session, clinica.id, paciente.id, "16", usuario_id=admin_user.id)
    assert r["estado"] == "sano"

    data = await svc.listar(session, clinica.id, paciente.id)
    assert data["con_datos"] == 0


async def test_resetear_pieza_sin_datos(session, clinica, paciente, admin_user):
    with pytest.raises(NotFoundError):
        await svc.resetear_pieza(session, clinica.id, paciente.id, "16", usuario_id=admin_user.id)


# ── aislamiento por paciente ─────────────────────────────────────────────────

async def test_odontograma_aislado_por_paciente(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    # Otro paciente no ve la marca.
    data_otro = await svc.listar(session, clinica.id, paciente.id + 9999)
    assert data_otro["con_datos"] == 0
