from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.caja import (
    CajaMovimiento,
    Comprobante,
    DeudaPaciente,
    MetodoPago,
    TipoMovimiento,
)
from clinica_app.models.paciente import Paciente
from clinica_app.services import cuotas as _cuotas
from clinica_app.services.exceptions import NotFoundError, ServiceError

D2 = Decimal("0.01")


def _dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _dump(d: DeudaPaciente, pac_nombre: str = "", comp_numero: str = "",
          prox: dict[str, Any] | None = None) -> dict[str, Any]:
    prox = prox or {}
    return {
        "id":                  d.id or 0,
        "paciente_id":         d.paciente_id,
        "paciente_nombre":     pac_nombre,
        "comprobante_id":      d.comprobante_id,
        "comprobante_numero":  comp_numero,
        "total":               str(_dec(d.total)),
        "pagado":              str(_dec(d.pagado)),
        "saldo":               str(_dec(d.saldo)),
        "estado":              d.estado or "pendiente",
        "creado_en":           d.creado_en.strftime("%d/%m/%Y") if d.creado_en else "",
        "actualizado_en":      d.actualizado_en.strftime("%d/%m/%Y") if d.actualizado_en else "",
        # Próxima cuota no saldada del cronograma (si la deuda tiene cuotas).
        "prox_vencimiento":    prox.get("vencimiento", ""),
        "prox_estado":         prox.get("estado", ""),
    }


async def listar(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    estado: str = "",
    paciente_q: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    from sqlalchemy import String, cast, or_

    base = (
        select(DeudaPaciente, Paciente, Comprobante)
        .join(Paciente,    Paciente.id    == DeudaPaciente.paciente_id)
        .join(Comprobante, Comprobante.id == DeudaPaciente.comprobante_id)
        .where(DeudaPaciente.clinica_id == clinica_id, DeudaPaciente.is_active.is_(True))
    )
    if sede_id:
        base = base.where(Comprobante.sede_id == sede_id)

    if estado:
        base = base.where(DeudaPaciente.estado == estado)

    if paciente_q:
        like = f"%{paciente_q}%"
        base = base.where(
            or_(
                Paciente.nombre.ilike(like),
                cast(Paciente.documento, String).ilike(like),
            )
        )

    base = base.order_by(DeudaPaciente.creado_en.desc())

    total_sub = base.subquery()
    total = (await session.execute(select(func.count()).select_from(total_sub))).scalar_one()

    rows = (await session.execute(base.offset((page - 1) * per_page).limit(per_page))).all()
    prox = await _cuotas.proximos_vencimientos(
        session, clinica_id, [d.id for d, _p, _c in rows if d.id]
    )
    data = [_dump(d, p.nombre, c.numero or "", prox.get(d.id)) for d, p, c in rows]

    # KPIs: deudores activos y saldo global pendiente
    kpi_q = (
        select(func.count(DeudaPaciente.id), func.coalesce(func.sum(DeudaPaciente.saldo), 0))
        .join(Comprobante, Comprobante.id == DeudaPaciente.comprobante_id)
        .where(
            DeudaPaciente.clinica_id == clinica_id,
            DeudaPaciente.is_active.is_(True),
            DeudaPaciente.estado.in_(["pendiente", "parcial"]),
        )
    )
    if sede_id:
        kpi_q = kpi_q.where(Comprobante.sede_id == sede_id)
    kpi = (await session.execute(kpi_q)).one()

    return {
        "data":            data,
        "total":           total,
        "pages":           max(1, -(-total // per_page)),
        "total_deudores":  kpi[0] or 0,
        "total_saldo":     str(_dec(kpi[1])),
    }


async def registrar_pago(
    session: AsyncSession,
    clinica_id: int,
    deuda_id: int,
    monto_str: str,
    metodo: str,
    observacion: str = "",
    sede_id: int = 0,
) -> dict[str, Any]:
    deuda = await session.get(DeudaPaciente, deuda_id)
    if not deuda or deuda.clinica_id != clinica_id or not deuda.is_active:
        raise NotFoundError("Deuda no encontrada")

    if deuda.estado == "saldado":
        raise ServiceError("Esta deuda ya está completamente pagada")

    monto = _dec(monto_str)
    if monto <= Decimal("0"):
        raise ServiceError("El monto debe ser mayor a cero")

    saldo_actual = _dec(deuda.saldo)
    if monto > saldo_actual:
        raise ServiceError(f"El monto supera el saldo pendiente (${saldo_actual})")

    deuda.pagado = (_dec(deuda.pagado) + monto).quantize(D2)
    deuda.saldo  = (saldo_actual - monto).quantize(D2)
    deuda.estado = "saldado" if deuda.saldo == Decimal("0") else "parcial"
    session.add(deuda)

    try:
        metodo_pago = MetodoPago(metodo)
    except ValueError:
        metodo_pago = MetodoPago.EFECTIVO

    mov = CajaMovimiento(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        tipo=TipoMovimiento.INGRESO,
        monto=monto,
        metodo_pago=metodo_pago,
        paciente_id=deuda.paciente_id,
        comprobante_id=deuda.comprobante_id,
        observacion=f"Pago cuota{' - ' + observacion if observacion else ''}",
    )
    session.add(mov)
    await session.flush()

    pac  = await session.get(Paciente,    deuda.paciente_id)
    comp = await session.get(Comprobante, deuda.comprobante_id)
    return _dump(
        deuda,
        pac.nombre    if pac  else "",
        comp.numero   if comp else "",
    )
