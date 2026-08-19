"""Estado del mapa estético facial 3D (E6).

Vista alterna sobre el backend E5 (`services/estetica_mapa` + `services/anatomia`):
el rostro 3D (viewer.js escena "facial") emite el `zona_codigo` clicado + la
coordenada normalizada del click; Python carga las evaluaciones/procedimientos de
esa zona y persiste evaluaciones, procedimientos y **puntos de aplicación**
(producto+lote+cantidad) por los servicios auditados. El renderer nunca toca la
BD; los listados laterales son la fuente de verdad y el fallback.
"""
from __future__ import annotations

import asyncio
import json
import os

import reflex as rx

from clinica_app.components.anatomy_viewer import (
    anatomy_boot_script,
    anatomy_setdata_script,
)
from clinica_app.database import get_async_session
from clinica_app.services import anatomia
from clinica_app.services import estetica_mapa as svc
from clinica_app.services import sesiones_esteticas as galeria_svc
from clinica_app.services import storage
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_FOTO_UPLOAD_ID = "mapa_estetico_upload"

# URL (servida desde /assets) de un modelo GLB realista del rostro. Vacío =>
# geometría procedural. Se configura por entorno para poder cambiar el modelo
# sin tocar código (ANATOMY_FACE_MODEL_URL=/models/anatomy/rostro.glb).
_FACE_MODEL_URL = os.getenv("ANATOMY_FACE_MODEL_URL", "")
# Modelo GLB del cuerpo (vista corporal). Vacío => vista corporal deshabilitada.
_BODY_MODEL_URL = os.getenv("ANATOMY_BODY_MODEL_URL", "")

# Colores del mapa por actividad de la zona.
_COLOR_PROC = "#0284c7"  # sky-600 — zona con procedimiento
_COLOR_EVAL = "#a855f7"  # violet-500 — zona sólo evaluada


