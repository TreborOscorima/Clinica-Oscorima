from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import cobro as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_COMP_VACIO: dict = {
    "id": 0, "numero": "", "tipo": "recibo", "fecha": "",
    "paciente_id": 0, "paciente_nombre": "",
    "total_bruto": "0.00", "descuento_global": "0.00",
    "total": "0.00", "forma_pago": "", "observacion": "",
}


class CobroState(BaseState):

    # ── Paciente ───────────────────────────────────────────────────────────────
    pac_busqueda:   str       = ""
    pac_resultados: list[dict] = []
    pac_id_sel:     str       = ""
    pac_nombre_sel: str       = ""
    pac_doc_sel:    str       = ""

    # ── Catálogos ──────────────────────────────────────────────────────────────
    servicios_todos:     list[dict] = []
    productos_todos:     list[dict] = []
    servicios_filtrados: list[dict] = []
    productos_filtrados: list[dict] = []

    # ── UI catálogo ────────────────────────────────────────────────────────────
    busqueda_item: str = ""
    tab_activa:    str = "servicios"

    # ── Carrito ────────────────────────────────────────────────────────────────
    carrito: list[dict] = []

    # ── Totales ────────────────────────────────────────────────────────────────
    total_bruto_str: str = "0.00"
    descuento_str:   str = "0.00"
    total_neto_str:  str = "0.00"

    # ── Formulario de pago ─────────────────────────────────────────────────────
    forma_pago:       str  = "efectivo"
    es_cuotas:        bool = False
    num_cuotas:       str  = "2"
    cuota_inicial:    str  = ""
    descuento_global: str  = "0"
    observacion:      str  = ""

    # ── Promociones ────────────────────────────────────────────────────────────
    promociones_vigentes: list[dict] = []
    promo_sel_id:         str        = ""

    # ── Último comprobante (para el modal recibo) ──────────────────────────────
    modal_recibo: bool       = False
    ultimo_comp:  dict       = _COMP_VACIO
    ultimo_items: list[dict] = []

    # ── UI general ─────────────────────────────────────────────────────────────
    form_error: str  = ""
    is_saving:  bool = False

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    def on_mount(self):
        return self.require_auth() or self._cargar_catalogos() or self._cargar_promociones() or self._precargar_turno()

    def _precargar_turno(self):
        turno_id_str = self.router.url.query_parameters.get("turno_id", "")
        if not turno_id_str:
            return
        try:
            turno_id = int(turno_id_str)
        except ValueError:
            return

        from clinica_app.models.turno import Turno
        from clinica_app.models.paciente import Paciente
        from sqlmodel import select

        with get_session() as session:
            turno = session.exec(
                select(Turno).where(
                    Turno.id == turno_id,
                    Turno.clinica_id == self.clinica_id,
                    Turno.is_active.is_(True),
                )
            ).first()
            if turno is None:
                return

            paciente = session.exec(
                select(Paciente).where(Paciente.id == turno.paciente_id)
            ).first()
            if paciente is None:
                return

            pac_nombre = paciente.nombre
            pac_doc = paciente.documento or ""
            pac_id = str(turno.paciente_id)

            servicio_nombre = None
            servicio_precio = None
            servicio_id = None
            if turno.servicio:
                servicio_nombre = turno.servicio.nombre
                servicio_precio = str(turno.servicio.precio or "0")
                servicio_id = str(turno.servicio_id)

        self.pac_id_sel     = pac_id
        self.pac_nombre_sel = pac_nombre
        self.pac_doc_sel    = pac_doc
        self.pac_busqueda   = pac_nombre
        self.pac_resultados = []

        if servicio_id and servicio_nombre and servicio_precio:
            self.agregar_servicio(servicio_id, servicio_nombre, servicio_precio)

    def _cargar_catalogos(self):
        from clinica_app.models.servicio   import Servicio
        from clinica_app.models.inventario import Producto
        from sqlmodel import select

        with get_session() as session:
            servs = session.exec(
                select(Servicio)
                .where(Servicio.clinica_id == self.clinica_id, Servicio.is_active.is_(True))
                .order_by(Servicio.nombre.asc())
                .limit(300)
            ).all()
            prods = session.exec(
                select(Producto)
                .where(Producto.clinica_id == self.clinica_id, Producto.is_active.is_(True))
                .order_by(Producto.nombre.asc())
                .limit(300)
            ).all()
            self.servicios_todos = [
                {"id": str(s.id), "nombre": s.nombre, "precio": str(s.precio or 0),
                 "categoria": s.categoria or ""}
                for s in servs
            ]
            self.productos_todos = [
                {"id": str(p.id), "nombre": p.nombre, "precio": str(p.precio_venta or 0)}
                for p in prods
            ]
        self.servicios_filtrados = self.servicios_todos[:40]
        self.productos_filtrados = self.productos_todos[:40]

    def _cargar_promociones(self):
        from clinica_app.models.promocion import Promocion
        from sqlmodel import select
        from datetime import datetime, timezone

        ahora = datetime.now(timezone.utc).replace(tzinfo=None)
        with get_session() as session:
            promos = session.exec(
                select(Promocion).where(
                    Promocion.clinica_id == self.clinica_id,
                    Promocion.activo.is_(True),
                    Promocion.is_active.is_(True),
                )
            ).all()
        self.promociones_vigentes = [
            {
                "id":       str(p.id),
                "nombre":   p.nombre,
                "tipo":     p.tipo,
                "valor":    str(p.valor),
                "aplica_a": p.aplica_a,
            }
            for p in promos
            if (
                (p.fecha_inicio is None or p.fecha_inicio.replace(tzinfo=None) <= ahora)
                and (p.fecha_fin is None or p.fecha_fin.replace(tzinfo=None) >= ahora)
            )
        ]

    # ── Búsqueda de paciente ───────────────────────────────────────────────────

    def set_pac_busqueda(self, v: str):
        self.pac_busqueda = v
        if self.pac_id_sel:
            self.pac_id_sel     = ""
            self.pac_nombre_sel = ""
            self.pac_doc_sel    = ""

        if len(v) >= 2:
            from clinica_app.models.paciente import Paciente
            from sqlalchemy import String, cast, or_
            from sqlmodel import select

            like = f"%{v}%"
            with get_session() as session:
                pacs = session.exec(
                    select(Paciente).where(
                        Paciente.clinica_id == self.clinica_id,
                        Paciente.is_active.is_(True),
                        or_(
                            Paciente.nombre.ilike(like),
                            cast(Paciente.documento, String).ilike(like),
                        ),
                    ).limit(8)
                ).all()
            self.pac_resultados = [
                {"id": str(p.id), "nombre": p.nombre, "documento": p.documento or ""}
                for p in pacs
            ]
        else:
            self.pac_resultados = []

    def seleccionar_paciente(self, pac_id: str, pac_nombre: str, pac_doc: str):
        self.pac_id_sel     = pac_id
        self.pac_nombre_sel = pac_nombre
        self.pac_doc_sel    = pac_doc
        self.pac_busqueda   = pac_nombre
        self.pac_resultados = []

    def limpiar_paciente(self):
        self.pac_id_sel     = ""
        self.pac_nombre_sel = ""
        self.pac_doc_sel    = ""
        self.pac_busqueda   = ""
        self.pac_resultados = []

    # ── Catálogo: pestañas y búsqueda ─────────────────────────────────────────

    def set_tab_activa(self, tab: str):
        self.tab_activa    = tab
        self.busqueda_item = ""
        self.servicios_filtrados = self.servicios_todos[:40]
        self.productos_filtrados = self.productos_todos[:40]

    def set_busqueda_item(self, v: str):
        self.busqueda_item = v
        q = v.lower()
        if self.tab_activa == "servicios":
            src = [s for s in self.servicios_todos if q in s["nombre"].lower()] if q else self.servicios_todos
            self.servicios_filtrados = src[:40]
        else:
            src = [p for p in self.productos_todos if q in p["nombre"].lower()] if q else self.productos_todos
            self.productos_filtrados = src[:40]

    # ── Carrito ────────────────────────────────────────────────────────────────

    def agregar_servicio(self, ref_id: str, nombre: str, precio: str):
        self._agregar("servicio", ref_id, nombre, precio)

    def agregar_producto(self, ref_id: str, nombre: str, precio: str):
        self._agregar("producto", ref_id, nombre, precio)

    def _agregar(self, tipo: str, ref_id: str, nombre: str, precio_str: str):
        try:
            precio = Decimal(precio_str or "0").quantize(Decimal("0.01"))
        except InvalidOperation:
            precio = Decimal("0")

        nueva: list[dict] = []
        encontrado = False
        for item in self.carrito:
            if item["tipo"] == tipo and item["ref_id"] == ref_id:
                qty      = Decimal(item["cantidad"]) + Decimal("1")
                subtotal = (qty * Decimal(item["precio_unit"])).quantize(Decimal("0.01"))
                nueva.append({**item, "cantidad": str(qty), "subtotal": str(subtotal)})
                encontrado = True
            else:
                nueva.append(item)

        if not encontrado:
            nueva.append({
                "tipo":        tipo,
                "ref_id":      ref_id,
                "nombre":      nombre,
                "cantidad":    "1",
                "precio_unit": str(precio),
                "subtotal":    str(precio),
            })

        self.carrito = nueva
        self._recalcular()

    def quitar_item(self, tipo: str, ref_id: str):
        self.carrito = [
            i for i in self.carrito
            if not (i["tipo"] == tipo and i["ref_id"] == ref_id)
        ]
        self._recalcular()

    def vaciar_carrito(self):
        self.carrito = []
        self._recalcular()

    def _recalcular(self):
        try:
            bruto = sum(Decimal(i["subtotal"]) for i in self.carrito)
        except InvalidOperation:
            bruto = Decimal("0")
        try:
            descuento = Decimal(self.descuento_global or "0")
        except InvalidOperation:
            descuento = Decimal("0")
        neto = max(Decimal("0"), bruto - descuento)
        q = Decimal("0.01")
        self.total_bruto_str = str(bruto.quantize(q))
        self.descuento_str   = str(descuento.quantize(q))
        self.total_neto_str  = str(neto.quantize(q))

    # ── Setters formulario ────────────────────────────────────────────────────

    def set_forma_pago(self, v: str):       self.forma_pago = v
    def set_es_cuotas(self, v: bool):       self.es_cuotas = v
    def set_num_cuotas(self, v: str):       self.num_cuotas = v
    def set_cuota_inicial(self, v: float):  self.cuota_inicial = str(v) if v else ""
    def set_observacion(self, v: str):      self.observacion = v

    def set_descuento_global(self, v: float):
        self.descuento_global = str(v) if v else "0"
        self.promo_sel_id = ""
        self._recalcular()

    def set_promo_sel_id(self, promo_id: str):
        self.promo_sel_id = promo_id
        if not promo_id:
            self.descuento_global = "0"
            self._recalcular()
            return
        promo = next((p for p in self.promociones_vigentes if p["id"] == promo_id), None)
        if promo is None:
            return
        try:
            valor = Decimal(promo["valor"])
            aplica_a = promo["aplica_a"]
            if aplica_a == "todo":
                base = Decimal(self.total_bruto_str)
            elif aplica_a == "servicios":
                base = sum(Decimal(i["subtotal"]) for i in self.carrito if i["tipo"] == "servicio")
            else:  # productos
                base = sum(Decimal(i["subtotal"]) for i in self.carrito if i["tipo"] == "producto")

            if promo["tipo"] == "porcentaje":
                descuento = (base * valor / Decimal("100")).quantize(Decimal("0.01"))
            else:
                descuento = valor.quantize(Decimal("0.01"))

            self.descuento_global = str(max(Decimal("0"), descuento))
        except (InvalidOperation, StopIteration):
            self.descuento_global = "0"
        self._recalcular()

    # ── Confirmar cobro ────────────────────────────────────────────────────────

    async def confirmar_cobro(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        if not self.pac_id_sel:
            self.form_error = "Seleccione un paciente antes de cobrar"
            self.is_saving  = False
            return

        if not self.carrito:
            self.form_error = "Agregue al menos un servicio o producto al carrito"
            self.is_saving  = False
            return

        items: list[dict[str, Any]] = [
            {
                "tipo":        i["tipo"],
                "ref_id":      int(i["ref_id"]),
                "nombre":      i["nombre"],
                "cantidad":    i["cantidad"],
                "precio_unit": i["precio_unit"],
            }
            for i in self.carrito
        ]

        payload: dict[str, Any] = {
            "paciente_id":      int(self.pac_id_sel),
            "items":            items,
            "forma_pago":       self.forma_pago,
            "descuento_global": self.descuento_global or "0",
            "observacion":      self.observacion.strip() or None,
            "es_cuotas":        self.es_cuotas,
            "num_cuotas":       int(self.num_cuotas or "1"),
            "cuota_inicial":    self.cuota_inicial or "0",
        }

        try:
            with get_session() as session:
                result = svc.crear(session, self.clinica_id, payload)
        except (ServiceError, Exception) as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        # Guardar datos del recibo ANTES de limpiar el formulario
        pac_nombre       = self.pac_nombre_sel
        items_recibo     = result.pop("items", [])
        result["paciente_nombre"] = pac_nombre

        self.is_saving = False
        self._limpiar_pos()
        self.ultimo_comp  = result
        self.ultimo_items = items_recibo
        self.modal_recibo = True

    def _limpiar_pos(self):
        """Resetea el formulario del POS sin tocar ultimo_comp/ultimo_items."""
        self.carrito          = []
        self.pac_id_sel       = ""
        self.pac_nombre_sel   = ""
        self.pac_doc_sel      = ""
        self.pac_busqueda     = ""
        self.pac_resultados   = []
        self.forma_pago       = "efectivo"
        self.es_cuotas        = False
        self.num_cuotas       = "2"
        self.cuota_inicial    = ""
        self.descuento_global = "0"
        self.promo_sel_id     = ""
        self.observacion      = ""
        self.total_bruto_str  = "0.00"
        self.descuento_str    = "0.00"
        self.total_neto_str   = "0.00"
        self.busqueda_item    = ""
        self.form_error       = ""

    # ── Modal recibo ───────────────────────────────────────────────────────────

    def cerrar_recibo(self):
        self.modal_recibo = False
        self.ultimo_comp  = _COMP_VACIO
        self.ultimo_items = []

    def imprimir_recibo(self):
        return rx.call_script("window.print()")
