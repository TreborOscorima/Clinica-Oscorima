"""Perfil de especialidad de la clínica (D1).

Traduce el `rubro` de la clínica (ya existente, se elige en Configuración) a qué
módulos de especialidad se muestran: los dentales (odontograma B1, plan de
tratamiento B2) y los estéticos (galería + ficha C1/C2). También filtra las
plantillas de nota (A3) por rubro y siembra catálogos de servicios precargados
para acelerar el alta.

No hay tabla nueva: reutiliza `Clinica.rubro`. Un rubro sin elegir (o
desconocido) no oculta nada, para no romper clínicas existentes.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.clinica import Clinica
from clinica_app.models.servicio import Servicio
from clinica_app.services import auditoria
from clinica_app.services import plantillas_nota

# rubro (valor de Configuración) → especialidades activas
_ESPECIALIDADES: dict[str, dict[str, bool]] = {
    "odontologia":      {"dental": True,  "estetica": False},
    "clinica_estetica": {"dental": False, "estetica": True},
    "spa_bienestar":    {"dental": False, "estetica": True},
    "general":          {"dental": True,  "estetica": True},
}

# Rubro vacío/None → no ocultar nada (clínica que aún no eligió perfil).
_PERFIL_SIN_ELEGIR = {"dental": True, "estetica": True}
# Rubro conocido pero no-especialidad (consultorio_medico, fisioterapia, …) → sin módulos.
_PERFIL_OTRO = {"dental": False, "estetica": False}


def perfil(rubro: str | None) -> dict[str, bool]:
    r = (rubro or "").strip().lower()
    if not r:
        return dict(_PERFIL_SIN_ELEGIR)
    return dict(_ESPECIALIDADES.get(r, _PERFIL_OTRO))


def dental_activa(rubro: str | None) -> bool:
    return perfil(rubro)["dental"]


def estetica_activa(rubro: str | None) -> bool:
    return perfil(rubro)["estetica"]


def plantillas_para(rubro: str | None) -> list[dict[str, str]]:
    """Opciones de plantilla de nota (A3) filtradas por rubro: las transversales
    siempre; la de odontología solo si hay perfil dental; la de estética solo si
    hay perfil estético."""
    p = perfil(rubro)
    salida = []
    for op in plantillas_nota.opciones():
        clave = op["clave"]
        if clave == "odontologia" and not p["dental"]:
            continue
        if clave == "estetica" and not p["estetica"]:
            continue
        salida.append(op)
    return salida


# ── Catálogos de servicios precargados por especialidad ───────────────────────
# Precios de ejemplo (0 = a definir por la clínica); aceleran el alta.
SERVICIOS_SEMILLA: dict[str, list[dict[str, Any]]] = {
    "dental": [
        {"nombre": "Consulta odontológica",          "precio": "0",  "duracion_min": 30, "categoria": "Odontología"},
        {"nombre": "Limpieza dental (profilaxis)",    "precio": "0",  "duracion_min": 30, "categoria": "Odontología"},
        {"nombre": "Restauración con resina",         "precio": "0",  "duracion_min": 45, "categoria": "Odontología"},
        {"nombre": "Extracción simple",               "precio": "0",  "duracion_min": 30, "categoria": "Odontología"},
        {"nombre": "Endodoncia unirradicular",        "precio": "0",  "duracion_min": 60, "categoria": "Odontología"},
        {"nombre": "Corona de porcelana",             "precio": "0",  "duracion_min": 60, "categoria": "Odontología"},
    ],
    "estetica": [
        {"nombre": "Consulta estética",               "precio": "0",  "duracion_min": 30, "categoria": "Estética"},
        {"nombre": "Aplicación de toxina botulínica", "precio": "0",  "duracion_min": 30, "categoria": "Estética"},
        {"nombre": "Relleno con ácido hialurónico",   "precio": "0",  "duracion_min": 45, "categoria": "Estética"},
        {"nombre": "Limpieza facial profunda",        "precio": "0",  "duracion_min": 60, "categoria": "Estética"},
        {"nombre": "Peeling químico",                 "precio": "0",  "duracion_min": 45, "categoria": "Estética"},
        {"nombre": "Sesión de láser",                 "precio": "0",  "duracion_min": 30, "categoria": "Estética"},
    ],
}


def _semilla_para(rubro: str | None) -> list[dict[str, Any]]:
    p = perfil(rubro)
    items: list[dict[str, Any]] = []
    if p["dental"]:
        items += SERVICIOS_SEMILLA["dental"]
    if p["estetica"]:
        items += SERVICIOS_SEMILLA["estetica"]
    return items


async def rubro_de(session: AsyncSession, clinica_id: int) -> str:
    r = (await session.execute(
        select(Clinica.rubro).where(Clinica.id == clinica_id)
    )).scalar_one_or_none()
    return r or ""


async def sembrar_servicios(
    session: AsyncSession,
    clinica_id: int,
    rubro: str | None,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, int]:
    """Crea los servicios precargados de la(s) especialidad(es) del rubro que aún
    no existan en la clínica (comparación por nombre, sin distinguir may/min).
    Idempotente: correrlo dos veces no duplica. Devuelve {creados, omitidos}."""
    semilla = _semilla_para(rubro)
    if not semilla:
        return {"creados": 0, "omitidos": 0}

    # Nombres existentes (activos) en la clínica, en minúsculas.
    existentes = {
        (n or "").strip().lower()
        for n in (await session.execute(
            select(Servicio.nombre).where(
                Servicio.clinica_id == clinica_id,
                Servicio.is_active.is_(True),
            )
        )).scalars().all()
    }

    creados = 0
    for item in semilla:
        if item["nombre"].strip().lower() in existentes:
            continue
        session.add(Servicio(
            clinica_id=clinica_id,
            sede_id=sede_id or None,
            nombre=item["nombre"],
            categoria=item["categoria"],
            precio=Decimal(item["precio"]),
            duracion_min=item["duracion_min"],
        ))
        existentes.add(item["nombre"].strip().lower())
        creados += 1

    if creados:
        await session.flush()
        await auditoria.registrar(
            session, clinica_id,
            usuario_id=usuario_id,
            accion="sembrar_catalogo", entidad="servicio",
            detalle={"rubro": (rubro or ""), "creados": creados},
            sede_id=sede_id or None,
        )
        await session.flush()
    return {"creados": creados, "omitidos": len(semilla) - creados}
