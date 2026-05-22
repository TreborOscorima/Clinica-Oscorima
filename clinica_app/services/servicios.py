from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_
from sqlmodel import Session, select

from clinica_app.models.base import tenant_select
from clinica_app.models.servicio import Servicio
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


def listar(
    session: Session,
    clinica_id: int,
    q: str = "",
    categoria: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict:
    stmt = tenant_select(Servicio, clinica_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Servicio.nombre.ilike(like), Servicio.descripcion.ilike(like))
        )
    if categoria:
        stmt = stmt.where(Servicio.categoria == categoria)

    total: int = session.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    items = session.exec(
        stmt.order_by(Servicio.categoria.asc(), Servicio.nombre.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return {
        "data":     [_dump(s) for s in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, (total + per_page - 1) // per_page),
    }


def categorias(session: Session, clinica_id: int) -> list[str]:
    rows = session.exec(
        select(Servicio.categoria)
        .where(
            Servicio.clinica_id == clinica_id,
            Servicio.is_active.is_(True),
            Servicio.categoria.isnot(None),
        )
        .distinct()
        .order_by(Servicio.categoria.asc())
    ).all()
    return [r for r in rows if r]


def obtener(session: Session, clinica_id: int, servicio_id: int) -> Servicio:
    s = session.exec(
        select(Servicio).where(
            Servicio.clinica_id == clinica_id,
            Servicio.id == servicio_id,
            Servicio.is_active.is_(True),
        )
    ).first()
    if not s:
        raise NotFoundError(f"Servicio {servicio_id} no encontrado")
    return s


def crear(session: Session, clinica_id: int, payload: dict) -> dict:
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
        nombre=nombre,
        categoria=(payload.get("categoria") or "").strip() or None,
        descripcion=(payload.get("descripcion") or "").strip() or None,
        precio=precio,
        duracion_min=duracion,
        protocolo=(payload.get("protocolo") or "").strip() or None,
    )
    session.add(s)
    session.flush()
    return _dump(s)


def actualizar(session: Session, clinica_id: int, servicio_id: int, payload: dict) -> dict:
    s = obtener(session, clinica_id, servicio_id)

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

    s.nombre      = nombre
    s.categoria   = (payload.get("categoria") or "").strip() or None
    s.descripcion = (payload.get("descripcion") or "").strip() or None
    s.precio      = precio
    s.duracion_min = duracion
    s.protocolo   = (payload.get("protocolo") or "").strip() or None
    session.flush()
    return _dump(s)


def eliminar(session: Session, clinica_id: int, servicio_id: int) -> None:
    s = obtener(session, clinica_id, servicio_id)
    s.soft_delete()
    session.flush()
