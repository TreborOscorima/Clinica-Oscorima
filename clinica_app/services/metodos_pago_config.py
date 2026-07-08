from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.base import tenant_select
from clinica_app.models.metodo_pago_config import MetodoPagoConfig
from clinica_app.services.exceptions import NotFoundError, ServiceError


def _dump(m: MetodoPagoConfig) -> dict[str, Any]:
    return {
        "id":               m.id,
        "nombre":           m.nombre,
        "descripcion":      m.descripcion or "",
        "tipo":             m.tipo,
        "is_active":        m.is_active,
        "visible_en_venta": m.visible_en_venta,
    }


async def listar(session: AsyncSession, clinica_id: int) -> list[dict]:
    rows = (await session.execute(
        tenant_select(MetodoPagoConfig, clinica_id).order_by(MetodoPagoConfig.nombre)
    )).scalars().all()
    return [_dump(m) for m in rows]


async def crear(session: AsyncSession, clinica_id: int, payload: dict) -> dict:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre del método de pago es obligatorio")

    tipo = (payload.get("tipo") or "otro").strip()
    m = MetodoPagoConfig(
        clinica_id=clinica_id,
        nombre=nombre,
        descripcion=payload.get("descripcion") or None,
        tipo=tipo,
        visible_en_venta=bool(payload.get("visible_en_venta", True)),
    )
    session.add(m)
    await session.flush()
    return _dump(m)


async def toggle_visible(session: AsyncSession, clinica_id: int, mid: int) -> dict:
    m = (await session.execute(
        select(MetodoPagoConfig).where(
            MetodoPagoConfig.id         == mid,
            MetodoPagoConfig.clinica_id == clinica_id,
            MetodoPagoConfig.is_active.is_(True),
        )
    )).scalars().first()
    if not m:
        raise NotFoundError("Método no encontrado")
    m.visible_en_venta = not m.visible_en_venta
    await session.flush()
    return _dump(m)


async def toggle_activo(session: AsyncSession, clinica_id: int, mid: int) -> dict:
    m = (await session.execute(
        select(MetodoPagoConfig).where(
            MetodoPagoConfig.id         == mid,
            MetodoPagoConfig.clinica_id == clinica_id,
        )
    )).scalars().first()
    if not m:
        raise NotFoundError("Método no encontrado")
    if m.is_active:
        m.soft_delete()
    else:
        m.is_active  = True
        m.deleted_at = None
    await session.flush()
    return _dump(m)


async def eliminar(session: AsyncSession, clinica_id: int, mid: int) -> None:
    m = (await session.execute(
        select(MetodoPagoConfig).where(
            MetodoPagoConfig.id         == mid,
            MetodoPagoConfig.clinica_id == clinica_id,
            MetodoPagoConfig.is_active.is_(True),
        )
    )).scalars().first()
    if not m:
        raise NotFoundError("Método no encontrado")
    m.soft_delete()
    await session.flush()
