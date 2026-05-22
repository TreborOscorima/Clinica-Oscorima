from __future__ import annotations

from clinica_app.database import get_session
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

    # ── Modal eliminar ─────────────────────────────────────────────────────────
    modal_eliminar: bool = False
    eliminar_id:    int  = 0
    eliminar_nombre: str = ""

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    def on_mount(self):
        return self.require_auth() or self.cargar()

    def cargar(self):
        with get_session() as session:
            result = svc.listar(
                session,
                self.clinica_id,
                solo_activas=self.solo_activas,
                q=self.busqueda,
                page=self.page,
                per_page=self.per_page,
            )
        self.promociones   = result["data"]
        self.total         = result["total"]
        self.total_pages   = result["pages"]
        self.total_activas = result["total_activas"]

    # ── Filtros ────────────────────────────────────────────────────────────────

    def set_busqueda(self, v: str):
        self.busqueda = v
        self.page = 1
        if len(v) >= 2 or v == "":
            return self.cargar()

    def toggle_solo_activas(self):
        self.solo_activas = not self.solo_activas
        self.page = 1
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
            with get_session() as session:
                if self.editando:
                    svc.actualizar(session, self.clinica_id, int(self.promo_sel["id"]), payload)
                else:
                    svc.crear(session, self.clinica_id, payload)
        except (ServiceError, Exception) as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving  = False
        self.modal_form = False
        self.cargar()

    # ── Toggle activo ──────────────────────────────────────────────────────────

    def toggle_activo(self, promo: dict):
        try:
            with get_session() as session:
                svc.toggle_activo(session, self.clinica_id, int(promo["id"]))
        except Exception:
            pass
        self.cargar()

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
        try:
            with get_session() as session:
                svc.eliminar(session, self.clinica_id, self.eliminar_id)
        except Exception:
            pass
        self.is_saving      = False
        self.modal_eliminar = False
        self.cargar()
