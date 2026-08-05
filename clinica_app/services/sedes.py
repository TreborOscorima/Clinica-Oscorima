from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.base import tenant_select
from clinica_app.models.clinica import Clinica
from clinica_app.models.sede import Sede
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


def _dump(s: Sede) -> dict[str, Any]:
    return {
        "id":           s.id,
        "nombre":       s.nombre,
        "direccion":    s.direccion or "",
        "telefono":     s.telefono or "",
        "email":        s.email or "",
        "es_principal": s.es_principal,
        "is_active":    s.is_active,
    }


async def listar(session: AsyncSession, clinica_id: int) -> list[dict]:
    rows = (await session.execute(
        tenant_select(Sede, clinica_id).order_by(Sede.es_principal.desc(), Sede.nombre)
    )).scalars().all()
    return [_dump(s) for s in rows]


async def crear(session: AsyncSession, clinica_id: int, payload: dict) -> dict:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre de la sede es obligatorio")

    existente = (await session.execute(
        select(Sede).where(
            Sede.clinica_id == clinica_id,
            Sede.nombre == nombre,
            Sede.is_active.is_(True),
        )
    )).scalars().first()
    if existente:
        raise ConflictError(f"Ya existe una sede con el nombre '{nombre}'")

    # Límite de sedes por clínica (override del owner; NULL = ilimitado).
    clinica = await session.get(Clinica, clinica_id)
    maximo = getattr(clinica, "max_sedes", None) if clinica else None
    if maximo:
        total = (await session.execute(
            select(func.count()).select_from(Sede).where(
                Sede.clinica_id == clinica_id, Sede.is_active.is_(True)
            )
        )).scalar_one()
        if total >= maximo:
            raise ServiceError(
                f"Límite alcanzado: máximo {maximo} sedes. "
                f"Contacte a TUWAYKI para ampliar su plan."
            )

    es_principal = bool(payload.get("es_principal", False))
    # Solo una sede puede ser principal: desmarcar las demás
    if es_principal:
        for s in (await session.execute(
            select(Sede).where(Sede.clinica_id == clinica_id, Sede.is_active.is_(True))
        )).scalars().all():
            s.es_principal = False

    sede = Sede(
        clinica_id=clinica_id,
        nombre=nombre,
        direccion=payload.get("direccion") or None,
        telefono=payload.get("telefono") or None,
        email=payload.get("email") or None,
        es_principal=es_principal,
    )
    session.add(sede)
    await session.flush()
    return _dump(sede)


async def actualizar(session: AsyncSession, clinica_id: int, sede_id: int, payload: dict) -> dict:
    sede = (await session.execute(
        select(Sede).where(
            Sede.id == sede_id,
            Sede.clinica_id == clinica_id,
            Sede.is_active.is_(True),
        )
    )).scalars().first()
    if not sede:
        raise NotFoundError("Sede no encontrada")

    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre de la sede es obligatorio")

    sede.nombre    = nombre
    sede.direccion = payload.get("direccion") or None
    sede.telefono  = payload.get("telefono") or None
    sede.email     = payload.get("email") or None

    es_principal = bool(payload.get("es_principal", False))
    if es_principal and not sede.es_principal:
        for s in (await session.execute(
            select(Sede).where(Sede.clinica_id == clinica_id, Sede.is_active.is_(True))
        )).scalars().all():
            s.es_principal = False
        sede.es_principal = True
    elif not es_principal:
        sede.es_principal = False

    await session.flush()
    return _dump(sede)


async def eliminar(session: AsyncSession, clinica_id: int, sede_id: int) -> None:
    sede = (await session.execute(
        select(Sede).where(
            Sede.id == sede_id,
            Sede.clinica_id == clinica_id,
            Sede.is_active.is_(True),
        )
    )).scalars().first()
    if not sede:
        raise NotFoundError("Sede no encontrada")
    if sede.es_principal:
        raise ConflictError("No se puede eliminar la sede principal. Establecé otra como principal primero.")
    sede.soft_delete()
    await session.flush()
