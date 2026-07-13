from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import servicios as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class ServiciosState(BaseState):

    servicios:      list[dict] = []
    total:          int  = 0
    page:           int  = 1
    per_page:       int  = 20
    total_pages:    int  = 1
    busqueda:       str  = ""
    filtro_cat:     str  = ""
    categorias_cat: list[str] = []
    is_loading:     bool = False

    # Modal
    modal_abierto:     bool = False
    editando_id:       int  = 0
    form_nombre:       str  = ""
    form_categoria:    str  = ""
    form_nueva_cat:    str  = ""
    form_descripcion:  str  = ""
    form_precio:       str  = ""
    form_duracion_min: str  = "30"
    form_protocolo:    str  = ""
    form_error:        str  = ""
    is_saving:         bool = False

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("servicios"):
            yield rx.redirect("/")
            return
        await self._cargar_cats()
        async for s in self.cargar():
            yield s

    async def _cargar_cats(self):
        async with get_async_session() as session:
            self.categorias_cat = await svc.categorias(session, self.clinica_id, self.sede_actual_id)

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
                categoria=self.filtro_cat,
                page=self.page,
                per_page=self.per_page,
            )
        self.servicios   = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]
        self.is_loading  = False

    # ── Filtros ────────────────────────────────────────────────────────────────

    async def set_busqueda(self, valor: str):
        self.busqueda = valor
        self.page = 1
        async for s in self.cargar():
            yield s

    async def set_filtro_cat(self, valor: str):
        self.filtro_cat = valor
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

    def set_form_nombre(self, v: str):        self.form_nombre = v
    def set_form_categoria(self, v: str):     self.form_categoria = v
    def set_form_nueva_cat(self, v: str):     self.form_nueva_cat = v
    def set_form_descripcion(self, v: str):   self.form_descripcion = v
    def set_form_precio(self, v: float):      self.form_precio = str(v) if v else ""
    def set_form_duracion_min(self, v: float): self.form_duracion_min = str(int(v)) if v else ""
    def set_form_protocolo(self, v: str):     self.form_protocolo = v

    def _limpiar_form(self):
        self.form_nombre = self.form_categoria = self.form_nueva_cat = ""
        self.form_descripcion = self.form_precio = self.form_protocolo = ""
        self.form_duracion_min = "30"
        self.form_error = ""
        self.editando_id = 0

    def abrir_nuevo(self):
        self._limpiar_form()
        self.modal_abierto = True

    def abrir_editar(self, srv: dict):
        self._limpiar_form()
        self.editando_id       = srv.get("id") or 0
        self.form_nombre       = srv.get("nombre") or ""
        self.form_categoria    = srv.get("categoria") or ""
        self.form_descripcion  = srv.get("descripcion") or ""
        self.form_precio       = srv.get("precio") or "0.00"
        self.form_duracion_min = str(srv.get("duracion_min") or 30)
        self.form_protocolo    = srv.get("protocolo") or ""
        self.modal_abierto     = True

    def cerrar_modal(self):
        self.modal_abierto = False
        self._limpiar_form()

    # ── Guardar ────────────────────────────────────────────────────────────────

    async def guardar(self):
        if not self.tiene_permiso("servicios", write=True):
            self.form_error = "Sin permiso de escritura"
            return
        self.is_saving  = True
        self.form_error = ""
        yield

        cat = (self.form_nueva_cat.strip() or self.form_categoria.strip()) or ""
        payload = {
            "nombre":       self.form_nombre,
            "categoria":    cat,
            "descripcion":  self.form_descripcion,
            "precio":       self.form_precio or "0",
            "duracion_min": self.form_duracion_min or "30",
            "protocolo":    self.form_protocolo,
        }
        try:
            async with get_async_session() as session:
                if self.editando_id:
                    await svc.actualizar(session, self.clinica_id, self.editando_id, payload, sede_id=self.sede_actual_id)
                else:
                    await svc.crear(session, self.clinica_id, payload, self.sede_actual_id)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        self._limpiar_form()
        await self._cargar_cats()
        async for s in self.cargar():
            yield s

    # ── Eliminar ───────────────────────────────────────────────────────────────

    async def eliminar(self, srv_id: int):
        async with get_async_session() as session:
            try:
                await svc.eliminar(session, self.clinica_id, srv_id, sede_id=self.sede_actual_id)
            except ServiceError:
                pass
        await self._cargar_cats()
        async for s in self.cargar():
            yield s

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    def handle_modal_key(self, key: str):
        if key == "Escape":
            self.cerrar_modal()

    async def handle_tabla_key(self, key: str):
        if key == "ArrowLeft":
            async for s in self.prev_page():
                yield s
        elif key == "ArrowRight":
            async for s in self.next_page():
                yield s
