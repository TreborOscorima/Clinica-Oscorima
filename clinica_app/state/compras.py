from __future__ import annotations

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import compras as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_COMPRA_VACIA: dict = {
    "id": 0, "fecha": "", "proveedor_id": 0, "proveedor": "",
    "tipo_doc": "", "numero": "", "nro_registro": "",
    "total": "0.00", "observacion": "",
}


class ComprasState(BaseState):

    # ── Lista ──────────────────────────────────────────────────────────────────
    compras:     list[dict] = []
    total:       int        = 0
    total_pages: int        = 1
    page:        int        = 1
    per_page:    int        = 20
    busqueda:    str        = ""

    # ── KPIs ───────────────────────────────────────────────────────────────────
    total_compras: int = 0
    total_gastado: str = "0.00"

    # ── Catálogos ──────────────────────────────────────────────────────────────
    proveedores_cat: list[dict] = []
    productos_cat:   list[dict] = []

    # ── Modal nueva compra ─────────────────────────────────────────────────────
    modal_nueva:       bool = False
    form_proveedor_id: str  = ""
    form_tipo_doc:     str  = "factura"
    form_numero:       str  = ""
    form_nro_registro: str  = ""
    form_observacion:  str  = ""
    form_error:        str  = ""
    is_saving:         bool = False

    # ── Carrito de items ───────────────────────────────────────────────────────
    carrito:          list[dict] = []
    cart_producto_id: str        = ""
    cart_cantidad:    str        = ""
    cart_costo:       str        = ""
    cart_error:       str        = ""

    # ── Modal detalle ──────────────────────────────────────────────────────────
    modal_detalle:  bool       = False
    compra_sel:     dict       = _COMPRA_VACIA
    detalle_items:  list[dict] = []

    # ── Modal anular ──────────────────────────────────────────────────────────
    modal_anular:  bool = False
    anular_id:     int  = 0
    anular_numero: str  = ""

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

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
            provs = svc.listar_proveedores(session, self.clinica_id)

        self.compras        = result["data"]
        self.total          = result["total"]
        self.total_pages    = result["pages"]
        self.total_compras  = result["total_compras"]
        self.total_gastado  = result["total_gastado"]
        self.proveedores_cat = provs

    def _cargar_productos(self):
        from clinica_app.services.inventario import listar_productos
        with get_session() as session:
            res = listar_productos(session, self.clinica_id, per_page=500)
            self.productos_cat = [
                {
                    "id":     str(p["id"]),
                    "nombre": p["nombre"],
                    "costo":  p["precio_costo"] or "0.00",
                }
                for p in res["data"]
            ]

    # ── Búsqueda ───────────────────────────────────────────────────────────────

    def set_busqueda(self, v: str):
        self.busqueda = v
        self.page = 1
        if len(v) >= 2 or v == "":
            return self.cargar()

    # ── Paginación ─────────────────────────────────────────────────────────────

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            return self.cargar()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            return self.cargar()

    # ── Modal nueva compra ─────────────────────────────────────────────────────

    def abrir_nueva(self):
        self._cargar_productos()
        self.form_proveedor_id = ""
        self.form_tipo_doc     = "factura"
        self.form_numero       = ""
        self.form_nro_registro = ""
        self.form_observacion  = ""
        self.form_error        = ""
        self.carrito           = []
        self.cart_producto_id  = ""
        self.cart_cantidad     = ""
        self.cart_costo        = ""
        self.cart_error        = ""
        self.modal_nueva       = True

    def cerrar_nueva(self):
        self.modal_nueva = False
        self.form_error  = ""

    def set_form_proveedor_id(self, v: str): self.form_proveedor_id = v
    def set_form_tipo_doc(self, v: str):     self.form_tipo_doc = v
    def set_form_numero(self, v: str):       self.form_numero = v
    def set_form_nro_registro(self, v: str): self.form_nro_registro = v
    def set_form_observacion(self, v: str):  self.form_observacion = v

    # ── Carrito ────────────────────────────────────────────────────────────────

    def set_cart_producto_id(self, v: str):
        self.cart_producto_id = v
        for p in self.productos_cat:
            if p["id"] == v:
                self.cart_costo = p["costo"] or ""
                break
        else:
            self.cart_costo = ""

    def set_cart_cantidad(self, v: str): self.cart_cantidad = v
    def set_cart_costo(self, v: str):    self.cart_costo = v

    def agregar_item(self):
        self.cart_error = ""
        if not self.cart_producto_id:
            self.cart_error = "Selecciona un producto"
            return
        try:
            cant = float(self.cart_cantidad or "0")
            if cant <= 0:
                raise ValueError()
        except ValueError:
            self.cart_error = "Cantidad inválida"
            return
        try:
            costo = float(self.cart_costo or "0")
            if costo < 0:
                raise ValueError()
        except ValueError:
            self.cart_error = "Costo inválido"
            return

        for p in self.productos_cat:
            if p["id"] == self.cart_producto_id:
                prod_nombre = p["nombre"]
                break
        else:
            self.cart_error = "Producto no encontrado"
            return

        subtotal = round(cant * costo, 2)
        self.carrito = [
            *self.carrito,
            {
                "producto_id":    self.cart_producto_id,
                "producto_nombre": prod_nombre,
                "cantidad":       f"{cant:.3f}",
                "costo_unitario": f"{costo:.2f}",
                "subtotal":       f"{subtotal:.2f}",
            },
        ]
        self.cart_producto_id = ""
        self.cart_cantidad    = ""
        self.cart_costo       = ""

    def quitar_item(self, idx: int):
        self.carrito = [i for j, i in enumerate(self.carrito) if j != idx]

    @rx.var
    def carrito_total(self) -> str:
        total = sum(float(i["subtotal"]) for i in self.carrito)
        return f"{total:.2f}"

    async def guardar_compra(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        payload = {
            "proveedor_id":  self.form_proveedor_id or None,
            "tipo_doc":      self.form_tipo_doc,
            "numero":        self.form_numero.strip(),
            "nro_registro":  self.form_nro_registro.strip(),
            "observacion":   self.form_observacion.strip(),
        }
        items = [
            {
                "producto_id":    int(i["producto_id"]),
                "cantidad":       i["cantidad"],
                "costo_unitario": i["costo_unitario"],
            }
            for i in self.carrito
        ]

        try:
            with get_session() as session:
                svc.crear(session, self.clinica_id, payload, items)
        except (ServiceError, Exception) as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving   = False
        self.modal_nueva = False
        self.cargar()

    # ── Modal detalle ──────────────────────────────────────────────────────────

    def ver_detalle(self, compra: dict):
        self.compra_sel = compra
        with get_session() as session:
            self.detalle_items = svc.obtener_items(session, int(compra["id"]))
        self.modal_detalle = True

    def cerrar_detalle(self):
        self.modal_detalle = False
        self.compra_sel    = _COMPRA_VACIA

    # ── Anular compra ──────────────────────────────────────────────────────────

    def confirmar_anular(self, compra: dict):
        self.anular_id     = int(compra["id"])
        self.anular_numero = compra["numero"] or f"#{compra['id']}"
        self.modal_anular  = True

    def cerrar_anular(self):
        self.modal_anular = False

    async def ejecutar_anular(self):
        self.is_saving = True
        yield
        try:
            with get_session() as session:
                svc.anular(session, self.clinica_id, self.anular_id)
        except (ServiceError, Exception) as exc:
            self.form_error   = str(exc)
            self.is_saving    = False
            self.modal_anular = False
            return

        self.is_saving    = False
        self.modal_anular = False
        self.cargar()
