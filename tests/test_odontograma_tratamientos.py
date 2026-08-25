"""Doble notación dx/tx del odontograma: cruce con el plan de tratamiento.

El "tratamiento planificado" de una pieza son los ítems del plan de tratamiento
(PlanTratamientoItem) que la referencian por número FDI. Estas consultas viven en
services/odontograma.py y alimentan el badge del odontograma + el modal.
"""
from __future__ import annotations

from clinica_app.services import odontograma as svc
from clinica_app.services import planes_tratamiento as pt


# ── Sugerencia de tratamiento ─────────────────────────────────────────────────

def test_sugerencia_tratamiento_por_estado():
    assert svc.sugerencia_tratamiento("caries", "16") == "Obturación pieza 16"
    assert svc.sugerencia_tratamiento("ausente", "36") == "Implante / prótesis pieza 36"
    # Estado sin sugerencia específica → genérico con la pieza.
    assert svc.sugerencia_tratamiento("sano", "11") == "Tratamiento pieza 11"
    # Sin número: sólo la base.
    assert svc.sugerencia_tratamiento("caries") == "Obturación"


def test_estados_tienen_naturaleza():
    by = {e["clave"]: e for e in svc.estados_catalogo()}
    assert by["caries"]["naturaleza"] == "hallazgo"
    assert by["obturado"]["naturaleza"] == "tratamiento"
    assert by["ausente"]["naturaleza"] == "hallazgo"
    assert by["sano"]["naturaleza"] == ""


# ── resumen_tratamientos ──────────────────────────────────────────────────────

async def _plan_con_piezas(session, clinica, paciente, admin_user):
    plan = await pt.crear_plan(session, clinica.id, paciente.id, titulo="Plan", usuario_id=admin_user.id)
    # Pieza 16: un propuesto + un terminado.
    await pt.agregar_item(session, clinica.id, plan["id"], descripcion="Obturación", pieza_numero="16", usuario_id=admin_user.id)
    i_term = await pt.agregar_item(session, clinica.id, plan["id"], descripcion="Endodoncia", pieza_numero="16", usuario_id=admin_user.id)
    await pt.cambiar_estado_item(session, clinica.id, plan["id"], i_term["id"], estado="terminado", usuario_id=admin_user.id)
    # Pieza 26: un aprobado (pendiente).
    i_apr = await pt.agregar_item(session, clinica.id, plan["id"], descripcion="Corona", pieza_numero="26", usuario_id=admin_user.id)
    await pt.cambiar_estado_item(session, clinica.id, plan["id"], i_apr["id"], estado="aprobado", usuario_id=admin_user.id)
    # Ítem sin pieza (no debe contar en ninguna).
    await pt.agregar_item(session, clinica.id, plan["id"], descripcion="Consulta", usuario_id=admin_user.id)
    return plan


async def test_resumen_tratamientos_cuenta_por_pieza(session, clinica, paciente, admin_user):
    await _plan_con_piezas(session, clinica, paciente, admin_user)
    resumen = await svc.resumen_tratamientos(session, clinica.id, paciente.id)
    assert resumen["16"] == {"pendientes": 1, "terminados": 1}
    assert resumen["26"] == {"pendientes": 1, "terminados": 0}
    # Piezas sin tratamiento no figuran.
    assert "11" not in resumen


async def test_resumen_tratamientos_ignora_plan_cancelado(session, clinica, paciente, admin_user):
    plan = await _plan_con_piezas(session, clinica, paciente, admin_user)
    await pt.actualizar_plan(session, clinica.id, plan["id"], estado="cancelado", usuario_id=admin_user.id)
    resumen = await svc.resumen_tratamientos(session, clinica.id, paciente.id)
    assert resumen == {}


async def test_listar_tratamientos_pieza(session, clinica, paciente, admin_user):
    await _plan_con_piezas(session, clinica, paciente, admin_user)
    items = await svc.listar_tratamientos_pieza(session, clinica.id, paciente.id, "16")
    assert len(items) == 2
    descripciones = {it["descripcion"] for it in items}
    assert descripciones == {"Obturación", "Endodoncia"}
    # Cada item trae etiqueta/colores de estado del plan.
    for it in items:
        assert it["estado_label"]
        assert it["plan_titulo"] == "Plan"


async def test_listar_tratamientos_pieza_vacia(session, clinica, paciente, admin_user):
    await _plan_con_piezas(session, clinica, paciente, admin_user)
    assert await svc.listar_tratamientos_pieza(session, clinica.id, paciente.id, "11") == []
    # Pieza inválida → lista vacía, sin error.
    assert await svc.listar_tratamientos_pieza(session, clinica.id, paciente.id, "99") == []
