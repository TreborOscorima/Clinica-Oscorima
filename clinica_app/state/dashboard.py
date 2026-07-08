from __future__ import annotations

from datetime import datetime, date, timedelta, timezone

import reflex as rx
from sqlalchemy import cast, Date as SADate, func
from sqlmodel import select

from clinica_app.database import get_async_session
from clinica_app.models.caja import CajaMovimiento, ComprobanteItem, Comprobante, TipoMovimiento
from clinica_app.models.paciente import Paciente
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.state.base import BaseState


class DashboardState(BaseState):

    # KPIs
    total_pacientes:   int = 0
    turnos_hoy:        int = 0
    ingresos_hoy:      str = "0.00"
    turnos_pendientes: int = 0
    turnos_recientes:  list[dict] = []
    is_loading:        bool = False

    # Gráfico ingresos 7 días
    ingresos_7dias: list[dict] = []

    # Top 5 servicios del mes
    top_servicios: list[dict] = []

    # Agenda del profesional
    mis_turnos_hoy: list[dict] = []

    # Dashboard financiero avanzado
    ingresos_mes:     str = "0.00"
    egresos_mes:      str = "0.00"
    saldo_mes:        str = "0.00"
    ingresos_mes_ant: str = "0.00"
    variacion_pct:    str = "0"
    top_servicios_margen: list[dict] = []

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        async for s in self.cargar():
            yield s

    # ── Carga progresiva — Fase 3: N+1 eliminado en 7 días con GROUP BY ────────

    async def cargar(self):
        self.is_loading = True
        yield

        ahora      = datetime.now(timezone.utc)
        inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_hoy    = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)
        sid        = self.sede_actual_id  # 0 = sin filtro de sucursal

        async with get_async_session() as session:
            # Total pacientes activos
            q_pac = select(func.count(Paciente.id)).where(
                Paciente.clinica_id == self.clinica_id,
                Paciente.is_active.is_(True),
            )
            if sid:
                q_pac = q_pac.where(Paciente.sede_id == sid)
            self.total_pacientes = (await session.execute(q_pac)).scalar_one()

            # Turnos hoy
            q_th = select(func.count(Turno.id)).where(
                Turno.clinica_id == self.clinica_id,
                Turno.is_active.is_(True),
                Turno.fecha_hora >= inicio_hoy,
                Turno.fecha_hora <= fin_hoy,
            )
            if sid:
                q_th = q_th.where(Turno.sede_id == sid)
            self.turnos_hoy = (await session.execute(q_th)).scalar_one()

            # Turnos pendientes
            q_tp = select(func.count(Turno.id)).where(
                Turno.clinica_id == self.clinica_id,
                Turno.is_active.is_(True),
                Turno.estado == EstadoTurno.PENDIENTE,
            )
            if sid:
                q_tp = q_tp.where(Turno.sede_id == sid)
            self.turnos_pendientes = (await session.execute(q_tp)).scalar_one()

            # Ingresos hoy
            q_ih = select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
                CajaMovimiento.clinica_id == self.clinica_id,
                CajaMovimiento.is_active.is_(True),
                CajaMovimiento.tipo == TipoMovimiento.INGRESO,
                CajaMovimiento.fecha >= inicio_hoy,
                CajaMovimiento.fecha <= fin_hoy,
            )
            if sid:
                q_ih = q_ih.where(CajaMovimiento.sede_id == sid)
            ingreso = (await session.execute(q_ih)).scalar_one()
            self.ingresos_hoy = f"{float(ingreso or 0):.2f}"

            # ── Ingresos 7 días — una sola consulta GROUP BY ──────────────────
            siete_dias_atras = (ahora - timedelta(days=6)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            q_7d = (
                select(
                    cast(CajaMovimiento.fecha, SADate).label("dia"),
                    func.coalesce(func.sum(CajaMovimiento.monto), 0).label("monto"),
                )
                .where(
                    CajaMovimiento.clinica_id == self.clinica_id,
                    CajaMovimiento.is_active.is_(True),
                    CajaMovimiento.tipo == TipoMovimiento.INGRESO,
                    CajaMovimiento.fecha >= siete_dias_atras,
                )
                .group_by(cast(CajaMovimiento.fecha, SADate))
            )
            if sid:
                q_7d = q_7d.where(CajaMovimiento.sede_id == sid)
            rows_7dias = (await session.execute(q_7d)).all()

            mapa_7dias: dict[date, float] = {row.dia: float(row.monto) for row in rows_7dias}
            dias_labels = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
            dias_data: list[dict] = []
            max_monto = 0.0
            for offset in range(6, -1, -1):
                dia     = ahora - timedelta(days=offset)
                dia_key = dia.date()
                m       = mapa_7dias.get(dia_key, 0.0)
                if m > max_monto:
                    max_monto = m
                dias_data.append({
                    "fecha": dias_labels[(dia.weekday() + 1) % 7],
                    "monto": f"{m:.2f}",
                    "raw":   m,
                })
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
            q_top = (
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
            )
            if sid:
                q_top = q_top.where(Comprobante.sede_id == sid)
            top_raw = (await session.execute(q_top)).all()
            self.top_servicios = [
                {
                    "nombre": row.nombre or "—",
                    "count":  str(row.cnt),
                    "total":  f"{float(row.total or 0):.2f}",
                }
                for row in top_raw
            ]

            # ── Financiero del mes ─────────────────────────────────────────────
            fin_mes = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)

            async def _suma_caja(tipo, desde, hasta) -> float:
                q = select(func.coalesce(func.sum(CajaMovimiento.monto), 0)).where(
                    CajaMovimiento.clinica_id == self.clinica_id,
                    CajaMovimiento.is_active.is_(True),
                    CajaMovimiento.tipo == tipo,
                    CajaMovimiento.fecha >= desde,
                    CajaMovimiento.fecha <= hasta,
                )
                if sid:
                    q = q.where(CajaMovimiento.sede_id == sid)
                return float((await session.execute(q)).scalar_one() or 0)

            ing_mes = await _suma_caja(TipoMovimiento.INGRESO, inicio_mes, fin_mes)
            egr_mes = await _suma_caja(TipoMovimiento.EGRESO,  inicio_mes, fin_mes)
            self.ingresos_mes = f"{ing_mes:.2f}"
            self.egresos_mes  = f"{egr_mes:.2f}"
            self.saldo_mes    = f"{ing_mes - egr_mes:.2f}"

            mes_ant_fin = inicio_mes - timedelta(seconds=1)
            mes_ant_ini = mes_ant_fin.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ing_ant = await _suma_caja(TipoMovimiento.INGRESO, mes_ant_ini, mes_ant_fin)
            self.ingresos_mes_ant = f"{ing_ant:.2f}"
            if ing_ant > 0:
                pct = ((ing_mes - ing_ant) / ing_ant) * 100
                self.variacion_pct = f"{pct:+.1f}"
            else:
                self.variacion_pct = "+100" if ing_mes > 0 else "0"

            # Agenda del profesional (si aplica)
            if self.user_role == "profesional" and self.profesional_id:
                from sqlalchemy.orm import selectinload
                q_mis = (
                    select(Turno)
                    .where(
                        Turno.clinica_id == self.clinica_id,
                        Turno.is_active.is_(True),
                        Turno.profesional_id == self.profesional_id,
                        Turno.fecha_hora >= inicio_hoy,
                        Turno.fecha_hora <= fin_hoy,
                    )
                    .options(
                        selectinload(Turno.paciente),
                        selectinload(Turno.servicio),
                    )
                    .order_by(Turno.fecha_hora)
                )
                if sid:
                    q_mis = q_mis.where(Turno.sede_id == sid)
                mis = (await session.execute(q_mis)).scalars().all()
                self.mis_turnos_hoy = [
                    {
                        "id":              t.id,
                        "paciente_nombre": t.paciente.nombre if t.paciente else f"#{t.paciente_id}",
                        "hora":            t.fecha_hora.strftime("%H:%M") if t.fecha_hora else "",
                        "servicio":        t.servicio.nombre if t.servicio else "—",
                        "estado":          t.estado.value if t.estado else "",
                    }
                    for t in mis
                ]

            # Turnos recientes con relaciones pre-cargadas
            from sqlalchemy.orm import selectinload as sl
            q_rec = (
                select(Turno)
                .where(
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                )
                .options(sl(Turno.paciente))
                .order_by(Turno.fecha_hora.desc())
                .limit(5)
            )
            if sid:
                q_rec = q_rec.where(Turno.sede_id == sid)
            turnos_rec = (await session.execute(q_rec)).scalars().all()
            self.turnos_recientes = [
                {
                    "id":              t.id,
                    "paciente_nombre": t.paciente.nombre if t.paciente else f"#{t.paciente_id}",
                    "fecha_hora":      t.fecha_hora.strftime("%d/%m %H:%M") if t.fecha_hora else "",
                    "estado":          t.estado.value if t.estado else "",
                }
                for t in turnos_rec
            ]

        self.is_loading = False
