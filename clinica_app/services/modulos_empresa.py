"""Módulos y límites habilitables por clínica (override del owner).

Fase 3 de la paridad Owner Panel. A diferencia de FOOD (que gatea por plan),
LIFE no gatea módulos por plan: por defecto TODOS están disponibles. El owner
puede deshabilitar módulos por clínica desde el panel; el módulo se ve en la app
si (el rol lo permite) AND (el owner no lo deshabilitó).

Los módulos "core" (dashboard, pacientes, historia, calendario, turnos, cobro,
caja, reportes, configuración) no son toggleables: siempre están.
"""
from __future__ import annotations

from sqlalchemy import select

from clinica_app.models.clinica import Clinica
from clinica_app.models.modulo import ClinicaModulo

# Catálogo de módulos toggleables por clínica (key = string de módulo del sidebar).
MODULOS_TOGGLEABLES: list[dict] = [
    {"key": "profesionales", "label": "Profesionales"},
    {"key": "servicios",     "label": "Servicios"},
    {"key": "cuentas",       "label": "Cuentas Ctes."},
    {"key": "compras",       "label": "Compras"},
    {"key": "inventario",    "label": "Inventario"},
    {"key": "promociones",   "label": "Promociones"},
]
_KEYS_APLICABLES: set[str] = {m["key"] for m in MODULOS_TOGGLEABLES}

# Límites ajustables por clínica. LIFE no tiene defaults de plan: None = ilimitado.
LIMITES: list[dict] = [
    {"key": "max_usuarios", "label": "Máx. usuarios"},
    {"key": "max_sedes",    "label": "Máx. sedes"},
]
_LIMITE_KEYS: set[str] = {l["key"] for l in LIMITES}


def modulo_habilitado(overrides: dict[str, bool], modulo: str) -> bool:
    """Resuelve si un módulo toggleable está habilitado. Default LIFE = True."""
    if modulo not in _KEYS_APLICABLES:
        return True  # core / desconocido: siempre disponible
    return bool(overrides.get(modulo, True))


def modulos_deshabilitados(overrides: dict[str, bool]) -> set[str]:
    """Set de módulos toggleables que el owner apagó (para restar en el gate)."""
    return {m["key"] for m in MODULOS_TOGGLEABLES if not modulo_habilitado(overrides, m["key"])}


async def cargar_overrides(session, clinica_id: int) -> dict[str, bool]:
    """Lee las filas de override de una clínica como {modulo: habilitado}."""
    rows = (await session.execute(
        select(ClinicaModulo).where(ClinicaModulo.clinica_id == clinica_id)
    )).scalars().all()
    return {r.modulo: bool(r.habilitado) for r in rows}


def estado_modulos(overrides: dict[str, bool]) -> dict[str, bool]:
    """Estado resuelto de TODOS los módulos toggleables (para el panel)."""
    return {m["key"]: modulo_habilitado(overrides, m["key"]) for m in MODULOS_TOGGLEABLES}


async def guardar_modulos(session, clinica_id: int, modulos: dict[str, bool]) -> None:
    """Upsert de los overrides. Ignora keys desconocidas."""
    existentes = {
        r.modulo: r
        for r in (await session.execute(
            select(ClinicaModulo).where(ClinicaModulo.clinica_id == clinica_id)
        )).scalars().all()
    }
    for key, val in (modulos or {}).items():
        if key not in _KEYS_APLICABLES:
            continue
        row = existentes.get(key)
        if row is not None:
            row.habilitado = bool(val)
            session.add(row)
        else:
            session.add(ClinicaModulo(
                clinica_id=clinica_id, modulo=key, habilitado=bool(val),
            ))


def limite_efectivo(clinica: Clinica, key: str) -> int | None:
    """Límite vigente de un recurso (None = ilimitado)."""
    val = getattr(clinica, key, None)
    return int(val) if val is not None else None


def guardar_limites(session, clinica: Clinica, limites: dict) -> None:
    """Setea las columnas de límite. None/'' = ilimitado (NULL). Fuera de rango se ignora."""
    for key, raw in (limites or {}).items():
        if key not in _LIMITE_KEYS:
            continue
        if raw in (None, ""):
            setattr(clinica, key, None)
            continue
        try:
            val = int(raw)
        except (TypeError, ValueError):
            continue
        if val < 1 or val > 100000:
            continue
        setattr(clinica, key, val)
    session.add(clinica)
