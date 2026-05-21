from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from clinica_app.config import REPORT_EXPORT_DIR
from clinica_app.database import get_session
from clinica_app.models.caja import CajaMovimiento, TipoMovimiento
from clinica_app.models.paciente import Paciente
from clinica_app.models.turno import Turno
from sqlalchemy import func, select


def generar_reporte(clinica_id: int, tipo: str, params: dict[str, Any]) -> str:
    """Worker RQ: genera el archivo y retorna su path relativo."""
    os.makedirs(REPORT_EXPORT_DIR, exist_ok=True)

    if tipo == "pacientes":
        return _reporte_pacientes(clinica_id, params)
    if tipo == "caja":
        return _reporte_caja(clinica_id, params)
    if tipo == "turnos":
        return _reporte_turnos(clinica_id, params)
    raise ValueError(f"Tipo de reporte desconocido: {tipo}")


def _reporte_pacientes(clinica_id: int, params: dict) -> str:
    import openpyxl

    with get_session() as session:
        rows = session.exec(
            select(Paciente).where(
                Paciente.clinica_id == clinica_id,
                Paciente.is_active.is_(True),
            ).order_by(Paciente.nombre)
        ).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pacientes"
    ws.append(["ID", "Nombre", "Documento", "Email", "Teléfono", "Registrado"])
    for p in rows:
        ws.append([
            p.id, p.nombre, p.documento, p.email, p.telefono,
            p.created_at.strftime("%Y-%m-%d") if p.created_at else "",
        ])

    filename = f"pacientes_{clinica_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.xlsx"
    path = os.path.join(REPORT_EXPORT_DIR, filename)
    wb.save(path)
    return path


def _reporte_caja(clinica_id: int, params: dict) -> str:
    import openpyxl

    desde_str = params.get("desde")
    hasta_str = params.get("hasta")

    with get_session() as session:
        stmt = select(CajaMovimiento).where(
            CajaMovimiento.clinica_id == clinica_id,
            CajaMovimiento.is_active.is_(True),
        )
        if desde_str:
            stmt = stmt.where(CajaMovimiento.fecha >= datetime.fromisoformat(desde_str))
        if hasta_str:
            stmt = stmt.where(CajaMovimiento.fecha <= datetime.fromisoformat(hasta_str))
        rows = session.exec(stmt.order_by(CajaMovimiento.fecha.desc())).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Caja"
    ws.append(["ID", "Fecha", "Tipo", "Monto", "Método", "Observación"])
    for m in rows:
        ws.append([
            m.id,
            m.fecha.strftime("%Y-%m-%d %H:%M") if m.fecha else "",
            m.tipo.value if m.tipo else "",
            float(m.monto),
            m.metodo_pago.value if m.metodo_pago else "",
            m.observacion or "",
        ])

    filename = f"caja_{clinica_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.xlsx"
    path = os.path.join(REPORT_EXPORT_DIR, filename)
    wb.save(path)
    return path


def _reporte_turnos(clinica_id: int, params: dict) -> str:
    import openpyxl

    with get_session() as session:
        rows = session.exec(
            select(Turno).where(
                Turno.clinica_id == clinica_id,
                Turno.is_active.is_(True),
            ).order_by(Turno.fecha_hora.desc())
        ).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Turnos"
    ws.append(["ID", "Paciente ID", "Profesional ID", "Fecha/Hora", "Estado"])
    for t in rows:
        ws.append([
            t.id,
            t.paciente_id,
            t.profesional_id,
            t.fecha_hora.strftime("%Y-%m-%d %H:%M") if t.fecha_hora else "",
            t.estado.value if t.estado else "",
        ])

    filename = f"turnos_{clinica_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.xlsx"
    path = os.path.join(REPORT_EXPORT_DIR, filename)
    wb.save(path)
    return path
