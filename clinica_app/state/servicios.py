from __future__ import annotations

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import servicios as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class ServiciosState(BaseState):

    servicios:      list[dict] = []
    total:          int = 0
    page:           int = 1
    per_page:       int = 20
    total_pages:    int = 1
    busqueda:       str = ""
    filtro_cat:     str = ""
    categorias_cat: list[str] = []

    # Modal
    modal_abierto:      bool = False
    editando_id:        int  = 0
    form_nombre:        str  = ""
    form_categoria:     str  = ""
    form_nueva_cat:     str  = ""   # cuando escribe una nueva categoría
    form_descripcion:   str  = ""
    form_precio:        str  = ""
    form_duracion_min:  str  = "30"
    form_protocolo:     str  = ""
    form_error:         str  = ""
    is_saving:          bool = False

    def on_mount(self):
        return self.require_auth() or self._cargar_cats() or self.cargar()

    def _cargar_cats(self):
        with get_session() as session:
            self.categorias_cat = svc.categorias(session, self.clinica_id)

    def cargar(self):
        with get_session() as session:
            result = svc.listar(
                session,
                self.clinica_id,
                q=self.busqueda,
                categoria=self.filtro_cat,
                page=self.page,
                per_page=self.per_page,
            )
        self.servicios   = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]

    def set_busqueda(self, valor: str):
        self.busqueda = valor
        self.page = 1
        return self.cargar()

    def set_filtro_cat(self, valor: str):
        self.filtro_cat = valor
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

    # ── Setters de formulario ─────────────────────────────────────────────────
    def set_form_nombre(self, v: str):       self.form_nombre = v
    def set_form_categoria(self, v: str):    self.form_categoria = v
    def set_form_nueva_cat(self, v: str):    self.form_nueva_cat = v
    def set_form_descripcion(self, v: str):  self.form_descripcion = v
    def set_form_precio(self, v: float):       self.form_precio = str(v) if v else ""
    def set_form_duracion_min(self, v: float): self.form_duracion_min = str(int(v)) if v else ""
    def set_form_protocolo(self, v: str):    self.form_protocolo = v

    def _limpiar_form(self):
        self.form_nombre = self.form_categoria = self.form_nueva_cat = ""
        self.form_descripcion = self.form_precio = self.form_protocolo = ""
        self.form_duracion_min = "30"
        self.form_error = ""
        self.editando_id = 0

    def abrir_nuevo(self):
        self._limpiar_form()
        self.modal_abierto = True

    def abrir_editar(self, srv: dict):
        self._limpiar_form()
        self.editando_id      = srv.get("id") or 0
        self.form_nombre      = srv.get("nombre") or ""
        self.form_categoria   = srv.get("categoria") or ""
        self.form_descripcion = srv.get("descripcion") or ""
        self.form_precio      = srv.get("precio") or "0.00"
        self.form_duracion_min = str(srv.get("duracion_min") or 30)
        self.form_protocolo   = srv.get("protocolo") or ""
        self.modal_abierto    = True

    def cerrar_modal(self):
        self.modal_abierto = False
        self._limpiar_form()

    async def guardar(self):
        self.is_saving  = True
        self.form_error = ""
        yield

        cat = (self.form_nueva_cat.strip() or self.form_categoria.strip()) or ""
        payload = {
            "nombre":       self.form_nombre,
            "categoria":    cat,
            "descripcion":  self.form_descripcion,
            "precio":       self.form_precio or "0",
            "duracion_min": self.form_duracion_min or "30",
            "protocolo":    self.form_protocolo,
        }
        try:
            with get_session() as session:
                if self.editando_id:
                    svc.actualizar(session, self.clinica_id, self.editando_id, payload)
                else:
                    svc.crear(session, self.clinica_id, payload)
        except ServiceError as exc:
            self.form_error = str(exc)
            self.is_saving  = False
            return

        self.is_saving     = False
        self.modal_abierto = False
        self._limpiar_form()
        self._cargar_cats()
        self.cargar()

    def eliminar(self, srv_id: int):
        try:
            with get_session() as session:
                svc.eliminar(session, self.clinica_id, srv_id)
        except ServiceError:
            pass
        self._cargar_cats()
        self.cargar()
