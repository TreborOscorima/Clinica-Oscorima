from __future__ import annotations

from typing import Any

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import turnos as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class TurnosState(BaseState):

    turnos:             list[dict] = []
    total:              int        = 0
    page:               int        = 1
    per_page:           int        = 20
    total_pages:        int        = 1
    filtro_estado:      str        = ""
    filtro_fecha_desde: str        = ""
    filtro_fecha_hasta: str        = ""
    is_loading:         bool       = False

    # Modal nuevo turno
    modal_nuevo:         bool = False
    form_paciente_id:    str  = ""
    form_profesional_id: str  = ""
    form_servicio_id:    str  = ""
    form_fecha_hora:     str  = ""
    form_error:          str  = ""
    is_saving:           bool = False

    # Selector de paciente (búsqueda server-side, sin tope — patrón cobro)
    pac_busqueda:   str        = ""
    pac_resultados: list[dict] = []
    pac_nombre_sel: str        = ""

    # Modal cambiar estado
    modal_estado:      bool = False
    turno_sel_id:      int  = 0
    form_nuevo_estado: str  = ""
    form_motivo:       str  = ""

    # Modal reprogramar
    modal_reprogramar:      bool = False
    form_reprogramar_fecha: str  = ""
    form_reprogramar_error: str  = ""

    # Catálogos (profesionales/servicios son acotados; pacientes se busca on-demand)
    profesionales_cat: list[dict] = []
    servicios_cat:    list[dict] = []

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("turnos"):
            yield rx.redirect("/")
            return
        await self._cargar_catalogos()
        async for s in self.cargar():
            yield s

    # ── Catálogos ──────────────────────────────────────────────────────────────

    async def _cargar_catalogos(self):
        from clinica_app.models.profesional import Profesional
        from clinica_app.models.servicio import Servicio
        from sqlmodel import select

        async with get_async_session() as session:
            stmt_profs = select(Profesional).where(
                Profesional.clinica_id == self.clinica_id,
                Profesional.is_active.is_(True),
            )
            if self.sede_actual_id:
                stmt_profs = stmt_profs.where(Profesional.sede_id == self.sede_actual_id)
            profs = (await session.execute(stmt_profs.limit(100))).scalars().all()
            stmt_servs = select(Servicio).where(
                Servicio.clinica_id == self.clinica_id,
                Servicio.is_active.is_(True),
            )
            if self.sede_actual_id:
                stmt_servs = stmt_servs.where(Servicio.sede_id == self.sede_actual_id)
            servs = (await session.execute(stmt_servs.limit(200))).scalars().all()

        self.profesionales_cat = [
            {"id": str(p.id), "nombre": f"{p.nombres} {p.apellidos}"}
            for p in profs
        ]
        self.servicios_cat = [{"id": str(s.id), "nombre": s.nombre} for s in servs]

    # ── Carga progresiva ───────────────────────────────────────────────────────

    async def cargar(self):
        self.is_loading = True
        yield
        async with get_async_session() as session:
            result = await svc.listar(
                session,
                self.clinica_id,
                sede_id=self.sede_actual_id,
                estado=self.filtro_estado,
                fecha_desde=self.filtro_fecha_desde,
                fecha_hasta=self.filtro_fecha_hasta,
                page=self.page,
                per_page=self.per_page,
            )
        self.turnos      = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]
        self.is_loading  = False

    # ── Filtros ────────────────────────────────────────────────────────────────

    async def set_filtro_estado(self, valor: str):
        self.filtro_estado = valor
        self.page = 1
        async for s in self.cargar():
            yield s

    async def set_filtro_fecha_desde(self, v: str):
        self.filtro_fecha_desde = v
        self.page = 1
        async for s in self.cargar():
            yield s

    async def set_filtro_fecha_hasta(self, v: str):
        self.filtro_fecha_hasta = v
        self.page = 1
        async for s in self.cargar():
            yield s

    # ── Selector de paciente (búsqueda server-side, sin tope) ────────────────────

    async def set_pac_busqueda(self, v: str):
        self.pac_busqueda = v
        # Si el usuario reescribe, se invalida la selección previa.
        if self.form_paciente_id:
            self.form_paciente_id = ""
            self.pac_nombre_sel   = ""

        if len(v) >= 2:
            from clinica_app.models.paciente import Paciente
            from sqlalchemy import String, cast, or_
            from sqlmodel import select

            like = f"%{v}%"
            async with get_async_session() as session:
                q_pacs = select(Paciente).where(
                    Paciente.clinica_id == self.clinica_id,
                    Paciente.is_active.is_(True),
                    or_(
                        Paciente.nombre.ilike(like),
                        cast(Paciente.documento, String).ilike(like),
                    ),
                )
                if self.sede_actual_id:
                    q_pacs = q_pacs.where(Paciente.sede_id == self.sede_actual_id)
                pacs = (await session.execute(q_pacs.limit(8))).scalars().all()
            self.pac_resultados = [
                {"id": str(p.id), "nombre": p.nombre, "documento": p.documento or ""}
                for p in pacs
            ]
        else:
            self.pac_resultados = []

    def seleccionar_paciente(self, pac_id: str, pac_nombre: str):
        self.form_paciente_id = pac_id
        self.pac_nombre_sel   = pac_nombre
        self.pac_busqueda     = pac_nombre
        self.pac_resultados   = []

    def limpiar_paciente(self):
        self.form_paciente_id = ""
        self.pac_nombre_sel   = ""
        self.pac_busqueda     = ""
        self.pac_resultados   = []

    async def handle_pac_busqueda_key(self, key: str):
        if key == "Escape" and self.pac_busqueda:
            async for s in self.set_pac_busqueda(""):
                yield s

    # ── Setters de formulario ──────────────────────────────────────────────────

    def set_form_paciente_id(self, v: str):       self.form_paciente_id = v
    def set_form_profesional_id(self, v: str):    self.form_profesional_id = v
    def set_form_servicio_id(self, v: str):       self.form_servicio_id = v
    def set_form_fecha_hora(self, v: str):        self.form_fecha_hora = v
    def set_form_nuevo_estado(self, v: str):      self.form_nuevo_estado = v
    def set_form_motivo(self, v: str):            self.form_motivo = v
    def set_form_reprogramar_fecha(self, v: str): self.form_reprogramar_fecha = v

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

    # ── Modal nuevo turno ──────────────────────────────────────────────────────

    def abrir_nuevo(self):
        self.form_paciente_id    = ""
        self.form_profesional_id = ""
        self.form_servicio_id    = ""
        self.form_fecha_hora     = ""
        self.form_error          = ""
        self.pac_busqueda        = ""
        self.pac_nombre_sel      = ""
        self.pac_resultados      = []
        self.modal_nuevo         = True

    def cerrar_nuevo(self):
        self.modal_nuevo = False

    async def guardar_turno(self):
        if not self.tiene_permiso("turnos", write=True):
            self.form_error = "Sin permiso de escritura"
            return
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
            async with get_async_session() as session:
                await svc.crear(
                    session, self.clinica_id, payload,
                    created_by_id=self.user_id, sede_id=self.sede_actual_id,
                    validar_agenda=True,
                )
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving   = False
        self.modal_nuevo = False
        async for s in self.cargar():
            yield s

    # ── Modal cambiar estado ───────────────────────────────────────────────────

    def abrir_estado(self, turno: dict):
        self.turno_sel_id      = turno.get("id") or 0
        self.form_nuevo_estado = turno.get("estado") or ""
        self.form_motivo       = ""
        self.modal_estado      = True

    def cerrar_estado(self):
        self.modal_estado = False

    async def guardar_estado(self):
        if not self.tiene_permiso("turnos", write=True):
            yield rx.toast.error("No tenés permiso para cambiar el estado del turno")
            return
        async with get_async_session() as session:
            try:
                await svc.cambiar_estado(
                    session,
                    self.clinica_id,
                    self.turno_sel_id,
                    {"estado": self.form_nuevo_estado, "motivo_cancelacion": self.form_motivo},
                    sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        self.modal_estado = False
        yield rx.toast.success("Estado del turno actualizado")
        async for s in self.cargar():
            yield s

    async def guardar_estado_y_cobrar(self):
        if not self.tiene_permiso("turnos", write=True):
            yield rx.toast.error("No tenés permiso para cambiar el estado del turno")
            return
        async with get_async_session() as session:
            try:
                await svc.cambiar_estado(
                    session,
                    self.clinica_id,
                    self.turno_sel_id,
                    {"estado": "atendido", "motivo_cancelacion": ""},
                    sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                # No redirigir a cobro si el cambio de estado falló.
                yield rx.toast.error(str(exc))
                return
        self.modal_estado = False
        yield rx.redirect(f"/cobro?turno_id={self.turno_sel_id}")

    def ir_a_cobro(self, turno: dict):
        turno_id = turno.get("id") or 0
        return rx.redirect(f"/cobro?turno_id={turno_id}")

    # ── Modal reprogramar ──────────────────────────────────────────────────────

    def abrir_reprogramar(self, turno: dict):
        self.turno_sel_id           = turno.get("id") or 0
        self.form_reprogramar_fecha = turno.get("fecha_hora", "").replace(" ", "T")
        self.form_reprogramar_error = ""
        self.modal_reprogramar      = True

    def cerrar_reprogramar(self):
        self.modal_reprogramar = False

    async def guardar_reprogramar(self):
        if not self.tiene_permiso("turnos", write=True):
            return
        if not self.form_reprogramar_fecha:
            return
        self.form_reprogramar_error = ""
        async with get_async_session() as session:
            try:
                await svc.reprogramar(
                    session,
                    self.clinica_id,
                    self.turno_sel_id,
                    {"fecha_hora": self.form_reprogramar_fecha},
                    sede_id=self.sede_actual_id,
                    validar_agenda=True,
                )
            except ServiceError as exc:
                self.form_reprogramar_error = str(exc)
                return
        self.modal_reprogramar = False
        async for s in self.cargar():
            yield s

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    async def handle_modal_nuevo_key(self, key: str):
        if key == "Escape":
            self.modal_nuevo = False
        elif key == "Enter" and self.modal_nuevo and not self.is_saving:
            async for s in self.guardar_turno():
                yield s

    def handle_modal_estado_key(self, key: str):
        if key == "Escape":
            self.modal_estado = False

    async def handle_modal_repro_key(self, key: str):
        if key == "Escape":
            self.modal_reprogramar = False
        elif key == "Enter" and self.modal_reprogramar:
            async for s in self.guardar_reprogramar():
                yield s

    async def handle_tabla_key(self, key: str):
        if key == "ArrowLeft":
            async for s in self.prev_page():
                yield s
        elif key == "ArrowRight":
            async for s in self.next_page():
                yield s
