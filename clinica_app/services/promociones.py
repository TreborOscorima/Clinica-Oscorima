from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.promocion import Promocion
from clinica_app.services.exceptions import NotFoundError, ServiceError

D2 = Decimal("0.01")


def _dec(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _parse_fecha(v: str) -> datetime | None:
    if not v or not v.strip():
        return None
    try:
        return datetime.strptime(v.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def _dump(p: Promocion) -> dict[str, Any]:
    return {
        "id":           p.id or 0,
        "nombre":       p.nombre,
        "descripcion":  p.descripcion or "",
        "tipo":         p.tipo,
        "valor":        str(_dec(p.valor)),
        "aplica_a":     p.aplica_a,
        "fecha_inicio": p.fecha_inicio.strftime("%Y-%m-%d") if p.fecha_inicio else "",
        "fecha_fin":    p.fecha_fin.strftime("%Y-%m-%d") if p.fecha_fin else "",
        "activo":       p.activo,
        "vigente":      p.vigente,
        "created_at":   p.created_at.strftime("%d/%m/%Y") if p.created_at else "",
    }


async def listar(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    solo_activas: bool = False,
    q: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    base = select(Promocion).where(
        Promocion.clinica_id == clinica_id,
        Promocion.is_active.is_(True),
    )
    if sede_id:
        base = base.where(Promocion.sede_id == sede_id)
    if solo_activas:
        base = base.where(Promocion.activo.is_(True))
    if q:
        base = base.where(Promocion.nombre.ilike(f"%{q}%"))

    base = base.order_by(Promocion.created_at.desc())

    total_sub = base.subquery()
    total = (await session.execute(select(func.count()).select_from(total_sub))).scalar_one()
    rows = (await session.execute(base.offset((page - 1) * per_page).limit(per_page))).all()
    data = [_dump(r[0]) for r in rows]

    kpi = (await session.execute(
        select(func.count())
        .where(
            Promocion.clinica_id == clinica_id,
            Promocion.is_active.is_(True),
            Promocion.activo.is_(True),
        )
    )).scalar_one()

    return {
        "data":           data,
        "total":          total,
        "pages":          max(1, -(-total // per_page)),
        "total_activas":  kpi or 0,
    }


async def crear(session: AsyncSession, clinica_id: int, payload: dict[str, Any], sede_id: int = 0) -> dict[str, Any]:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre es requerido")

    tipo = payload.get("tipo", "porcentaje")
    if tipo not in ("porcentaje", "monto_fijo"):
        raise ServiceError("Tipo inválido")

    valor = _dec(payload.get("valor", 0))
    if tipo == "porcentaje" and not (Decimal("0") <= valor <= Decimal("100")):
        raise ServiceError("El porcentaje debe estar entre 0 y 100")
    if valor < Decimal("0"):
        raise ServiceError("El valor no puede ser negativo")

    aplica_a = payload.get("aplica_a", "todo")
    if aplica_a not in ("todo", "servicios", "productos"):
        raise ServiceError("aplica_a inválido")

    p = Promocion(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        nombre=nombre,
        descripcion=(payload.get("descripcion") or "").strip() or None,
        tipo=tipo,
        valor=valor,
        aplica_a=aplica_a,
        fecha_inicio=_parse_fecha(payload.get("fecha_inicio", "")),
        fecha_fin=_parse_fecha(payload.get("fecha_fin", "")),
    )
    session.add(p)
    await session.flush()
    return _dump(p)


async def actualizar(
    session: AsyncSession,
    clinica_id: int,
    promo_id: int,
    payload: dict[str, Any],
    sede_id: int = 0,
) -> dict[str, Any]:
    p = await _get(session, clinica_id, promo_id, sede_id=sede_id)

    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre es requerido")

    tipo = payload.get("tipo", p.tipo)
    valor = _dec(payload.get("valor", p.valor))
    if tipo == "porcentaje" and not (Decimal("0") <= valor <= Decimal("100")):
        raise ServiceError("El porcentaje debe estar entre 0 y 100")

    p.nombre      = nombre
    p.descripcion = (payload.get("descripcion") or "").strip() or None
    p.tipo        = tipo
    p.valor       = valor
    p.aplica_a    = payload.get("aplica_a", p.aplica_a)
    p.fecha_inicio = _parse_fecha(payload.get("fecha_inicio", ""))
    p.fecha_fin    = _parse_fecha(payload.get("fecha_fin", ""))
    await session.flush()
    return _dump(p)


async def toggle_activo(session: AsyncSession, clinica_id: int, promo_id: int, sede_id: int = 0) -> dict[str, Any]:
    p = await _get(session, clinica_id, promo_id, sede_id=sede_id)
    p.activo = not p.activo
    await session.flush()
    return _dump(p)


async def eliminar(session: AsyncSession, clinica_id: int, promo_id: int, sede_id: int = 0) -> None:
    p = await _get(session, clinica_id, promo_id, sede_id=sede_id)
    p.soft_delete()
    await session.flush()


async def _get(session: AsyncSession, clinica_id: int, promo_id: int, sede_id: int = 0) -> Promocion:
    p = await session.get(Promocion, promo_id)
    if not p or p.clinica_id != clinica_id or not p.is_active:
        raise NotFoundError("Promoción no encontrada")
    if sede_id and p.sede_id and p.sede_id != sede_id:
        raise NotFoundError("Promoción no encontrada")
    return p
