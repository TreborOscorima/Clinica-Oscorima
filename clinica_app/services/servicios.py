from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.base import tenant_select
from clinica_app.models.servicio import Servicio, ServicioPrecioHist
from clinica_app.services.exceptions import NotFoundError, ServiceError


def _dump(s: Servicio) -> dict:
    return {
        "id":           s.id,
        "nombre":       s.nombre,
        "categoria":    s.categoria or "",
        "descripcion":  s.descripcion or "",
        "precio":       str(s.precio or "0.00"),
        "duracion_min": s.duracion_min or 30,
        "protocolo":    s.protocolo or "",
        "is_active":    s.is_active,
        "created_at":   s.created_at.strftime("%d/%m/%Y") if s.created_at else "",
    }


async def listar(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    q: str = "",
    categoria: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict:
    stmt = tenant_select(Servicio, clinica_id)
    if sede_id:
        stmt = stmt.where(Servicio.sede_id == sede_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Servicio.nombre.ilike(like), Servicio.descripcion.ilike(like))
        )
    if categoria:
        stmt = stmt.where(Servicio.categoria == categoria)

    total: int = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    items = (
        await session.execute(
            stmt.order_by(Servicio.categoria.asc(), Servicio.nombre.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    return {
        "data":     [_dump(s) for s in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, (total + per_page - 1) // per_page),
    }


async def categorias(session: AsyncSession, clinica_id: int, sede_id: int = 0) -> list[str]:
    stmt = (
        select(Servicio.categoria)
        .where(
            Servicio.clinica_id == clinica_id,
            Servicio.is_active.is_(True),
            Servicio.categoria.isnot(None),
        )
    )
    if sede_id:
        stmt = stmt.where(Servicio.sede_id == sede_id)
    rows = (
        await session.execute(stmt.distinct().order_by(Servicio.categoria.asc()))
    ).scalars().all()
    return [r for r in rows if r]


async def obtener(session: AsyncSession, clinica_id: int, servicio_id: int, sede_id: int = 0) -> Servicio:
    stmt = select(Servicio).where(
        Servicio.clinica_id == clinica_id,
        Servicio.id == servicio_id,
        Servicio.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(Servicio.sede_id == sede_id)
    s = (await session.execute(stmt)).scalars().first()
    if not s:
        raise NotFoundError(f"Servicio {servicio_id} no encontrado")
    return s


async def crear(session: AsyncSession, clinica_id: int, payload: dict, sede_id: int = 0) -> dict:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre del servicio es obligatorio")

    try:
        precio = Decimal(str(payload.get("precio") or "0")).quantize(Decimal("0.01"))
    except Exception:
        raise ServiceError("Precio inválido")

    try:
        duracion = int(payload.get("duracion_min") or 30)
    except (ValueError, TypeError):
        raise ServiceError("Duración inválida")

    s = Servicio(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        nombre=nombre,
        categoria=(payload.get("categoria") or "").strip() or None,
        descripcion=(payload.get("descripcion") or "").strip() or None,
        precio=precio,
        duracion_min=duracion,
        protocolo=(payload.get("protocolo") or "").strip() or None,
    )
    session.add(s)
    await session.flush()
    return _dump(s)


async def actualizar(session: AsyncSession, clinica_id: int, servicio_id: int, payload: dict, sede_id: int = 0) -> dict:
    s = await obtener(session, clinica_id, servicio_id, sede_id=sede_id)

    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre del servicio es obligatorio")

    try:
        precio = Decimal(str(payload.get("precio") or "0")).quantize(Decimal("0.01"))
    except Exception:
        raise ServiceError("Precio inválido")

    try:
        duracion = int(payload.get("duracion_min") or 30)
    except (ValueError, TypeError):
        raise ServiceError("Duración inválida")

    precio_anterior = s.precio
    s.nombre       = nombre
    s.categoria    = (payload.get("categoria") or "").strip() or None
    s.descripcion  = (payload.get("descripcion") or "").strip() or None
    s.precio       = precio
    s.duracion_min = duracion
    s.protocolo    = (payload.get("protocolo") or "").strip() or None

    if precio != precio_anterior:
        hist = ServicioPrecioHist(
            clinica_id=clinica_id,
            servicio_id=servicio_id,
            precio_anterior=precio_anterior,
            precio_nuevo=precio,
            motivo=payload.get("motivo_precio"),
            usuario_id=payload.get("usuario_id"),
        )
        session.add(hist)

    await session.flush()
    return _dump(s)


async def eliminar(session: AsyncSession, clinica_id: int, servicio_id: int, sede_id: int = 0) -> None:
    s = await obtener(session, clinica_id, servicio_id, sede_id=sede_id)
    s.soft_delete()
    await session.flush()


async def historial_precios(session: AsyncSession, clinica_id: int, servicio_id: int) -> list[dict]:
    registros = (
        await session.execute(
            select(ServicioPrecioHist)
            .where(
                ServicioPrecioHist.clinica_id == clinica_id,
                ServicioPrecioHist.servicio_id == servicio_id,
            )
            .order_by(ServicioPrecioHist.registrado_en.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        {
            "id":              r.id,
            "precio_anterior": str(r.precio_anterior),
            "precio_nuevo":    str(r.precio_nuevo),
            "motivo":          r.motivo or "—",
            "usuario_id":      r.usuario_id,
            "registrado_en":   r.registrado_en.strftime("%Y-%m-%d %H:%M") if r.registrado_en else "",
        }
        for r in registros
    ]
