from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import caja as svc
from clinica_app.services import cobro as cobro_svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class CajaState(BaseState):

    # ── Pestaña activa ────────────────────────────────────────────────────────
    tab_caja: str = "movimientos"

    movimientos:  list[dict] = []
    total:        int        = 0
    page:         int        = 1
    per_page:     int        = 30
    total_pages:  int        = 1
    filtro_tipo:  str        = ""
    is_loading:   bool       = False

    # KPIs del día
    ingresos_dia:    str = "0.00"
    egresos_dia:     str = "0.00"
    saldo_dia:       str = "0.00"
    total_movs_dia:  int = 0

    # Modal nuevo movimiento
    modal_abierto:    bool = False
    form_tipo:        str  = "ingreso"
    form_monto:       str  = ""
    form_metodo:      str  = "efectivo"
    form_observacion: str  = ""
    form_error:       str  = ""
    is_saving:        bool = False

    # Cierre de caja
    modal_cierre:  bool       = False
    cierres:       list[dict] = []
    cierre_error:  str        = ""
    cierre_msg:    str        = ""
    is_cerrando:   bool       = False
    ver_historial: bool       = False

    # ── Pestaña Comprobantes ──────────────────────────────────────────────────
    comprobantes:       list[dict] = []
    comp_total:         int        = 0
    comp_page:          int        = 1
    comp_total_pages:   int        = 1
    comp_busqueda:      str        = ""
    comp_filtro_pago:   str        = ""
    comp_is_loading:    bool       = False

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("caja"):
            yield rx.redirect("/")
            return
        await self._cargar_resumen()
        async for s in self.cargar():
            yield s

    async def _cargar_resumen(self):
        async with get_async_session() as session:
            r = await svc.resumen_dia(session, self.clinica_id, sede_id=self.sede_actual_id)
        self.ingresos_dia   = r["ingresos"]
        self.egresos_dia    = r["egresos"]
        self.saldo_dia      = r["saldo"]
        self.total_movs_dia = r["total_movimientos"]

    # ── Carga progresiva ───────────────────────────────────────────────────────

    async def cargar(self):
        self.is_loading = True
        yield
        async with get_async_session() as session:
            result = await svc.listar_movimientos(
                session,
                self.clinica_id,
                sede_id=self.sede_actual_id,
                tipo=self.filtro_tipo,
                page=self.page,
                per_page=self.per_page,
            )
        self.movimientos = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]
        self.is_loading  = False

    async def set_filtro_tipo(self, valor: str):
        self.filtro_tipo = valor
        self.page = 1
        async for s in self.cargar():
            yield s

    # ── Setters de formulario ──────────────────────────────────────────────────

    def set_form_tipo(self, v: str):        self.form_tipo = v
    def set_form_monto(self, v: str):       self.form_monto = v
    def set_form_metodo(self, v: str):      self.form_metodo = v
    def set_form_observacion(self, v: str): self.form_observacion = v

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

    def abrir_modal(self):
        self.form_tipo        = "ingreso"
        self.form_monto       = ""
        self.form_metodo      = "efectivo"
        self.form_observacion = ""
        self.form_error       = ""
        self.modal_abierto    = True

    def cerrar_modal(self):
        self.modal_abierto = False

    async def guardar_movimiento(self):
        if not self.tiene_permiso("caja", write=True):
            self.form_error = "Sin permiso de escritura"
            return
        self.is_saving  = True
        self.form_error = ""
        yield

        if not self.form_monto:
            self.form_error = "El monto es obligatorio"
            self.is_saving  = False
            return

        try:
            async with get_async_session() as session:
                await svc.registrar_movimiento(
                    session,
                    self.clinica_id,
                    {
                        "tipo":        self.form_tipo,
                        "monto":       self.form_monto,
                        "metodo_pago": self.form_metodo,
                        "observacion": self.form_observacion.strip() or None,
                    },
                    sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        await self._cargar_resumen()
        async for s in self.cargar():
            yield s

    async def eliminar_movimiento(self, mov_id: int):
        if not self.tiene_permiso("caja", write=True):
            return
        async with get_async_session() as session:
            try:
                await svc.eliminar_movimiento(session, self.clinica_id, mov_id, sede_id=self.sede_actual_id)
            except ServiceError:
                pass
        await self._cargar_resumen()
        async for s in self.cargar():
            yield s

    # ── Cierre de caja ─────────────────────────────────────────────────────────

    def abrir_cierre(self):
        self.cierre_error = ""
        self.cierre_msg   = ""
        self.modal_cierre = True

    def cerrar_modal_cierre(self):
        self.modal_cierre = False

    async def toggle_historial(self):
        self.ver_historial = not self.ver_historial
        if self.ver_historial:
            await self._cargar_cierres()

    async def _cargar_cierres(self):
        async with get_async_session() as session:
            result = await svc.listar_cierres(session, self.clinica_id, sede_id=self.sede_actual_id)
        self.cierres = result["data"]

    async def confirmar_cierre(self):
        if not self.tiene_permiso("caja", write=True):
            return
        self.is_cerrando  = True
        self.cierre_error = ""
        self.cierre_msg   = ""
        yield
        try:
            async with get_async_session() as session:
                resultado = await svc.realizar_cierre_dia(
                    session, self.clinica_id, sede_id=self.sede_actual_id, usuario_id=self.user_id
                )
            self.cierre_msg = (
                f"Cierre registrado: Ingresos ${resultado['total_ingresos']} | "
                f"Egresos ${resultado['total_egresos']} | Saldo ${resultado['saldo']}"
            )
        except ServiceError as exc:
            self.cierre_error = str(exc)
        self.is_cerrando = False

    # ── Pestaña activa ────────────────────────────────────────────────────────

    async def set_tab_caja(self, tab: str):
        self.tab_caja = tab
        if tab == "comprobantes" and not self.comprobantes:
            async for s in self.cargar_comprobantes():
                yield s

    # ── Comprobantes ──────────────────────────────────────────────────────────

    async def cargar_comprobantes(self):
        self.comp_is_loading = True
        yield
        async with get_async_session() as session:
            result = await cobro_svc.listar(
                session,
                self.clinica_id,
                sede_id=self.sede_actual_id,
                q=self.comp_busqueda,
                forma_pago=self.comp_filtro_pago,
                page=self.comp_page,
                per_page=30,
            )
        self.comprobantes     = result["data"]
        self.comp_total       = result["total"]
        self.comp_total_pages = result["pages"]
        self.comp_is_loading  = False

    async def set_comp_busqueda(self, v: str):
        self.comp_busqueda = v
        self.comp_page = 1
        async for s in self.cargar_comprobantes():
            yield s

    async def set_comp_filtro_pago(self, v: str):
        self.comp_filtro_pago = v
        self.comp_page = 1
        async for s in self.cargar_comprobantes():
            yield s

    async def comp_prev_page(self):
        if self.comp_page > 1:
            self.comp_page -= 1
            async for s in self.cargar_comprobantes():
                yield s

    async def comp_next_page(self):
        if self.comp_page < self.comp_total_pages:
            self.comp_page += 1
            async for s in self.cargar_comprobantes():
                yield s

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    def handle_modal_key(self, key: str):
        if key == "Escape":
            self.modal_abierto = False

    def handle_modal_cierre_key(self, key: str):
        if key == "Escape":
            self.modal_cierre = False

    async def handle_tabla_key(self, key: str):
        if key == "ArrowLeft":
            if self.tab_caja == "comprobantes":
                async for s in self.comp_prev_page():
                    yield s
            else:
                async for s in self.prev_page():
                    yield s
        elif key == "ArrowRight":
            if self.tab_caja == "comprobantes":
                async for s in self.comp_next_page():
                    yield s
            else:
                async for s in self.next_page():
                    yield s
