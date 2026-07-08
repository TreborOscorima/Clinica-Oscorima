from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.base import tenant_select
from clinica_app.models.moneda import Moneda
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


def _dump(m: Moneda) -> dict[str, Any]:
    return {
        "id":        m.id,
        "codigo":    m.codigo,
        "nombre":    m.nombre,
        "simbolo":   m.simbolo,
        "es_activa": m.es_activa,
    }


async def listar(session: AsyncSession, clinica_id: int) -> list[dict]:
    rows = (await session.execute(
        tenant_select(Moneda, clinica_id).order_by(Moneda.nombre)
    )).scalars().all()
    return [_dump(m) for m in rows]


async def crear(session: AsyncSession, clinica_id: int, payload: dict) -> dict:
    codigo  = (payload.get("codigo")  or "").strip().upper()
    nombre  = (payload.get("nombre")  or "").strip()
    simbolo = (payload.get("simbolo") or "").strip()
    if not codigo or not nombre or not simbolo:
        raise ServiceError("Código, nombre y símbolo son obligatorios")

    existente = (await session.execute(
        select(Moneda).where(
            Moneda.clinica_id == clinica_id,
            Moneda.codigo     == codigo,
            Moneda.is_active.is_(True),
        )
    )).scalars().first()
    if existente:
        raise ConflictError(f"Ya existe la moneda '{codigo}'")

    m = Moneda(clinica_id=clinica_id, codigo=codigo, nombre=nombre, simbolo=simbolo)
    session.add(m)
    await session.flush()
    return _dump(m)


async def set_activa(session: AsyncSession, clinica_id: int, moneda_id: int) -> None:
    for m in (await session.execute(
        select(Moneda).where(Moneda.clinica_id == clinica_id, Moneda.is_active.is_(True))
    )).scalars().all():
        m.es_activa = False

    m = (await session.execute(
        select(Moneda).where(Moneda.id == moneda_id, Moneda.clinica_id == clinica_id)
    )).scalars().first()
    if not m:
        raise NotFoundError("Moneda no encontrada")
    m.es_activa = True
    await session.flush()


async def eliminar(session: AsyncSession, clinica_id: int, moneda_id: int) -> None:
    m = (await session.execute(
        select(Moneda).where(
            Moneda.id         == moneda_id,
            Moneda.clinica_id == clinica_id,
            Moneda.is_active.is_(True),
        )
    )).scalars().first()
    if not m:
        raise NotFoundError("Moneda no encontrada")
    if m.es_activa:
        raise ServiceError("No se puede eliminar la moneda activa. Seleccioná otra primero.")
    m.soft_delete()
    await session.flush()
