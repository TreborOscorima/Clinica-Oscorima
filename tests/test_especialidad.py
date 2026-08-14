"""Tests del perfil de especialidad de la clínica (D1)."""
from __future__ import annotations

from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.models.servicio import Servicio
from clinica_app.services import especialidad as svc


# ── Mapeo rubro → especialidades ──────────────────────────────────────────────

def test_perfil_odontologia():
    assert svc.dental_activa("odontologia") is True
    assert svc.estetica_activa("odontologia") is False


def test_perfil_estetica():
    assert svc.dental_activa("clinica_estetica") is False
    assert svc.estetica_activa("clinica_estetica") is True


def test_perfil_general_ambos():
    assert svc.dental_activa("general") is True
    assert svc.estetica_activa("general") is True


def test_perfil_sin_elegir_no_oculta_nada():
    # Rubro vacío/None: para no romper clínicas existentes, ambos activos.
    for r in ("", None):
        assert svc.dental_activa(r) is True
        assert svc.estetica_activa(r) is True


def test_perfil_no_especialidad_sin_modulos():
    # Un rubro conocido que no es dental ni estético no muestra esos módulos.
    assert svc.dental_activa("consultorio_medico") is False
    assert svc.estetica_activa("consultorio_medico") is False


# ── Plantillas por rubro ──────────────────────────────────────────────────────

def test_plantillas_para_odontologia():
    claves = {op["clave"] for op in svc.plantillas_para("odontologia")}
    assert "odontologia" in claves
    assert "estetica" not in claves
    assert {"anamnesis", "evolucion"} <= claves


def test_plantillas_para_estetica():
    claves = {op["clave"] for op in svc.plantillas_para("clinica_estetica")}
    assert "estetica" in claves
    assert "odontologia" not in claves


def test_plantillas_sin_elegir_incluye_todas():
    claves = {op["clave"] for op in svc.plantillas_para("")}
    assert {"anamnesis", "evolucion", "odontologia", "estetica"} <= claves


# ── Semilla de servicios ──────────────────────────────────────────────────────

async def test_sembrar_dental(session, clinica, admin_user):
    res = await svc.sembrar_servicios(session, clinica.id, "odontologia", usuario_id=admin_user.id)
    assert res["creados"] == len(svc.SERVICIOS_SEMILLA["dental"])
    servicios = (await session.execute(
        select(Servicio).where(Servicio.clinica_id == clinica.id, Servicio.is_active.is_(True))
    )).scalars().all()
    nombres = {s.nombre for s in servicios}
    assert "Consulta odontológica" in nombres
    # No sembró estéticos.
    assert "Consulta estética" not in nombres


async def test_sembrar_es_idempotente(session, clinica, admin_user):
    await svc.sembrar_servicios(session, clinica.id, "odontologia", usuario_id=admin_user.id)
    res2 = await svc.sembrar_servicios(session, clinica.id, "odontologia", usuario_id=admin_user.id)
    assert res2["creados"] == 0
    n = (await session.execute(
        select(Servicio).where(Servicio.clinica_id == clinica.id, Servicio.is_active.is_(True))
    )).scalars().all()
    assert len(n) == len(svc.SERVICIOS_SEMILLA["dental"])


async def test_sembrar_respeta_existentes(session, clinica, admin_user):
    # Ya existe un servicio con el mismo nombre (distinta capitalización).
    from decimal import Decimal
    session.add(Servicio(clinica_id=clinica.id, nombre="consulta odontológica", precio=Decimal("500")))
    await session.flush()
    res = await svc.sembrar_servicios(session, clinica.id, "odontologia", usuario_id=admin_user.id)
    assert res["creados"] == len(svc.SERVICIOS_SEMILLA["dental"]) - 1


async def test_sembrar_general_ambas_especialidades(session, clinica, admin_user):
    res = await svc.sembrar_servicios(session, clinica.id, "general", usuario_id=admin_user.id)
    esperado = len(svc.SERVICIOS_SEMILLA["dental"]) + len(svc.SERVICIOS_SEMILLA["estetica"])
    assert res["creados"] == esperado


async def test_sembrar_no_especialidad_no_crea(session, clinica, admin_user):
    res = await svc.sembrar_servicios(session, clinica.id, "consultorio_medico", usuario_id=admin_user.id)
    assert res["creados"] == 0


async def test_sembrar_registra_auditoria(session, clinica, admin_user):
    await svc.sembrar_servicios(session, clinica.id, "odontologia", usuario_id=admin_user.id)
    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "servicio", AuditLog.accion == "sembrar_catalogo")
    )).scalars().all()
    assert len(logs) == 1


async def test_rubro_de(session, clinica, admin_user):
    clinica.rubro = "odontologia"
    await session.flush()
    assert await svc.rubro_de(session, clinica.id) == "odontologia"
