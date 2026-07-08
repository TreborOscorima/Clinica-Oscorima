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
from clinica_app.models.turno import Turno


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
