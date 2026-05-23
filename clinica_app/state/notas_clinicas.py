from __future__ import annotations

from typing import Any

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import notas_clinicas as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class NotasClinicasState(BaseState):

    notas:       list[dict] = []
    total:       int        = 0
    page:        int        = 1
    per_page:    int        = 20
    total_pages: int        = 1

    # Paciente activo
    paciente_id:     int = 0
    paciente_nombre: str = ""

    # Modal nueva/editar nota
    modal_abierto:  bool = False
    editar_id:      int  = 0
    form_tipo:      str  = "evolucion"
    form_contenido: str  = ""
    form_turno_id:  str  = ""
    form_error:     str  = ""
    is_saving:      bool = False

    # Catálogos
    profesionales_cat: list[dict] = []

    def on_mount(self):
        if redir := self.require_auth():
            return redir
        self._cargar_catalogos()
        # Leer paciente_id desde query param ?paciente_id=X
        pid_str = self.router.url.query_parameters.get("paciente_id", "")
        if pid_str:
            try:
                self.paciente_id = int(pid_str)
                self._cargar_nombre_paciente()
                self.cargar()
            except (ValueError, TypeError):
                pass

    def _cargar_nombre_paciente(self):
        from clinica_app.models.paciente import Paciente
        from sqlmodel import select
        with get_session() as session:
            p = session.exec(
                select(Paciente).where(
                    Paciente.id == self.paciente_id,
                    Paciente.clinica_id == self.clinica_id,
                )
            ).first()
            if p:
                self.paciente_nombre = p.nombre

    def _cargar_catalogos(self):
        from clinica_app.models.profesional import Profesional
        from sqlmodel import select
        with get_session() as session:
            profs = session.exec(select(Profesional).limit(100)).all()
            self.profesionales_cat = [
                {"id": str(p.id), "nombre": f"{p.nombres} {p.apellidos}"}
                for p in profs
            ]

    def cargar(self):
        if not self.paciente_id:
            return
        with get_session() as session:
            result = svc.listar_por_paciente(
                session,
                self.clinica_id,
                self.paciente_id,
                page=self.page,
                per_page=self.per_page,
            )
        self.notas       = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]

    def set_paciente(self, paciente_id: int, nombre: str):
        self.paciente_id     = paciente_id
        self.paciente_nombre = nombre
        self.page            = 1
        return self.cargar()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            return self.cargar()

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            return self.cargar()

    # ── Setters ────────────────────────────────────────────────────────────────

    def set_form_tipo(self, v: str):      self.form_tipo = v
    def set_form_contenido(self, v: str): self.form_contenido = v
    def set_form_turno_id(self, v: str):  self.form_turno_id = v

    # ── Modal ──────────────────────────────────────────────────────────────────

    def abrir_nueva(self):
        self.editar_id      = 0
        self.form_tipo      = "evolucion"
        self.form_contenido = ""
        self.form_turno_id  = ""
        self.form_error     = ""
        self.modal_abierto  = True

    def abrir_editar(self, nota: dict):
        self.editar_id      = nota.get("id") or 0
        self.form_tipo      = nota.get("tipo") or "evolucion"
        self.form_contenido = nota.get("contenido") or ""
        self.form_turno_id  = str(nota.get("turno_id") or "")
        self.form_error     = ""
        self.modal_abierto  = True

    def cerrar_modal(self):
        self.modal_abierto = False

    async def guardar(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        payload: dict[str, Any] = {
            "paciente_id":    self.paciente_id,
            "tipo":           self.form_tipo,
            "contenido":      self.form_contenido,
            "turno_id":       int(self.form_turno_id) if self.form_turno_id.strip() else None,
            "profesional_id": self.user_id if self.is_profesional else None,
        }
        try:
            with get_session() as session:
                if self.editar_id:
                    svc.actualizar(session, self.clinica_id, self.editar_id, payload)
                else:
                    svc.crear(session, self.clinica_id, payload, created_by_id=self.user_id)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        self.cargar()

    def eliminar(self, nota_id: int):
        try:
            with get_session() as session:
                svc.eliminar(session, self.clinica_id, nota_id)
        except ServiceError:
            pass
        return self.cargar()
