from __future__ import annotations

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import profesionales as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class ProfesionalesState(BaseState):

    profesionales:  list[dict] = []
    total:          int = 0
    page:           int = 1
    per_page:       int = 20
    total_pages:    int = 1
    busqueda:       str = ""

    # Modal
    modal_abierto:  bool = False
    editando_id:    int  = 0
    form_nombres:   str  = ""
    form_apellidos: str  = ""
    form_dni:       str  = ""
    form_matricula: str  = ""
    form_especialidad: str = ""
    form_telefono:  str  = ""
    form_email:     str  = ""
    form_error:     str  = ""
    is_saving:      bool = False

    def on_mount(self):
        return self.require_auth() or self.cargar()

    def cargar(self):
        with get_session() as session:
            result = svc.listar(
                session,
                self.clinica_id,
                q=self.busqueda,
                page=self.page,
                per_page=self.per_page,
            )
        self.profesionales = result["data"]
        self.total         = result["total"]
        self.total_pages   = result["pages"]

    def set_busqueda(self, valor: str):
        self.busqueda = valor
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

    # ── Setters de formulario ─────────────────────────────────────────────────
    def set_form_nombres(self, v: str):    self.form_nombres = v
    def set_form_apellidos(self, v: str):  self.form_apellidos = v
    def set_form_dni(self, v: str):        self.form_dni = v
    def set_form_matricula(self, v: str):  self.form_matricula = v
    def set_form_especialidad(self, v: str): self.form_especialidad = v
    def set_form_telefono(self, v: str):   self.form_telefono = v
    def set_form_email(self, v: str):      self.form_email = v

    def _limpiar_form(self):
        self.form_nombres = self.form_apellidos = self.form_dni = ""
        self.form_matricula = self.form_especialidad = ""
        self.form_telefono = self.form_email = self.form_error = ""
        self.editando_id = 0

    def abrir_nuevo(self):
        self._limpiar_form()
        self.modal_abierto = True

    def abrir_editar(self, prof: dict):
        self._limpiar_form()
        self.editando_id       = prof.get("id") or 0
        self.form_nombres      = prof.get("nombres") or ""
        self.form_apellidos    = prof.get("apellidos") or ""
        self.form_dni          = prof.get("dni") or ""
        self.form_matricula    = prof.get("matricula") or ""
        self.form_especialidad = prof.get("especialidad") or ""
        self.form_telefono     = prof.get("telefono") or ""
        self.form_email        = prof.get("email") or ""
        self.modal_abierto     = True

    def cerrar_modal(self):
        self.modal_abierto = False
        self._limpiar_form()

    async def guardar(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        payload = {
            "nombres":      self.form_nombres,
            "apellidos":    self.form_apellidos,
            "dni":          self.form_dni,
            "matricula":    self.form_matricula,
            "especialidad": self.form_especialidad,
            "telefono":     self.form_telefono,
            "email":        self.form_email,
        }
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
        self._limpiar_form()
        self.cargar()

    def eliminar(self, prof_id: int):
        try:
            with get_session() as session:
                svc.eliminar(session, self.clinica_id, prof_id)
        except ServiceError:
            pass
        self.cargar()
