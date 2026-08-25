"""Anulación de venta: reversión atómica y auditada del cobro.

Anular un comprobante debe (a) dar de baja el ingreso de caja, (b) reponer el
stock de los productos vendidos, (c) cancelar la deuda si fue en cuotas, (d)
marcar el comprobante ANULADO sin borrarlo y (e) dejar rastro en el audit log.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.models.caja import CajaMovimiento, DeudaPaciente, TipoMovimiento
from clinica_app.services import cobro as svc
from clinica_app.services.exceptions import ConflictError, ServiceError


def _payload(paciente_id: int, items=None, **extra) -> dict:
    base = {
        "paciente_id": paciente_id,
        "items": items or [
            {"tipo": "servicio", "ref_id": 1, "nombre": "Consulta",
             "cantidad": "1", "precio_unit": "100.00"},
        ],
        "forma_pago":       "efectivo",
        "descuento_global": "0",
        "es_cuotas":        False,
        "num_cuotas":       1,
        "cuota_inicial":    "0",
    }
    base.update(extra)
    return base


async def _ingresos_activos(session, comp_id: int):
    return (await session.execute(
        select(CajaMovimiento).where(
            CajaMovimiento.comprobante_id == comp_id,
            CajaMovimiento.tipo == TipoMovimiento.INGRESO,
            CajaMovimiento.is_active.is_(True),
        )
    )).scalars().all()


async def _producto(session, clinica, stock="10"):
    from clinica_app.models.inventario import Producto
    p = Producto(clinica_id=clinica.id, nombre="Ácido hialurónico",
                 precio_venta=Decimal("50.00"), stock_actual=Decimal(stock))
    session.add(p)
    await session.flush()
    return p


# ── Reversión de caja ─────────────────────────────────────────────────────────

async def test_anular_revierte_caja(session, clinica, paciente, admin_user):
    res = await svc.crear(session, clinica.id, _payload(paciente.id), usuario_id=admin_user.id)
    assert len(await _ingresos_activos(session, res["id"])) == 1

    out = await svc.anular(session, clinica.id, res["id"], motivo="error de monto",
                           usuario_id=admin_user.id)
    assert out["anulado"] is True
    assert out["anulado_motivo"] == "error de monto"
    # El ingreso ya no cuenta en caja.
    assert await _ingresos_activos(session, res["id"]) == []


async def test_anular_repone_stock(session, clinica, paciente, admin_user):
    from clinica_app.models.inventario import MovimientoStock
    prod = await _producto(session, clinica, stock="10")
    items = [{"tipo": "producto", "ref_id": prod.id, "nombre": prod.nombre,
              "cantidad": "2", "precio_unit": "50.00"}]

    res = await svc.crear(session, clinica.id, _payload(paciente.id, items=items),
                          usuario_id=admin_user.id)
    await session.refresh(prod)
    assert prod.stock_actual == Decimal("8.000")   # 10 - 2

    await svc.anular(session, clinica.id, res["id"], motivo="devolución", usuario_id=admin_user.id)
    await session.refresh(prod)
    assert prod.stock_actual == Decimal("10.000")  # repuesto

    movs = (await session.execute(
        select(MovimientoStock).where(
            MovimientoStock.producto_id == prod.id,
            MovimientoStock.tipo == "ingreso",
        )
    )).scalars().all()
    assert any(m.referencia == f"anul:{res['id']}" for m in movs)


async def test_anular_cancela_deuda(session, clinica, paciente, admin_user):
    res = await svc.crear(
        session, clinica.id,
        _payload(paciente.id, es_cuotas=True, num_cuotas=3, cuota_inicial="10"),
        usuario_id=admin_user.id,
    )
    deuda = (await session.execute(
        select(DeudaPaciente).where(DeudaPaciente.comprobante_id == res["id"])
    )).scalars().first()
    assert deuda is not None and deuda.is_active

    await svc.anular(session, clinica.id, res["id"], motivo="anulación", usuario_id=admin_user.id)
    await session.refresh(deuda)
    assert deuda.is_active is False
    assert deuda.estado == "anulado"
    assert deuda.saldo == Decimal("0")


# ── Validaciones ──────────────────────────────────────────────────────────────

async def test_anular_requiere_motivo(session, clinica, paciente, admin_user):
    res = await svc.crear(session, clinica.id, _payload(paciente.id), usuario_id=admin_user.id)
    with pytest.raises(ServiceError):
        await svc.anular(session, clinica.id, res["id"], motivo="   ", usuario_id=admin_user.id)


async def test_anular_dos_veces_conflicto(session, clinica, paciente, admin_user):
    res = await svc.crear(session, clinica.id, _payload(paciente.id), usuario_id=admin_user.id)
    await svc.anular(session, clinica.id, res["id"], motivo="uno", usuario_id=admin_user.id)
    with pytest.raises(ConflictError):
        await svc.anular(session, clinica.id, res["id"], motivo="dos", usuario_id=admin_user.id)


async def test_anular_comprobante_inexistente(session, clinica, admin_user):
    with pytest.raises(ServiceError):
        await svc.anular(session, clinica.id, 99999, motivo="x", usuario_id=admin_user.id)


# ── Rastro ────────────────────────────────────────────────────────────────────

async def test_anular_audita(session, clinica, paciente, admin_user):
    res = await svc.crear(session, clinica.id, _payload(paciente.id), usuario_id=admin_user.id)
    await svc.anular(session, clinica.id, res["id"], motivo="cobro duplicado",
                     usuario_id=admin_user.id)
    filas = (await session.execute(
        select(AuditLog).where(
            AuditLog.clinica_id == clinica.id,
            AuditLog.accion == "anular",
            AuditLog.entidad == "comprobante",
        )
    )).scalars().all()
    assert len(filas) == 1
    assert filas[0].entidad_id == res["id"]


async def test_anulado_sigue_visible_en_listar(session, clinica, paciente, admin_user):
    res = await svc.crear(session, clinica.id, _payload(paciente.id), usuario_id=admin_user.id)
    await svc.anular(session, clinica.id, res["id"], motivo="x", usuario_id=admin_user.id)
    listado = await svc.listar(session, clinica.id)
    fila = next((c for c in listado["data"] if c["id"] == res["id"]), None)
    assert fila is not None            # no desaparece
    assert fila["anulado"] is True
