from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import agenda as agenda_svc
from clinica_app.services import profesionales as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class ProfesionalesState(BaseState):

    profesionales: list[dict] = []
    total:         int  = 0
    page:          int  = 1
    per_page:      int  = 20
    total_pages:   int  = 1
    busqueda:      str  = ""
    is_loading:    bool = False

    # Modal
    modal_abierto:     bool = False
    editando_id:       int  = 0
    form_nombres:      str  = ""
    form_apellidos:    str  = ""
    form_dni:          str  = ""
    form_matricula:    str  = ""
    form_especialidad: str  = ""
    form_telefono:     str  = ""
    form_email:        str  = ""
    form_error:        str  = ""
    is_saving:         bool = False

    # ── Agenda (disponibilidad + bloqueos) ──────────────────────────────────────
    modal_agenda:       bool = False
    agenda_prof_id:     int  = 0
    agenda_prof_nombre: str  = ""
    disponibilidad:     list[dict] = []
    bloqueos:           list[dict] = []
    dias_cat:           list[dict] = []
    agenda_error:       str  = ""
    # Form disponibilidad
    disp_dia:    str = "0"
    disp_inicio: str = "09:00"
    disp_fin:    str = "13:00"
    # Form bloqueo
    bloq_inicio: str = ""
    bloq_fin:    str = ""
    bloq_motivo: str = ""

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("profesionales"):
            yield rx.redirect("/")
            return
        async for s in self.cargar():
            yield s

    # ── Carga progresiva ───────────────────────────────────────────────────────

    async def cargar(self):
        self.is_loading = True
        yield
        async with get_async_session() as session:
            result = await svc.listar(
                session,
                self.clinica_id,
                sede_id=self.sede_actual_id,
                q=self.busqueda,
                page=self.page,
                per_page=self.per_page,
            )
        self.profesionales = result["data"]
        self.total         = result["total"]
        self.total_pages   = result["pages"]
        self.is_loading    = False

    async def set_busqueda(self, valor: str):
        self.busqueda = valor
        self.page = 1
        async for s in self.cargar():
            yield s

    # ── Paginación ─────────────────────────────────────────────────────────────

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            async for s in self.cargar():
                yield s

    async def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            async for s in self.cargar():
                yield s

    # ── Setters de formulario ──────────────────────────────────────────────────

    def set_form_nombres(self, v: str):      self.form_nombres = v
    def set_form_apellidos(self, v: str):    self.form_apellidos = v
    def set_form_dni(self, v: str):          self.form_dni = v
    def set_form_matricula(self, v: str):    self.form_matricula = v
    def set_form_especialidad(self, v: str): self.form_especialidad = v
    def set_form_telefono(self, v: str):     self.form_telefono = v
    def set_form_email(self, v: str):        self.form_email = v

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

    # ── Guardar ────────────────────────────────────────────────────────────────

    async def guardar(self):
        if not self.tiene_permiso("profesionales", write=True):
            self.form_error = "Sin permiso de escritura"
            return
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
            async with get_async_session() as session:
                if self.editando_id:
                    await svc.actualizar(session, self.clinica_id, self.editando_id, payload, sede_id=self.sede_actual_id)
                else:
                    await svc.crear(session, self.clinica_id, payload, sede_id=self.sede_actual_id)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        self._limpiar_form()
        async for s in self.cargar():
            yield s

    # ── Eliminar ───────────────────────────────────────────────────────────────

    async def eliminar(self, prof_id: int):
        if not self.tiene_permiso("profesionales", write=True):
            return
        async with get_async_session() as session:
            try:
                await svc.eliminar(session, self.clinica_id, prof_id, sede_id=self.sede_actual_id)
            except ServiceError:
                pass
        async for s in self.cargar():
            yield s

    # ── Agenda (disponibilidad + bloqueos) ──────────────────────────────────────

    async def abrir_agenda(self, prof: dict):
        self.agenda_prof_id     = prof.get("id") or 0
        self.agenda_prof_nombre = f"{prof.get('nombres', '')} {prof.get('apellidos', '')}".strip()
        self.agenda_error       = ""
        self.disp_dia    = "0"
        self.disp_inicio = "09:00"
        self.disp_fin    = "13:00"
        self.bloq_inicio = ""
        self.bloq_fin    = ""
        self.bloq_motivo = ""
        self.dias_cat    = agenda_svc.dias_catalogo()
        await self._cargar_agenda()
        self.modal_agenda = True

    def cerrar_agenda(self):
        self.modal_agenda = False

    def set_disp_dia(self, v: str):    self.disp_dia = v
    def set_disp_inicio(self, v: str): self.disp_inicio = v
    def set_disp_fin(self, v: str):    self.disp_fin = v
    def set_bloq_inicio(self, v: str): self.bloq_inicio = v
    def set_bloq_fin(self, v: str):    self.bloq_fin = v
    def set_bloq_motivo(self, v: str): self.bloq_motivo = v

    async def _cargar_agenda(self):
        if not self.agenda_prof_id:
            return
        async with get_async_session() as session:
            self.disponibilidad = await agenda_svc.listar_disponibilidad(
                session, self.clinica_id, self.agenda_prof_id, sede_id=self.sede_actual_id
            )
            self.bloqueos = await agenda_svc.listar_bloqueos(
                session, self.clinica_id, self.agenda_prof_id, sede_id=self.sede_actual_id
            )

    async def agregar_disponibilidad(self):
        if not self.tiene_permiso("profesionales", write=True):
            return
        self.agenda_error = ""
        try:
            async with get_async_session() as session:
                await agenda_svc.agregar_disponibilidad(
                    session, self.clinica_id, self.agenda_prof_id,
                    dia_semana=int(self.disp_dia),
                    hora_inicio=self.disp_inicio, hora_fin=self.disp_fin,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except (ServiceError, ValueError) as exc:
            self.agenda_error = str(exc)
            return
        await self._cargar_agenda()

    async def eliminar_disponibilidad(self, disp_id: int):
        if not self.tiene_permiso("profesionales", write=True):
            return
        async with get_async_session() as session:
            try:
                await agenda_svc.eliminar_disponibilidad(
                    session, self.clinica_id, disp_id, usuario_id=self.user_id, sede_id=self.sede_actual_id
                )
            except ServiceError:
                pass
        await self._cargar_agenda()

    async def agregar_bloqueo(self):
        if not self.tiene_permiso("profesionales", write=True):
            return
        self.agenda_error = ""
        if not self.bloq_inicio or not self.bloq_fin:
            self.agenda_error = "Inicio y fin son obligatorios"
            return
        try:
            async with get_async_session() as session:
                await agenda_svc.agregar_bloqueo(
                    session, self.clinica_id, self.agenda_prof_id,
                    inicio=self.bloq_inicio, fin=self.bloq_fin, motivo=self.bloq_motivo,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            self.agenda_error = str(exc)
            return
        self.bloq_inicio = ""
        self.bloq_fin    = ""
        self.bloq_motivo = ""
        await self._cargar_agenda()

    async def eliminar_bloqueo(self, bloqueo_id: int):
        if not self.tiene_permiso("profesionales", write=True):
            return
        async with get_async_session() as session:
            try:
                await agenda_svc.eliminar_bloqueo(
                    session, self.clinica_id, bloqueo_id, usuario_id=self.user_id, sede_id=self.sede_actual_id
                )
            except ServiceError:
                pass
        await self._cargar_agenda()

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    async def handle_modal_key(self, key: str):
        if key == "Escape":
            self.cerrar_modal()
        elif key == "Enter" and self.modal_abierto and not self.is_saving:
            async for s in self.guardar():
                yield s

    async def handle_busqueda_key(self, key: str):
        if key == "Escape" and self.busqueda:
            async for s in self.set_busqueda(""):
                yield s

    async def handle_tabla_key(self, key: str):
        if key == "ArrowLeft":
            async for s in self.prev_page():
                yield s
        elif key == "ArrowRight":
            async for s in self.next_page():
                yield s
