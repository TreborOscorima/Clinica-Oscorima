from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.config import REPORT_EXPORT_DIR
from clinica_app.models.caja import CajaMovimiento, TipoMovimiento
from clinica_app.models.paciente import Paciente
from clinica_app.models.profesional import Profesional
from clinica_app.models.servicio import Servicio
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.models.turno_servicio import TurnoServicio


def generar_reporte(clinica_id: int, tipo: str, params: dict[str, Any], sede_id: int = 0) -> str:
    """Genera el Excel en disco. Retorna el nombre del archivo (no el path completo)."""
    from clinica_app.tasks.reportes import generar_reporte as _gen

    os.makedirs(REPORT_EXPORT_DIR, exist_ok=True)
    if sede_id:
        params = {**params, "sede_id": sede_id}
    path = _gen(clinica_id, tipo, params)
    return os.path.basename(path)


async def kpis_mes(session: AsyncSession, clinica_id: int, sede_id: int = 0) -> dict[str, Any]:
    """KPIs del mes en curso para el panel de Reportes."""
    now = datetime.now(timezone.utc)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    q_ing = select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
        CajaMovimiento.clinica_id == clinica_id,
        CajaMovimiento.is_active.is_(True),
        CajaMovimiento.tipo == TipoMovimiento.INGRESO,
        CajaMovimiento.fecha >= inicio_mes,
    )
    if sede_id:
        q_ing = q_ing.where(CajaMovimiento.sede_id == sede_id)
    ingresos = (await session.execute(q_ing)).scalar_one()

    q_egr = select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
        CajaMovimiento.clinica_id == clinica_id,
        CajaMovimiento.is_active.is_(True),
        CajaMovimiento.tipo == TipoMovimiento.EGRESO,
        CajaMovimiento.fecha >= inicio_mes,
    )
    if sede_id:
        q_egr = q_egr.where(CajaMovimiento.sede_id == sede_id)
    egresos = (await session.execute(q_egr)).scalar_one()

    q_tur = select(func.count()).select_from(Turno).where(
        Turno.clinica_id == clinica_id,
        Turno.is_active.is_(True),
        Turno.fecha_hora >= inicio_mes,
    )
    if sede_id:
        q_tur = q_tur.where(Turno.sede_id == sede_id)
    turnos = (await session.execute(q_tur)).scalar_one()

    q_pac = select(func.count()).select_from(Paciente).where(
        Paciente.clinica_id == clinica_id,
        Paciente.is_active.is_(True),
        Paciente.created_at >= inicio_mes,
    )
    if sede_id:
        q_pac = q_pac.where(Paciente.sede_id == sede_id)
    pacientes_nuevos = (await session.execute(q_pac)).scalar_one()

    D2 = Decimal("0.01")
    return {
        "ingresos":         str(Decimal(str(ingresos or 0)).quantize(D2)),
        "egresos":          str(Decimal(str(egresos or 0)).quantize(D2)),
        "turnos":           int(turnos or 0),
        "pacientes_nuevos": int(pacientes_nuevos or 0),
    }


# ── Analíticas ampliadas ────────────────────────────────────────────────────────
# Producción por profesional / por servicio, ocupación (horas agendadas),
# asistencia y cancelaciones (no-shows). Los datos ya viven en los modelos.

_D2 = Decimal("0.01")


def _rango_fechas(desde: str | None, hasta: str | None) -> tuple[datetime | None, datetime | None]:
    """Convierte 'YYYY-MM-DD' → (inicio-de-día, fin-de-día). Tolera cadenas vacías."""
    desde_dt = datetime.fromisoformat(desde) if desde else None
    hasta_dt = datetime.fromisoformat(hasta + "T23:59:59") if hasta else None
    return desde_dt, hasta_dt


def _revenue_turno(
    turno_id: int,
    servicio_id: int | None,
    items_por_turno: dict[int, list[Any]],
    precio_servicio: dict[int, Decimal],
) -> Decimal:
    """Producción de un turno: usa sus ítems (precio×cant − desc); si no tiene, el precio del servicio."""
    items = items_por_turno.get(turno_id)
    if items:
        total = Decimal("0")
        for it in items:
            precio = it.precio if it.precio is not None else precio_servicio.get(it.servicio_id, Decimal("0"))
            cantidad = it.cantidad if it.cantidad is not None else Decimal("1")
            descuento = it.descuento if it.descuento is not None else Decimal("0")
            total += (Decimal(str(precio)) * Decimal(str(cantidad))) - Decimal(str(descuento))
        return total
    if servicio_id and servicio_id in precio_servicio:
        return Decimal(str(precio_servicio[servicio_id]))
    return Decimal("0")


