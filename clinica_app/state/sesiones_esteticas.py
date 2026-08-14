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

    # ── Ficha clínica (C2) ──────────────────────────────────────────────────────
    sa_numero_sesion: int = 0
    sa_parametros:    str = ""
    sa_proxima:       str = ""
    sa_proxima_fmt:   str = ""
    insumos:   list[dict] = []
    productos: list[dict] = []          # catálogo de inventario [{id,nombre}]

    # Modal editar ficha
    modal_ficha: bool = False
    ef_numero:     str = ""
    ef_zona:       str = ""
    ef_parametros: str = ""
    ef_proxima:    str = ""

    # Modal agregar insumo
    modal_insumo:   bool = False
    ni_producto_id: str = "0"
    ni_descripcion: str = ""
    ni_cantidad:    str = ""
    ni_unidad:      str = ""
    insumo_stock_msg: str = ""   # aviso de stock tras registrar un insumo

    # Modal agendar próxima sesión (turno)
    profesionales:  list[dict] = []       # [{id, nombre}]
    modal_agendar:  bool = False
    ag_fecha:       str = ""
    ag_hora:        str = "09:00"
    ag_profesional_id: str = "0"
    is_agendando:   bool = False
    ag_msg:         str = ""
    ag_ok:          bool = False

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
            await self._cargar_productos()
            await self._cargar_profesionales()
            await self._cargar_sesiones()

    @rx.var
    def puede_agendar(self) -> bool:
        return self.tiene_permiso("turnos", write=True)

    async def _cargar_productos(self):
        from clinica_app.models.inventario import Producto
        async with get_async_session() as session:
            stmt = (
                select(Producto)
                .where(Producto.clinica_id == self.clinica_id, Producto.is_active.is_(True))
                .order_by(Producto.nombre.asc())
                .limit(300)
            )
            if self.sede_actual_id:
                stmt = stmt.where(Producto.sede_id == self.sede_actual_id)
            prods = (await session.execute(stmt)).scalars().all()
        self.productos = [{"id": str(p.id), "nombre": p.nombre} for p in prods]

    async def _cargar_profesionales(self):
        from clinica_app.models.profesional import Profesional
        async with get_async_session() as session:
            stmt = (
                select(Profesional)
                .where(Profesional.clinica_id == self.clinica_id, Profesional.is_active.is_(True))
                .order_by(Profesional.apellidos.asc())
                .limit(300)
            )
            if self.sede_actual_id:
                stmt = stmt.where(Profesional.sede_id == self.sede_actual_id)
            profs = (await session.execute(stmt)).scalars().all()
        self.profesionales = [
            {"id": str(p.id), "nombre": f"{(p.nombres or '').strip()} {(p.apellidos or '').strip()}".strip()}
            for p in profs
        ]

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
        self.sa_numero_sesion = full["numero_sesion"]
        self.sa_parametros    = full["parametros"]
        self.sa_proxima       = full["proxima"]
        self.sa_proxima_fmt   = full["proxima_fmt"]
        self.insumos          = full["insumos"]

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

    # ── Ficha clínica (C2) ──────────────────────────────────────────────────────

    def abrir_modal_ficha(self):
        self.ef_numero = self.sa_numero_sesion.to_string() if self.sa_numero_sesion else ""
        self.ef_zona = self.sa_zona
        self.ef_parametros = self.sa_parametros
        self.ef_proxima = self.sa_proxima
        self.modal_ficha = True

    def cerrar_modal_ficha(self):
        self.modal_ficha = False

    def set_ef_numero(self, v: str):     self.ef_numero = v
    def set_ef_zona(self, v: str):       self.ef_zona = v
    def set_ef_parametros(self, v: str): self.ef_parametros = v
    def set_ef_proxima(self, v: str):    self.ef_proxima = v

    async def guardar_ficha(self):
        if not self.tiene_permiso("historia", write=True) or not self.sesion_actual_id:
            self.modal_ficha = False
            return
        async with get_async_session() as session:
            try:
                await svc.actualizar_sesion(
                    session, self.clinica_id, self.sesion_actual_id,
                    zona=self.ef_zona,
                    numero_sesion=self.ef_numero,
                    parametros=self.ef_parametros,
                    proxima=self.ef_proxima,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                self.upload_error = str(exc)
        self.modal_ficha = False
        await self._cargar_sesiones()

    # ── Insumos aplicados (C2) ──────────────────────────────────────────────────

    def abrir_modal_insumo(self):
        self.ni_producto_id = "0"
        self.ni_descripcion = ""
        self.ni_cantidad = ""
        self.ni_unidad = ""
        self.modal_insumo = True

    def cerrar_modal_insumo(self):
        self.modal_insumo = False

    def set_ni_descripcion(self, v: str): self.ni_descripcion = v
    def set_ni_cantidad(self, v: str):    self.ni_cantidad = v
    def set_ni_unidad(self, v: str):      self.ni_unidad = v

    def set_ni_producto(self, pid: str):
        self.ni_producto_id = pid
        for p in self.productos:
            if p["id"] == pid and not self.ni_descripcion.strip():
                self.ni_descripcion = p["nombre"]
                break

    async def guardar_insumo(self):
        if not self.tiene_permiso("historia", write=True) or not self.sesion_actual_id:
            self.modal_insumo = False
            return
        self.insumo_stock_msg = ""
        async with get_async_session() as session:
            try:
                res = await svc.agregar_insumo(
                    session, self.clinica_id, self.sesion_actual_id,
                    descripcion=self.ni_descripcion,
                    producto_id=int(self.ni_producto_id) if self.ni_producto_id not in ("", "0") else None,
                    cantidad=self.ni_cantidad,
                    unidad=self.ni_unidad,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
                if res.get("stock_warning"):
                    self.insumo_stock_msg = "Insumo registrado, pero el stock no se descontó: " + res["stock_warning"]
            except ServiceError as exc:
                self.upload_error = str(exc)
        self.modal_insumo = False
        await self._cargar_sesiones()

    async def eliminar_insumo(self, insumo_id: int):
        if not self.tiene_permiso("historia", write=True):
            return
        async with get_async_session() as session:
            try:
                await svc.eliminar_insumo(
                    session, self.clinica_id, insumo_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError:
                pass
        await self._cargar_sesiones()

    # ── Agendar próxima sesión (turno) ──────────────────────────────────────────

    def abrir_modal_agendar(self):
        self.ag_fecha = self.sa_proxima          # prefill con la fecha recomendada
        self.ag_hora = "09:00"
        self.ag_profesional_id = "0"
        self.ag_msg = ""
        self.ag_ok = False
        self.modal_agendar = True

    def cerrar_modal_agendar(self):
        self.modal_agendar = False

    def set_ag_fecha(self, v: str):        self.ag_fecha = v
    def set_ag_hora(self, v: str):         self.ag_hora = v
    def set_ag_profesional(self, v: str):  self.ag_profesional_id = v

    async def agendar_turno(self):
        if not self.tiene_permiso("turnos", write=True):
            self.ag_msg = "No tenés permiso para agendar turnos."
            return
        if not self.sesion_actual_id:
            return
        self.is_agendando = True
        self.ag_msg = ""
        self.ag_ok = False
        yield
        async with get_async_session() as session:
            try:
                turno = await svc.agendar_proxima_sesion(
                    session, self.clinica_id, self.sesion_actual_id,
                    fecha=self.ag_fecha,
                    hora=self.ag_hora,
                    profesional_id=int(self.ag_profesional_id) if self.ag_profesional_id not in ("", "0") else None,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
                self.ag_msg = f"Turno agendado para el {turno['fecha_hora']}."
                self.ag_ok = True
            except ServiceError as exc:
                self.ag_msg = str(exc)
        self.is_agendando = False
