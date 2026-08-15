"""Tests del mapa estético (E5): evaluaciones, procedimientos y puntos de aplicación."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.models.procedimiento_estetico import PuntoAplicacion
from clinica_app.services import anatomia
from clinica_app.services import estetica_mapa as svc
from clinica_app.services.exceptions import NotFoundError, ValidationError


async def _producto(session, clinica, nombre="Toxina botulínica", stock="50"):
    from clinica_app.models.inventario import Producto
    p = Producto(clinica_id=clinica.id, nombre=nombre, stock_actual=Decimal(stock))
    session.add(p)
    await session.flush()
    return p


# ── Catálogo (services/anatomia) ──────────────────────────────────────────────

def test_catalogo_zonas_grupos():
    facial = anatomia.zonas_catalogo("facial")
    corporal = anatomia.zonas_catalogo("corporal")
    todo = anatomia.zonas_catalogo()
    assert facial and corporal
    assert all(z["grupo"] == "facial" for z in facial)
    assert all(z["grupo"] == "corporal" for z in corporal)
    assert len(todo) == len(facial) + len(corporal)
    # Códigos únicos.
    codigos = [z["codigo"] for z in todo]
    assert len(codigos) == len(set(codigos))


def test_catalogo_validadores():
    assert anatomia.es_zona_valida("frente")
    assert not anatomia.es_zona_valida("inexistente")
    assert anatomia.es_tipo_valido("toxina_botulinica")
    assert not anatomia.es_tipo_valido("magia")
    assert anatomia.es_categoria_valida("arrugas")
    assert not anatomia.es_categoria_valida("xyz")


def test_normalizar_severidad():
    assert anatomia.normalizar_severidad("3") == 3
    assert anatomia.normalizar_severidad(0) == 0
    assert anatomia.normalizar_severidad("") is None
    assert anatomia.normalizar_severidad(None) is None
    assert anatomia.normalizar_severidad("9") is None
    assert anatomia.normalizar_severidad("x") is None


# ── Evaluaciones ──────────────────────────────────────────────────────────────

async def test_registrar_y_listar_evaluacion(session, clinica, paciente, admin_user):
    e = await svc.registrar_evaluacion(
        session, clinica.id, paciente.id,
        zona_codigo="frente", categoria="arrugas", severidad="2",
        observacion="Líneas dinámicas", usuario_id=admin_user.id,
    )
    assert e["zona_label"] == "Frente"
    assert e["categoria_label"] == "Arrugas"
    assert e["severidad"] == 2
    lista = await svc.listar_evaluaciones(session, clinica.id, paciente.id)
    assert len(lista) == 1
    solo_frente = await svc.listar_evaluaciones(session, clinica.id, paciente.id, zona_codigo="frente")
    assert len(solo_frente) == 1
    otra_zona = await svc.listar_evaluaciones(session, clinica.id, paciente.id, zona_codigo="labios")
    assert otra_zona == []


async def test_evaluacion_zona_invalida(session, clinica, paciente, admin_user):
    with pytest.raises(ValidationError):
        await svc.registrar_evaluacion(
            session, clinica.id, paciente.id,
            zona_codigo="nariz_falsa", categoria="arrugas", usuario_id=admin_user.id,
        )


async def test_evaluacion_categoria_invalida(session, clinica, paciente, admin_user):
    with pytest.raises(ValidationError):
        await svc.registrar_evaluacion(
            session, clinica.id, paciente.id,
            zona_codigo="frente", categoria="inventada", usuario_id=admin_user.id,
        )


async def test_evaluacion_paciente_inexistente(session, clinica, admin_user):
    with pytest.raises(NotFoundError):
        await svc.registrar_evaluacion(
            session, clinica.id, 999999,
            zona_codigo="frente", categoria="arrugas", usuario_id=admin_user.id,
        )


async def test_eliminar_evaluacion(session, clinica, paciente, admin_user):
    e = await svc.registrar_evaluacion(
        session, clinica.id, paciente.id,
        zona_codigo="frente", categoria="arrugas", usuario_id=admin_user.id,
    )
    await svc.eliminar_evaluacion(session, clinica.id, e["id"], usuario_id=admin_user.id)
    assert await svc.listar_evaluaciones(session, clinica.id, paciente.id) == []


# ── Procedimientos ────────────────────────────────────────────────────────────

async def test_crear_procedimiento(session, clinica, paciente, admin_user):
    pr = await svc.crear_procedimiento(
        session, clinica.id, paciente.id,
        zona_codigo="entrecejo", tipo="toxina_botulinica",
        observacion="20 UI", usuario_id=admin_user.id,
    )
    assert pr["zona_label"] == "Entrecejo (glabela)"
    assert pr["tipo_label"] == "Toxina botulínica"
    assert pr["puntos"] == []


async def test_procedimiento_tipo_invalido(session, clinica, paciente, admin_user):
    with pytest.raises(ValidationError):
        await svc.crear_procedimiento(
            session, clinica.id, paciente.id,
            zona_codigo="entrecejo", tipo="rayos_gamma", usuario_id=admin_user.id,
        )


# ── Puntos de aplicación ──────────────────────────────────────────────────────

async def test_agregar_punto_con_producto(session, clinica, paciente, admin_user):
    prod = await _producto(session, clinica)
    pr = await svc.crear_procedimiento(
        session, clinica.id, paciente.id,
        zona_codigo="entrecejo", tipo="toxina_botulinica", usuario_id=admin_user.id,
    )
    p = await svc.agregar_punto(
        session, clinica.id, pr["id"],
        coord_x="0.5", coord_y="0.3",
        producto_id=prod.id, lote="LOT-2026-A", cantidad="4", unidad="UI",
        usuario_id=admin_user.id,
    )
    assert p["coord_x"] == 0.5
    assert p["coord_y"] == 0.3
    assert p["producto_id"] == prod.id
    assert p["lote"] == "LOT-2026-A"
    assert p["cantidad"] == "4"
    assert p["zona_codigo"] == "entrecejo"  # heredada del procedimiento


async def test_agregar_punto_clampa_coordenadas(session, clinica, paciente, admin_user):
    pr = await svc.crear_procedimiento(
        session, clinica.id, paciente.id,
        zona_codigo="frente", tipo="toxina_botulinica", usuario_id=admin_user.id,
    )
    p = await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="1.8", coord_y="-0.4", usuario_id=admin_user.id)
    assert p["coord_x"] == 1.0
    assert p["coord_y"] == 0.0


async def test_agregar_punto_producto_inexistente(session, clinica, paciente, admin_user):
    pr = await svc.crear_procedimiento(
        session, clinica.id, paciente.id,
        zona_codigo="frente", tipo="toxina_botulinica", usuario_id=admin_user.id,
    )
    with pytest.raises(NotFoundError):
        await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.5", coord_y="0.5", producto_id=999999, usuario_id=admin_user.id)


async def test_agregar_punto_cantidad_negativa(session, clinica, paciente, admin_user):
    pr = await svc.crear_procedimiento(
        session, clinica.id, paciente.id,
        zona_codigo="frente", tipo="toxina_botulinica", usuario_id=admin_user.id,
    )
    with pytest.raises(ValidationError):
        await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.5", coord_y="0.5", cantidad="-1", usuario_id=admin_user.id)


async def test_punto_en_obtener_procedimiento(session, clinica, paciente, admin_user):
    pr = await svc.crear_procedimiento(
        session, clinica.id, paciente.id,
        zona_codigo="frente", tipo="toxina_botulinica", usuario_id=admin_user.id,
    )
    await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.2", coord_y="0.2", usuario_id=admin_user.id)
    await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.8", coord_y="0.2", usuario_id=admin_user.id)
    full = await svc.obtener_procedimiento(session, clinica.id, pr["id"])
    assert full["n_puntos"] == 2


async def test_eliminar_procedimiento_da_de_baja_puntos(session, clinica, paciente, admin_user):
    pr = await svc.crear_procedimiento(
        session, clinica.id, paciente.id,
        zona_codigo="frente", tipo="toxina_botulinica", usuario_id=admin_user.id,
    )
    await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.5", coord_y="0.5", usuario_id=admin_user.id)
    await svc.eliminar_procedimiento(session, clinica.id, pr["id"], usuario_id=admin_user.id)
    activos = (await session.execute(
        select(PuntoAplicacion).where(PuntoAplicacion.procedimiento_id == pr["id"], PuntoAplicacion.is_active.is_(True))
    )).scalars().all()
    assert activos == []
    assert await svc.listar_procedimientos(session, clinica.id, paciente.id) == []


async def test_eliminar_punto(session, clinica, paciente, admin_user):
    pr = await svc.crear_procedimiento(
        session, clinica.id, paciente.id,
        zona_codigo="frente", tipo="toxina_botulinica", usuario_id=admin_user.id,
    )
    p = await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.5", coord_y="0.5", usuario_id=admin_user.id)
    await svc.eliminar_punto(session, clinica.id, p["id"], usuario_id=admin_user.id)
    full = await svc.obtener_procedimiento(session, clinica.id, pr["id"])
    assert full["n_puntos"] == 0


# ── Resumen del mapa ──────────────────────────────────────────────────────────

async def test_resumen_mapa(session, clinica, paciente, admin_user):
    await svc.registrar_evaluacion(session, clinica.id, paciente.id, zona_codigo="frente", categoria="arrugas", usuario_id=admin_user.id)
    pr = await svc.crear_procedimiento(session, clinica.id, paciente.id, zona_codigo="frente", tipo="toxina_botulinica", usuario_id=admin_user.id)
    await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.4", coord_y="0.3", usuario_id=admin_user.id)
    await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.6", coord_y="0.3", usuario_id=admin_user.id)
    res = await svc.resumen_mapa(session, clinica.id, paciente.id)
    assert res["n_evaluaciones"] == 1
    assert res["n_procedimientos"] == 1
    assert res["n_puntos"] == 2
    assert res["zonas"]["frente"]["evaluaciones"] == 1
    assert res["zonas"]["frente"]["procedimientos"] == 1
    assert res["zonas"]["frente"]["puntos"] == 2


# ── Aislamiento por tenant ────────────────────────────────────────────────────

async def test_tenant_aislado(session, clinica, paciente, admin_user):
    e = await svc.registrar_evaluacion(session, clinica.id, paciente.id, zona_codigo="frente", categoria="arrugas", usuario_id=admin_user.id)
    # Otra clínica no ve la evaluación.
    otra = await svc.listar_evaluaciones(session, 999999, paciente.id)
    assert otra == []
    # Eliminar desde otra clínica falla.
    with pytest.raises(NotFoundError):
        await svc.eliminar_evaluacion(session, 999999, e["id"], usuario_id=admin_user.id)


# ── Auditoría ─────────────────────────────────────────────────────────────────

async def test_auditoria_registrada(session, clinica, paciente, admin_user):
    pr = await svc.crear_procedimiento(session, clinica.id, paciente.id, zona_codigo="frente", tipo="toxina_botulinica", usuario_id=admin_user.id)
    p = await svc.agregar_punto(session, clinica.id, pr["id"], coord_x="0.5", coord_y="0.5", usuario_id=admin_user.id)
    await svc.eliminar_punto(session, clinica.id, p["id"], usuario_id=admin_user.id)
    logs = (await session.execute(
        select(AuditLog).where(AuditLog.entidad == "procedimiento_estetico")
    )).scalars().all()
    acciones = {log.accion for log in logs}
    assert "crear" in acciones
    assert "agregar_punto" in acciones
    assert "eliminar_punto" in acciones
