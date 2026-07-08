from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.base import tenant_select
from clinica_app.models.profesional import Profesional
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


def _dump(p: Profesional) -> dict:
    return {
        "id":              p.id,
        "nombres":         p.nombres,
        "apellidos":       p.apellidos,
        "nombre_completo": p.nombre_completo,
        "dni":             p.dni or "",
        "matricula":       p.matricula or "",
        "especialidad":    p.especialidad or "",
        "telefono":        p.telefono or "",
        "email":           p.email or "",
        "is_active":       p.is_active,
        "created_at":      p.created_at.strftime("%d/%m/%Y") if p.created_at else "",
    }


async def listar(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    q: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict:
    stmt = tenant_select(Profesional, clinica_id)
    if sede_id:
        stmt = stmt.where(Profesional.sede_id == sede_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Profesional.nombres.ilike(like),
                Profesional.apellidos.ilike(like),
                Profesional.dni.ilike(like),
                Profesional.especialidad.ilike(like),
                Profesional.matricula.ilike(like),
            )
        )
    total: int = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    items = (
        await session.execute(
            stmt.order_by(Profesional.apellidos.asc(), Profesional.nombres.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()
    return {
        "data":     [_dump(p) for p in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, (total + per_page - 1) // per_page),
    }


async def obtener(session: AsyncSession, clinica_id: int, prof_id: int, sede_id: int = 0) -> Profesional:
    stmt = select(Profesional).where(
        Profesional.clinica_id == clinica_id,
        Profesional.id == prof_id,
        Profesional.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(Profesional.sede_id == sede_id)
    p = (await session.execute(stmt)).scalars().first()
    if not p:
        raise NotFoundError(f"Profesional {prof_id} no encontrado")
    return p


async def _check_dni_libre(
    session: AsyncSession, clinica_id: int, dni: str, excluir_id: int | None = None
) -> None:
    q = select(Profesional).where(
        Profesional.clinica_id == clinica_id,
        Profesional.dni == dni,
        Profesional.is_active.is_(True),
    )
    if excluir_id:
        q = q.where(Profesional.id != excluir_id)
    if (await session.execute(q)).scalars().first():
        raise ConflictError(f"Ya existe un profesional con DNI {dni}")


async def _check_matricula_libre(
    session: AsyncSession, clinica_id: int, matricula: str, excluir_id: int | None = None
) -> None:
    q = select(Profesional).where(
        Profesional.clinica_id == clinica_id,
        Profesional.matricula == matricula,
        Profesional.is_active.is_(True),
    )
    if excluir_id:
        q = q.where(Profesional.id != excluir_id)
    if (await session.execute(q)).scalars().first():
        raise ConflictError(f"Ya existe un profesional con matrícula {matricula}")


async def crear(session: AsyncSession, clinica_id: int, payload: dict, sede_id: int = 0) -> dict:
    nombres   = (payload.get("nombres") or "").strip()
    apellidos = (payload.get("apellidos") or "").strip()
    if not nombres or not apellidos:
        raise ServiceError("Nombres y apellidos son obligatorios")

    dni       = (payload.get("dni")       or "").strip() or None
    matricula = (payload.get("matricula") or "").strip() or None

    if dni:
        await _check_dni_libre(session, clinica_id, dni)
    if matricula:
        await _check_matricula_libre(session, clinica_id, matricula)

    p = Profesional(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        nombres=nombres,
        apellidos=apellidos,
        dni=dni,
        matricula=matricula,
        especialidad=(payload.get("especialidad") or "").strip() or None,
        telefono=(payload.get("telefono") or "").strip() or None,
        email=(payload.get("email") or "").strip() or None,
    )
    session.add(p)
    await session.flush()
    return _dump(p)


async def actualizar(session: AsyncSession, clinica_id: int, prof_id: int, payload: dict, sede_id: int = 0) -> dict:
    p = await obtener(session, clinica_id, prof_id, sede_id)

    nombres   = (payload.get("nombres") or "").strip()
    apellidos = (payload.get("apellidos") or "").strip()
    if not nombres or not apellidos:
        raise ServiceError("Nombres y apellidos son obligatorios")

    nuevo_dni      = (payload.get("dni")       or "").strip() or None
    nueva_matricula = (payload.get("matricula") or "").strip() or None

    if nuevo_dni and nuevo_dni != p.dni:
        await _check_dni_libre(session, clinica_id, nuevo_dni, excluir_id=prof_id)
    if nueva_matricula and nueva_matricula != p.matricula:
        await _check_matricula_libre(session, clinica_id, nueva_matricula, excluir_id=prof_id)

    p.nombres      = nombres
    p.apellidos    = apellidos
    p.dni          = nuevo_dni
    p.matricula    = nueva_matricula
    p.especialidad = (payload.get("especialidad") or "").strip() or None
    p.telefono     = (payload.get("telefono") or "").strip() or None
    p.email        = (payload.get("email") or "").strip() or None
    await session.flush()
    return _dump(p)


async def eliminar(session: AsyncSession, clinica_id: int, prof_id: int, sede_id: int = 0) -> None:
    p = await obtener(session, clinica_id, prof_id, sede_id)
    p.soft_delete()
    await session.flush()
