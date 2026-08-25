"""Cronograma de cuotas de una deuda financiada.

Genera y lista el plan de cuotas (número, monto, vencimiento) de una
`DeudaPaciente`. El estado de pago de cada cuota NO se persiste: se deriva del
`pagado` de la deuda en cascada por número de cuota (waterfall), de modo que un
solo campo `pagado` (que ya mantiene `cuentas.registrar_pago`) sigue siendo la
única fuente de verdad. Así el cronograma es informativo/planificador y nunca
se desincroniza del ledger de caja.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.caja import CuotaDeuda, DeudaPaciente

D2 = Decimal("0.01")


def _dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _add_meses(d: date, meses: int) -> date:
    """Suma `meses` a una fecha conservando el día (con clamp a fin de mes)."""
    total = d.month - 1 + meses
    anio = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def _montos(total: Decimal, num_cuotas: int) -> list[Decimal]:
    """Divide `total` en `num_cuotas` montos; el resto de redondeo va a la última."""
    total = _dec(total)
    base = (total / num_cuotas).quantize(D2, rounding=ROUND_HALF_UP)
    montos = [base] * (num_cuotas - 1)
    montos.append((total - base * (num_cuotas - 1)).quantize(D2))
    return montos


async def generar(
    session: AsyncSession,
    *,
    clinica_id: int,
    deuda_id: int,
    total: Decimal | str,
    num_cuotas: int,
    desde: date | None = None,
    periodicidad_meses: int = 1,
) -> list[dict[str, Any]]:
    """Crea el cronograma de `num_cuotas` cuotas que suman `total`.

    La primera vence `periodicidad_meses` después de `desde` (hoy por defecto);
    las siguientes, mensualmente. No-op si num_cuotas < 1 o total <= 0.
    """
    num_cuotas = int(num_cuotas)
    total = _dec(total)
    if num_cuotas < 1 or total <= 0:
        return []

    base_fecha = desde or date.today()
    montos = _montos(total, num_cuotas)
    filas: list[CuotaDeuda] = []
    for i, monto in enumerate(montos, start=1):
        filas.append(CuotaDeuda(
            clinica_id=clinica_id,
            deuda_id=deuda_id,
            numero=i,
            monto=monto,
            vencimiento=_add_meses(base_fecha, periodicidad_meses * i),
        ))
    session.add_all(filas)
    await session.flush()
    return [_dump(c, pagado=Decimal("0"), acumulado_previo=sum(montos[: c.numero - 1], Decimal("0")))
            for c in filas]


def _estado(cuota: CuotaDeuda, pagado: Decimal, acumulado_previo: Decimal, hoy: date) -> str:
    """Estado derivado por waterfall: cuánto del `pagado` de la deuda cubre esta cuota."""
    monto = _dec(cuota.monto)
    acumulado_post = acumulado_previo + monto
    if pagado >= acumulado_post:
        return "pagada"
    if pagado <= acumulado_previo:
        return "vencida" if cuota.vencimiento and cuota.vencimiento < hoy else "pendiente"
    return "parcial"


def _dump(c: CuotaDeuda, *, pagado: Decimal, acumulado_previo: Decimal,
          hoy: date | None = None) -> dict[str, Any]:
    hoy = hoy or date.today()
    return {
        "id":          c.id or 0,
        "numero":      c.numero,
        "monto":       str(_dec(c.monto)),
        "vencimiento": c.vencimiento.strftime("%d/%m/%Y") if c.vencimiento else "",
        "estado":      _estado(c, pagado, acumulado_previo, hoy),
    }


async def listar_por_deuda(
    session: AsyncSession, clinica_id: int, deuda_id: int, *, hoy: date | None = None,
) -> list[dict[str, Any]]:
    """Cuotas de la deuda ordenadas por número, con estado derivado del pagado."""
    hoy = hoy or date.today()
    deuda = await session.get(DeudaPaciente, deuda_id)
    if not deuda or deuda.clinica_id != clinica_id:
        return []
    pagado = _dec(deuda.pagado)

    cuotas = (await session.execute(
        select(CuotaDeuda)
        .where(CuotaDeuda.deuda_id == deuda_id, CuotaDeuda.clinica_id == clinica_id)
        .order_by(CuotaDeuda.numero)
    )).scalars().all()

    out: list[dict[str, Any]] = []
    acumulado = Decimal("0")
    for c in cuotas:
        out.append(_dump(c, pagado=pagado, acumulado_previo=acumulado, hoy=hoy))
        acumulado += _dec(c.monto)
    return out


async def proximos_vencimientos(
    session: AsyncSession, clinica_id: int, deuda_ids: list[int], *, hoy: date | None = None,
) -> dict[int, dict[str, Any]]:
    """Para cada deuda, la próxima cuota NO cubierta por el pagado (o la vencida más
    antigua). Devuelve {deuda_id: {"vencimiento", "estado"}}. Evita el N+1 en la lista."""
    if not deuda_ids:
        return {}
    hoy = hoy or date.today()
    deudas = (await session.execute(
        select(DeudaPaciente).where(
            DeudaPaciente.id.in_(deuda_ids),
            DeudaPaciente.clinica_id == clinica_id,
        )
    )).scalars().all()
    pagado_por_deuda = {d.id: _dec(d.pagado) for d in deudas}

    cuotas = (await session.execute(
        select(CuotaDeuda)
        .where(CuotaDeuda.deuda_id.in_(deuda_ids), CuotaDeuda.clinica_id == clinica_id)
        .order_by(CuotaDeuda.deuda_id, CuotaDeuda.numero)
    )).scalars().all()

    acumulado: dict[int, Decimal] = {}
    resultado: dict[int, dict[str, Any]] = {}
    for c in cuotas:
        prev = acumulado.get(c.deuda_id, Decimal("0"))
        pagado = pagado_por_deuda.get(c.deuda_id, Decimal("0"))
        estado = _estado(c, pagado, prev, hoy)
        # la primera cuota no saldada es "la próxima" a mostrar
        if estado in ("pendiente", "vencida", "parcial") and c.deuda_id not in resultado:
            resultado[c.deuda_id] = {
                "vencimiento": c.vencimiento.strftime("%d/%m/%Y") if c.vencimiento else "",
                "estado":      estado,
            }
        acumulado[c.deuda_id] = prev + _dec(c.monto)
    return resultado
