from __future__ import annotations

import json
import os

import reflex as rx

from clinica_app.components.anatomy_viewer import (
    anatomy_boot_script,
    anatomy_setdata_script,
)
from clinica_app.database import get_async_session
from clinica_app.services import odontograma as svc
from clinica_app.services import planes_tratamiento as pt
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

# URLs (servidas desde /assets) de las arcadas GLB realistas. Si faltan, el motor
# usa la dentadura procedural. Se configuran por entorno para cambiar de modelo
# sin tocar código (ANATOMY_TEETH_LOWER_URL / ANATOMY_TEETH_UPPER_URL).
_TEETH_LOWER = os.getenv("ANATOMY_TEETH_LOWER_URL", "")
_TEETH_UPPER = os.getenv("ANATOMY_TEETH_UPPER_URL", "")
_DENTAL_MODEL_JSON = (
    json.dumps({"inferior": _TEETH_LOWER, "superior": _TEETH_UPPER})
    if _TEETH_LOWER and _TEETH_UPPER else ""
)

# Disposición de las 5 caras en la cruz del odontograma (E4). El orden de la
# lista es el que consume `caras_view`; la página lo dibuja como cruz 3×3:
#   [ vestibular ] / [ mesial · oclusal · distal ] / [ palatina ]
_CARAS_LAYOUT: tuple[tuple[str, str, str], ...] = (
    ("vestibular", "V", "Vestibular"),
    ("mesial",     "M", "Mesial"),
    ("oclusal",    "O", "Oclusal / Incisal"),
    ("distal",     "D", "Distal"),
    ("palatina",   "P", "Palatina / Lingual"),
)


