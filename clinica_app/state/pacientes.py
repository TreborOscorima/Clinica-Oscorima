from __future__ import annotations

from typing import Any

import reflex as rx
from sqlalchemy.orm import selectinload
from sqlmodel import select

from clinica_app.database import get_async_session
from clinica_app.services import pacientes as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class PacientesState(BaseState):
    """Estado del módulo Pacientes."""

    # ── Tabla ──────────────────────────────────────────────────────────────────
    pacientes:   list[dict] = []
    total:       int        = 0
    page:        int        = 1
    per_page:    int        = 20
    total_pages: int        = 1
    busqueda:    str        = ""
    is_loading:  bool       = False

    # ── Modal creación/edición ─────────────────────────────────────────────────
    modal_abierto:   bool = False
    editando_id:     int  = 0
    form_nombre:     str  = ""
    form_documento:  str  = ""
    form_email:      str  = ""
    form_telefono:   str  = ""
    form_direccion:  str  = ""
    form_nacimiento: str  = ""
    form_emergencia: str  = ""
    form_error:      str  = ""
    is_saving:       bool = False

    # ── Panel de detalle ───────────────────────────────────────────────────────
    panel_detalle: bool = False
    paciente_sel: dict = {
        "id": 0, "nombre": "", "documento": "", "email": "",
        "telefono": "", "direccion": "", "contacto_emergencia": "", "edad": 0,
    }
    historial_turnos:       list[dict] = []
    historial_comprobantes: list[dict] = []
    historial_deudas:       list[dict] = []

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("pacientes"):
            yield rx.redirect("/")
            return
        async for s in self.cargar():
            yield s

    # ── Carga progresiva ───────────────────────────────────────────────────────

    async def cargar(self):
        self.is_loading = True
        yield
        async with get_async_session() as session:
            resultado = await svc.listar(
                session,
                self.clinica_id,
                sede_id=self.sede_actual_id,
                q=self.busqueda,
                page=self.page,
                per_page=self.per_page,
            )
        self.pacientes   = resultado["data"]
        self.total       = resultado["total"]
        self.total_pages = resultado["pages"]
        self.is_loading  = False

    # ── Búsqueda ───────────────────────────────────────────────────────────────

    async def set_busqueda(self, value: str):
        self.busqueda = value
        self.page = 1
        async for s in self.cargar():
            yield s

    # ── Setters de formulario ──────────────────────────────────────────────────

    def set_form_nombre(self, v: str):     self.form_nombre = v
    def set_form_documento(self, v: str):  self.form_documento = v
    def set_form_email(self, v: str):      self.form_email = v
    def set_form_telefono(self, v: str):   self.form_telefono = v
    def set_form_direccion(self, v: str):  self.form_direccion = v
    def set_form_nacimiento(self, v: str): self.form_nacimiento = v
    def set_form_emergencia(self, v: str): self.form_emergencia = v

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
        if not self.tiene_permiso("pacientes", write=True):
            self.form_error = "Sin permiso de escritura"
            return
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
            async with get_async_session() as session:
                if self.editando_id:
                    await svc.actualizar(session, self.clinica_id, self.editando_id, payload, sede_id=self.sede_actual_id)
                else:
                    await svc.crear(session, self.clinica_id, sede_id=self.sede_actual_id, payload=payload)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        async for s in self.cargar():
            yield s

    # ── Panel de detalle — Fase 3: N+1 eliminado con selectinload ─────────────

    async def abrir_detalle(self, p: dict):
        from clinica_app.models.caja import Comprobante, DeudaPaciente
        from clinica_app.models.turno import Turno

        self.paciente_sel = p
        pac_id = p.get("id") or 0

        async with get_async_session() as session:
            # Turno con relaciones pre-cargadas en UNA sola consulta (no N+1)
            q_turnos = (
                select(Turno)
                .where(
                    Turno.paciente_id == pac_id,
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                )
                .options(
                    selectinload(Turno.profesional),
                    selectinload(Turno.servicio),
                )
                .order_by(Turno.fecha_hora.desc())
                .limit(10)
            )
            if self.sede_actual_id:
                q_turnos = q_turnos.where(Turno.sede_id == self.sede_actual_id)
            turnos = (await session.execute(q_turnos)).scalars().all()
            self.historial_turnos = [
                {
                    "fecha_hora":         t.fecha_hora.strftime("%d/%m/%Y %H:%M") if t.fecha_hora else "",
                    "profesional_nombre": (
                        f"{t.profesional.nombres} {t.profesional.apellidos}"
                        if t.profesional else "—"
                    ),
                    "servicio_nombre":    t.servicio.nombre if t.servicio else "—",
                    "estado":             t.estado.value if t.estado else "",
                }
                for t in turnos
            ]

            q_comp = (
                select(Comprobante)
                .where(
                    Comprobante.paciente_id == pac_id,
                    Comprobante.clinica_id == self.clinica_id,
                    Comprobante.is_active.is_(True),
                )
                .order_by(Comprobante.fecha.desc())
                .limit(10)
            )
            if self.sede_actual_id:
                q_comp = q_comp.where(Comprobante.sede_id == self.sede_actual_id)
            comprobantes = (await session.execute(q_comp)).scalars().all()
            self.historial_comprobantes = [
                {
                    "id":         str(c.id),
                    "numero":     c.numero or f"#{c.id}",
                    "fecha":      c.fecha.strftime("%d/%m/%Y") if c.fecha else "",
                    "total":      f"{float(c.total or 0):.2f}",
                    "forma_pago": c.forma_pago.value if c.forma_pago else "",
                }
                for c in comprobantes
            ]

            deudas = (
                await session.execute(
                    select(DeudaPaciente)
                    .where(
                        DeudaPaciente.paciente_id == pac_id,
                        DeudaPaciente.clinica_id == self.clinica_id,
                        DeudaPaciente.estado != "saldado",
                        DeudaPaciente.is_active.is_(True),
                    )
                    .order_by(DeudaPaciente.creado_en.desc())
                )
            ).scalars().all()
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

    async def eliminar(self, paciente_id: int):
        if not self.tiene_permiso("pacientes", write=True):
            return
        async with get_async_session() as session:
            try:
                await svc.eliminar(session, self.clinica_id, paciente_id, sede_id=self.sede_actual_id)
            except ServiceError:
                pass
        async for s in self.cargar():
            yield s

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    async def handle_modal_key(self, key: str):
        if key == "Escape":
            self.modal_abierto = False
        elif key == "Enter" and self.modal_abierto and not self.is_saving:
            async for s in self.guardar():
                yield s

    def handle_panel_key(self, key: str):
        if key == "Escape":
            self.panel_detalle = False

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
