from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.base import tenant_select
from clinica_app.models.impuesto_tasa import ImpuestoTasa
from clinica_app.services.exceptions import NotFoundError, ServiceError

_PAIS_DEFAULTS: dict[str, list[tuple]] = {
    "peru":      [("IGV", "Estándar",     18.0, True)],
    "argentina": [("IVA", "Estándar",     21.0, True),
                  ("IVA", "Reducida",     10.5, False),
                  ("IVA", "Incrementada", 27.0, False)],
    "colombia":  [("IVA", "Estándar",     19.0, True),
                  ("IVA", "Reducida",      5.0, False)],
    "chile":     [("IVA", "Estándar",     19.0, True)],
    "ecuador":   [("IVA", "Estándar",     12.0, True),
                  ("IVA", "Reducida",      5.0, False)],
    "bolivia":   [("IVA", "Estándar",     13.0, True)],
    "uruguay":   [("IVA", "Estándar",     22.0, True),
                  ("IVA", "Reducida",     10.0, False)],
    "paraguay":  [("IVA", "Estándar",     10.0, True),
                  ("IVA", "Reducida",      5.0, False)],
    "mexico":    [("IVA", "Estándar",     16.0, True)],
}


def _dump(t: ImpuestoTasa) -> dict[str, Any]:
    return {
        "id":            t.id,
        "tipo_impuesto": t.tipo_impuesto,
        "nombre":        t.nombre,
        "porcentaje":    t.porcentaje,
        "is_default":    t.is_default,
    }


async def listar(session: AsyncSession, clinica_id: int) -> list[dict]:
    rows = (await session.execute(
        tenant_select(ImpuestoTasa, clinica_id)
        .order_by(ImpuestoTasa.tipo_impuesto, ImpuestoTasa.nombre)
    )).scalars().all()
    return [_dump(t) for t in rows]


async def crear(session: AsyncSession, clinica_id: int, payload: dict) -> dict:
    tipo   = (payload.get("tipo_impuesto") or "IVA").strip().upper()
    nombre = (payload.get("nombre") or "").strip()
    try:
        porcentaje = float(payload.get("porcentaje", 0))
    except (ValueError, TypeError):
        raise ServiceError("Porcentaje inválido")
    if not nombre:
        raise ServiceError("El nombre de la tasa es obligatorio")
    if porcentaje < 0:
        raise ServiceError("El porcentaje no puede ser negativo")

    is_default = bool(payload.get("is_default", False))
    if is_default:
        await _quitar_default(session, clinica_id)

    t = ImpuestoTasa(
        clinica_id=clinica_id,
        tipo_impuesto=tipo,
        nombre=nombre,
        porcentaje=porcentaje,
        is_default=is_default,
    )
    session.add(t)
    await session.flush()
    return _dump(t)


async def actualizar(session: AsyncSession, clinica_id: int, tid: int, payload: dict) -> dict:
    t = (await session.execute(
        select(ImpuestoTasa).where(
            ImpuestoTasa.id         == tid,
            ImpuestoTasa.clinica_id == clinica_id,
            ImpuestoTasa.is_active.is_(True),
        )
    )).scalars().first()
    if not t:
        raise NotFoundError("Tasa no encontrada")
    try:
        t.porcentaje = float(payload.get("porcentaje", t.porcentaje))
    except (ValueError, TypeError):
        raise ServiceError("Porcentaje inválido")
    if nombre := (payload.get("nombre") or "").strip():
        t.nombre = nombre
    if tipo := (payload.get("tipo_impuesto") or "").strip():
        t.tipo_impuesto = tipo.upper()
    await session.flush()
    return _dump(t)


async def set_default(session: AsyncSession, clinica_id: int, tid: int) -> None:
    await _quitar_default(session, clinica_id)
    t = (await session.execute(
        select(ImpuestoTasa).where(
            ImpuestoTasa.id         == tid,
            ImpuestoTasa.clinica_id == clinica_id,
        )
    )).scalars().first()
    if not t:
        raise NotFoundError("Tasa no encontrada")
    t.is_default = True
    await session.flush()


async def eliminar(session: AsyncSession, clinica_id: int, tid: int) -> None:
    t = (await session.execute(
        select(ImpuestoTasa).where(
            ImpuestoTasa.id         == tid,
            ImpuestoTasa.clinica_id == clinica_id,
            ImpuestoTasa.is_active.is_(True),
        )
    )).scalars().first()
    if not t:
        raise NotFoundError("Tasa no encontrada")
    if t.is_default:
        raise ServiceError("No se puede eliminar la tasa por defecto. Seleccioná otra primero.")
    t.soft_delete()
    await session.flush()


async def cargar_pais(session: AsyncSession, clinica_id: int, pais: str) -> None:
    defaults = _PAIS_DEFAULTS.get(pais.lower())
    if not defaults:
        raise ServiceError(f"País no soportado: {pais}")
    for t in (await session.execute(
        select(ImpuestoTasa).where(
            ImpuestoTasa.clinica_id == clinica_id,
            ImpuestoTasa.is_active.is_(True),
        )
    )).scalars().all():
        t.soft_delete()
    for tipo, nombre, porcentaje, is_default in defaults:
        session.add(ImpuestoTasa(
            clinica_id=clinica_id,
            tipo_impuesto=tipo,
            nombre=nombre,
            porcentaje=porcentaje,
            is_default=is_default,
        ))
    await session.flush()


async def _quitar_default(session: AsyncSession, clinica_id: int) -> None:
    for t in (await session.execute(
        select(ImpuestoTasa).where(
            ImpuestoTasa.clinica_id  == clinica_id,
            ImpuestoTasa.is_active.is_(True),
            ImpuestoTasa.is_default.is_(True),
        )
    )).scalars().all():
        t.is_default = False
