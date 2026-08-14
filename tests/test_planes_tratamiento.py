"""Tests del plan de tratamiento por fases + presupuesto (B2)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.models.plan_tratamiento import PlanTratamientoItem
from clinica_app.services import planes_tratamiento as svc
from clinica_app.services.exceptions import NotFoundError, ValidationError


async def _servicio(session, clinica, nombre="Corona porcelana", precio="15000.00"):
    from clinica_app.models.servicio import Servicio
    s = Servicio(clinica_id=clinica.id, nombre=nombre, precio=Decimal(precio))
    session.add(s)
    await session.flush()
    return s


# ── Catálogos ─────────────────────────────────────────────────────────────────

def test_catalogos_estado():
    planes = {e["clave"] for e in svc.estados_plan_catalogo()}
    items = {e["clave"] for e in svc.estados_item_catalogo()}
    assert {"borrador", "aprobado", "en_curso", "terminado", "cancelado"} <= planes
    assert {"propuesto", "aprobado", "en_curso", "terminado"} <= items


# ── crear_plan ────────────────────────────────────────────────────────────────

async def test_crear_plan(session, clinica, paciente, admin_user):
    p = await svc.crear_plan(
        session, clinica.id, paciente.id,
        titulo="Rehabilitación superior", usuario_id=admin_user.id,
    )
    assert p["id"] > 0
    assert p["titulo"] == "Rehabilitación superior"
    assert p["estado"] == "borrador"
    assert p["total"] == "0.00"
    assert p["n_items"] == 0


async def test_crear_plan_titulo_obligatorio(session, clinica, paciente, admin_user):
    with pytest.raises(ValidationError):
        await svc.crear_plan(session, clinica.id, paciente.id, titulo="   ", usuario_id=admin_user.id)


async def test_crear_plan_paciente_inexistente(session, clinica, admin_user):
    with pytest.raises(NotFoundError):
        await svc.crear_plan(session, clinica.id, 999999, titulo="X", usuario_id=admin_user.id)


# ── agregar_item ──────────────────────────────────────────────────────────────

async def test_agregar_item_manual(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    it = await svc.agregar_item(
        session, clinica.id, plan["id"],
        descripcion="Extracción 18", fase=1, pieza_numero="18", precio="8000",
        usuario_id=admin_user.id,
    )
    assert it["descripcion"] == "Extracción 18"
    assert it["pieza_numero"] == "18"
    assert it["precio"] == "8000.00"
    assert it["estado"] == "propuesto"
    assert it["orden"] == 1


async def test_agregar_item_hereda_precio_y_nombre_del_servicio(session, clinica, paciente, admin_user):
    serv = await _servicio(session, clinica, nombre="Corona", precio="15000.00")
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    # Sin descripción ni precio → los hereda del servicio.
    it = await svc.agregar_item(
        session, clinica.id, plan["id"],
        descripcion="", servicio_id=serv.id, usuario_id=admin_user.id,
    )
    assert it["descripcion"] == "Corona"
    assert it["precio"] == "15000.00"
    assert it["servicio_id"] == serv.id


async def test_agregar_item_servicio_inexistente(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    with pytest.raises(NotFoundError):
        await svc.agregar_item(
            session, clinica.id, plan["id"],
            descripcion="x", servicio_id=999999, usuario_id=admin_user.id,
        )


async def test_agregar_item_descripcion_obligatoria(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    with pytest.raises(ValidationError):
        await svc.agregar_item(session, clinica.id, plan["id"], descripcion="   ", usuario_id=admin_user.id)


async def test_agregar_item_precio_negativo(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    with pytest.raises(ValidationError):
        await svc.agregar_item(session, clinica.id, plan["id"], descripcion="x", precio="-5", usuario_id=admin_user.id)


# ── totales / avance ──────────────────────────────────────────────────────────

async def test_totales_y_avance(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    i1 = await svc.agregar_item(session, clinica.id, plan["id"], descripcion="A", precio="1000", usuario_id=admin_user.id)
    i2 = await svc.agregar_item(session, clinica.id, plan["id"], descripcion="B", precio="3000", usuario_id=admin_user.id)
    await svc.agregar_item(session, clinica.id, plan["id"], descripcion="C", precio="1000", usuario_id=admin_user.id)

    # Marca 2 de 3 como terminado (uno aprobado en el medio).
    await svc.cambiar_estado_item(session, clinica.id, plan["id"], i1["id"], estado="terminado", usuario_id=admin_user.id)
    await svc.cambiar_estado_item(session, clinica.id, plan["id"], i2["id"], estado="aprobado", usuario_id=admin_user.id)

    full = await svc.obtener_plan(session, clinica.id, plan["id"])
    assert full["total"] == "5000.00"
    assert full["total_aprobado"] == "4000.00"   # i1 terminado + i2 aprobado
    assert full["total_terminado"] == "1000.00"  # solo i1
    assert full["n_items"] == 3
    assert full["avance"] == 33                   # 1 de 3 terminado


# ── obtener_plan agrupa por fase ──────────────────────────────────────────────

async def test_obtener_plan_agrupa_por_fase(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    await svc.agregar_item(session, clinica.id, plan["id"], descripcion="Fase1-a", fase=1, precio="100", usuario_id=admin_user.id)
    await svc.agregar_item(session, clinica.id, plan["id"], descripcion="Fase2-a", fase=2, precio="200", usuario_id=admin_user.id)
    await svc.agregar_item(session, clinica.id, plan["id"], descripcion="Fase1-b", fase=1, precio="50", usuario_id=admin_user.id)

    full = await svc.obtener_plan(session, clinica.id, plan["id"])
    fases = full["fases"]
    assert [f["fase"] for f in fases] == [1, 2]
    assert len(fases[0]["items"]) == 2
    assert fases[0]["subtotal"] == "150.00"
    assert fases[1]["subtotal"] == "200.00"


# ── actualizar_plan ───────────────────────────────────────────────────────────

async def test_actualizar_plan_estado(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    upd = await svc.actualizar_plan(session, clinica.id, plan["id"], estado="aprobado", usuario_id=admin_user.id)
    assert upd["estado"] == "aprobado"


async def test_actualizar_plan_estado_invalido(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    with pytest.raises(ValidationError):
        await svc.actualizar_plan(session, clinica.id, plan["id"], estado="volando", usuario_id=admin_user.id)


async def test_cambiar_estado_item_invalido(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    it = await svc.agregar_item(session, clinica.id, plan["id"], descripcion="x", precio="1", usuario_id=admin_user.id)
    with pytest.raises(ValidationError):
        await svc.cambiar_estado_item(session, clinica.id, plan["id"], it["id"], estado="marciano", usuario_id=admin_user.id)


# ── eliminar ──────────────────────────────────────────────────────────────────

async def test_eliminar_item(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    it = await svc.agregar_item(session, clinica.id, plan["id"], descripcion="x", precio="500", usuario_id=admin_user.id)
    await svc.eliminar_item(session, clinica.id, plan["id"], it["id"], usuario_id=admin_user.id)
    full = await svc.obtener_plan(session, clinica.id, plan["id"])
    assert full["n_items"] == 0


async def test_eliminar_plan_soft_delete_cascada(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    await svc.agregar_item(session, clinica.id, plan["id"], descripcion="x", precio="500", usuario_id=admin_user.id)
    await svc.eliminar_plan(session, clinica.id, plan["id"], usuario_id=admin_user.id)

    # El plan ya no aparece.
    planes = await svc.listar_planes(session, clinica.id, paciente.id)
    assert planes == []
    # Sus items quedaron inactivos.
    activos = (await session.execute(
        select(PlanTratamientoItem).where(
            PlanTratamientoItem.plan_id == plan["id"],
            PlanTratamientoItem.is_active.is_(True),
        )
    )).scalars().all()
    assert activos == []
    # El plan eliminado no se puede obtener.
    with pytest.raises(NotFoundError):
        await svc.obtener_plan(session, clinica.id, plan["id"])


# ── auditoría ─────────────────────────────────────────────────────────────────

async def test_auditoria_registrada(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    await svc.agregar_item(session, clinica.id, plan["id"], descripcion="x", precio="1", usuario_id=admin_user.id)
    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "plan_tratamiento")
    )).scalars().all()
    acciones = {log.accion for log in logs}
    assert "crear" in acciones
    assert "agregar_item" in acciones


# ── aislamiento por paciente ──────────────────────────────────────────────────

async def test_planes_aislados_por_paciente(session, clinica, paciente, admin_user):
    await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan A", usuario_id=admin_user.id)
    otros = await svc.listar_planes(session, clinica.id, paciente.id + 9999)
    assert otros == []
