from __future__ import annotations

from datetime import datetime, timezone

import reflex as rx

from clinica_app.database import get_session
from clinica_app.models.caja import CajaMovimiento, TipoMovimiento
from clinica_app.models.paciente import Paciente
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.state.base import BaseState
from sqlalchemy import func, select


class DashboardState(BaseState):

    # KPIs
    total_pacientes:  int = 0
    turnos_hoy:       int = 0
    ingresos_hoy:     str = "0.00"
    turnos_pendientes: int = 0
    turnos_recientes: list[dict] = []

    def on_mount(self):
        return self.require_auth() or self.cargar()

    def cargar(self):
        ahora = datetime.now(timezone.utc)
        inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_hoy    = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)

        with get_session() as session:
            # Total pacientes activos
            self.total_pacientes = session.exec(
                select(func.count(Paciente.id)).where(
                    Paciente.clinica_id == self.clinica_id,
                    Paciente.is_active.is_(True),
                )
            ).one()

            # Turnos hoy
            self.turnos_hoy = session.exec(
                select(func.count(Turno.id)).where(
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                    Turno.fecha_hora >= inicio_hoy,
                    Turno.fecha_hora <= fin_hoy,
                )
            ).one()

            # Turnos pendientes
            self.turnos_pendientes = session.exec(
                select(func.count(Turno.id)).where(
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                    Turno.estado == EstadoTurno.PENDIENTE,
                )
            ).one()

            # Ingresos hoy
            ingreso = session.exec(
                select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
                    CajaMovimiento.clinica_id == self.clinica_id,
                    CajaMovimiento.is_active.is_(True),
                    CajaMovimiento.tipo == TipoMovimiento.INGRESO,
                    CajaMovimiento.fecha >= inicio_hoy,
                    CajaMovimiento.fecha <= fin_hoy,
                )
            ).one()
            self.ingresos_hoy = f"{float(ingreso or 0):.2f}"

            # Turnos recientes (5)
            turnos = session.exec(
                select(Turno)
                .where(
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                )
                .order_by(Turno.fecha_hora.desc())
                .limit(5)
            ).all()
            self.turnos_recientes = [
                {
                    "id":        t.id,
                    "paciente_id": t.paciente_id,
                    "fecha_hora": t.fecha_hora.strftime("%d/%m %H:%M") if t.fecha_hora else "",
                    "estado":    t.estado.value if t.estado else "",
                }
                for t in turnos
            ]
