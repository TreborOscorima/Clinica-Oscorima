from __future__ import annotations

from typing import Any

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import pacientes as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class PacientesState(BaseState):
    """Estado del módulo Pacientes. clinica_id viene de BaseState."""

    # ── Datos de tabla ─────────────────────────────────────────────────────────
    pacientes:   list[dict] = []
    total:       int        = 0
    page:        int        = 1
    per_page:    int        = 20
    total_pages: int        = 1
    busqueda:    str        = ""

    # ── Modal de creación/edición ──────────────────────────────────────────────
    modal_abierto:   bool = False
    editando_id:     int  = 0     # 0 = creación
    form_nombre:     str  = ""
    form_documento:  str  = ""
    form_email:      str  = ""
    form_telefono:   str  = ""
    form_direccion:  str  = ""
    form_nacimiento: str  = ""
    form_emergencia: str  = ""
    form_error:      str  = ""
    is_saving:       bool = False

    # ── Panel de detalle / historial ───────────────────────────────────────────
    panel_detalle: bool = False
    paciente_sel: dict = {
        "id": 0, "nombre": "", "documento": "", "email": "",
        "telefono": "", "direccion": "", "contacto_emergencia": "", "edad": 0,
    }
    historial_turnos:       list[dict] = []
    historial_comprobantes: list[dict] = []
    historial_deudas:       list[dict] = []

    # ── Carga ─────────────────────────────────────────────────────────────────

    def on_mount(self):
        return self.require_auth() or self.cargar()

    def cargar(self):
        with get_session() as session:
            resultado = svc.listar(
                session,
                self.clinica_id,
                q=self.busqueda,
                page=self.page,
                per_page=self.per_page,
            )
        self.pacientes   = resultado["data"]
        self.total       = resultado["total"]
        self.total_pages = resultado["pages"]

    # ── Búsqueda ───────────────────────────────────────────────────────────────

    def set_busqueda(self, value: str):
        self.busqueda = value
        self.page = 1
        return self.cargar()

    # ── Setters de formulario (Reflex 0.9.x no auto-genera setters en sub-states)
    def set_form_nombre(self, v: str):     self.form_nombre = v
    def set_form_documento(self, v: str):  self.form_documento = v
    def set_form_email(self, v: str):      self.form_email = v
    def set_form_telefono(self, v: str):   self.form_telefono = v
    def set_form_direccion(self, v: str):  self.form_direccion = v
    def set_form_nacimiento(self, v: str): self.form_nacimiento = v
    def set_form_emergencia(self, v: str): self.form_emergencia = v

    # ── Paginación ─────────────────────────────────────────────────────────────

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            return self.cargar()

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            return self.cargar()

    # ── Modal ──────────────────────────────────────────────────────────────────

    def abrir_nuevo(self):
        self._limpiar_form()
        self.editando_id   = 0
        self.modal_abierto = True

    def abrir_editar(self, paciente: dict):
        self._limpiar_form()
        self.editando_id     = paciente.get("id") or 0
        self.form_nombre     = paciente.get("nombre") or ""
        self.form_documento  = paciente.get("documento") or ""
        self.form_email      = paciente.get("email") or ""
        self.form_telefono   = paciente.get("telefono") or ""
        self.form_direccion  = paciente.get("direccion") or ""
        self.form_nacimiento = paciente.get("fecha_nacimiento") or ""
        self.form_emergencia = paciente.get("contacto_emergencia") or ""
        self.modal_abierto   = True

    def cerrar_modal(self):
        self.modal_abierto = False

    def _limpiar_form(self):
        self.form_nombre     = ""
        self.form_documento  = ""
        self.form_email      = ""
        self.form_telefono   = ""
        self.form_direccion  = ""
        self.form_nacimiento = ""
        self.form_emergencia = ""
        self.form_error      = ""

    # ── Guardar ────────────────────────────────────────────────────────────────

    async def guardar(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        payload: dict[str, Any] = {
            "nombre":              self.form_nombre.strip(),
            "documento":           self.form_documento.strip() or None,
            "email":               self.form_email.strip() or None,
            "telefono":            self.form_telefono.strip() or None,
            "direccion":           self.form_direccion.strip() or None,
            "fecha_nacimiento":    self.form_nacimiento or None,
            "contacto_emergencia": self.form_emergencia.strip() or None,
        }

        if not payload["nombre"]:
            self.form_error = "El nombre es obligatorio"
            self.is_saving  = False
            return

        try:
            with get_session() as session:
                if self.editando_id:
                    svc.actualizar(session, self.clinica_id, self.editando_id, payload)
                else:
                    svc.crear(session, self.clinica_id, payload)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        self.cargar()

    # ── Panel de detalle ───────────────────────────────────────────────────────

    def abrir_detalle(self, p: dict):
        from clinica_app.models.caja import Comprobante, DeudaPaciente
        from clinica_app.models.turno import Turno
        from sqlmodel import select

        self.paciente_sel = p
        pac_id = p.get("id") or 0

        with get_session() as session:
            turnos = session.exec(
                select(Turno)
                .where(Turno.paciente_id == pac_id, Turno.is_active.is_(True))
                .order_by(Turno.fecha_hora.desc())
                .limit(10)
            ).all()
            self.historial_turnos = [
                {
                    "fecha_hora":        t.fecha_hora.strftime("%d/%m/%Y %H:%M") if t.fecha_hora else "",
                    "profesional_nombre": t.profesional.nombres + " " + t.profesional.apellidos if t.profesional else "—",
                    "servicio_nombre":   t.servicio.nombre if t.servicio else "—",
                    "estado":            t.estado.value if t.estado else "",
                }
                for t in turnos
            ]

            comprobantes = session.exec(
                select(Comprobante)
                .where(
                    Comprobante.paciente_id == pac_id,
                    Comprobante.clinica_id == self.clinica_id,
                    Comprobante.is_active.is_(True),
                )
                .order_by(Comprobante.fecha.desc())
                .limit(10)
            ).all()
            self.historial_comprobantes = [
                {
                    "numero":     c.numero or f"#{c.id}",
                    "fecha":      c.fecha.strftime("%d/%m/%Y") if c.fecha else "",
                    "total":      f"{float(c.total or 0):.2f}",
                    "forma_pago": c.forma_pago.value if c.forma_pago else "",
                }
                for c in comprobantes
            ]

            deudas = session.exec(
                select(DeudaPaciente)
                .where(
                    DeudaPaciente.paciente_id == pac_id,
                    DeudaPaciente.clinica_id == self.clinica_id,
                    DeudaPaciente.estado != "saldado",
                    DeudaPaciente.is_active.is_(True),
                )
                .order_by(DeudaPaciente.creado_en.desc())
            ).all()
            self.historial_deudas = [
                {
                    "saldo":  f"{float(d.saldo or 0):.2f}",
                    "total":  f"{float(d.total or 0):.2f}",
                    "estado": d.estado or "",
                }
                for d in deudas
            ]

        self.panel_detalle = True

    def cerrar_detalle(self):
        self.panel_detalle = False

    # ── Eliminar ───────────────────────────────────────────────────────────────

    def eliminar(self, paciente_id: int):
        try:
            with get_session() as session:
                svc.eliminar(session, self.clinica_id, paciente_id)
        except ServiceError:
            pass
        return self.cargar()