def _calcular_analiticas(
    turnos: list[Any],
    items_por_turno: dict[int, list[Any]],
    servicios: dict[int, dict],
    profesionales: dict[int, str],
) -> dict[str, Any]:
    """Núcleo puro (sin sesión): agrega turnos ya cargados en las métricas del panel/Excel."""
    precio_servicio = {sid: s["precio"] for sid, s in servicios.items()}

    total = atendidos = confirmados = pendientes = cancelados = 0
    produccion = Decimal("0")
    horas_min = 0

    prof_acc: dict[int, dict] = {}
    serv_acc: dict[int, dict] = {}

    def _prof(pid: int | None) -> dict:
        key = pid or 0
        if key not in prof_acc:
            prof_acc[key] = {
                "profesional_id": key,
                "nombre": profesionales.get(key, "— Sin profesional —"),
                "total": 0, "atendidos": 0, "cancelados": 0,
                "produccion": Decimal("0"), "minutos": 0,
            }
        return prof_acc[key]

    def _serv(sid: int | None) -> dict:
        key = sid or 0
        if key not in serv_acc:
            info = servicios.get(key, {})
            serv_acc[key] = {
                "servicio_id": key,
                "nombre": info.get("nombre", "— Sin servicio —"),
                "veces": 0, "produccion": Decimal("0"),
            }
        return serv_acc[key]

    for t in turnos:
        total += 1
        estado = t.estado
        pa = _prof(t.profesional_id)
        pa["total"] += 1

        es_cancelado = estado == EstadoTurno.CANCELADO
        es_atendido = estado == EstadoTurno.ATENDIDO

        if es_atendido:
            atendidos += 1
            pa["atendidos"] += 1
            rev = _revenue_turno(t.id, t.servicio_id, items_por_turno, precio_servicio)
            produccion += rev
            pa["produccion"] += rev
            sa = _serv(t.servicio_id)
            sa["veces"] += 1
            sa["produccion"] += rev
        elif es_cancelado:
            cancelados += 1
            pa["cancelados"] += 1
        elif estado == EstadoTurno.CONFIRMADO:
            confirmados += 1
        else:
            pendientes += 1

        # Ocupación: minutos agendados de turnos no cancelados
        if not es_cancelado:
            dur = servicios.get(t.servicio_id or 0, {}).get("duracion_min", 30)
            horas_min += int(dur or 30)
            pa["minutos"] += int(dur or 30)

    def _pct(num: int, den: int) -> str:
        return str((Decimal(num) / Decimal(den) * 100).quantize(_D2)) if den else "0.00"

    por_profesional = [
        {
            "profesional_id": p["profesional_id"],
            "nombre": p["nombre"],
            "total": p["total"],
            "atendidos": p["atendidos"],
            "cancelados": p["cancelados"],
            "produccion": str(p["produccion"].quantize(_D2)),
            "horas": str((Decimal(p["minutos"]) / 60).quantize(_D2)),
            "tasa_asistencia": _pct(p["atendidos"], p["total"]),
        }
        for p in sorted(prof_acc.values(), key=lambda x: x["produccion"], reverse=True)
    ]

    por_servicio = [
        {
            "servicio_id": s["servicio_id"],
            "nombre": s["nombre"],
            "veces": s["veces"],
            "produccion": str(s["produccion"].quantize(_D2)),
        }
        for s in sorted(serv_acc.values(), key=lambda x: x["produccion"], reverse=True)
    ]

    return {
        "resumen": {
            "total": total,
            "atendidos": atendidos,
            "confirmados": confirmados,
            "pendientes": pendientes,
            "cancelados": cancelados,
            "produccion": str(produccion.quantize(_D2)),
            "horas_agendadas": str((Decimal(horas_min) / 60).quantize(_D2)),
            "tasa_asistencia": _pct(atendidos, total),
            "tasa_cancelacion": _pct(cancelados, total),
        },
        "por_profesional": por_profesional,
        "por_servicio": por_servicio,
    }


async def _cargar_datos_analiticas(
    session: AsyncSession, clinica_id: int, *, desde_dt, hasta_dt, sede_id: int,
) -> tuple[list, dict, dict, dict]:
    """Carga turnos del rango + mapas de servicios/profesionales/ítems (async o sync session)."""
    stmt = select(Turno).where(Turno.clinica_id == clinica_id, Turno.is_active.is_(True))
    if sede_id:
        stmt = stmt.where(Turno.sede_id == sede_id)
    if desde_dt:
        stmt = stmt.where(Turno.fecha_hora >= desde_dt)
    if hasta_dt:
        stmt = stmt.where(Turno.fecha_hora <= hasta_dt)
    turnos = list((await session.execute(stmt)).scalars().all())

    servicios: dict[int, dict] = {}
    for s in (await session.execute(
        select(Servicio).where(Servicio.clinica_id == clinica_id)
    )).scalars().all():
        servicios[s.id] = {"nombre": s.nombre, "precio": s.precio or Decimal("0"), "duracion_min": s.duracion_min}

    profesionales: dict[int, str] = {}
    for p in (await session.execute(
        select(Profesional).where(Profesional.clinica_id == clinica_id)
    )).scalars().all():
        profesionales[p.id] = p.nombre_completo

    items_por_turno: dict[int, list] = {}
    turno_ids = [t.id for t in turnos]
    if turno_ids:
        items = (await session.execute(
            select(TurnoServicio).where(TurnoServicio.turno_id.in_(turno_ids))
        )).scalars().all()
        for it in items:
            items_por_turno.setdefault(it.turno_id, []).append(it)

    return turnos, items_por_turno, servicios, profesionales


async def analiticas(
    session: AsyncSession, clinica_id: int, *,
    desde: str | None = None, hasta: str | None = None, sede_id: int = 0,
) -> dict[str, Any]:
    """Panel de analíticas ampliadas para un rango de fechas (por defecto: mes en curso)."""
    if not desde and not hasta:
        now = datetime.now(timezone.utc)
        desde = now.replace(day=1).strftime("%Y-%m-%d")
    desde_dt, hasta_dt = _rango_fechas(desde, hasta)

    turnos, items_por_turno, servicios, profesionales = await _cargar_datos_analiticas(
        session, clinica_id, desde_dt=desde_dt, hasta_dt=hasta_dt, sede_id=sede_id,
    )
    resultado = _calcular_analiticas(turnos, items_por_turno, servicios, profesionales)
    resultado["desde"] = desde or ""
    resultado["hasta"] = hasta or ""
    return resultado
