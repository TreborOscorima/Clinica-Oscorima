from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.caja import CajaMovimiento, CierreCaja, MetodoPago, TipoMovimiento
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError

D2 = Decimal("0.01")


def dec2(v) -> Decimal:
    if v is None:
        v = 0
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _dump_mov(m: CajaMovimiento) -> dict[str, Any]:
    return {
        "id":             m.id,
        "fecha":          m.fecha.strftime("%Y-%m-%d %H:%M") if m.fecha else "",
        "tipo":           m.tipo.value if m.tipo else None,
        "monto":          str(m.monto),
        "metodo_pago":    m.metodo_pago.value if m.metodo_pago else None,
        "paciente_id":    m.paciente_id,
        "profesional_id": m.profesional_id,
        "servicio_id":    m.servicio_id,
        "turno_id":       m.turno_id,
        "observacion":    m.observacion,
    }


def _base_query(clinica_id: int, sede_id: int = 0):
    stmt = select(CajaMovimiento).where(
        CajaMovimiento.clinica_id == clinica_id,
        CajaMovimiento.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(CajaMovimiento.sede_id == sede_id)
    return stmt


async def listar_movimientos(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    tipo: str = "",
    page: int = 1,
    per_page: int = 30,
) -> dict[str, Any]:
    stmt = _base_query(clinica_id, sede_id)
    if desde:
        stmt = stmt.where(CajaMovimiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(CajaMovimiento.fecha <= hasta)
    if tipo:
        try:
            stmt = stmt.where(CajaMovimiento.tipo == TipoMovimiento(tipo))
        except ValueError as exc:
            raise ServiceError("Tipo inválido") from exc

    total: int = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    items = (
        await session.execute(
            stmt.order_by(CajaMovimiento.fecha.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    return {
        "data":     [_dump_mov(m) for m in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, -(-total // per_page)),
    }


async def resumen_dia(
    session: AsyncSession, clinica_id: int, sede_id: int = 0, fecha: datetime | None = None
) -> dict[str, Any]:
    if fecha is None:
        fecha = datetime.now(timezone.utc)
    inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    fin    = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)

    stmt = _base_query(clinica_id, sede_id).where(
        CajaMovimiento.fecha >= inicio,
        CajaMovimiento.fecha <= fin,
    )
    movs = (await session.execute(stmt)).scalars().all()

    ingresos = sum(dec2(m.monto) for m in movs if m.tipo == TipoMovimiento.INGRESO)
    egresos  = sum(dec2(m.monto) for m in movs if m.tipo == TipoMovimiento.EGRESO)
    return {
        "ingresos":           str(ingresos),
        "egresos":            str(egresos),
        "saldo":              str(ingresos - egresos),
        "total_movimientos":  len(movs),
    }


async def registrar_movimiento(
    session: AsyncSession, clinica_id: int, payload: dict[str, Any], sede_id: int = 0
) -> dict[str, Any]:
    tipo_str = (payload.get("tipo") or "").lower()
    try:
        tipo = TipoMovimiento(tipo_str)
    except ValueError as exc:
        raise ServiceError("tipo debe ser 'ingreso' o 'egreso'") from exc

    try:
        monto = Decimal(str(payload.get("monto") or 0))
    except Exception as exc:
        raise ServiceError("Monto inválido") from exc
    if monto <= 0:
        raise ServiceError("Monto debe ser positivo")

    metodo_str = (payload.get("metodo_pago") or "efectivo").lower()
    try:
        metodo = MetodoPago(metodo_str)
    except ValueError:
        metodo = MetodoPago.OTRO

    mov = CajaMovimiento(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        tipo=tipo,
        monto=monto,
        metodo_pago=metodo,
        observacion=payload.get("observacion"),
        paciente_id=payload.get("paciente_id"),
    )
    session.add(mov)
    await session.flush()
    return _dump_mov(mov)


async def realizar_cierre_dia(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    usuario_id: int | None = None,
    fecha: datetime | None = None,
) -> dict[str, Any]:
    if fecha is None:
        fecha = datetime.now(timezone.utc)

    fecha_solo = fecha.date()
    stmt_existente = select(CierreCaja).where(
        CierreCaja.clinica_id == clinica_id,
        CierreCaja.fecha == fecha_solo,
        CierreCaja.is_active.is_(True),
    )
    if sede_id:
        stmt_existente = stmt_existente.where(CierreCaja.sede_id == sede_id)
    existente = (await session.execute(stmt_existente)).scalars().first()
    if existente:
        raise ConflictError(f"Ya existe un cierre de caja para {fecha_solo.strftime('%d/%m/%Y')}")

    resumen = await resumen_dia(session, clinica_id, sede_id, fecha)
    cierre = CierreCaja(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        fecha=fecha_solo,
        total_ingresos=Decimal(resumen["ingresos"]),
        total_egresos=Decimal(resumen["egresos"]),
        saldo=Decimal(resumen["saldo"]),
        usuario_id=usuario_id,
    )
    session.add(cierre)
    await session.flush()
    return {
        "id":                cierre.id,
        "fecha":             fecha_solo.strftime("%Y-%m-%d"),
        "total_ingresos":    resumen["ingresos"],
        "total_egresos":     resumen["egresos"],
        "saldo":             resumen["saldo"],
        "total_movimientos": resumen["total_movimientos"],
        "creado_en":         cierre.creado_en.strftime("%Y-%m-%d %H:%M") if cierre.creado_en else "",
    }


async def listar_cierres(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = select(CierreCaja).where(
        CierreCaja.clinica_id == clinica_id, CierreCaja.is_active.is_(True)
    )
    if sede_id:
        stmt = stmt.where(CierreCaja.sede_id == sede_id)
    stmt = stmt.order_by(CierreCaja.fecha.desc())
    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    items = (
        await session.execute(stmt.offset((page - 1) * per_page).limit(per_page))
    ).scalars().all()
    return {
        "data": [
            {
                "id":             c.id,
                "fecha":          c.fecha.strftime("%Y-%m-%d") if c.fecha else "",
                "total_ingresos": str(c.total_ingresos or "0"),
                "total_egresos":  str(c.total_egresos or "0"),
                "saldo":          str(c.saldo or "0"),
                "creado_en":      c.creado_en.strftime("%Y-%m-%d %H:%M") if c.creado_en else "",
            }
            for c in items
        ],
        "total": total,
        "pages": max(1, -(-total // per_page)),
        "page":  page,
    }


async def eliminar_movimiento(
    session: AsyncSession, clinica_id: int, mov_id: int, sede_id: int = 0
) -> None:
    mov = (
        await session.execute(_base_query(clinica_id, sede_id).where(CajaMovimiento.id == mov_id))
    ).scalars().first()
    if mov is None:
        raise NotFoundError("Movimiento no encontrado")
    mov.soft_delete()
    await session.flush()