class OdontogramaState(BaseState):

    paciente_id:     int = 0
    paciente_nombre: str = ""

    superior:    list[dict] = []
    inferior:    list[dict] = []
    resumen:     list[dict] = []   # [{estado, label, color, count}]
    estados_cat: list[dict] = []
    con_datos:   int  = 0
    is_loading:  bool = False

    # ── Vista 3D (E3 — motor anatómico sobre los mismos datos) ──────────────────
    vista_3d: bool = False
    # Visor 3D a pantalla completa (llena el viewport).
    pantalla_completa: bool = False

    # ── Modal edición de pieza ──────────────────────────────────────────────────
    modal_abierto: bool = False
    sel_numero:    str  = ""
    sel_estado:    str  = "sano"
    sel_nota:      str  = ""
    sel_caras:     dict[str, str] = {}   # {cara: estado} — detalle por superficie (E4)
    cara_pincel:   str  = "caries"       # estado con el que se pintan las caras
    is_saving:     bool = False

    # ── Tratamiento planificado de la pieza (doble notación dx/tx) ──────────────
    # Los tratamientos son ítems del plan de tratamiento que referencian la pieza.
    tx_items:      list[dict] = []       # ítems de plan de la pieza abierta (modal)
    tx_desc:       str  = ""             # descripción sugerida al agregar al plan
    is_agregando_tx: bool = False

    # ── Pincel de superficies sobre la grilla 2D (E5) ───────────────────────────
    # Con el pincel activo, tocar una cara del diente en la grilla la pinta al
    # instante (sin abrir el modal). Reutiliza `cara_pincel` como estado a aplicar.
    pincel_activo: bool = False

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

    # ── Comparar dos versiones (lado a lado) ────────────────────────────────────
    cmp_abierto:  bool = False
    cmp_a_id:     int  = 0
    cmp_b_id:     int  = 0
    cmp_opciones: list[dict] = []   # [{value, label}] para los selectores
    cmp_sup_a:    list[dict] = []
    cmp_inf_a:    list[dict] = []
    cmp_sup_b:    list[dict] = []
    cmp_inf_b:    list[dict] = []
    cmp_cambios:  list[dict] = []
    cmp_n:        int  = 0
    cmp_titulo_a: str  = ""
    cmp_fecha_a:  str  = ""
    cmp_titulo_b: str  = ""
    cmp_fecha_b:  str  = ""

    @rx.var
    def puede_versionar(self) -> bool:
        return self.tiene_permiso("historia", write=True)

    @rx.var
    def puede_comparar(self) -> bool:
        return len(self.versiones) >= 1

    @rx.var
    def estados_hallazgo(self) -> list[dict]:
        """Estados que son hallazgos/diagnóstico (para la leyenda dx)."""
        return [e for e in self.estados_cat if e.get("naturaleza") == "hallazgo"]

    @rx.var
    def estados_tratamiento(self) -> list[dict]:
        """Estados que son tratamientos presentes en la pieza (para la leyenda tx)."""
        return [e for e in self.estados_cat if e.get("naturaleza") == "tratamiento"]

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
            tx_map = await svc.resumen_tratamientos(
                session, self.clinica_id, self.paciente_id, sede_id=self.sede_actual_id
            )
        self.superior = self._anotar_tx(data["superior"], tx_map)
        self.inferior = self._anotar_tx(data["inferior"], tx_map)
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

    # ── Pincel de superficies (E5) ───────────────────────────────────────────────

    def toggle_pincel(self):
        self.pincel_activo = not self.pincel_activo

    @staticmethod
    def _anotar_tx(piezas: list[dict], tx_map: dict) -> list[dict]:
        """Agrega a cada pieza la capa de tratamiento planificado (badge dx/tx):
        `tx_pend` (ítems no terminados) y `tx_done` (ítems terminados)."""
        salida = []
        for p in piezas:
            cont = tx_map.get(p["numero"], {})
            salida.append({
                **p,
                "tx_pend": cont.get("pendientes", 0),
                "tx_done": cont.get("terminados", 0),
            })
        return salida

    def _reemplazar_pieza(self, nueva: dict):
        """Reemplaza una pieza en las arcadas vivas por su nuevo dump, sin recargar
        todo (evita el flicker de re-render de la arcada completa al pintar).
        Conserva la capa de tratamiento (tx_*) que no viene en el dump del servicio."""
        num = nueva["numero"]

        def _merge(p):
            if p["numero"] != num:
                return p
            return {**nueva, "tx_pend": p.get("tx_pend", 0), "tx_done": p.get("tx_done", 0)}

        self.superior = [_merge(p) for p in self.superior]
        self.inferior = [_merge(p) for p in self.inferior]

    def _pieza_actual(self, numero: str) -> dict | None:
        """La pieza tal como está *ahora* en el estado del servidor (no en el
        payload del cliente). Clave para pintar varias caras seguidas sin carrera:
        Reflex procesa los eventos en orden, así que cada click ve el resultado del
        anterior a través de este lookup."""
        for p in list(self.superior) + list(self.inferior):
            if p.get("numero") == numero:
                return p
        return None

    async def tocar_superficie(self, numero: str, cara: str):
        """Click en una cara del diente en la grilla 2D. Con el pincel activo, la
        pinta (toggle) con el estado del pincel y persiste; si no, abre el modal."""
        pieza = self._pieza_actual(numero)
        if pieza is None:
            return
        if not self.pincel_activo:
            self.abrir_pieza(dict(pieza))
            await self._cargar_tx_pieza(numero)
            return
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para editar el odontograma")
            return
        caras = {c: e for c, e in dict(pieza.get("caras") or {}).items() if c and e}
        if caras.get(cara) == self.cara_pincel:
            caras.pop(cara, None)          # tocar de nuevo con el mismo pincel = quitar
        else:
            caras[cara] = self.cara_pincel
        try:
            async with get_async_session() as session:
                nueva = await svc.guardar_pieza(
                    session, self.clinica_id, self.paciente_id, numero,
                    estado=pieza.get("estado") or "sano",
                    caras=caras,
                    nota=pieza.get("nota") or "",
                    usuario_id=self.user_id,
                    sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            yield rx.toast.error(str(exc))
            return
        self._reemplazar_pieza(nueva)
        if self.vista_3d:
            yield rx.call_script(anatomy_setdata_script(self._payload_3d()))

    # ── Modal ────────────────────────────────────────────────────────────────────

    def abrir_pieza(self, pieza: dict):
        self.sel_numero = pieza.get("numero") or ""
        self.sel_estado = pieza.get("estado") or "sano"
        self.sel_nota   = pieza.get("nota") or ""
        # Detalle por cara (E4). Copiamos el dict para no mutar el de la lista.
        caras = pieza.get("caras") or {}
        self.sel_caras = {c: e for c, e in dict(caras).items() if c and e}
        # Doble notación: limpiamos la capa de tratamiento y sugerimos uno.
        self.tx_items = []
        self.tx_desc = svc.sugerencia_tratamiento(self.sel_estado, self.sel_numero)
        self.modal_abierto = True

    async def abrir_modal_pieza(self, pieza: dict):
        """Abre el modal de la pieza (desde la grilla) y carga su tratamiento planificado."""
        self.abrir_pieza(pieza)
        await self._cargar_tx_pieza(self.sel_numero)

    async def _cargar_tx_pieza(self, numero: str):
        if not numero:
            self.tx_items = []
            return
        async with get_async_session() as session:
            self.tx_items = await svc.listar_tratamientos_pieza(
                session, self.clinica_id, self.paciente_id, numero, sede_id=self.sede_actual_id,
            )

    def set_tx_desc(self, v: str):
        self.tx_desc = v

    async def _plan_destino(self, session) -> int:
        """Plan de tratamiento donde agregar: el más reciente no cancelado, o uno nuevo."""
        planes = await pt.listar_planes(session, self.clinica_id, self.paciente_id)
        activos = [p for p in planes if p["estado"] != "cancelado"]
        if activos:
            return activos[0]["id"]
        nuevo = await pt.crear_plan(
            session, self.clinica_id, self.paciente_id,
            titulo="Plan de tratamiento", usuario_id=self.user_id, sede_id=self.sede_actual_id,
        )
        return nuevo["id"]

    async def agregar_tratamiento(self):
        """Crea un ítem de plan de tratamiento para la pieza abierta (doble notación)."""
        if not self.tiene_permiso("historia", write=True):
            yield rx.toast.error("No tenés permiso para editar el plan de tratamiento")
            return
        desc = (self.tx_desc or "").strip()
        if not desc:
            yield rx.toast.error("Escribí una descripción para el tratamiento")
            return
        self.is_agregando_tx = True
        yield
        try:
            async with get_async_session() as session:
                plan_id = await self._plan_destino(session)
                await pt.agregar_item(
                    session, self.clinica_id, plan_id,
                    descripcion=desc, pieza_numero=self.sel_numero,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
                self.tx_items = await svc.listar_tratamientos_pieza(
                    session, self.clinica_id, self.paciente_id, self.sel_numero, sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            self.is_agregando_tx = False
            yield rx.toast.error(str(exc))
            return
        self.is_agregando_tx = False
        yield rx.toast.success("Tratamiento agregado al plan")
        await self._cargar()          # refresca los badges de tratamiento en la arcada

    def cerrar_modal(self):
        self.modal_abierto = False

    def set_sel_estado(self, v: str): self.sel_estado = v
    def set_sel_nota(self, v: str):   self.sel_nota = v

    # ── Detalle por cara (E4) ────────────────────────────────────────────────────

    @rx.var
    def caras_view(self) -> list[dict]:
        """Las 5 caras en orden de layout, cada una con su estado/color actual
        (color vacío = cara sin detalle). Lo consume la cruz del modal."""
        colores = {e["clave"]: e for e in self.estados_cat}
        salida: list[dict] = []
        for cara, corto, label in _CARAS_LAYOUT:
            est = self.sel_caras.get(cara, "")
            info = colores.get(est)
            salida.append({
                "cara":   cara,
                "corto":  corto,
                "label":  label,
                "estado": est,
                "color":  info["color"] if info else "#f3f4f6",
                "text":   info["text"] if info else "#9ca3af",
                "tiene":  bool(est),
            })
        return salida

    def set_cara_pincel(self, v: str):
        self.cara_pincel = v

    def pintar_cara(self, cara: str):
        """Pinta la cara con el pincel actual; si ya la tenía con ese estado, la
        limpia (toggle). Reasigna el dict para disparar la reactividad."""
        nuevo = dict(self.sel_caras)
        if nuevo.get(cara) == self.cara_pincel:
            nuevo.pop(cara, None)
        else:
            nuevo[cara] = self.cara_pincel
        self.sel_caras = nuevo

    def limpiar_caras(self):
        self.sel_caras = {}

    # ── Vista 3D ─────────────────────────────────────────────────────────────────

    def _payload_3d(self, seleccionado: str = "") -> str:
        """Colores por pieza FDI (estado real) para el visor 3D."""
        colores = {p["numero"]: p["color"] for p in list(self.superior) + list(self.inferior)}
        return json.dumps({"colores": colores, "seleccionado": seleccionado})

    def mostrar_3d(self):
        if self.vista_3d:
            return
        self.vista_3d = True
        yield rx.call_script(anatomy_boot_script(
            self._payload_3d(), model_url=_DENTAL_MODEL_JSON,
        ))

    def mostrar_2d(self):
        if not self.vista_3d:
            return
        self.vista_3d = False
        # Al volver a 2D, liberamos el renderer (evita un loop de render huérfano).
        yield rx.call_script("window.AnatomyViewer&&window.AnatomyViewer.dispose();")

    def set_camara(self, nombre: str):
        yield rx.call_script(
            "window.AnatomyViewer&&window.AnatomyViewer.setCamera('" + nombre + "');"
        )

    def toggle_pantalla_completa(self):
        self.pantalla_completa = not self.pantalla_completa
        # El canvas WebGL no siempre detecta el cambio de tamaño del contenedor
        # (ResizeObserver no dispara confiable con el toggle de clase) → forzamos
        # un resize tras aplicar el nuevo layout.
        yield rx.call_script(
            "setTimeout(function(){window.dispatchEvent(new Event('resize'));},80);"
        )

    async def on_pick_3d(self, value: str):
        """Selección desde el visor 3D → abre el mismo modal que el 2D."""
        try:
            data = json.loads(value or "{}")
        except (ValueError, TypeError):
            return
        numero = str(data.get("anatomy_id") or "")
        if not numero:
            return
        pieza = next(
            (p for p in list(self.superior) + list(self.inferior) if p["numero"] == numero),
            None,
        )
        if pieza is None:
            return
        self.abrir_pieza(pieza)
        await self._cargar_tx_pieza(numero)
        # Resalta la pieza elegida en el visor mientras el modal está abierto.
        yield rx.call_script(anatomy_setdata_script(self._payload_3d(seleccionado=numero)))

    async def guardar_pieza(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_abierto = False
            yield rx.toast.error("No tenés permiso para editar el odontograma")
            return
        self.is_saving = True
        yield
        try:
            async with get_async_session() as session:
                await svc.guardar_pieza(
                    session, self.clinica_id, self.paciente_id, self.sel_numero,
                    estado=self.sel_estado,
                    caras=dict(self.sel_caras),
                    nota=self.sel_nota,
                    usuario_id=self.user_id,
                    sede_id=self.sede_actual_id,
                )
        except ServiceError as exc:
            self.is_saving = False
            yield rx.toast.error(str(exc))
            return
        self.is_saving = False
        self.modal_abierto = False
        await self._cargar()
        if self.vista_3d:
            yield rx.call_script(anatomy_setdata_script(self._payload_3d()))

    async def resetear_pieza(self):
        if not self.tiene_permiso("historia", write=True):
            self.modal_abierto = False
            yield rx.toast.error("No tenés permiso para editar el odontograma")
            return
        async with get_async_session() as session:
            try:
                await svc.resetear_pieza(
                    session, self.clinica_id, self.paciente_id, self.sel_numero,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        self.modal_abierto = False
        await self._cargar()
        if self.vista_3d:
            yield rx.call_script(anatomy_setdata_script(self._payload_3d()))

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
            yield rx.toast.error("No tenés permiso para versionar el odontograma")
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
        except ServiceError as exc:
            self.is_versionando = False
            yield rx.toast.error(str(exc))
            return
        self.is_versionando = False
        self.modal_version = False
        self.mostrar_historial = True
        yield rx.toast.success("Versión guardada")
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

    def confirmar_eliminar(self, v: dict):
        self._pedir_eliminar(
            kind="version",
            id=v["id"],
            titulo="¿Eliminar versión?",
            mensaje=f"La versión «{v['titulo']}» del odontograma se eliminará.",
        )

    async def ejecutar_eliminar(self):
        if not self.tiene_permiso("historia", write=True):
            self.del_open = False
            yield rx.toast.error("No tenés permiso para eliminar versiones")
            return
        self.del_procesando = True
        yield
        async with get_async_session() as session:
            try:
                await svc.eliminar_version(
                    session, self.clinica_id, self.paciente_id, self._del_id,
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                self.del_procesando = False
                yield rx.toast.error(str(exc))
                return
        self.del_open       = False
        self.del_procesando = False
        yield rx.toast.success("Versión eliminada")
        await self._cargar_versiones()

    # ── Comparar versiones ───────────────────────────────────────────────────────

    async def abrir_comparar(self):
        # Opciones: cada versión + "Estado actual" (value 0).
        self.cmp_opciones = (
            [{"value": str(v["id"]), "label": v["titulo"] + " — " + v["fecha"]} for v in self.versiones]
            + [{"value": "0", "label": "Estado actual"}]
        )
        # Por defecto: A = versión más reciente, B = estado actual.
        self.cmp_a_id = self.versiones[0]["id"] if self.versiones else 0
        self.cmp_b_id = 0
        await self._cargar_comparacion()
        self.cmp_abierto = True

    def cerrar_comparar(self):
        self.cmp_abierto = False

    async def set_cmp_a(self, v: str):
        try:
            self.cmp_a_id = int(v)
        except (ValueError, TypeError):
            self.cmp_a_id = 0
        await self._cargar_comparacion()

    async def set_cmp_b(self, v: str):
        try:
            self.cmp_b_id = int(v)
        except (ValueError, TypeError):
            self.cmp_b_id = 0
        await self._cargar_comparacion()

    async def _cargar_comparacion(self):
        async with get_async_session() as session:
            try:
                data = await svc.comparar(
                    session, self.clinica_id, self.paciente_id,
                    self.cmp_a_id, self.cmp_b_id, sede_id=self.sede_actual_id,
                )
            except ServiceError:
                return
        self.cmp_sup_a = data["superior_a"]
        self.cmp_inf_a = data["inferior_a"]
        self.cmp_sup_b = data["superior_b"]
        self.cmp_inf_b = data["inferior_b"]
        self.cmp_cambios = data["cambios"]
        self.cmp_n = data["n_cambios"]
        self.cmp_titulo_a = data["titulo_a"]
        self.cmp_fecha_a = data["fecha_a"]
        self.cmp_titulo_b = data["titulo_b"]
        self.cmp_fecha_b = data["fecha_b"]
