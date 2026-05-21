from __future__ import annotations

import reflex as rx

from clinica_app.database import get_session
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

    # Modal producto
    modal_producto:  bool = False
    editando_id:     int  = 0
    form_nombre:     str  = ""
    form_sku:        str  = ""
    form_precio_costo: str = ""
    form_precio_venta: str = ""
    form_stock_actual: str = ""
    form_stock_minimo: str = ""
    form_error:      str  = ""
    is_saving:       bool = False

    # Modal movimiento de stock
    modal_mov:     bool = False
    mov_prod_id:   int  = 0
    mov_prod_nombre: str = ""
    form_mov_tipo: str  = "ingreso"
    form_mov_cantidad: str = ""
    form_mov_motivo: str = ""

    def on_mount(self):
        return self.require_auth() or self.cargar()

    def cargar(self):
        with get_session() as session:
            result = svc.listar_productos(
                session, self.clinica_id,
                q=self.busqueda,
                bajo_minimo=self.solo_minimo,
                page=self.page,
                per_page=self.per_page,
            )
        self.productos   = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]

    def set_busqueda(self, v: str):
        self.busqueda = v
        self.page = 1
        return self.cargar()

    def toggle_minimo(self):
        self.solo_minimo = not self.solo_minimo
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

    # ── Modal producto ─────────────────────────────────────────────────────────

    def abrir_nuevo(self):
        self._limpiar_form()
        self.editando_id    = 0
        self.modal_producto = True

    def abrir_editar(self, p: dict):
        self._limpiar_form()
        self.editando_id      = p.get("id") or 0
        self.form_nombre      = p.get("nombre") or ""
        self.form_sku         = p.get("sku") or ""
        self.form_precio_costo = p.get("precio_costo") or ""
        self.form_precio_venta = p.get("precio_venta") or ""
        self.form_stock_actual = p.get("stock_actual") or ""
        self.form_stock_minimo = p.get("stock_minimo") or ""
        self.modal_producto   = True

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
            with get_session() as session:
                if self.editando_id:
                    svc.actualizar_producto(session, self.clinica_id, self.editando_id, payload)
                else:
                    svc.crear_producto(session, self.clinica_id, payload)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving      = False
        self.modal_producto = False
        return self.cargar()

    def eliminar_producto(self, prod_id: int):
        try:
            with get_session() as session:
                svc.eliminar_producto(session, self.clinica_id, prod_id)
        except ServiceError:
            pass
        return self.cargar()

    # ── Modal movimiento de stock ──────────────────────────────────────────────

    def abrir_mov(self, p: dict):
        self.mov_prod_id     = p.get("id") or 0
        self.mov_prod_nombre = p.get("nombre") or ""
        self.form_mov_tipo   = "ingreso"
        self.form_mov_cantidad = ""
        self.form_mov_motivo   = ""
        self.modal_mov       = True

    def cerrar_mov(self):
        self.modal_mov = False

    def guardar_movimiento(self):
        if not self.form_mov_cantidad:
            return
        try:
            with get_session() as session:
                svc.registrar_movimiento_stock(
                    session,
                    self.clinica_id,
                    self.mov_prod_id,
                    self.form_mov_tipo,
                    self.form_mov_cantidad,
                    motivo=self.form_mov_motivo,
                )
        except ServiceError:
            pass
        self.modal_mov = False
        return self.cargar()
