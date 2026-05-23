from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import reflex as rx

from clinica_app.database import get_session
from clinica_app.state.base import BaseState

_DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
_HORAS   = [f"{h:02d}:00" for h in range(7, 21)]  # 07:00 – 20:00


class CalendarioState(BaseState):

    # Semana actual — almacenamos como string ISO para que sea serializable
    semana_inicio: str = ""   # lunes de la semana actual

    # Turnos de la semana: lista plana de dicts
    turnos_semana: list[dict] = []

    # Catálogos
    profesionales_cat: list[dict] = []
    filtro_profesional_id: str = ""

    # Modal nuevo turno (inline en el calendario)
    modal_nuevo:         bool = False
    form_paciente_id:    str  = ""
    form_profesional_id: str  = ""
    form_servicio_id:    str  = ""
    form_fecha_hora:     str  = ""
    form_error:          str  = ""
    is_saving:           bool = False
    pacientes_cat:       list[dict] = []
    servicios_cat:       list[dict] = []

    # ── Computed vars ──────────────────────────────────────────────────────────

    @rx.var
    def dias_semana(self) -> list[dict]:
        """Lista de 7 dicts: {label: 'Lun 3', iso: '2025-01-06', turnos_count: N}"""
        if not self.semana_inicio:
            return []
        try:
            inicio = date.fromisoformat(self.semana_inicio)
        except ValueError:
            return []
        dias = []
        for i, label in enumerate(_DIAS_ES):
            dia = inicio + timedelta(days=i)
            iso = dia.isoformat()
            count = sum(1 for t in self.turnos_semana if t.get("fecha_hora", "").startswith(iso))
            dias.append({"label": f"{label} {dia.day}", "iso": iso, "count": count})
        return dias

    @rx.var
    def grilla_horas(self) -> list[dict]:
        """Filas de la tabla: [{hora, celdas: [{dia_iso, hora, fecha_hora_key, turnos: [...]}]}]"""
        if not self.semana_inicio:
            return []
        dias = self.dias_semana
        rows = []
        for hora in [f"{h:02d}:00" for h in range(7, 21)]:
            hora_prefix = hora[:2]
            celdas = []
            for dia in dias:
                iso = dia["iso"]
                prefix = f"{iso} {hora_prefix}"
                celdas.append({
                    "dia_iso": iso,
                    "hora": hora,
                    "fecha_hora_key": f"{iso}T{hora}",
                    "turnos": [
                        {
                            "hora": t.get("hora", ""),
                            "paciente_nombre": t.get("paciente_nombre", ""),
                            "profesional_nombre": t.get("profesional_nombre", ""),
                            "servicio_nombre": t.get("servicio_nombre", ""),
                            "estado": t.get("estado", ""),
                        }
                        for t in self.turnos_semana
                        if t.get("fecha_hora", "").startswith(prefix)
                    ],
                })
            rows.append({"hora": hora, "celdas": celdas})
        return rows

    @rx.var
    def rango_label(self) -> str:
        if not self.semana_inicio:
            return ""
        try:
            inicio = date.fromisoformat(self.semana_inicio)
            fin    = inicio + timedelta(days=6)
            meses  = ["", "ene", "feb", "mar", "abr", "may", "jun",
                      "jul", "ago", "sep", "oct", "nov", "dic"]
            return f"{inicio.day} {meses[inicio.month]} – {fin.day} {meses[fin.month]} {fin.year}"
        except (ValueError, IndexError):
            return ""

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _lunes_de(self, d: date) -> date:
        return d - timedelta(days=d.weekday())

    def on_mount(self):
        if redir := self.require_auth():
            return redir
        hoy = date.today()
        self.semana_inicio = self._lunes_de(hoy).isoformat()
        self._cargar_catalogos()
        self.cargar()

    def _cargar_catalogos(self):
        from clinica_app.models.paciente import Paciente
        from clinica_app.models.profesional import Profesional
        from clinica_app.models.servicio import Servicio
        from sqlmodel import select
        with get_session() as session:
            pacs = session.exec(
                select(Paciente).where(
                    Paciente.clinica_id == self.clinica_id,
                    Paciente.is_active.is_(True),
                ).limit(300)
            ).all()
            profs = session.exec(select(Profesional).limit(100)).all()
            servs = session.exec(
                select(Servicio).where(
                    Servicio.clinica_id == self.clinica_id,
                    Servicio.is_active.is_(True),
                ).limit(200)
            ).all()
            self.pacientes_cat = [{"id": str(p.id), "nombre": p.nombre} for p in pacs]
            self.profesionales_cat = [
                {"id": str(p.id), "nombre": f"{p.nombres} {p.apellidos}"}
                for p in profs
            ]
            self.servicios_cat = [{"id": str(s.id), "nombre": s.nombre} for s in servs]

    def cargar(self):
        if not self.semana_inicio:
            return
        try:
            inicio_date = date.fromisoformat(self.semana_inicio)
            fin_date    = inicio_date + timedelta(days=7)
            inicio_dt   = datetime(inicio_date.year, inicio_date.month, inicio_date.day, 0, 0, 0)
            fin_dt      = datetime(fin_date.year,    fin_date.month,    fin_date.day,    0, 0, 0)
        except ValueError:
            return

        from clinica_app.models.turno import Turno
        from clinica_app.models.paciente import Paciente
        from clinica_app.models.profesional import Profesional
        from sqlmodel import select
        from sqlalchemy.orm import selectinload

        with get_session() as session:
            stmt = (
                select(Turno)
                .options(
                    selectinload(Turno.paciente),
                    selectinload(Turno.profesional),
                    selectinload(Turno.servicio),
                )
                .where(
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                    Turno.fecha_hora >= inicio_dt,
                    Turno.fecha_hora < fin_dt,
                )
                .order_by(Turno.fecha_hora)
            )
            if self.filtro_profesional_id:
                try:
                    stmt = stmt.where(Turno.profesional_id == int(self.filtro_profesional_id))
                except ValueError:
                    pass

            turnos = session.exec(stmt).all()
            self.turnos_semana = [
                {
                    "id":                t.id,
                    "paciente_nombre":   getattr(t.paciente, "nombre", "—"),
                    "profesional_nombre": (
                        f"{getattr(t.profesional, 'nombres', '')} {getattr(t.profesional, 'apellidos', '')}".strip()
                        if t.profesional else "—"
                    ),
                    "servicio_nombre":   getattr(t.servicio, "nombre", "—") if t.servicio else "—",
                    "fecha_hora":        t.fecha_hora.strftime("%Y-%m-%d %H:%M") if t.fecha_hora else "",
                    "hora":              t.fecha_hora.strftime("%H:%M") if t.fecha_hora else "",
                    "estado":            t.estado.value if t.estado else "pendiente",
                }
                for t in turnos
            ]

    # ── Navegación ─────────────────────────────────────────────────────────────

    def semana_anterior(self):
        try:
            d = date.fromisoformat(self.semana_inicio) - timedelta(weeks=1)
            self.semana_inicio = d.isoformat()
            self.cargar()
        except ValueError:
            pass

    def semana_siguiente(self):
        try:
            d = date.fromisoformat(self.semana_inicio) + timedelta(weeks=1)
            self.semana_inicio = d.isoformat()
            self.cargar()
        except ValueError:
            pass

    def ir_a_hoy(self):
        self.semana_inicio = self._lunes_de(date.today()).isoformat()
        self.cargar()

    def set_filtro_profesional_id(self, v: str):
        self.filtro_profesional_id = v
        self.cargar()

    # ── Modal nuevo turno ──────────────────────────────────────────────────────

    def abrir_nuevo(self, fecha_hora: str = ""):
        self.form_paciente_id    = ""
        self.form_profesional_id = self.filtro_profesional_id
        self.form_servicio_id    = ""
        self.form_fecha_hora     = fecha_hora
        self.form_error          = ""
        self.modal_nuevo         = True

    def cerrar_nuevo(self):
        self.modal_nuevo = False

    def set_form_paciente_id(self, v: str):    self.form_paciente_id = v
    def set_form_profesional_id(self, v: str): self.form_profesional_id = v
    def set_form_servicio_id(self, v: str):    self.form_servicio_id = v
    def set_form_fecha_hora(self, v: str):     self.form_fecha_hora = v

    async def guardar_turno(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        if not self.form_paciente_id or not self.form_fecha_hora:
            self.form_error = "Paciente y fecha/hora son obligatorios"
            self.is_saving  = False
            return

        from clinica_app.services import turnos as svc
        from clinica_app.services.exceptions import ServiceError
        payload: dict[str, Any] = {
            "paciente_id":    int(self.form_paciente_id),
            "profesional_id": int(self.form_profesional_id) if self.form_profesional_id else None,
            "servicio_id":    int(self.form_servicio_id) if self.form_servicio_id else None,
            "fecha_hora":     self.form_fecha_hora,
        }
        try:
            with get_session() as session:
                svc.crear(session, self.clinica_id, payload, created_by_id=self.user_id)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving   = False
        self.modal_nuevo = False
        self.cargar()
