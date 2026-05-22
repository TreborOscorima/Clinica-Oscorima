from __future__ import annotations

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import cuentas as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_DEUDA_VACIA: dict = {
    "id": 0, "paciente_id": 0, "paciente_nombre": "",
    "comprobante_id": 0, "comprobante_numero": "",
    "total": "0.00", "pagado": "0.00", "saldo": "0.00",
    "estado": "pendiente", "creado_en": "", "actualizado_en": "",
}


class CuentasState(BaseState):

    # ── Lista ──────────────────────────────────────────────────────────────────
    deudas:      list[dict] = []
    total:       int        = 0
    total_pages: int        = 1
    page:        int        = 1
    per_page:    int        = 20

    # ── KPIs ───────────────────────────────────────────────────────────────────
    total_deudores: int = 0
    total_saldo:    str = "0.00"

    # ── Filtros ────────────────────────────────────────────────────────────────
    filtro_estado: str = ""
    busqueda:      str = ""

    # ── Modal pago ─────────────────────────────────────────────────────────────
    modal_pago:  bool = False
    deuda_sel:   dict = _DEUDA_VACIA
    form_monto:  str  = ""
    form_metodo: str  = "efectivo"
    form_obs:    str  = ""
    form_error:  str  = ""
    is_saving:   bool = False

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    def on_mount(self):
        return self.require_auth() or self.cargar()

    def cargar(self):
        with get_session() as session:
            result = svc.listar(
                session,
                self.clinica_id,
                estado=self.filtro_estado,
                paciente_q=self.busqueda,
                page=self.page,
                per_page=self.per_page,
            )
        self.deudas         = result["data"]
        self.total          = result["total"]
        self.total_pages    = result["pages"]
        self.total_deudores = result["total_deudores"]
        self.total_saldo    = result["total_saldo"]

    # ── Filtros ────────────────────────────────────────────────────────────────

    def set_filtro_estado(self, v: str):
        self.filtro_estado = v
        self.page = 1
        return self.cargar()

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

    # ── Modal pago ─────────────────────────────────────────────────────────────

    def abrir_pago(self, deuda: dict):
        self.deuda_sel   = deuda
        self.form_monto  = deuda["saldo"]
        self.form_metodo = "efectivo"
        self.form_obs    = ""
        self.form_error  = ""
        self.modal_pago  = True

    def cerrar_pago(self):
        self.modal_pago = False
        self.deuda_sel  = _DEUDA_VACIA
        self.form_error = ""

    def set_form_monto(self, v: str):  self.form_monto = v
    def set_form_metodo(self, v: str): self.form_metodo = v
    def set_form_obs(self, v: str):    self.form_obs = v

    async def confirmar_pago(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        try:
            with get_session() as session:
                svc.registrar_pago(
                    session,
                    self.clinica_id,
                    int(self.deuda_sel["id"]),
                    self.form_monto,
                    self.form_metodo,
                    self.form_obs.strip(),
                )
        except (ServiceError, Exception) as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving  = False
        self.modal_pago = False
        self.deuda_sel  = _DEUDA_VACIA
        self.cargar()
