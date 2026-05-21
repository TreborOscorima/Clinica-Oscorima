from __future__ import annotations

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import caja as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class CajaState(BaseState):

    movimientos: list[dict] = []
    total:       int        = 0
    page:        int        = 1
    per_page:    int        = 30
    total_pages: int        = 1
    filtro_tipo: str        = ""

    # KPIs del día
    ingresos_dia:  str = "0.00"
    egresos_dia:   str = "0.00"
    saldo_dia:     str = "0.00"
    total_movs_dia: int = 0

    # Modal nuevo movimiento
    modal_abierto: bool = False
    form_tipo:         str  = "ingreso"
    form_monto:        str  = ""
    form_metodo:       str  = "efectivo"
    form_observacion:  str  = ""
    form_error:        str  = ""
    is_saving:         bool = False

    def on_mount(self):
        return self.require_auth() or self._cargar_resumen() or self.cargar()

    def _cargar_resumen(self):
        with get_session() as session:
            r = svc.resumen_dia(session, self.clinica_id)
        self.ingresos_dia   = r["ingresos"]
        self.egresos_dia    = r["egresos"]
        self.saldo_dia      = r["saldo"]
        self.total_movs_dia = r["total_movimientos"]

    def cargar(self):
        with get_session() as session:
            result = svc.listar_movimientos(
                session,
                self.clinica_id,
                tipo=self.filtro_tipo,
                page=self.page,
                per_page=self.per_page,
            )
        self.movimientos = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]

    def set_filtro_tipo(self, valor: str):
        self.filtro_tipo = valor
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
        self.is_saving  = True
        self.form_error = ""
        yield

        if not self.form_monto:
            self.form_error = "El monto es obligatorio"
            self.is_saving  = False
            return

        try:
            with get_session() as session:
                svc.registrar_movimiento(
                    session,
                    self.clinica_id,
                    {
                        "tipo":        self.form_tipo,
                        "monto":       self.form_monto,
                        "metodo_pago": self.form_metodo,
                        "observacion": self.form_observacion.strip() or None,
                    },
                )
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        return self._cargar_resumen() or self.cargar()

    def eliminar_movimiento(self, mov_id: int):
        try:
            with get_session() as session:
                svc.eliminar_movimiento(session, self.clinica_id, mov_id)
        except ServiceError:
            pass
        return self._cargar_resumen() or self.cargar()
