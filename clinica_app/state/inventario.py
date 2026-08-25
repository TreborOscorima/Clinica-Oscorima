from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import inventario as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class InventarioState(BaseState):

    productos:   list[dict] = []
    total:       int        = 0
    page:        int        = 1
    per_page:    int        = 20
    total_pages: int        = 1
    busqueda:    str        = ""
    solo_minimo: bool       = False
    is_loading:  bool       = False

    # Margen de ganancia de la clínica (para sugerir precio de venta)
    margen_global: float = 50.0

    # Modal producto
    modal_producto:    bool = False
    editando_id:       int  = 0
    form_nombre:       str  = ""
    form_sku:          str  = ""
    form_precio_costo: str  = ""
    form_precio_venta: str  = ""
    form_stock_actual: str  = ""
    form_stock_minimo: str  = ""
    form_error:        str  = ""
    is_saving:         bool = False

    # Modal movimiento de stock
    modal_mov:            bool = False
    mov_prod_id:          int  = 0
    mov_prod_nombre:      str  = ""
    form_mov_tipo:        str  = "ingreso"
    form_mov_cantidad:    str  = ""
    form_mov_motivo:      str  = ""
    form_mov_lote:        str  = ""
    form_mov_vencimiento: str  = ""
    lotes_producto:       list[dict] = []

    # Alertas de vencimiento de lotes
    alertas_vencidos:   list[dict] = []
    alertas_por_vencer: list[dict] = []
    total_vencidos:     int        = 0
    total_por_vencer:   int        = 0
    ver_vencimientos:   bool       = False

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("inventario"):
            yield rx.redirect("/")
            return
        async with get_async_session() as session:
            from clinica_app.services.configuracion import obtener_clinica
            c = await obtener_clinica(session, self.clinica_id)
            self.margen_global = c["margen_global"]
        async for s in self.cargar():
            yield s

    # ── Carga progresiva ───────────────────────────────────────────────────────

    async def cargar(self):
        self.is_loading = True
        yield
        async with get_async_session() as session:
            result = await svc.listar_productos(
                session, self.clinica_id,
                sede_id=self.sede_actual_id,
                q=self.busqueda,
                bajo_minimo=self.solo_minimo,
                page=self.page,
                per_page=self.per_page,
            )
        self.productos   = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]
        self.is_loading  = False
        await self._cargar_alertas()

    async def _cargar_alertas(self):
        from clinica_app.services import lotes as lotes_svc
        async with get_async_session() as session:
            al = await lotes_svc.alertas_vencimiento(
                session, self.clinica_id, sede_id=self.sede_actual_id, dias=30
            )
        self.alertas_vencidos   = al["vencidos"]
        self.alertas_por_vencer = al["por_vencer"]
        self.total_vencidos     = al["total_vencidos"]
        self.total_por_vencer   = al["total_por_vencer"]

    def toggle_vencimientos(self):
        self.ver_vencimientos = not self.ver_vencimientos

    async def set_busqueda(self, v: str):
        self.busqueda = v
        self.page = 1
        async for s in self.cargar():
            yield s

    # ── Setters de formulario ──────────────────────────────────────────────────

    def set_form_nombre(self, v: str):        self.form_nombre = v
    def set_form_sku(self, v: str):           self.form_sku = v
    def set_form_precio_costo(self, v: str):
        self.form_precio_costo = v
        if not self.form_precio_venta and v:
            try:
                costo = float(v)
                if costo > 0:
                    sugerido = costo * (1 + self.margen_global / 100)
                    self.form_precio_venta = f"{sugerido:.2f}"
            except ValueError:
                pass
    def set_form_precio_venta(self, v: str):  self.form_precio_venta = v
    def set_form_stock_actual(self, v: str):  self.form_stock_actual = v
    def set_form_stock_minimo(self, v: str):  self.form_stock_minimo = v
    def set_form_mov_tipo(self, v: str):      self.form_mov_tipo = v
    def set_form_mov_cantidad(self, v: str):  self.form_mov_cantidad = v
    def set_form_mov_motivo(self, v: str):    self.form_mov_motivo = v
    def set_form_mov_lote(self, v: str):      self.form_mov_lote = v
    def set_form_mov_vencimiento(self, v: str): self.form_mov_vencimiento = v

    async def toggle_minimo(self):
        self.solo_minimo = not self.solo_minimo
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

    # ── Modal producto ─────────────────────────────────────────────────────────

    def abrir_nuevo(self):
        self._limpiar_form()
        self.editando_id    = 0
        self.modal_producto = True

    def abrir_editar(self, p: dict):
        self._limpiar_form()
        self.editando_id       = p.get("id") or 0
        self.form_nombre       = p.get("nombre") or ""
        self.form_sku          = p.get("sku") or ""
        self.form_precio_costo = p.get("precio_costo") or ""
        self.form_precio_venta = p.get("precio_venta") or ""
        self.form_stock_actual = p.get("stock_actual") or ""
        self.form_stock_minimo = p.get("stock_minimo") or ""
        self.modal_producto    = True

    def cerrar_producto(self):
        self.modal_producto = False

    def _limpiar_form(self):
        self.form_nombre       = ""
        self.form_sku          = ""
        self.form_precio_costo = ""
        self.form_precio_venta = ""
        self.form_stock_actual = ""
        self.form_stock_minimo = ""
        self.form_error        = ""

    async def guardar_producto(self):
        if not self.tiene_permiso("inventario", write=True):
            self.form_error = "Sin permiso de escritura"
            return
        self.is_saving  = True
        self.form_error = ""
        yield

        payload = {
            "nombre":       self.form_nombre.strip(),
            "sku":          self.form_sku.strip() or None,
            "precio_costo": self.form_precio_costo or None,
            "precio_venta": self.form_precio_venta or None,
            "stock_actual": self.form_stock_actual or 0,
            "stock_minimo": self.form_stock_minimo or 0,
        }

        try:
            async with get_async_session() as session:
                if self.editando_id:
                    await svc.actualizar_producto(session, self.clinica_id, self.editando_id, payload, self.sede_actual_id)
                else:
                    await svc.crear_producto(session, self.clinica_id, payload, self.sede_actual_id)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving      = False
        self.modal_producto = False
        async for s in self.cargar():
            yield s

    def confirmar_eliminar(self, p: dict):
        self._pedir_eliminar(
            kind="producto",
            id=p["id"],
            titulo="¿Eliminar producto?",
            mensaje=f"{p['nombre']} se eliminará del inventario.",
        )

    async def ejecutar_eliminar(self):
        if not self.tiene_permiso("inventario", write=True):
            self.del_open = False
            yield rx.toast.error("No tenés permiso para eliminar productos")
            return
        self.del_procesando = True
        yield
        async with get_async_session() as session:
            try:
                await svc.eliminar_producto(session, self.clinica_id, self._del_id, self.sede_actual_id)
            except ServiceError as exc:
                self.del_procesando = False
                yield rx.toast.error(str(exc))
                return
        self.del_open       = False
        self.del_procesando = False
        yield rx.toast.success("Producto eliminado")
        async for s in self.cargar():
            yield s

    # ── Modal movimiento de stock ──────────────────────────────────────────────

    async def abrir_mov(self, p: dict):
        self.mov_prod_id          = p.get("id") or 0
        self.mov_prod_nombre      = p.get("nombre") or ""
        self.form_mov_tipo        = "ingreso"
        self.form_mov_cantidad    = ""
        self.form_mov_motivo      = ""
        self.form_mov_lote        = ""
        self.form_mov_vencimiento = ""
        self.lotes_producto       = []
        self.modal_mov            = True
        from clinica_app.services import lotes as lotes_svc
        async with get_async_session() as session:
            self.lotes_producto = await lotes_svc.listar_por_producto(
                session, self.clinica_id, self.mov_prod_id, sede_id=self.sede_actual_id
            )

    def cerrar_mov(self):
        self.modal_mov = False

    async def guardar_movimiento(self):
        if not self.tiene_permiso("inventario", write=True):
            yield rx.toast.error("No tenés permiso para mover stock")
            return
        if not self.form_mov_cantidad:
            yield rx.toast.error("La cantidad es obligatoria")
            return
        async with get_async_session() as session:
            try:
                await svc.registrar_movimiento_stock(
                    session,
                    self.clinica_id,
                    self.mov_prod_id,
                    self.form_mov_tipo,
                    self.form_mov_cantidad,
                    motivo=self.form_mov_motivo,
                    sede_id=self.sede_actual_id,
                    lote=self.form_mov_lote,
                    vencimiento=self.form_mov_vencimiento,
                )
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        yield rx.toast.success("Movimiento de stock registrado")
        self.modal_mov = False
        async for s in self.cargar():
            yield s

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    async def handle_modal_producto_key(self, key: str):
        if key == "Escape":
            self.cerrar_producto()
        elif key == "Enter" and self.modal_producto and not self.is_saving:
            async for s in self.guardar_producto():
                yield s

    async def handle_modal_mov_key(self, key: str):
        if key == "Escape":
            self.cerrar_mov()
        elif key == "Enter" and self.modal_mov and not self.is_saving:
            async for s in self.guardar_movimiento():
                yield s

    async def handle_tabla_key(self, key: str):
        if key == "ArrowLeft":
            async for s in self.prev_page():
                yield s
        elif key == "ArrowRight":
            async for s in self.next_page():
                yield s
