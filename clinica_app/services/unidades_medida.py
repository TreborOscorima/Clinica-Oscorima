from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.base import tenant_select
from clinica_app.models.unidad_medida import UnidadMedida
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


def _dump(u: UnidadMedida) -> dict[str, Any]:
    return {
        "id":                u.id,
        "nombre":            u.nombre,
        "permite_decimales": u.permite_decimales,
    }


async def listar(session: AsyncSession, clinica_id: int) -> list[dict]:
    rows = (await session.execute(
        tenant_select(UnidadMedida, clinica_id).order_by(UnidadMedida.nombre)
    )).scalars().all()
    return [_dump(u) for u in rows]


async def crear(session: AsyncSession, clinica_id: int, payload: dict) -> dict:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre de la unidad es obligatorio")

    existente = (await session.execute(
        select(UnidadMedida).where(
            UnidadMedida.clinica_id == clinica_id,
            UnidadMedida.nombre     == nombre,
            UnidadMedida.is_active.is_(True),
        )
    )).scalars().first()
    if existente:
        raise ConflictError(f"Ya existe la unidad '{nombre}'")

    u = UnidadMedida(
        clinica_id=clinica_id,
        nombre=nombre,
        permite_decimales=bool(payload.get("permite_decimales", False)),
    )
    session.add(u)
    await session.flush()
    return _dump(u)


async def toggle_decimales(session: AsyncSession, clinica_id: int, uid: int) -> dict:
    u = (await session.execute(
        select(UnidadMedida).where(
            UnidadMedida.id         == uid,
            UnidadMedida.clinica_id == clinica_id,
            UnidadMedida.is_active.is_(True),
        )
    )).scalars().first()
    if not u:
        raise NotFoundError("Unidad no encontrada")
    u.permite_decimales = not u.permite_decimales
    await session.flush()
    return _dump(u)


async def eliminar(session: AsyncSession, clinica_id: int, uid: int) -> None:
    u = (await session.execute(
        select(UnidadMedida).where(
            UnidadMedida.id         == uid,
            UnidadMedida.clinica_id == clinica_id,
            UnidadMedida.is_active.is_(True),
        )
    )).scalars().first()
    if not u:
        raise NotFoundError("Unidad no encontrada")
    u.soft_delete()
    await session.flush()
