"""Tests de la bitácora de auditoría (registro directo + rastro de las
operaciones sensibles: cobro, cierre de caja, borrado de movimiento, anulación)."""
from __future__ import annotations

from sqlalchemy import func
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.services import auditoria
from clinica_app.services import caja as caja_svc
from clinica_app.services import cobro as cobro_svc
from clinica_app.services import compras as compras_svc
from clinica_app.services import inventario as inv_svc


async def _audits(session, clinica_id, entidad=None):
    stmt = select(AuditLog).where(AuditLog.clinica_id == clinica_id)
    if entidad is not None:
        stmt = stmt.where(AuditLog.entidad == entidad)
    return (await session.execute(stmt)).scalars().all()


def _cobro_payload(paciente_id):
    return {
        "paciente_id": paciente_id,
        "items": [{"tipo": "servicio", "ref_id": 1, "nombre": "Consulta",
                   "cantidad": "1", "precio_unit": "100.00"}],
        "forma_pago": "efectivo", "descuento_global": "0",
        "es_cuotas": False, "num_cuotas": 1, "cuota_inicial": "0",
    }


# ── Servicio directo ─────────────────────────────────────────────────────────

async def test_registrar_crea_fila(session, clinica):
    await auditoria.registrar(
        session, clinica.id, usuario_id=7,
        accion="crear", entidad="comprobante", entidad_id=42,
        detalle={"total": "100.00"},
    )
    filas = await _audits(session, clinica.id)
    assert len(filas) == 1
    a = filas[0]
    assert a.usuario_id == 7
    assert a.accion == "crear"
    assert a.entidad == "comprobante"
    assert a.entidad_id == 42
    assert '"total": "100.00"' in a.detalle  # detalle dict → JSON


async def test_registrar_detalle_string(session, clinica):
    await auditoria.registrar(
        session, clinica.id, accion="x", entidad="y", detalle="texto plano"
    )
    a = (await _audits(session, clinica.id))[0]
    assert a.detalle == "texto plano"
    assert a.usuario_id is None  # opcional


# ── Rastro de operaciones sensibles ──────────────────────────────────────────

async def test_cobro_deja_auditoria(session, clinica, paciente, admin_user):
    await cobro_svc.crear(session, clinica.id, _cobro_payload(paciente.id), usuario_id=admin_user.id)
    filas = await _audits(session, clinica.id, entidad="comprobante")
    assert len(filas) == 1
    assert filas[0].accion == "crear"
    assert filas[0].usuario_id == admin_user.id


async def test_cierre_caja_deja_auditoria(session, clinica, admin_user):
    await caja_svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "50"})
    await caja_svc.realizar_cierre_dia(session, clinica.id, usuario_id=admin_user.id)
    filas = await _audits(session, clinica.id, entidad="cierre_caja")
    assert len(filas) == 1
    assert filas[0].accion == "cerrar_caja"


async def test_eliminar_movimiento_deja_auditoria(session, clinica, admin_user):
    mov = await caja_svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "80"})
    await caja_svc.eliminar_movimiento(session, clinica.id, mov["id"], usuario_id=admin_user.id)
    filas = await _audits(session, clinica.id, entidad="caja_movimiento")
    assert len(filas) == 1
    assert filas[0].accion == "eliminar"
    assert filas[0].entidad_id == mov["id"]


async def test_anular_compra_deja_auditoria(session, clinica, admin_user):
    prod = await inv_svc.crear_producto(session, clinica.id, {"nombre": "Insumo", "sku": "A1", "stock_actual": "0"})
    items = [{"producto_id": prod["id"], "cantidad": "5", "costo_unitario": "3"}]
    compra = await compras_svc.crear(session, clinica.id, {"numero": "F-9"}, items)
    await compras_svc.anular(session, clinica.id, compra["id"], usuario_id=admin_user.id)
    filas = await _audits(session, clinica.id, entidad="compra")
    assert len(filas) == 1
    assert filas[0].accion == "anular"


async def test_operacion_fallida_no_deja_rastro(session, clinica, admin_user):
    # Un cobro sin paciente válido revienta antes de escribir auditoría.
    from clinica_app.services.exceptions import NotFoundError
    payload = _cobro_payload(999999)
    try:
        await cobro_svc.crear(session, clinica.id, payload, usuario_id=admin_user.id)
    except (NotFoundError, Exception):
        pass
    total = (await session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.clinica_id == clinica.id)
    )).scalar_one()
    assert total == 0
