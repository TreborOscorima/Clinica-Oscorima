from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import compras as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_COMPRA_VACIA: dict = {
    "id": 0, "fecha": "", "proveedor_id": 0, "proveedor": "",
    "tipo_doc": "", "numero": "", "nro_registro": "",
    "total": "0.00", "observacion": "",
}

_PROV_VACIO: dict = {
    "id": 0, "nombre": "", "documento": "", "email": "", "telefono": "", "direccion": ""
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
    is_loading:        bool = False
    prov_sel_detalle:  dict = _PROV_VACIO

    # ── Carrito de items ───────────────────────────────────────────────────────
    carrito:              list[dict] = []
    cart_producto_id:     str        = ""
    cart_producto_nombre: str        = ""
    cart_cantidad:        str        = ""
    cart_costo:           str        = ""
    cart_error:           str        = ""

    # Búsqueda de producto (reemplaza select)
    cart_busqueda:     str        = ""
    cart_prod_matches: list[dict] = []

    # ── Modal detalle ──────────────────────────────────────────────────────────
    modal_detalle:  bool       = False
    compra_sel:     dict       = _COMPRA_VACIA
    detalle_items:  list[dict] = []

    # ── Modal anular ──────────────────────────────────────────────────────────
    modal_anular:  bool = False
    anular_id:     int  = 0
    anular_numero: str  = ""

    # ── Modal: nuevo producto rápido ───────────────────────────────────────────
    modal_nuevo_prod: bool = False
    np_nombre:        str  = ""
    np_sku:           str  = ""
    np_precio_costo:  str  = ""
    np_precio_venta:  str  = ""
    np_stock_inicial: str  = "0"
    np_error:         str  = ""
    np_is_saving:     bool = False

    # ── Modal: gestionar proveedores ──────────────────────────────────────────
    modal_proveedores:   bool = False
    prov_edit_id:        int  = 0
    prov_form_nombre:    str  = ""
    prov_form_documento: str  = ""
    prov_form_email:     str  = ""
    prov_form_telefono:  str  = ""
    prov_form_direccion: str  = ""
    prov_form_error:     str  = ""
    prov_is_saving:      bool = False

    # ── Computed vars ─────────────────────────────────────────────────────────

    @rx.var
    def cart_sin_coincidencias(self) -> bool:
        return (
            bool(self.cart_busqueda.strip())
            and len(self.cart_prod_matches) == 0
            and self.cart_producto_id == ""
        )

    @rx.var
    def cart_tiene_producto(self) -> bool:
        return self.cart_producto_id != ""

    @rx.var
    def prov_tiene_sel(self) -> bool:
        return self.form_proveedor_id not in ("", "0")

    @rx.var
    def prov_editando(self) -> bool:
        return self.prov_edit_id > 0

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("compras"):
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
                q=self.busqueda,
                page=self.page,
                per_page=self.per_page,
            )
            provs = await svc.listar_proveedores(session, self.clinica_id, self.sede_actual_id)

        self.compras         = result["data"]
        self.total           = result["total"]
        self.total_pages     = result["pages"]
        self.total_compras   = result["total_compras"]
        self.total_gastado   = result["total_gastado"]
        self.proveedores_cat = provs
        self.is_loading      = False

    async def _cargar_productos(self):
        from clinica_app.services.inventario import listar_productos
        async with get_async_session() as session:
            res = await listar_productos(session, self.clinica_id, sede_id=self.sede_actual_id, per_page=500)
            self.productos_cat = [
                {
                    "id":     str(p["id"]),
                    "nombre": p["nombre"],
                    "sku":    p.get("sku") or "",
                    "costo":  p["precio_costo"] or "0.00",
                }
                for p in res["data"]
            ]

    # ── Búsqueda lista ─────────────────────────────────────────────────────────

    async def set_busqueda(self, v: str):
        self.busqueda = v
        self.page = 1
        if len(v) >= 2 or v == "":
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

    # ── Modal nueva compra ─────────────────────────────────────────────────────

    async def abrir_nueva(self):
        await self._cargar_productos()
        self.form_proveedor_id    = ""
        self.form_tipo_doc        = "factura"
        self.form_numero          = ""
        self.form_nro_registro    = ""
        self.form_observacion     = ""
        self.form_error           = ""
        self.carrito              = []
        self.cart_producto_id     = ""
        self.cart_producto_nombre = ""
        self.cart_cantidad        = ""
        self.cart_costo           = ""
        self.cart_error           = ""
        self.cart_busqueda        = ""
        self.cart_prod_matches    = []
        self.prov_sel_detalle     = _PROV_VACIO
        self.modal_nueva          = True

    def cerrar_nueva(self):
        self.modal_nueva = False
        self.form_error  = ""

    def set_form_proveedor_id(self, v: str):
        self.form_proveedor_id = v
        self.prov_sel_detalle  = _PROV_VACIO
        for p in self.proveedores_cat:
            if str(p["id"]) == v:
                self.prov_sel_detalle = p
                break

    def set_form_tipo_doc(self, v: str):     self.form_tipo_doc = v
    def set_form_numero(self, v: str):       self.form_numero = v
    def set_form_nro_registro(self, v: str): self.form_nro_registro = v
    def set_form_observacion(self, v: str):  self.form_observacion = v

    # ── Búsqueda de producto en carrito ───────────────────────────────────────

    def set_cart_busqueda(self, v: str):
        self.cart_busqueda = v
        if not v.strip():
            self.cart_prod_matches = []
            return
        q = v.strip().lower()
        self.cart_prod_matches = [
            p for p in self.productos_cat
            if q in p["nombre"].lower() or q in (p.get("sku") or "").lower()
        ][:10]

    def seleccionar_producto(self, prod_id: str):
        for p in self.productos_cat:
            if p["id"] == prod_id:
                self.cart_producto_id    = prod_id
                self.cart_producto_nombre = p["nombre"]
                self.cart_costo          = p["costo"] or ""
                break
        self.cart_busqueda     = ""
        self.cart_prod_matches = []

    def limpiar_producto_sel(self):
        self.cart_producto_id    = ""
        self.cart_producto_nombre = ""
        self.cart_costo          = ""
        self.cart_busqueda       = ""
        self.cart_prod_matches   = []

    def handle_cart_busqueda_key(self, key: str):
        if key != "Enter":
            return
        q = self.cart_busqueda.strip()
        if not q:
            return
        # Exact SKU match (barcode scanner sends full code + Enter)
        q_upper = q.upper()
        for p in self.productos_cat:
            if (p.get("sku") or "").upper() == q_upper:
                self.seleccionar_producto(p["id"])
                return
        # Single match auto-select
        if len(self.cart_prod_matches) == 1:
            self.seleccionar_producto(self.cart_prod_matches[0]["id"])
            return
        # Not found → open new product modal with SKU/nombre pre-filled
        if not self.cart_prod_matches:
            self.np_sku           = q
            self.np_nombre        = q
            self.np_precio_costo  = ""
            self.np_precio_venta  = ""
            self.np_stock_inicial = "0"
            self.np_error         = ""
            self.modal_nuevo_prod = True

    # ── Carrito ────────────────────────────────────────────────────────────────

    def set_cart_cantidad(self, v: str): self.cart_cantidad = v
    def set_cart_costo(self, v: str):    self.cart_costo = v

    def agregar_item(self):
        self.cart_error = ""
        if not self.cart_producto_id:
            self.cart_error = "Selecciona un producto de la lista"
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

        subtotal = round(cant * costo, 2)
        self.carrito = [
            *self.carrito,
            {
                "producto_id":     self.cart_producto_id,
                "producto_nombre": self.cart_producto_nombre or self.cart_producto_id,
                "cantidad":        f"{cant:.3f}",
                "costo_unitario":  f"{costo:.2f}",
                "subtotal":        f"{subtotal:.2f}",
            },
        ]
        self.cart_producto_id    = ""
        self.cart_producto_nombre = ""
        self.cart_cantidad        = ""
        self.cart_costo           = ""
        self.cart_busqueda        = ""
        self.cart_prod_matches    = []

    def quitar_item(self, idx: int):
        self.carrito = [i for j, i in enumerate(self.carrito) if j != idx]

    @rx.var
    def carrito_total(self) -> str:
        total = sum(float(i["subtotal"]) for i in self.carrito)
        return f"{total:.2f}"

    async def guardar_compra(self):
        if not self.tiene_permiso("compras", write=True):
            self.form_error = "Sin permiso de escritura"
            return
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
            async with get_async_session() as session:
                from clinica_app.services.configuracion import obtener_clinica
                config = await obtener_clinica(session, self.clinica_id)
                await svc.crear(session, self.clinica_id, payload, items,
                                margen_global=config["margen_global"], sede_id=self.sede_actual_id)
        except (ServiceError, Exception) as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving   = False
        self.modal_nueva = False
        async for s in self.cargar():
            yield s

    # ── Modal detalle ──────────────────────────────────────────────────────────

    async def ver_detalle(self, compra: dict):
        self.compra_sel = compra
        async with get_async_session() as session:
            self.detalle_items = await svc.obtener_items(session, int(compra["id"]))
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
            async with get_async_session() as session:
                await svc.anular(session, self.clinica_id, self.anular_id)
        except (ServiceError, Exception) as exc:
            self.form_error   = str(exc)
            self.is_saving    = False
            self.modal_anular = False
            return

        self.is_saving    = False
        self.modal_anular = False
        async for s in self.cargar():
            yield s

    # ── Modal: nuevo producto rápido ───────────────────────────────────────────

    def abrir_nuevo_prod(self):
        self.np_nombre        = self.cart_busqueda.strip()
        self.np_sku           = ""
        self.np_precio_costo  = ""
        self.np_precio_venta  = ""
        self.np_stock_inicial = "0"
        self.np_error         = ""
        self.modal_nuevo_prod = True

    def cerrar_nuevo_prod(self):
        self.modal_nuevo_prod = False
        self.np_error         = ""

    def set_np_nombre(self, v: str):        self.np_nombre = v
    def set_np_sku(self, v: str):           self.np_sku = v
    def set_np_precio_costo(self, v: float):  self.np_precio_costo = str(v) if v else ""
    def set_np_precio_venta(self, v: float):  self.np_precio_venta = str(v) if v else ""
    def set_np_stock_inicial(self, v: float): self.np_stock_inicial = str(int(v)) if v else "0"

    async def guardar_nuevo_prod(self):
        self.np_error    = ""
        self.np_is_saving = True
        yield
        if not self.np_nombre.strip():
            self.np_error    = "El nombre es requerido"
            self.np_is_saving = False
            return
        from clinica_app.services.inventario import crear_producto
        try:
            async with get_async_session() as session:
                prod = await crear_producto(session, self.clinica_id, {
                    "nombre":       self.np_nombre.strip(),
                    "sku":          self.np_sku.strip() or None,
                    "precio_costo": self.np_precio_costo or None,
                    "precio_venta": self.np_precio_venta or None,
                    "stock_actual": self.np_stock_inicial or "0",
                }, sede_id=self.sede_actual_id)
        except Exception as exc:
            self.np_error    = str(exc)
            self.np_is_saving = False
            return

        new_entry = {
            "id":     str(prod["id"]),
            "nombre": prod["nombre"],
            "sku":    prod.get("sku") or "",
            "costo":  prod.get("precio_costo") or "0.00",
        }
        self.productos_cat    = [*self.productos_cat, new_entry]
        self.np_is_saving     = False
        self.modal_nuevo_prod = False
        self.seleccionar_producto(new_entry["id"])

    # ── Modal: gestionar proveedores ──────────────────────────────────────────

    def abrir_proveedores(self):
        self.prov_edit_id        = 0
        self.prov_form_nombre    = ""
        self.prov_form_documento = ""
        self.prov_form_email     = ""
        self.prov_form_telefono  = ""
        self.prov_form_direccion = ""
        self.prov_form_error     = ""
        self.modal_proveedores   = True

    def cerrar_proveedores(self):
        self.modal_proveedores   = False
        self.prov_edit_id        = 0
        self.prov_form_nombre    = ""
        self.prov_form_documento = ""
        self.prov_form_email     = ""
        self.prov_form_telefono  = ""
        self.prov_form_direccion = ""
        self.prov_form_error     = ""

    def set_prov_form_nombre(self, v: str):    self.prov_form_nombre = v
    def set_prov_form_documento(self, v: str): self.prov_form_documento = v
    def set_prov_form_email(self, v: str):     self.prov_form_email = v
    def set_prov_form_telefono(self, v: str):  self.prov_form_telefono = v
    def set_prov_form_direccion(self, v: str): self.prov_form_direccion = v

    def prov_iniciar_edicion(self, prov: dict):
        self.prov_edit_id        = int(prov.get("id") or 0)
        self.prov_form_nombre    = prov.get("nombre") or ""
        self.prov_form_documento = prov.get("documento") or ""
        self.prov_form_email     = prov.get("email") or ""
        self.prov_form_telefono  = prov.get("telefono") or ""
        self.prov_form_direccion = prov.get("direccion") or ""
        self.prov_form_error     = ""

    def prov_cancelar_edicion(self):
        self.prov_edit_id        = 0
        self.prov_form_nombre    = ""
        self.prov_form_documento = ""
        self.prov_form_email     = ""
        self.prov_form_telefono  = ""
        self.prov_form_direccion = ""
        self.prov_form_error     = ""

    async def guardar_proveedor(self):
        self.prov_form_error = ""
        self.prov_is_saving  = True
        yield
        payload = {
            "nombre":    self.prov_form_nombre.strip(),
            "documento": self.prov_form_documento.strip(),
            "email":     self.prov_form_email.strip(),
            "telefono":  self.prov_form_telefono.strip(),
            "direccion": self.prov_form_direccion.strip(),
        }
        try:
            async with get_async_session() as session:
                if self.prov_edit_id:
                    await svc.actualizar_proveedor(session, self.clinica_id, self.prov_edit_id, payload)
                else:
                    await svc.crear_proveedor(session, self.clinica_id, payload, self.sede_actual_id)
                provs = await svc.listar_proveedores(session, self.clinica_id, self.sede_actual_id)
        except Exception as exc:
            self.prov_form_error = str(exc)
            self.prov_is_saving  = False
            return

        self.proveedores_cat     = provs
        self.prov_is_saving      = False
        self.prov_edit_id        = 0
        self.prov_form_nombre    = ""
        self.prov_form_documento = ""
        self.prov_form_email     = ""
        self.prov_form_telefono  = ""
        self.prov_form_direccion = ""
        # Refresh selected provider detail if visible
        if self.form_proveedor_id:
            for p in self.proveedores_cat:
                if str(p["id"]) == self.form_proveedor_id:
                    self.prov_sel_detalle = p
                    break

    async def prov_eliminar(self, prov_id: int):
        try:
            async with get_async_session() as session:
                await svc.eliminar_proveedor(session, self.clinica_id, prov_id)
                provs = await svc.listar_proveedores(session, self.clinica_id, self.sede_actual_id)
        except Exception:
            return
        self.proveedores_cat = provs
        if str(prov_id) == self.form_proveedor_id:
            self.form_proveedor_id = ""
            self.prov_sel_detalle  = _PROV_VACIO

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    async def handle_modal_nueva_key(self, key: str):
        if key == "Escape":
            self.cerrar_nueva()
        elif key == "Enter" and self.modal_nueva and not self.is_saving:
            async for s in self.guardar_compra():
                yield s

    async def handle_modal_anular_key(self, key: str):
        if key == "Escape":
            self.cerrar_anular()
        elif key == "Enter" and self.modal_anular and not self.is_saving:
            async for s in self.ejecutar_anular():
                yield s

    async def handle_tabla_key(self, key: str):
        if key == "ArrowLeft":
            async for s in self.prev_page():
                yield s
        elif key == "ArrowRight":
            async for s in self.next_page():
                yield s
