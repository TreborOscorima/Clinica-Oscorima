"""Tests de la ficha de tratamiento estético (C2): ficha + insumos."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.models.sesion_estetica import SesionInsumo
from clinica_app.services import sesiones_esteticas as svc
from clinica_app.services.exceptions import NotFoundError, ValidationError


async def _sesion(session, clinica, paciente, admin_user):
    return await svc.crear_sesion(
        session, clinica.id, paciente.id,
        fecha="2026-08-10", titulo="Botox", zona="Frente", usuario_id=admin_user.id,
    )


async def _producto(session, clinica, nombre="Toxina botulínica", stock="50"):
    from clinica_app.models.inventario import Producto
    p = Producto(clinica_id=clinica.id, nombre=nombre, stock_actual=Decimal(stock))
    session.add(p)
    await session.flush()
    return p


# ── Ficha (campos de la sesión) ───────────────────────────────────────────────

async def test_actualizar_ficha(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    await svc.actualizar_sesion(
        session, clinica.id, s["id"],
        numero_sesion="2", parametros="50 UI, 5 puntos", proxima="2026-09-10",
        usuario_id=admin_user.id,
    )
    full = await svc.obtener_sesion(session, clinica.id, s["id"])
    assert full["numero_sesion"] == 2
    assert full["parametros"] == "50 UI, 5 puntos"
    assert full["proxima"] == "2026-09-10"
    assert full["proxima_fmt"] == "10/09/2026"


async def test_proxima_vacia_queda_none(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    await svc.actualizar_sesion(session, clinica.id, s["id"], proxima="", usuario_id=admin_user.id)
    full = await svc.obtener_sesion(session, clinica.id, s["id"])
    assert full["proxima"] == ""


async def test_proxima_invalida(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    with pytest.raises(ValidationError):
        await svc.actualizar_sesion(session, clinica.id, s["id"], proxima="10/09/2026", usuario_id=admin_user.id)


# ── Insumos ───────────────────────────────────────────────────────────────────

async def test_agregar_insumo_manual(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    i = await svc.agregar_insumo(
        session, clinica.id, s["id"],
        descripcion="Ácido hialurónico", cantidad="1.5", unidad="ml",
        usuario_id=admin_user.id,
    )
    assert i["descripcion"] == "Ácido hialurónico"
    assert i["cantidad"] == "1.5"
    assert i["unidad"] == "ml"


async def test_agregar_insumo_hereda_nombre_producto(session, clinica, paciente, admin_user):
    prod = await _producto(session, clinica, nombre="Toxina botulínica")
    s = await _sesion(session, clinica, paciente, admin_user)
    i = await svc.agregar_insumo(
        session, clinica.id, s["id"],
        descripcion="", producto_id=prod.id, cantidad="50", unidad="UI",
        usuario_id=admin_user.id,
    )
    assert i["descripcion"] == "Toxina botulínica"
    assert i["producto_id"] == prod.id


async def test_agregar_insumo_producto_inexistente(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    with pytest.raises(NotFoundError):
        await svc.agregar_insumo(session, clinica.id, s["id"], descripcion="x", producto_id=999999, usuario_id=admin_user.id)


async def test_agregar_insumo_descripcion_obligatoria(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    with pytest.raises(ValidationError):
        await svc.agregar_insumo(session, clinica.id, s["id"], descripcion="   ", usuario_id=admin_user.id)


async def test_agregar_insumo_cantidad_negativa(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    with pytest.raises(ValidationError):
        await svc.agregar_insumo(session, clinica.id, s["id"], descripcion="x", cantidad="-3", usuario_id=admin_user.id)


async def test_insumos_en_obtener_sesion(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    await svc.agregar_insumo(session, clinica.id, s["id"], descripcion="A", cantidad="1", unidad="ml", usuario_id=admin_user.id)
    await svc.agregar_insumo(session, clinica.id, s["id"], descripcion="B", cantidad="2", unidad="UI", usuario_id=admin_user.id)
    full = await svc.obtener_sesion(session, clinica.id, s["id"])
    assert len(full["insumos"]) == 2
    assert {i["descripcion"] for i in full["insumos"]} == {"A", "B"}


async def test_eliminar_insumo(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    i = await svc.agregar_insumo(session, clinica.id, s["id"], descripcion="X", cantidad="1", usuario_id=admin_user.id)
    await svc.eliminar_insumo(session, clinica.id, i["id"], usuario_id=admin_user.id)
    full = await svc.obtener_sesion(session, clinica.id, s["id"])
    assert full["insumos"] == []


async def test_eliminar_sesion_da_de_baja_insumos(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    await svc.agregar_insumo(session, clinica.id, s["id"], descripcion="X", cantidad="1", usuario_id=admin_user.id)
    await svc.eliminar_sesion(session, clinica.id, s["id"], usuario_id=admin_user.id)
    activos = (await session.execute(
        select(SesionInsumo).where(SesionInsumo.sesion_id == s["id"], SesionInsumo.is_active.is_(True))
    )).scalars().all()
    assert activos == []


async def test_auditoria_insumos(session, clinica, paciente, admin_user):
    s = await _sesion(session, clinica, paciente, admin_user)
    i = await svc.agregar_insumo(session, clinica.id, s["id"], descripcion="X", cantidad="1", usuario_id=admin_user.id)
    await svc.eliminar_insumo(session, clinica.id, i["id"], usuario_id=admin_user.id)
    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "sesion_estetica")
    )).scalars().all()
    acciones = {log.accion for log in logs}
    assert "agregar_insumo" in acciones
    assert "eliminar_insumo" in acciones
