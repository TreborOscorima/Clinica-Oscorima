"""Tests del cobro automático de un plan de tratamiento hacia Caja."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.models.caja import CajaMovimiento, Comprobante, TipoMovimiento
from clinica_app.services import planes_tratamiento as svc
from clinica_app.services.exceptions import ServiceError


async def _plan_con_items(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    i_prop = await svc.agregar_item(session, clinica.id, plan["id"], descripcion="Propuesto", precio="1000", usuario_id=admin_user.id)
    i_apr  = await svc.agregar_item(session, clinica.id, plan["id"], descripcion="Aprobado", precio="3000", usuario_id=admin_user.id)
    i_term = await svc.agregar_item(session, clinica.id, plan["id"], descripcion="Terminado", precio="2000", usuario_id=admin_user.id)
    await svc.cambiar_estado_item(session, clinica.id, plan["id"], i_apr["id"], estado="aprobado", usuario_id=admin_user.id)
    await svc.cambiar_estado_item(session, clinica.id, plan["id"], i_term["id"], estado="terminado", usuario_id=admin_user.id)
    return plan, {"propuesto": i_prop, "aprobado": i_apr, "terminado": i_term}


async def test_cobrar_plan_crea_comprobante_y_movimiento(session, clinica, paciente, admin_user):
    plan, _ = await _plan_con_items(session, clinica, paciente, admin_user)
    res = await svc.cobrar_plan(session, clinica.id, plan["id"], forma_pago="efectivo", usuario_id=admin_user.id)

    # Solo cobra aprobado (3000) + terminado (2000) = 5000; el propuesto queda afuera.
    assert res["cobrados"] == 2
    assert res["comprobante"]["total"] == "5000.00"

    comp = (await session.execute(
        select(Comprobante).where(Comprobante.clinica_id == clinica.id, Comprobante.is_active.is_(True))
    )).scalars().all()
    assert len(comp) == 1
    assert comp[0].paciente_id == paciente.id

    mov = (await session.execute(
        select(CajaMovimiento).where(CajaMovimiento.comprobante_id == comp[0].id)
    )).scalars().all()
    assert len(mov) == 1
    assert mov[0].tipo == TipoMovimiento.INGRESO
    assert mov[0].monto == Decimal("5000.00")


async def test_cobrar_plan_enlaza_items(session, clinica, paciente, admin_user):
    plan, items = await _plan_con_items(session, clinica, paciente, admin_user)
    await svc.cobrar_plan(session, clinica.id, plan["id"], usuario_id=admin_user.id)

    full = await svc.obtener_plan(session, clinica.id, plan["id"])
    by_desc = {it["descripcion"]: it for f in full["fases"] for it in f["items"]}
    assert by_desc["Aprobado"]["cobrado"] is True
    assert by_desc["Terminado"]["cobrado"] is True
    assert by_desc["Propuesto"]["cobrado"] is False
    assert full["total_cobrado"] == "5000.00"
    assert full["total_por_cobrar"] == "0.00"


async def test_cobrar_plan_excluye_propuesto_y_precio_cero(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    # Aprobado pero precio 0 → no cobrable.
    z = await svc.agregar_item(session, clinica.id, plan["id"], descripcion="Gratis", precio="0", usuario_id=admin_user.id)
    await svc.cambiar_estado_item(session, clinica.id, plan["id"], z["id"], estado="aprobado", usuario_id=admin_user.id)
    with pytest.raises(ServiceError):
        await svc.cobrar_plan(session, clinica.id, plan["id"], usuario_id=admin_user.id)


async def test_cobrar_plan_sin_elegibles(session, clinica, paciente, admin_user):
    plan = await svc.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    await svc.agregar_item(session, clinica.id, plan["id"], descripcion="Propuesto", precio="1000", usuario_id=admin_user.id)
    with pytest.raises(ServiceError):
        await svc.cobrar_plan(session, clinica.id, plan["id"], usuario_id=admin_user.id)


async def test_cobrar_plan_no_recobra(session, clinica, paciente, admin_user):
    plan, _ = await _plan_con_items(session, clinica, paciente, admin_user)
    await svc.cobrar_plan(session, clinica.id, plan["id"], usuario_id=admin_user.id)
    # Segundo intento: ya no hay pendientes.
    with pytest.raises(ServiceError):
        await svc.cobrar_plan(session, clinica.id, plan["id"], usuario_id=admin_user.id)


async def test_cobrar_plan_item_ids_filtra(session, clinica, paciente, admin_user):
    plan, items = await _plan_con_items(session, clinica, paciente, admin_user)
    # Cobra solo el aprobado (3000).
    res = await svc.cobrar_plan(
        session, clinica.id, plan["id"],
        item_ids=[items["aprobado"]["id"]], usuario_id=admin_user.id,
    )
    assert res["cobrados"] == 1
    assert res["comprobante"]["total"] == "3000.00"
    # El terminado sigue por cobrar.
    full = await svc.obtener_plan(session, clinica.id, plan["id"])
    assert full["total_por_cobrar"] == "2000.00"


async def test_cobrar_plan_audita(session, clinica, paciente, admin_user):
    plan, _ = await _plan_con_items(session, clinica, paciente, admin_user)
    await svc.cobrar_plan(session, clinica.id, plan["id"], usuario_id=admin_user.id)
    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "plan_tratamiento", AuditLog.accion == "cobrar")
    )).scalars().all()
    assert len(logs) == 1
    # cobro.crear también audita el comprobante.
    comp_logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "comprobante", AuditLog.accion == "crear")
    )).scalars().all()
    assert len(comp_logs) == 1
