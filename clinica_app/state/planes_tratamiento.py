from __future__ import annotations

import reflex as rx
from sqlmodel import select

from clinica_app.database import get_async_session
from clinica_app.services import planes_tratamiento as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class PlanesTratamientoState(BaseState):

    paciente_id:     int = 0
    paciente_nombre: str = ""

    planes:      list[dict] = []          # lista de planes del paciente (con totales)
    servicios:   list[dict] = []          # catálogo para el selector [{id,nombre,precio}]
    estados_plan_cat: list[dict] = []
    estados_item_cat: list[dict] = []
    is_loading:  bool = False

    # ── Plan actualmente abierto ────────────────────────────────────────────────
    plan_actual_id: int  = 0
    pa_titulo:      str  = ""
    pa_estado:      str  = "borrador"
    pa_notas:       str  = ""
    pa_total:       str  = "0.00"
    pa_total_aprobado:  str = "0.00"
    pa_total_terminado: str = "0.00"
    pa_total_cobrado:   str = "0.00"
    pa_total_por_cobrar: str = "0.00"
    pa_n_por_cobrar:    int  = 0
    pa_avance:      int  = 0
    pa_n_items:     int  = 0
    fases:          list[dict] = []       # [{fase, items, subtotal}]

    # ── Modal: cobrar plan → Caja ───────────────────────────────────────────────
    modal_cobro: bool = False
    cobro_forma: str  = "efectivo"
    is_cobrando: bool = False
    cobro_msg:   str  = ""

    # ── Modal: nuevo plan ───────────────────────────────────────────────────────
    modal_plan: bool = False
    np_titulo:  str  = ""
    np_notas:   str  = ""

    # ── Modal: nuevo tratamiento (item) ─────────────────────────────────────────
    modal_item:     bool = False
    ni_fase:        str  = "1"
    ni_servicio_id: str  = "0"
    ni_descripcion: str  = ""
    ni_pieza:       str  = ""
    ni_precio:      str  = ""
    is_saving:      bool = False

    @rx.var
    def puede_cobrar(self) -> bool:
        return self.tiene_permiso("cobro", write=True)

    # ── Ciclo de vida ───────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("historia"):
            yield rx.redirect("/")
            return
        self.estados_plan_cat = svc.estados_plan_catalogo()
        self.estados_item_cat = svc.estados_item_catalogo()
        pid_str = self.router.url.query_parameters.get("paciente_id", "")
        if pid_str:
            try:
                self.paciente_id = int(pid_str)
            except (ValueError, TypeError):
                self.paciente_id = 0
        if self.paciente_id:
            await self._cargar_paciente()
            await self._cargar_servicios()
            await self._cargar_planes()

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

    async def _cargar_servicios(self):
        from clinica_app.models.servicio import Servicio
        async with get_async_session() as session:
            stmt = (
                select(Servicio)
                .where(Servicio.clinica_id == self.clinica_id, Servicio.is_active.is_(True))
                .order_by(Servicio.nombre.asc())
                .limit(300)
            )
            if self.sede_actual_id:
                stmt = stmt.where(Servicio.sede_id == self.sede_actual_id)
            servs = (await session.execute(stmt)).scalars().all()
        self.servicios = [
            {"id": str(s.id), "nombre": s.nombre, "precio": f"{s.precio or 0:.2f}"}
            for s in servs
        ]

    async def _cargar_planes(self):
        self.is_loading = True
        async with get_async_session() as session:
            self.planes = await svc.listar_planes(session, self.clinica_id, self.paciente_id)
        self.is_loading = False
        # Si había un plan abierto, recargarlo; si no, abrir el primero.
        if self.plan_actual_id:
            await self._cargar_plan(self.plan_actual_id)
        elif self.planes:
            await self._cargar_plan(self.planes[0]["id"])

    async def _cargar_plan(self, plan_id: int):
        async with get_async_session() as session:
            try:
                full = await svc.obtener_plan(session, self.clinica_id, plan_id)
            except ServiceError:
                self.plan_actual_id = 0
                return
        self.plan_actual_id     = full["id"]
        self.pa_titulo          = full["titulo"]
        self.pa_estado          = full["estado"]
        self.pa_notas           = full["notas"]
        self.pa_total           = full["total"]
        self.pa_total_aprobado  = full["total_aprobado"]
        self.pa_total_terminado = full["total_terminado"]
        self.pa_total_cobrado   = full["total_cobrado"]
        self.pa_total_por_cobrar = full["total_por_cobrar"]
        self.pa_n_por_cobrar    = full["n_por_cobrar"]
        self.pa_avance          = full["avance"]
        self.pa_n_items         = full["n_items"]
        self.fases              = full["fases"]

    async def seleccionar_plan(self, plan_id: int):
        await self._cargar_plan(plan_id)

    # ── Cobrar plan → Caja ──────────────────────────────────────────────────────

    def abrir_modal_cobro(self):
        self.cobro_forma = "efectivo"
        self.cobro_msg = ""
        self.modal_cobro = True

    def cerrar_modal_cobro(self):
        self.modal_cobro = False

    def set_cobro_forma(self, v: str):
        self.cobro_forma = v

    async def cobrar_plan(self):
        if not self.tiene_permiso("cobro", write=True):
            self.cobro_msg = "No tenés permiso para cobrar."
            return
        if not self.plan_actual_id:
            return
        self.is_cobrando = True
        self.cobro_msg = ""
        yield
        exito = False
        async with get_async_session() as session:
            try:
                res = await svc.cobrar_plan(
                    session, self.clinica_id, self.plan_actual_id,
                    forma_pago=self.cobro_forma,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
                numero = res["comprobante"].get("numero", "")
                total = res["comprobante"].get("total", "0")
                self.cobro_msg = f"Cobro registrado: {res['cobrados']} tratamiento(s), comprobante {numero} por ${total}."
                exito = True
            except ServiceError as exc:
                self.cobro_msg = str(exc)
        self.is_cobrando = False
        if exito:
            self.modal_cobro = False
        await self._cargar_planes()

    # ── Nuevo plan ──────────────────────────────────────────────────────────────

    def abrir_modal_plan(self):
        self.np_titulo = ""
        self.np_notas = ""
        self.modal_plan = True

    def cerrar_modal_plan(self):
        self.modal_plan = False

    def set_np_titulo(self, v: str): self.np_titulo = v
    def set_np_notas(self, v: str):  self.np_notas = v

    async def guardar_plan(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_plan = False
            yield rx.toast.error("No tenés permiso para crear planes")
            return
        if not self.np_titulo.strip():
            yield rx.toast.error("El título del plan es obligatorio")
            return
        self.is_saving = True
        yield
        nuevo_id = 0
        async with get_async_session() as session:
            try:
                res = await svc.crear_plan(
                    session, self.clinica_id, self.paciente_id,
                    titulo=self.np_titulo, notas=self.np_notas,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
                nuevo_id = res["id"]
            except ServiceError as exc:
                self.is_saving = False
                yield rx.toast.error(str(exc))
                return
        self.is_saving = False
        self.modal_plan = False
        if nuevo_id:
            self.plan_actual_id = nuevo_id
        await self._cargar_planes()

    async def cambiar_estado_plan(self, estado: str):
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para modificar el plan")
            return
        if not self.plan_actual_id:
            return
        async with get_async_session() as session:
            try:
                await svc.actualizar_plan(
                    session, self.clinica_id, self.plan_actual_id,
                    estado=estado, usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        await self._cargar_planes()

    async def eliminar_plan(self):
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para eliminar planes")
            return
        if not self.plan_actual_id:
            return
        async with get_async_session() as session:
            try:
                await svc.eliminar_plan(
                    session, self.clinica_id, self.plan_actual_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        yield rx.toast.success("Plan eliminado")
        self.plan_actual_id = 0
        self.fases = []
        await self._cargar_planes()

    # ── Nuevo tratamiento (item) ────────────────────────────────────────────────

    def abrir_modal_item(self):
        self.ni_fase = "1"
        self.ni_servicio_id = "0"
        self.ni_descripcion = ""
        self.ni_pieza = ""
        self.ni_precio = ""
        self.modal_item = True

    def cerrar_modal_item(self):
        self.modal_item = False

    def set_ni_fase(self, v: str):        self.ni_fase = v
    def set_ni_descripcion(self, v: str): self.ni_descripcion = v
    def set_ni_pieza(self, v: str):       self.ni_pieza = v
    def set_ni_precio(self, v: str):      self.ni_precio = v

    def set_ni_servicio(self, sid: str):
        """Al elegir un servicio del catálogo, hereda nombre y precio."""
        self.ni_servicio_id = sid
        for s in self.servicios:
            if s["id"] == sid:
                if not self.ni_descripcion.strip():
                    self.ni_descripcion = s["nombre"]
                self.ni_precio = s["precio"]
                break

    async def guardar_item(self):
        if not self.tiene_permiso("historia", write=True) or not self.plan_actual_id:
            self.modal_item = False
            if not self.tiene_permiso("historia", write=True):
                yield rx.toast.error("No tenés permiso para agregar tratamientos")
            return
        self.is_saving = True
        yield
        async with get_async_session() as session:
            try:
                await svc.agregar_item(
                    session, self.clinica_id, self.plan_actual_id,
                    descripcion=self.ni_descripcion,
                    fase=self.ni_fase,
                    pieza_numero=self.ni_pieza or None,
                    servicio_id=int(self.ni_servicio_id) if self.ni_servicio_id not in ("", "0") else None,
                    precio=self.ni_precio,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                self.is_saving = False
                self.modal_item = False
                yield rx.toast.error(str(exc))
                return
        self.is_saving = False
        self.modal_item = False
        await self._cargar_planes()

    async def cambiar_estado_item(self, item_id: int, estado: str):
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para modificar tratamientos")
            return
        if not self.plan_actual_id:
            return
        async with get_async_session() as session:
            try:
                await svc.cambiar_estado_item(
                    session, self.clinica_id, self.plan_actual_id, item_id,
                    estado=estado, usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        await self._cargar_planes()

    async def eliminar_item(self, item_id: int):
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para eliminar tratamientos")
            return
        if not self.plan_actual_id:
            return
        async with get_async_session() as session:
            try:
                await svc.eliminar_item(
                    session, self.clinica_id, self.plan_actual_id, item_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        yield rx.toast.success("Tratamiento eliminado")
        await self._cargar_planes()
