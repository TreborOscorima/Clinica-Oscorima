from __future__ import annotations

from typing import Any

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import turnos as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class TurnosState(BaseState):

    turnos:           list[dict] = []
    total:            int        = 0
    page:             int        = 1
    per_page:         int        = 20
    total_pages:      int        = 1
    filtro_estado:    str        = ""
    filtro_fecha_desde: str      = ""
    filtro_fecha_hasta: str      = ""

    # Modal nuevo turno
    modal_nuevo:         bool = False
    form_paciente_id: str  = ""
    form_profesional_id: str = ""
    form_servicio_id: str = ""
    form_fecha_hora:  str  = ""
    form_error:       str  = ""
    is_saving:        bool = False

    # Modal cambiar estado
    modal_estado:      bool = False
    turno_sel_id:      int  = 0
    form_nuevo_estado: str  = ""
    form_motivo:       str  = ""

    # Modal reprogramar
    modal_reprogramar:       bool = False
    form_reprogramar_fecha:  str  = ""

    # Catálogos simplificados (id, nombre)
    pacientes_cat:    list[dict] = []
    profesionales_cat: list[dict] = []
    servicios_cat:    list[dict] = []

    def on_mount(self):
        return self.require_auth() or self._cargar_catalogos() or self.cargar()

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
                ).limit(200)
            ).all()
            profs = session.exec(select(Profesional).limit(100)).all()
            servs = session.exec(
                select(Servicio).where(
                    Servicio.clinica_id == self.clinica_id,
                    Servicio.is_active.is_(True),
                ).limit(200)
            ).all()
            self.pacientes_cat    = [{"id": str(p.id), "nombre": p.nombre} for p in pacs]
            self.profesionales_cat = [
                {"id": str(p.id), "nombre": f"{p.nombres} {p.apellidos}"}
                for p in profs
            ]
            self.servicios_cat = [{"id": str(s.id), "nombre": s.nombre} for s in servs]

    def cargar(self):
        with get_session() as session:
            result = svc.listar(
                session,
                self.clinica_id,
                estado=self.filtro_estado,
                fecha_desde=self.filtro_fecha_desde,
                fecha_hasta=self.filtro_fecha_hasta,
                page=self.page,
                per_page=self.per_page,
            )
        self.turnos      = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]

    def set_filtro_estado(self, valor: str):
        self.filtro_estado = valor
        self.page = 1
        return self.cargar()

    # ── Setters de formulario (Reflex 0.9.x no auto-genera setters en sub-states)
    def set_form_paciente_id(self, v: str):       self.form_paciente_id = v
    def set_form_profesional_id(self, v: str):    self.form_profesional_id = v
    def set_form_servicio_id(self, v: str):       self.form_servicio_id = v
    def set_form_fecha_hora(self, v: str):        self.form_fecha_hora = v
    def set_form_nuevo_estado(self, v: str):      self.form_nuevo_estado = v
    def set_form_motivo(self, v: str):            self.form_motivo = v
    def set_form_reprogramar_fecha(self, v: str): self.form_reprogramar_fecha = v

    def set_filtro_fecha_desde(self, v: str):
        self.filtro_fecha_desde = v
        self.page = 1
        return self.cargar()

    def set_filtro_fecha_hasta(self, v: str):
        self.filtro_fecha_hasta = v
        self.page = 1
        return self.cargar()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            return self.cargar()

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            return self.cargar()

    # ── Modal nuevo turno ──────────────────────────────────────────────────────

    def abrir_nuevo(self):
        self.form_paciente_id    = ""
        self.form_profesional_id = ""
        self.form_servicio_id    = ""
        self.form_fecha_hora     = ""
        self.form_error          = ""
        self.modal_nuevo         = True

    def cerrar_nuevo(self):
        self.modal_nuevo = False

    async def guardar_turno(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        if not self.form_paciente_id or not self.form_fecha_hora:
            self.form_error = "Paciente y fecha/hora son obligatorios"
            self.is_saving  = False
            return

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

    # ── Modal cambiar estado ───────────────────────────────────────────────────

    def abrir_estado(self, turno: dict):
        self.turno_sel_id     = turno.get("id") or 0
        self.form_nuevo_estado = turno.get("estado") or ""
        self.form_motivo      = ""
        self.modal_estado     = True

    def cerrar_estado(self):
        self.modal_estado = False

    def guardar_estado(self):
        try:
            with get_session() as session:
                svc.cambiar_estado(
                    session,
                    self.clinica_id,
                    self.turno_sel_id,
                    {"estado": self.form_nuevo_estado, "motivo_cancelacion": self.form_motivo},
                )
        except ServiceError:
            pass
        self.modal_estado = False
        return self.cargar()

    def guardar_estado_y_cobrar(self):
        try:
            with get_session() as session:
                svc.cambiar_estado(
                    session,
                    self.clinica_id,
                    self.turno_sel_id,
                    {"estado": "atendido", "motivo_cancelacion": ""},
                )
        except ServiceError:
            pass
        self.modal_estado = False
        return rx.redirect(f"/cobro?turno_id={self.turno_sel_id}")

    # ── Ir a cobrar ────────────────────────────────────────────────────────────

    def ir_a_cobro(self, turno: dict):
        turno_id = turno.get("id") or 0
        return rx.redirect(f"/cobro?turno_id={turno_id}")

    # ── Modal reprogramar ──────────────────────────────────────────────────────

    def abrir_reprogramar(self, turno: dict):
        self.turno_sel_id           = turno.get("id") or 0
        self.form_reprogramar_fecha = turno.get("fecha_hora", "").replace(" ", "T")
        self.modal_reprogramar      = True

    def cerrar_reprogramar(self):
        self.modal_reprogramar = False

    def guardar_reprogramar(self):
        if not self.form_reprogramar_fecha:
            return
        try:
            with get_session() as session:
                svc.reprogramar(
                    session,
                    self.clinica_id,
                    self.turno_sel_id,
                    {"fecha_hora": self.form_reprogramar_fecha},
                )
        except ServiceError:
            pass
        self.modal_reprogramar = False
        return self.cargar()
