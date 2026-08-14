from __future__ import annotations

import asyncio

import reflex as rx
from sqlmodel import select

from clinica_app.database import get_async_session
from clinica_app.services import sesiones_esteticas as svc
from clinica_app.services import storage
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_FOTO_UPLOAD_ID = "galeria_estetica_upload"


class SesionesEsteticasState(BaseState):

    paciente_id:     int = 0
    paciente_nombre: str = ""

    sesiones:     list[dict] = []          # timeline con conteos
    momentos_cat: list[dict] = []
    is_loading:   bool = False

    # ── Sesión abierta ──────────────────────────────────────────────────────────
    sesion_actual_id: int  = 0
    sa_titulo:  str = ""
    sa_fecha:   str = ""
    sa_zona:    str = ""
    sa_notas:   str = ""
    n_fotos:    int = 0
    fotos_antes:   list[dict] = []
    fotos_durante: list[dict] = []
    fotos_despues: list[dict] = []

    # ── Modal: nueva sesión ─────────────────────────────────────────────────────
    modal_sesion: bool = False
    ns_fecha:  str = ""
    ns_titulo: str = ""
    ns_zona:   str = ""
    ns_notas:  str = ""

    # ── Subida de fotos ─────────────────────────────────────────────────────────
    upload_momento: str  = "antes"
    is_uploading:   bool = False
    upload_error:   str  = ""

    # ── Ciclo de vida ───────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("historia"):
            yield rx.redirect("/")
            return
        self.momentos_cat = svc.momentos_catalogo()
        pid_str = self.router.url.query_parameters.get("paciente_id", "")
        if pid_str:
            try:
                self.paciente_id = int(pid_str)
            except (ValueError, TypeError):
                self.paciente_id = 0
        if self.paciente_id:
            await self._cargar_paciente()
            await self._cargar_sesiones()

    async def _cargar_paciente(self):
        from clinica_app.models.paciente import Paciente
        async with get_async_session() as session:
            p = (await session.execute(
                select(Paciente).where(
                    Paciente.id == self.paciente_id,
                    Paciente.clinica_id == self.clinica_id,
                )
            )).scalars().first()
            self.paciente_nombre = p.nombre if p else ""

    async def _cargar_sesiones(self):
        self.is_loading = True
        async with get_async_session() as session:
            self.sesiones = await svc.listar_sesiones(session, self.clinica_id, self.paciente_id)
        self.is_loading = False
        if self.sesion_actual_id:
            await self._cargar_sesion(self.sesion_actual_id)
        elif self.sesiones:
            await self._cargar_sesion(self.sesiones[0]["id"])

    async def _cargar_sesion(self, sesion_id: int):
        async with get_async_session() as session:
            try:
                full = await svc.obtener_sesion(session, self.clinica_id, sesion_id)
            except ServiceError:
                self.sesion_actual_id = 0
                return
        self.sesion_actual_id = full["id"]
        self.sa_titulo = full["titulo"]
        self.sa_fecha  = full["fecha_fmt"]
        self.sa_zona   = full["zona"]
        self.sa_notas  = full["notas"]
        self.n_fotos   = full["n_fotos"]
        self.fotos_antes   = full["antes"]
        self.fotos_durante = full["durante"]
        self.fotos_despues = full["despues"]

    async def seleccionar_sesion(self, sesion_id: int):
        await self._cargar_sesion(sesion_id)

    # ── Nueva sesión ────────────────────────────────────────────────────────────

    def abrir_modal_sesion(self):
        self.ns_fecha = ""
        self.ns_titulo = ""
        self.ns_zona = ""
        self.ns_notas = ""
        self.modal_sesion = True

    def cerrar_modal_sesion(self):
        self.modal_sesion = False

    def set_ns_fecha(self, v: str):  self.ns_fecha = v
    def set_ns_titulo(self, v: str): self.ns_titulo = v
    def set_ns_zona(self, v: str):   self.ns_zona = v
    def set_ns_notas(self, v: str):  self.ns_notas = v

    async def guardar_sesion(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_sesion = False
            return
        if not self.ns_titulo.strip() or not self.ns_fecha.strip():
            self.upload_error = "Completá fecha y título de la sesión."
            return
        self.is_uploading = True
        yield
        nuevo_id = 0
        async with get_async_session() as session:
            try:
                res = await svc.crear_sesion(
                    session, self.clinica_id, self.paciente_id,
                    fecha=self.ns_fecha, titulo=self.ns_titulo,
                    zona=self.ns_zona, notas=self.ns_notas,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
                nuevo_id = res["id"]
            except ServiceError as exc:
                self.upload_error = str(exc)
        self.is_uploading = False
        self.modal_sesion = False
        if nuevo_id:
            self.sesion_actual_id = nuevo_id
            self.upload_error = ""
        await self._cargar_sesiones()

    async def eliminar_sesion(self):
        if not self.tiene_permiso("historia", write=True) or not self.sesion_actual_id:
            return
        stored: list[str] = []
        async with get_async_session() as session:
            try:
                stored = await svc.eliminar_sesion(
                    session, self.clinica_id, self.sesion_actual_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError:
                pass
        for name in stored:
            await asyncio.to_thread(storage.eliminar, self.clinica_id, name)
        self.sesion_actual_id = 0
        self.fotos_antes = []
        self.fotos_durante = []
        self.fotos_despues = []
        await self._cargar_sesiones()

    # ── Subida de fotos ─────────────────────────────────────────────────────────

    def set_upload_momento(self, v: str):
        self.upload_momento = v

    async def handle_upload(self, files: list[rx.UploadFile]):
        self.upload_error = ""
        if not self.tiene_permiso("historia", write=True):
            self.upload_error = "Sin permiso de escritura"
            return
        if not self.sesion_actual_id:
            self.upload_error = "Seleccioná o creá una sesión primero"
            return
        if not files:
            return

        self.is_uploading = True
        yield

        try:
            for file in files:
                data = await file.read()
                nombre = file.filename or file.name or "foto"
                try:
                    stored = await asyncio.to_thread(
                        storage.guardar, self.clinica_id, nombre, data
                    )
                except ServiceError as exc:
                    self.upload_error = str(exc)
                    continue
                async with get_async_session() as session:
                    try:
                        await svc.registrar_foto(
                            session, self.clinica_id, self.paciente_id, self.sesion_actual_id,
                            momento=self.upload_momento,
                            nombre=nombre,
                            stored_name=stored,
                            mime=file.content_type,
                            tamano=len(data),
                            usuario_id=self.user_id,
                            sede_id=self.sede_actual_id,
                        )
                    except ServiceError as exc:
                        self.upload_error = str(exc)
        except Exception:
            self.upload_error = "Ocurrió un error al subir la foto."

        self.is_uploading = False
        await self._cargar_sesiones()
        yield rx.clear_selected_files(_FOTO_UPLOAD_ID)

    async def eliminar_foto(self, foto_id: int):
        if not self.tiene_permiso("historia", write=True):
            return
        stored_name = ""
        async with get_async_session() as session:
            try:
                stored_name = await svc.eliminar_foto(
                    session, self.clinica_id, foto_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError:
                pass
        if stored_name:
            await asyncio.to_thread(storage.eliminar, self.clinica_id, stored_name)
        await self._cargar_sesiones()