class MapaEsteticoState(BaseState):

    paciente_id:     int = 0
    paciente_nombre: str = ""

    # Vista activa del visor 3D: "facial" (rostro) | "corporal" (cuerpo).
    vista: str = "facial"

    # Visor a pantalla completa (llena el viewport).
    pantalla_completa: bool = False

    # Catálogos (código, no BD).
    zonas_cat:       list[dict] = []   # {codigo, label, region, grupo}
    tipos_cat:       list[dict] = []   # {value, label}
    categorias_cat:  list[dict] = []   # {value, label}
    severidades_cat: list[dict] = []   # {value, label}
    productos_cat:   list[dict] = []   # {value, label}

    # Resumen del mapa + totales.
    resumen_zonas: dict[str, dict] = {}   # {codigo: {evaluaciones, procedimientos, puntos, zona_label}}
    n_evaluaciones:   int = 0
    n_procedimientos: int = 0
    n_puntos:         int = 0
    n_fotos:          int = 0
    is_loading:       bool = False

    # Zona seleccionada + coordenada del último click en el rostro.
    zona_sel:       str = ""
    zona_sel_label: str = ""
    last_x:         float = 0.5
    last_y:         float = 0.5
    evaluaciones:   list[dict] = []
    procedimientos: list[dict] = []

    # Fotos antes/después de la zona (E8).
    momentos_cat:  list[dict] = []   # {clave, label}
    fotos_antes:   list[dict] = []
    fotos_durante: list[dict] = []
    fotos_despues: list[dict] = []
    foto_momento:  str  = "antes"
    is_uploading:  bool = False
    foto_error:    str  = ""

    # Modal evaluación.
    modal_eval:   bool = False
    ev_categoria: str  = "arrugas"
    ev_severidad: str  = "0"
    ev_obs:       str  = ""

    # Modal procedimiento.
    modal_proc: bool = False
    pr_tipo:    str  = "toxina_botulinica"
    pr_obs:     str  = ""

    # Modal punto de aplicación.
    modal_punto:   bool = False
    pt_proc_id:    int  = 0
    pt_producto:   str  = "0"
    pt_lote:       str  = ""
    pt_cantidad:   str  = ""
    pt_unidad:     str  = ""
    pt_obs:        str  = ""

    is_saving: bool = False

    @rx.var
    def puede_editar(self) -> bool:
        return self.tiene_permiso("historia", write=True)

    @rx.var
    def es_corporal(self) -> bool:
        return self.vista == "corporal"

    @rx.var
    def tiene_corporal(self) -> bool:
        """La vista corporal solo se ofrece si hay un modelo GLB configurado."""
        return bool(_BODY_MODEL_URL)

    @rx.var
    def titulo_vista(self) -> str:
        return "Cuerpo 3D" if self.vista == "corporal" else "Rostro 3D"

    @rx.var
    def camaras_cat(self) -> list[dict]:
        """Cámaras del visor según la vista (mismas claves que viewer.js)."""
        if self.vista == "corporal":
            return [
                {"clave": "frontal",    "label": "Frontal"},
                {"clave": "posterior",  "label": "Posterior"},
                {"clave": "perfil_izq", "label": "Perfil izq."},
                {"clave": "perfil_der", "label": "Perfil der."},
            ]
        return [
            {"clave": "frontal",    "label": "Frontal"},
            {"clave": "perfil_izq", "label": "Perfil izq."},
            {"clave": "perfil_der", "label": "Perfil der."},
            {"clave": "superior",   "label": "Superior"},
        ]

    def toggle_pantalla_completa(self):
        self.pantalla_completa = not self.pantalla_completa
        # El canvas WebGL no siempre detecta el cambio de tamaño del contenedor
        # (ResizeObserver no dispara confiable con el toggle de clase) → forzamos
        # un resize tras aplicar el nuevo layout.
        yield rx.call_script(
            "setTimeout(function(){window.dispatchEvent(new Event('resize'));},80);"
        )

    @rx.var
    def tiene_zona(self) -> bool:
        return self.zona_sel != ""

    @rx.var
    def coord_label(self) -> str:
        return f"x {self.last_x:.2f} · y {self.last_y:.2f}"

    # ── Carga ────────────────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("historia"):
            yield rx.redirect("/")
            return
        self.zonas_cat = anatomia.zonas_catalogo("facial")
        self.tipos_cat = [{"value": t["clave"], "label": t["label"]} for t in anatomia.tipos_catalogo()]
        self.categorias_cat = [{"value": c["clave"], "label": c["label"]} for c in anatomia.categorias_catalogo()]
        self.severidades_cat = [{"value": str(s["valor"]), "label": f'{s["valor"]} · {s["label"]}'} for s in anatomia.SEVERIDADES]
        self.momentos_cat = galeria_svc.momentos_catalogo()
        pid_str = self.router.url.query_parameters.get("paciente_id", "")
        if pid_str:
            try:
                self.paciente_id = int(pid_str)
            except (ValueError, TypeError):
                self.paciente_id = 0
        if self.paciente_id:
            await self._cargar_nombre_paciente()
            await self._cargar_productos()
            await self._cargar_resumen()
        yield rx.call_script(anatomy_boot_script(
            self._payload_facial(), scene_type="facial", model_url=_FACE_MODEL_URL,
        ))

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

    async def _cargar_productos(self):
        from sqlmodel import select

        from clinica_app.models.inventario import Producto
        async with get_async_session() as session:
            rows = (await session.execute(
                select(Producto.id, Producto.nombre).where(
                    Producto.clinica_id == self.clinica_id,
                    Producto.is_active.is_(True),
                ).order_by(Producto.nombre)
            )).all()
        self.productos_cat = [{"value": "0", "label": "— Sin producto —"}] + [
            {"value": str(r[0]), "label": r[1]} for r in rows
        ]

    async def _cargar_resumen(self):
        if not self.paciente_id:
            return
        async with get_async_session() as session:
            data = await svc.resumen_mapa(session, self.clinica_id, self.paciente_id)
        self.resumen_zonas = data["zonas"]
        self.n_evaluaciones = data["n_evaluaciones"]
        self.n_procedimientos = data["n_procedimientos"]
        self.n_puntos = data["n_puntos"]
        self.n_fotos = data.get("n_fotos", 0)

    async def _cargar_zona(self):
        if not self.paciente_id or not self.zona_sel:
            self.evaluaciones = []
            self.procedimientos = []
            self.fotos_antes = []
            self.fotos_durante = []
            self.fotos_despues = []
            return
        async with get_async_session() as session:
            self.evaluaciones = await svc.listar_evaluaciones(
                session, self.clinica_id, self.paciente_id, zona_codigo=self.zona_sel
            )
            self.procedimientos = await svc.listar_procedimientos(
                session, self.clinica_id, self.paciente_id, zona_codigo=self.zona_sel
            )
            fotos = await svc.listar_fotos_zona(
                session, self.clinica_id, self.paciente_id, zona_codigo=self.zona_sel
            )
        self.fotos_antes   = [f for f in fotos if f["momento"] == "antes"]
        self.fotos_durante = [f for f in fotos if f["momento"] == "durante"]
        self.fotos_despues = [f for f in fotos if f["momento"] == "despues"]

    def _payload_facial(self, seleccionado: str = "") -> str:
        colores: dict[str, str] = {}
        for codigo, cont in self.resumen_zonas.items():
            if cont.get("procedimientos", 0) > 0:
                colores[codigo] = _COLOR_PROC
            elif cont.get("evaluaciones", 0) > 0:
                colores[codigo] = _COLOR_EVAL
        return json.dumps({"colores": colores, "seleccionado": seleccionado or self.zona_sel})

    def _repintar(self):
        return rx.call_script(anatomy_setdata_script(self._payload_facial()))

    # ── Selección de zona ────────────────────────────────────────────────────────

    async def seleccionar_zona(self, codigo: str):
        codigo = (codigo or "").strip()
        if not anatomia.es_zona_valida(codigo):
            return
        self.zona_sel = codigo
        self.zona_sel_label = anatomia.zona_label(codigo)
        await self._cargar_zona()
        yield self._repintar()

    async def on_pick(self, value: str):
        try:
            data = json.loads(value or "{}")
        except (ValueError, TypeError):
            return
        codigo = str(data.get("anatomy_id") or "")
        if not codigo:
            return
        try:
            self.last_x = float(data.get("coord_x", 0.5))
            self.last_y = float(data.get("coord_y", 0.5))
        except (ValueError, TypeError):
            self.last_x, self.last_y = 0.5, 0.5
        async for ev in self.seleccionar_zona(codigo):
            yield ev

    def set_camara(self, nombre: str):
        yield rx.call_script(
            "window.AnatomyViewer&&window.AnatomyViewer.setCamera('" + nombre + "');"
        )

    async def cambiar_vista(self, v: str):
        """Alterna rostro↔cuerpo: recarga el catálogo de zonas del grupo y
        re-arranca el visor con la escena/modelo correspondiente."""
        v = v if v in ("facial", "corporal") else "facial"
        if v == "corporal" and not _BODY_MODEL_URL:
            return
        if v == self.vista:
            return
        self.vista = v
        self.zonas_cat = anatomia.zonas_catalogo(v)
        self.zona_sel = ""
        self.zona_sel_label = ""
        self.evaluaciones = []
        self.procedimientos = []
        self.fotos_antes = []
        self.fotos_durante = []
        self.fotos_despues = []
        self.foto_error = ""
        model = _BODY_MODEL_URL if v == "corporal" else _FACE_MODEL_URL
        yield rx.call_script(anatomy_boot_script(
            self._payload_facial(), scene_type=v, model_url=model,
        ))

    # ── Evaluación ───────────────────────────────────────────────────────────────

    def abrir_eval(self):
        if not self.zona_sel:
            return
        self.ev_categoria = "arrugas"
        self.ev_severidad = "0"
        self.ev_obs = ""
        self.modal_eval = True

    def cerrar_eval(self): self.modal_eval = False
    def set_ev_categoria(self, v: str): self.ev_categoria = v
    def set_ev_severidad(self, v: str): self.ev_severidad = v
    def set_ev_obs(self, v: str): self.ev_obs = v

    async def guardar_eval(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_eval = False
            yield rx.toast.error("No tenés permiso para editar el mapa estético")
            return
        self.is_saving = True
        yield
        try:
            async with get_async_session() as session:
                await svc.registrar_evaluacion(
                    session, self.clinica_id, self.paciente_id,
                    zona_codigo=self.zona_sel, categoria=self.ev_categoria,
                    severidad=self.ev_severidad, observacion=self.ev_obs,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            self.is_saving = False
            yield rx.toast.error(str(exc))
            return
        self.is_saving = False
        self.modal_eval = False
        await self._cargar_zona()
        await self._cargar_resumen()
        yield self._repintar()

    async def eliminar_eval(self, evaluacion_id: int):
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para editar el mapa estético")
            return
        try:
            async with get_async_session() as session:
                await svc.eliminar_evaluacion(
                    session, self.clinica_id, evaluacion_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            yield rx.toast.error(str(exc))
            return
        await self._cargar_zona()
        await self._cargar_resumen()
        yield self._repintar()

    # ── Procedimiento ────────────────────────────────────────────────────────────

    def abrir_proc(self):
        if not self.zona_sel:
            return
        self.pr_tipo = "toxina_botulinica"
        self.pr_obs = ""
        self.modal_proc = True

    def cerrar_proc(self): self.modal_proc = False
    def set_pr_tipo(self, v: str): self.pr_tipo = v
    def set_pr_obs(self, v: str): self.pr_obs = v

    async def guardar_proc(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_proc = False
            yield rx.toast.error("No tenés permiso para editar el mapa estético")
            return
        self.is_saving = True
        yield
        try:
            async with get_async_session() as session:
                await svc.crear_procedimiento(
                    session, self.clinica_id, self.paciente_id,
                    zona_codigo=self.zona_sel, tipo=self.pr_tipo,
                    observacion=self.pr_obs,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            self.is_saving = False
            yield rx.toast.error(str(exc))
            return
        self.is_saving = False
        self.modal_proc = False
        await self._cargar_zona()
        await self._cargar_resumen()
        yield self._repintar()

    async def eliminar_proc(self, procedimiento_id: int):
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para editar el mapa estético")
            return
        try:
            async with get_async_session() as session:
                await svc.eliminar_procedimiento(
                    session, self.clinica_id, procedimiento_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            yield rx.toast.error(str(exc))
            return
        await self._cargar_zona()
        await self._cargar_resumen()
        yield self._repintar()

    # ── Punto de aplicación ──────────────────────────────────────────────────────

    def abrir_punto(self, procedimiento_id: int):
        self.pt_proc_id = procedimiento_id
        self.pt_producto = "0"
        self.pt_lote = ""
        self.pt_cantidad = ""
        self.pt_unidad = ""
        self.pt_obs = ""
        self.modal_punto = True

    def cerrar_punto(self): self.modal_punto = False
    def set_pt_producto(self, v: str): self.pt_producto = v
    def set_pt_lote(self, v: str): self.pt_lote = v
    def set_pt_cantidad(self, v: str): self.pt_cantidad = v
    def set_pt_unidad(self, v: str): self.pt_unidad = v
    def set_pt_obs(self, v: str): self.pt_obs = v

    async def guardar_punto(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_punto = False
            yield rx.toast.error("No tenés permiso para editar el mapa estético")
            return
        try:
            producto_id = int(self.pt_producto) if self.pt_producto not in ("", "0") else None
        except (ValueError, TypeError):
            producto_id = None
        self.is_saving = True
        yield
        try:
            async with get_async_session() as session:
                await svc.agregar_punto(
                    session, self.clinica_id, self.pt_proc_id,
                    coord_x=self.last_x, coord_y=self.last_y,
                    producto_id=producto_id, lote=self.pt_lote,
                    cantidad=self.pt_cantidad, unidad=self.pt_unidad,
                    observacion=self.pt_obs,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            self.is_saving = False
            yield rx.toast.error(str(exc))
            return
        self.is_saving = False
        self.modal_punto = False
        await self._cargar_zona()
        await self._cargar_resumen()
        yield self._repintar()

    async def eliminar_punto(self, punto_id: int):
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para editar el mapa estético")
            return
        try:
            async with get_async_session() as session:
                await svc.eliminar_punto(
                    session, self.clinica_id, punto_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            yield rx.toast.error(str(exc))
            return
        await self._cargar_zona()
        await self._cargar_resumen()
        yield self._repintar()

    # ── Fotos antes/después por zona (E8) ─────────────────────────────────────────

    def set_foto_momento(self, v: str):
        self.foto_momento = v

    async def handle_upload_foto(self, files: list[rx.UploadFile]):
        self.foto_error = ""
        if not self.tiene_permiso("historia", write=True):
            self.foto_error = "Sin permiso de escritura"
            return
        if not self.zona_sel:
            self.foto_error = "Elegí una zona primero"
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
                    self.foto_error = str(exc)
                    continue
                async with get_async_session() as session:
                    try:
                        await svc.registrar_foto_zona(
                            session, self.clinica_id, self.paciente_id,
                            zona_codigo=self.zona_sel,
                            momento=self.foto_momento,
                            nombre=nombre,
                            stored_name=stored,
                            mime=file.content_type,
                            tamano=len(data),
                            usuario_id=self.user_id,
                            sede_id=self.sede_actual_id,
                        )
                    except ServiceError as exc:
                        self.foto_error = str(exc)
        except Exception:
            self.foto_error = "Ocurrió un error al subir la foto."
        self.is_uploading = False
        await self._cargar_zona()
        await self._cargar_resumen()
        yield rx.clear_selected_files(_FOTO_UPLOAD_ID)
        yield self._repintar()

    async def eliminar_foto(self, foto_id: int):
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para eliminar fotos")
            return
        stored_name = ""
        try:
            async with get_async_session() as session:
                stored_name = await svc.eliminar_foto_zona(
                    session, self.clinica_id, foto_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            yield rx.toast.error(str(exc))
            return
        if stored_name:
            await asyncio.to_thread(storage.eliminar, self.clinica_id, stored_name)
        await self._cargar_zona()
        await self._cargar_resumen()
        yield self._repintar()
