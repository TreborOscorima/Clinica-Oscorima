from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlmodel import select
from sqlmodel import Session

from clinica_app.config import REPORT_EXPORT_DIR
from clinica_app.models.caja import CajaMovimiento, TipoMovimiento
from clinica_app.models.paciente import Paciente
from clinica_app.models.turno import Turno


def generar_reporte(clinica_id: int, tipo: str, params: dict[str, Any]) -> str:
    """Genera el Excel en disco. Retorna el nombre del archivo (no el path completo)."""
    from clinica_app.tasks.reportes import generar_reporte as _gen

    os.makedirs(REPORT_EXPORT_DIR, exist_ok=True)
    path = _gen(clinica_id, tipo, params)
    return os.path.basename(path)


def kpis_mes(session: Session, clinica_id: int) -> dict[str, Any]:
    """KPIs del mes en curso para el panel de Reportes."""
    now = datetime.now(timezone.utc)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    ingresos = session.execute(
        select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
            CajaMovimiento.clinica_id == clinica_id,
            CajaMovimiento.is_active.is_(True),
            CajaMovimiento.tipo == TipoMovimiento.INGRESO,
            CajaMovimiento.fecha >= inicio_mes,
        )
    ).scalar_one()

    egresos = session.execute(
        select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
            CajaMovimiento.clinica_id == clinica_id,
            CajaMovimiento.is_active.is_(True),
            CajaMovimiento.tipo == TipoMovimiento.EGRESO,
            CajaMovimiento.fecha >= inicio_mes,
        )
    ).scalar_one()

    turnos = session.execute(
        select(func.count()).select_from(Turno).where(
            Turno.clinica_id == clinica_id,
            Turno.is_active.is_(True),
            Turno.fecha_hora >= inicio_mes,
        )
    ).scalar_one()

    pacientes_nuevos = session.execute(
        select(func.count()).select_from(Paciente).where(
            Paciente.clinica_id == clinica_id,
            Paciente.is_active.is_(True),
            Paciente.created_at >= inicio_mes,
        )
    ).scalar_one()

    D2 = Decimal("0.01")
    return {
        "ingresos":         str(Decimal(str(ingresos or 0)).quantize(D2)),
        "egresos":          str(Decimal(str(egresos or 0)).quantize(D2)),
        "turnos":           int(turnos or 0),
        "pacientes_nuevos": int(pacientes_nuevos or 0),
    }
