from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import promociones as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_PROMO_VACIA: dict = {
    "id": 0, "nombre": "", "descripcion": "", "tipo": "porcentaje",
    "valor": "0.00", "aplica_a": "todo", "fecha_inicio": "", "fecha_fin": "",
    "activo": True, "vigente": False, "created_at": "",
}


class PromocionesState(BaseState):

    # ── Lista ──────────────────────────────────────────────────────────────────
    promociones:  list[dict] = []
    total:        int        = 0
    total_pages:  int        = 1
    page:         int        = 1
    per_page:     int        = 20
    busqueda:     str        = ""
    solo_activas: bool       = False
    total_activas: int       = 0

    # ── Modal formulario ───────────────────────────────────────────────────────
    modal_form:        bool = False
    editando:          bool = False
    promo_sel:         dict = _PROMO_VACIA
    form_nombre:       str  = ""
    form_descripcion:  str  = ""
    form_tipo:         str  = "porcentaje"
    form_valor:        str  = ""
    form_aplica_a:     str  = "todo"
    form_fecha_inicio: str  = ""
    form_fecha_fin:    str  = ""
    form_error:        str  = ""
    is_saving:         bool = False
    is_loading:        bool = False

    # ── Modal eliminar ─────────────────────────────────────────────────────────
    modal_eliminar: bool = False
    eliminar_id:    int  = 0
    eliminar_nombre: str = ""

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("promociones"):
            yield rx.redirect("/")
            return
        async for s in self.cargar():
            yield s

    async def cargar(self):
        self.is_loading = True
        yield
        async with get_async_session() as session:
            result = await svc.listar(
                session,
                self.clinica_id,
                sede_id=self.sede_actual_id,
                solo_activas=self.solo_activas,
                q=self.busqueda,
                page=self.page,
                per_page=self.per_page,
            )
        self.promociones   = result["data"]
        self.total         = result["total"]
        self.total_pages   = result["pages"]
        self.total_activas = result["total_activas"]
        self.is_loading = False

    # ── Filtros ────────────────────────────────────────────────────────────────

    async def set_busqueda(self, v: str):
        self.busqueda = v
        self.page = 1
        if len(v) >= 2 or v == "":
            async for s in self.cargar():
                yield s

    async def toggle_solo_activas(self):
        self.solo_activas = not self.solo_activas
        self.page = 1
        async for s in self.cargar():
            yield s

    # ── Paginación ─────────────────────────────────────────────────────────────

    async def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            async for s in self.cargar():
                yield s

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            async for s in self.cargar():
                yield s

    # ── Modal formulario ───────────────────────────────────────────────────────

    def abrir_nueva(self):
        self.editando          = False
        self.promo_sel         = _PROMO_VACIA
        self.form_nombre       = ""
        self.form_descripcion  = ""
        self.form_tipo         = "porcentaje"
        self.form_valor        = ""
        self.form_aplica_a     = "todo"
        self.form_fecha_inicio = ""
        self.form_fecha_fin    = ""
        self.form_error        = ""
        self.modal_form        = True

    def abrir_editar(self, promo: dict):
        self.editando          = True
        self.promo_sel         = promo
        self.form_nombre       = promo["nombre"]
        self.form_descripcion  = promo["descripcion"]
        self.form_tipo         = promo["tipo"]
        self.form_valor        = promo["valor"]
        self.form_aplica_a     = promo["aplica_a"]
        self.form_fecha_inicio = promo["fecha_inicio"]
        self.form_fecha_fin    = promo["fecha_fin"]
        self.form_error        = ""
        self.modal_form        = True

    def cerrar_form(self):
        self.modal_form = False
        self.form_error = ""

    def set_form_nombre(self, v: str):       self.form_nombre = v
    def set_form_descripcion(self, v: str):  self.form_descripcion = v
    def set_form_tipo(self, v: str):         self.form_tipo = v
    def set_form_valor(self, v: str):        self.form_valor = v
    def set_form_aplica_a(self, v: str):     self.form_aplica_a = v
    def set_form_fecha_inicio(self, v: str): self.form_fecha_inicio = v
    def set_form_fecha_fin(self, v: str):    self.form_fecha_fin = v

    async def guardar(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        payload = {
            "nombre":       self.form_nombre.strip(),
            "descripcion":  self.form_descripcion.strip(),
            "tipo":         self.form_tipo,
            "valor":        self.form_valor,
            "aplica_a":     self.form_aplica_a,
            "fecha_inicio": self.form_fecha_inicio,
            "fecha_fin":    self.form_fecha_fin,
        }

        try:
            async with get_async_session() as session:
                if self.editando:
                    await svc.actualizar(session, self.clinica_id, int(self.promo_sel["id"]), payload, sede_id=self.sede_actual_id)
                else:
                    await svc.crear(session, self.clinica_id, payload, sede_id=self.sede_actual_id)
        except (ServiceError, Exception) as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving  = False
        self.modal_form = False
        async for s in self.cargar():
            yield s

    # ── Toggle activo ──────────────────────────────────────────────────────────

    async def toggle_activo(self, promo: dict):
        async with get_async_session() as session:
            try:
                await svc.toggle_activo(session, self.clinica_id, int(promo["id"]), sede_id=self.sede_actual_id)
            except Exception:
                pass
        async for s in self.cargar():
            yield s

    # ── Eliminar ───────────────────────────────────────────────────────────────

    def confirmar_eliminar(self, promo: dict):
        self.eliminar_id     = int(promo["id"])
        self.eliminar_nombre = promo["nombre"]
        self.modal_eliminar  = True

    def cerrar_eliminar(self):
        self.modal_eliminar = False

    async def ejecutar_eliminar(self):
        self.is_saving = True
        yield
        async with get_async_session() as session:
            try:
                await svc.eliminar(session, self.clinica_id, self.eliminar_id, sede_id=self.sede_actual_id)
            except Exception:
                pass
        self.is_saving      = False
        self.modal_eliminar = False
        async for s in self.cargar():
            yield s

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    async def handle_modal_form_key(self, key: str):
        if key == "Escape":
            self.cerrar_form()
        elif key == "Enter" and self.modal_form and not self.is_saving:
            async for s in self.guardar():
                yield s

    async def handle_modal_eliminar_key(self, key: str):
        if key == "Escape":
            self.cerrar_eliminar()
        elif key == "Enter" and self.modal_eliminar and not self.is_saving:
            async for s in self.ejecutar_eliminar():
                yield s

    async def handle_tabla_key(self, key: str):
        if key == "ArrowLeft":
            async for s in self.prev_page():
                yield s
        elif key == "ArrowRight":
            async for s in self.next_page():
                yield s
