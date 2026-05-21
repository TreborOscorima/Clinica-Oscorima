from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlmodel import Session

from clinica_app.models.caja import CajaMovimiento, MetodoPago, TipoMovimiento
from clinica_app.services.exceptions import NotFoundError, ServiceError

D2 = Decimal("0.01")


def dec2(v) -> Decimal:
    if v is None:
        v = 0
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _dump_mov(m: CajaMovimiento) -> dict[str, Any]:
    return {
        "id":           m.id,
        "fecha":        m.fecha.isoformat() if m.fecha else None,
        "tipo":         m.tipo.value if m.tipo else None,
        "monto":        str(m.monto),
        "metodo_pago":  m.metodo_pago.value if m.metodo_pago else None,
        "paciente_id":  m.paciente_id,
        "profesional_id": m.profesional_id,
        "servicio_id":  m.servicio_id,
        "turno_id":     m.turno_id,
        "observacion":  m.observacion,
    }


def _base_query(clinica_id: int):
    return select(CajaMovimiento).where(
        CajaMovimiento.clinica_id == clinica_id,
        CajaMovimiento.is_active.is_(True),
    )


def listar_movimientos(
    session: Session,
    clinica_id: int,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    tipo: str = "",
    page: int = 1,
    per_page: int = 30,
) -> dict[str, Any]:
    stmt = _base_query(clinica_id)
    if desde:
        stmt = stmt.where(CajaMovimiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(CajaMovimiento.fecha <= hasta)
    if tipo:
        try:
            stmt = stmt.where(CajaMovimiento.tipo == TipoMovimiento(tipo))
        except ValueError as exc:
            raise ServiceError("Tipo inválido") from exc

    total: int = session.exec(
        select(func.count()).select_from(stmt.subquery())
    ).one()
    items = session.exec(
        stmt.order_by(CajaMovimiento.fecha.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    return {
        "data":     [_dump_mov(m) for m in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, -(-total // per_page)),
    }


def resumen_dia(session: Session, clinica_id: int, fecha: datetime | None = None) -> dict[str, Any]:
    if fecha is None:
        fecha = datetime.now(timezone.utc)
    inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    fin    = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)

    stmt = _base_query(clinica_id).where(
        CajaMovimiento.fecha >= inicio,
        CajaMovimiento.fecha <= fin,
    )
    movs = session.exec(stmt).all()

    ingresos = sum(dec2(m.monto) for m in movs if m.tipo == TipoMovimiento.INGRESO)
    egresos  = sum(dec2(m.monto) for m in movs if m.tipo == TipoMovimiento.EGRESO)
    return {
        "ingresos": str(ingresos),
        "egresos":  str(egresos),
        "saldo":    str(ingresos - egresos),
        "total_movimientos": len(movs),
    }


def registrar_movimiento(session: Session, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
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
        tipo=tipo,
        monto=monto,
        metodo_pago=metodo,
        observacion=payload.get("observacion"),
        paciente_id=payload.get("paciente_id"),
    )
    session.add(mov)
    session.flush()
    return _dump_mov(mov)


def eliminar_movimiento(session: Session, clinica_id: int, mov_id: int) -> None:
    mov = session.exec(
        _base_query(clinica_id).where(CajaMovimiento.id == mov_id)
    ).first()
    if mov is None:
        raise NotFoundError("Movimiento no encontrado")
    mov.soft_delete()
    session.flush()
