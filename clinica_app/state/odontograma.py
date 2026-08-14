from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import odontograma as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class OdontogramaState(BaseState):

    paciente_id:     int = 0
    paciente_nombre: str = ""

    superior:    list[dict] = []
    inferior:    list[dict] = []
    resumen:     list[dict] = []   # [{estado, label, color, count}]
    estados_cat: list[dict] = []
    con_datos:   int  = 0
    is_loading:  bool = False

    # ── Modal edición de pieza ──────────────────────────────────────────────────
    modal_abierto: bool = False
    sel_numero:    str  = ""
    sel_estado:    str  = "sano"
    sel_nota:      str  = ""
    is_saving:     bool = False

    # ── Versionado (evolución en el tiempo) ─────────────────────────────────────
    versiones:        list[dict] = []
    mostrar_historial: bool = False
    # Crear versión
    modal_version:    bool = False
    ver_titulo:       str  = ""
    ver_nota:         str  = ""
    is_versionando:   bool = False
    # Ver una versión histórica (solo lectura)
    viendo_version:   bool = False
    v_id:             int  = 0
    v_titulo:         str  = ""
    v_fecha:          str  = ""
    v_nota:           str  = ""
    v_superior:       list[dict] = []
    v_inferior:       list[dict] = []
    v_resumen:        list[dict] = []

    @rx.var
    def puede_versionar(self) -> bool:
        return self.tiene_permiso("historia", write=True)

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("historia"):
            yield rx.redirect("/")
            return
        self.estados_cat = svc.estados_catalogo()
        pid_str = self.router.url.query_parameters.get("paciente_id", "")
        if pid_str:
            try:
                self.paciente_id = int(pid_str)
                await self._cargar_nombre_paciente()
                await self._cargar()
            except (ValueError, TypeError):
                pass

    async def _cargar_nombre_paciente(self):
        from sqlmodel import select

        from clinica_app.models.paciente import Paciente
        async with get_async_session() as session:
            p = (await session.execute(
                select(Paciente).where(
                    Paciente.id == self.paciente_id,
                    Paciente.clinica_id == self.clinica_id,
                )
            )).scalars().first()
            if p:
                self.paciente_nombre = p.nombre

    async def _cargar(self):
        if not self.paciente_id:
            return
        self.is_loading = True
        async with get_async_session() as session:
            data = await svc.listar(
                session, self.clinica_id, self.paciente_id, sede_id=self.sede_actual_id
            )
        self.superior = data["superior"]
        self.inferior = data["inferior"]
        self.con_datos = data["con_datos"]
        self.resumen = [
            {
                "estado": est,
                "label":  svc.ESTADOS.get(est, {}).get("label", est),
                "color":  svc.ESTADOS.get(est, {}).get("color", "#e5e7eb"),
                "count":  cnt,
            }
            for est, cnt in sorted(data["resumen"].items(), key=lambda kv: -kv[1])
        ]
        await self._cargar_versiones()
        self.is_loading = False

    async def _cargar_versiones(self):
        if not self.paciente_id:
            return
        async with get_async_session() as session:
            self.versiones = await svc.listar_versiones(
                session, self.clinica_id, self.paciente_id, sede_id=self.sede_actual_id
            )

    # ── Modal ────────────────────────────────────────────────────────────────────

    def abrir_pieza(self, pieza: dict):
        self.sel_numero = pieza.get("numero") or ""
        self.sel_estado = pieza.get("estado") or "sano"
        self.sel_nota   = pieza.get("nota") or ""
        self.modal_abierto = True

    def cerrar_modal(self):
        self.modal_abierto = False

    def set_sel_estado(self, v: str): self.sel_estado = v
    def set_sel_nota(self, v: str):   self.sel_nota = v

    async def guardar_pieza(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_abierto = False
            return
        self.is_saving = True
        yield
        try:
            async with get_async_session() as session:
                await svc.guardar_pieza(
                    session, self.clinica_id, self.paciente_id, self.sel_numero,
                    estado=self.sel_estado,
                    nota=self.sel_nota,
                    usuario_id=self.user_id,
                    sede_id=self.sede_actual_id,
                )
        except ServiceError:
            pass
        self.is_saving = False
        self.modal_abierto = False
        await self._cargar()

    async def resetear_pieza(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_abierto = False
            return
        async with get_async_session() as session:
            try:
                await svc.resetear_pieza(
                    session, self.clinica_id, self.paciente_id, self.sel_numero,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError:
                pass
        self.modal_abierto = False
        await self._cargar()

    # ── Versionado ───────────────────────────────────────────────────────────────

    def toggle_historial(self):
        self.mostrar_historial = not self.mostrar_historial

    def abrir_modal_version(self):
        self.ver_titulo = ""
        self.ver_nota = ""
        self.modal_version = True

    def cerrar_modal_version(self):
        self.modal_version = False

    def set_ver_titulo(self, v: str): self.ver_titulo = v
    def set_ver_nota(self, v: str):   self.ver_nota = v

    async def crear_version(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_version = False
            return
        self.is_versionando = True
        yield
        try:
            async with get_async_session() as session:
                await svc.crear_version(
                    session, self.clinica_id, self.paciente_id,
                    titulo=self.ver_titulo, nota=self.ver_nota,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError:
            pass
        self.is_versionando = False
        self.modal_version = False
        self.mostrar_historial = True
        await self._cargar_versiones()

    async def ver_version(self, version_id: int):
        async with get_async_session() as session:
            try:
                data = await svc.obtener_version(
                    session, self.clinica_id, self.paciente_id, version_id,
                )
            except ServiceError:
                return
        self.v_id = data["id"]
        self.v_titulo = data["titulo"]
        self.v_fecha = data["fecha"]
        self.v_nota = data["nota"]
        self.v_superior = data["superior"]
        self.v_inferior = data["inferior"]
        self.v_resumen = [
            {
                "estado": est,
                "label":  svc.ESTADOS.get(est, {}).get("label", est),
                "color":  svc.ESTADOS.get(est, {}).get("color", "#e5e7eb"),
                "count":  cnt,
            }
            for est, cnt in sorted(data["resumen"].items(), key=lambda kv: -kv[1])
        ]
        self.viendo_version = True

    def cerrar_version(self):
        self.viendo_version = False

    async def eliminar_version(self, version_id: int):
        if not self.tiene_permiso("historia", write=True):
            return
        async with get_async_session() as session:
            try:
                await svc.eliminar_version(
                    session, self.clinica_id, self.paciente_id, version_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError:
                pass
        await self._cargar_versiones()
