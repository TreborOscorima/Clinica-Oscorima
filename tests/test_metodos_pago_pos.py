"""Métodos de pago configurables en el POS.

Cubre el selector del POS (listar_visibles) y la traza del método específico
elegido en la auditoría del comprobante (metodo_nombre).
"""
from __future__ import annotations

import json

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.services import cobro as cobro_svc
from clinica_app.services import metodos_pago_config as svc_mp


async def _crear(session, clinica_id, **extra):
    m = await svc_mp.crear(session, clinica_id, {
        "nombre":      extra.get("nombre", "Yape"),
        "tipo":        extra.get("tipo", "transferencia"),
        "descripcion": extra.get("descripcion", ""),
        "visible_en_venta": extra.get("visible_en_venta", True),
    })
    return m


# ── listar_visibles ─────────────────────────────────────────────────────────

async def test_listar_visibles_incluye_visible(session, clinica):
    await _crear(session, clinica.id, nombre="Yape", visible_en_venta=True)
    visibles = await svc_mp.listar_visibles(session, clinica.id)
    assert [m["nombre"] for m in visibles] == ["Yape"]


async def test_listar_visibles_excluye_no_visible(session, clinica):
    await _crear(session, clinica.id, nombre="Interno", visible_en_venta=False)
    await _crear(session, clinica.id, nombre="Yape", visible_en_venta=True)
    visibles = await svc_mp.listar_visibles(session, clinica.id)
    assert [m["nombre"] for m in visibles] == ["Yape"]


async def test_listar_visibles_excluye_eliminado(session, clinica):
    m = await _crear(session, clinica.id, nombre="Plin", visible_en_venta=True)
    await svc_mp.eliminar(session, clinica.id, m["id"])
    visibles = await svc_mp.listar_visibles(session, clinica.id)
    assert visibles == []


async def test_listar_visibles_vacio_sin_config(session, clinica):
    assert await svc_mp.listar_visibles(session, clinica.id) == []


# ── traza del método específico en la auditoría del cobro ────────────────────

def _payload(paciente_id, **extra):
    p = {
        "paciente_id": paciente_id,
        "items": [{
            "tipo": "servicio", "ref_id": 1, "nombre": "Consulta",
            "cantidad": "1", "precio_unit": "100.00",
        }],
        "forma_pago": "transferencia",
        "descuento_global": "0",
        "es_cuotas": False, "num_cuotas": 1, "cuota_inicial": "0",
    }
    p.update(extra)
    return p


async def _detalle_comprobante(session, clinica_id):
    row = (await session.execute(
        select(AuditLog).where(
            AuditLog.clinica_id == clinica_id,
            AuditLog.entidad == "comprobante",
            AuditLog.accion == "crear",
        )
    )).scalars().first()
    return json.loads(row.detalle) if row and row.detalle else {}


async def test_audit_guarda_metodo_nombre(session, clinica, paciente):
    await cobro_svc.crear(
        session, clinica.id,
        _payload(paciente.id, metodo_nombre="Yape"),
    )
    det = await _detalle_comprobante(session, clinica.id)
    assert det["forma_pago"] == "transferencia"   # enum como bucket
    assert det["metodo_nombre"] == "Yape"          # método específico trazado


async def test_audit_sin_metodo_nombre_no_agrega_clave(session, clinica, paciente):
    await cobro_svc.crear(session, clinica.id, _payload(paciente.id))
    det = await _detalle_comprobante(session, clinica.id)
    assert "metodo_nombre" not in det
