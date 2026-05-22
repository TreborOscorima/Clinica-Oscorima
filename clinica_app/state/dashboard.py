from __future__ import annotations

from datetime import datetime, timedelta, timezone

import reflex as rx

from clinica_app.database import get_session
from clinica_app.models.caja import CajaMovimiento, ComprobanteItem, Comprobante, TipoMovimiento
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

    # Gráfico ingresos 7 días  {"fecha": "Lun", "monto": "$1500.00", "pct": "75%"}
    ingresos_7dias:   list[dict] = []

    # Top 5 servicios del mes  {"nombre": "Limpieza facial", "count": "12", "total": "1800.00"}
    top_servicios:    list[dict] = []

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
            ).scalar_one()

            # Turnos hoy
            self.turnos_hoy = session.exec(
                select(func.count(Turno.id)).where(
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                    Turno.fecha_hora >= inicio_hoy,
                    Turno.fecha_hora <= fin_hoy,
                )
            ).scalar_one()

            # Turnos pendientes
            self.turnos_pendientes = session.exec(
                select(func.count(Turno.id)).where(
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                    Turno.estado == EstadoTurno.PENDIENTE,
                )
            ).scalar_one()

            # Ingresos hoy
            ingreso = session.exec(
                select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
                    CajaMovimiento.clinica_id == self.clinica_id,
                    CajaMovimiento.is_active.is_(True),
                    CajaMovimiento.tipo == TipoMovimiento.INGRESO,
                    CajaMovimiento.fecha >= inicio_hoy,
                    CajaMovimiento.fecha <= fin_hoy,
                )
            ).scalar_one()
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
                    "id":              t.id,
                    "paciente_nombre": t.paciente.nombre if t.paciente else f"#{t.paciente_id}",
                    "fecha_hora":      t.fecha_hora.strftime("%d/%m %H:%M") if t.fecha_hora else "",
                    "estado":          t.estado.value if t.estado else "",
                }
                for t in turnos
            ]

            # Ingresos últimos 7 días
            dias_labels = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
            dias_data: list[dict] = []
            max_monto = 0.0
            for offset in range(6, -1, -1):
                dia = ahora - timedelta(days=offset)
                d_ini = dia.replace(hour=0, minute=0, second=0, microsecond=0)
                d_fin = dia.replace(hour=23, minute=59, second=59, microsecond=999999)
                monto_dia = session.exec(
                    select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
                        CajaMovimiento.clinica_id == self.clinica_id,
                        CajaMovimiento.is_active.is_(True),
                        CajaMovimiento.tipo == TipoMovimiento.INGRESO,
                        CajaMovimiento.fecha >= d_ini,
                        CajaMovimiento.fecha <= d_fin,
                    )
                ).scalar_one()
                m = float(monto_dia or 0)
                if m > max_monto:
                    max_monto = m
                dias_data.append({
                    "fecha": dias_labels[dia.weekday() + 1 if dia.weekday() < 6 else 0],
                    "monto": f"{m:.2f}",
                    "raw":   m,
                })
            # Calcular porcentaje para altura de barra
            self.ingresos_7dias = [
                {
                    "fecha": d["fecha"],
                    "monto": f"${d['monto']}",
                    "pct":   f"{int(d['raw'] / max_monto * 100)}%" if max_monto > 0 else "5%",
                }
                for d in dias_data
            ]

            # Top 5 servicios del mes
            inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            top_raw = session.execute(
                select(
                    ComprobanteItem.nombre,
                    func.count(ComprobanteItem.id).label("cnt"),
                    func.coalesce(
                        func.sum(ComprobanteItem.precio_unit * ComprobanteItem.cantidad), 0
                    ).label("total"),
                )
                .join(Comprobante, Comprobante.id == ComprobanteItem.comprobante_id)
                .where(
                    Comprobante.clinica_id == self.clinica_id,
                    ComprobanteItem.tipo == "servicio",
                    Comprobante.fecha >= inicio_mes,
                )
                .group_by(ComprobanteItem.nombre)
                .order_by(func.count(ComprobanteItem.id).desc())
                .limit(5)
            ).all()
            self.top_servicios = [
                {
                    "nombre": row.nombre or "—",
                    "count":  str(row.cnt),
                    "total":  f"{float(row.total or 0):.2f}",
                }
                for row in top_raw
            ]
