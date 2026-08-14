from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import configuracion as svc
from clinica_app.services import especialidad as _especialidad
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class ConfiguracionState(BaseState):
    """Estado del módulo Configuración (solo administradores)."""

    # ── Tab activo ─────────────────────────────────────────────────────────────
    tab_activo: str = "empresa"

    # ══════════════════════════════════════════════════════════════════
    # EMPRESA
    # ══════════════════════════════════════════════════════════════════
    form_nombre:            str  = ""
    form_razon_social:      str  = ""
    form_documento_fiscal:  str  = ""
    form_email_clinica:     str  = ""
    form_telefono:          str  = ""
    form_direccion_fiscal:  str  = ""
    form_zona_horaria:      str  = ""
    form_rubro:             str  = ""
    form_mensaje_recibo:    str  = ""
    form_papel_impresion:   str  = "80mm"
    form_ancho_recibo:      str  = ""
    form_margen_global:     str  = "50.00"
    empresa_error:          str  = ""
    empresa_success:        str  = ""
    semilla_msg:            str  = ""
    is_saving_empresa:      bool = False
    margenes_error:         str  = ""
    margenes_success:       str  = ""
    is_saving_margenes:     bool = False

    # ══════════════════════════════════════════════════════════════════
    # SUCURSALES
    # ══════════════════════════════════════════════════════════════════
    sedes:              list[dict] = []
    modal_sede:         bool = False
    sede_editar_id:     int  = 0
    form_sede_nombre:   str  = ""
    form_sede_dir:      str  = ""
    form_sede_tel:      str  = ""
    form_sede_email:    str  = ""
    form_sede_principal: bool = False
    form_sede_error:    str  = ""
    is_saving_sede:     bool = False

    # ══════════════════════════════════════════════════════════════════
    # USUARIOS
    # ══════════════════════════════════════════════════════════════════
    usuarios:          list[dict] = []
    modal_usuario:     bool = False
    form_u_nombre:     str  = ""
    form_u_email:      str  = ""
    form_u_rol:        str  = "recepcionista"
    form_u_password:   str  = ""
    form_u_password2:  str  = ""
    form_u_sede_ids:   list[int]  = []
    form_u_error:      str  = ""
    is_saving_usuario: bool = False
    sedes_form:        list[dict] = []

    modal_password:    bool = False
    pw_user_id:        int  = 0
    pw_user_nombre:    str  = ""
    form_pw_nueva:     str  = ""
    form_pw_nueva2:    str  = ""
    form_pw_error:     str  = ""
    form_pw_success:   str  = ""
    is_saving_pw:      bool = False

    # ══════════════════════════════════════════════════════════════════
    # MONEDAS
    # ══════════════════════════════════════════════════════════════════
    monedas:             list[dict] = []
    form_moneda_codigo:  str  = ""
    form_moneda_nombre:  str  = ""
    form_moneda_simbolo: str  = ""
    moneda_error:        str  = ""
    is_saving_moneda:    bool = False

    # ══════════════════════════════════════════════════════════════════
    # UNIDADES DE MEDIDA
    # ══════════════════════════════════════════════════════════════════
    unidades:              list[dict] = []
    form_unidad_nombre:    str  = ""
    form_unidad_decimales: bool = False
    unidad_error:          str  = ""
    is_saving_unidad:      bool = False

    # ══════════════════════════════════════════════════════════════════
    # MÉTODOS DE PAGO
    # ══════════════════════════════════════════════════════════════════
    metodos_pago:        list[dict] = []
    form_mp_nombre:      str  = ""
    form_mp_descripcion: str  = ""
    form_mp_tipo:        str  = "otro"
    mp_error:            str  = ""
    is_saving_mp:        bool = False

    # ══════════════════════════════════════════════════════════════════
    # IMPUESTOS
    # ══════════════════════════════════════════════════════════════════
    impuesto_tasas:           list[dict] = []
    mostrar_impuesto_recibo:  bool = False
    modal_impuesto:           bool = False
    impuesto_editar_id:       int  = 0
    form_it_tipo:             str  = "IVA"
    form_it_nombre:           str  = ""
    form_it_porcentaje:       str  = ""
    form_it_es_default:       bool = False
    it_error:                 str  = ""
    is_saving_it:             bool = False

    # ── Permisos ───────────────────────────────────────────────────────────────
    modal_permisos:        bool       = False
    permisos_rol_activo:   str        = ""
    permisos_rol_label:    str        = ""
    permisos_rol_modulos:  list[dict] = []
    permisos_matrix:       list[dict] = []

    # ── Computed vars ──────────────────────────────────────────────────────────

    @rx.var
    def precio_ejemplo_venta(self) -> str:
        try:
            margen = float(self.form_margen_global)
            precio = 10.0 * (1 + margen / 100)
            return f"{precio:.2f}"
        except (ValueError, ZeroDivisionError):
            return "10.00"

    @rx.var
    def impuesto_default_label(self) -> str:
        for t in self.impuesto_tasas:
            if t.get("is_default"):
                return f"{t['tipo_impuesto']} ({t['porcentaje']:.2f}%)"
        return "Sin impuesto"

    @rx.var
    def impuesto_default_pct(self) -> float:
        for t in self.impuesto_tasas:
            if t.get("is_default"):
                return float(t.get("porcentaje", 0))
        return 0.0

    @rx.var
    def impuesto_preview_monto(self) -> str:
        return f"{100.0 * self.impuesto_default_pct / 100.0:.2f}"

    @rx.var
    def impuesto_preview_total(self) -> str:
        return f"{100.0 + 100.0 * self.impuesto_default_pct / 100.0:.2f}"

    @rx.var
    def moneda_activa_nombre(self) -> str:
        for m in self.monedas:
            if m.get("es_activa"):
                return m.get("nombre", "")
        return "Sin moneda activa"

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("configuracion"):
            yield rx.redirect("/")
            return
        await self._cargar()

    async def _cargar(self):
        async with get_async_session() as session:
            clinica  = await svc.obtener_clinica(session, self.clinica_id)
            usuarios = await svc.listar_usuarios(session, self.clinica_id)
        self._populate_clinica(clinica)
        self.usuarios        = usuarios
        self.empresa_error   = ""
        self.empresa_success = ""

    def _populate_clinica(self, c: dict):
        self.form_nombre           = c["nombre"]
        self.form_razon_social     = c["razon_social"]
        self.form_documento_fiscal = c["documento_fiscal"]
        self.form_email_clinica    = c["email"]
        self.form_telefono         = c["telefono"]
        self.form_direccion_fiscal = c["direccion_fiscal"]
        self.form_zona_horaria     = c["zona_horaria"]
        self.form_rubro            = c["rubro"]
        self.form_mensaje_recibo   = c["mensaje_recibo"]
        self.form_papel_impresion  = c["papel_impresion"]
        self.form_ancho_recibo     = str(c["ancho_recibo"]) if c["ancho_recibo"] else ""
        self.form_margen_global    = f"{c['margen_global']:.2f}"
        self.mostrar_impuesto_recibo = c["mostrar_impuesto_recibo"]

    async def set_tab(self, tab: str):
        self.tab_activo = tab
        if tab == "sucursales":
            await self._cargar_sedes()
        elif tab == "monedas":
            await self._cargar_monedas()
        elif tab == "unidades":
            await self._cargar_unidades()
        elif tab == "pagos":
            await self._cargar_metodos_pago()
        elif tab == "impuestos":
            await self._cargar_impuestos()

    # ── Perfil de especialidad (D1) — refleja el rubro elegido en el dropdown ──
    @rx.var
    def perfil_dental_sel(self) -> bool:
        return _especialidad.dental_activa(self.form_rubro)

    @rx.var
    def perfil_estetica_sel(self) -> bool:
        return _especialidad.estetica_activa(self.form_rubro)

    # ── Setters ────────────────────────────────────────────────────────────────

    def set_form_nombre(self, v: str):            self.form_nombre = v
    def set_form_razon_social(self, v: str):      self.form_razon_social = v
    def set_form_documento_fiscal(self, v: str):  self.form_documento_fiscal = v
    def set_form_email_clinica(self, v: str):     self.form_email_clinica = v
    def set_form_telefono(self, v: str):          self.form_telefono = v
    def set_form_direccion_fiscal(self, v: str):  self.form_direccion_fiscal = v
    def set_form_zona_horaria(self, v: str):      self.form_zona_horaria = v
    def set_form_rubro(self, v: str):             self.form_rubro = v
    def set_form_mensaje_recibo(self, v: str):    self.form_mensaje_recibo = v
    def set_form_papel_impresion(self, v: str):   self.form_papel_impresion = v
    def set_form_ancho_recibo(self, v: float | str): self.form_ancho_recibo = str(v) if str(v) != "0" else ""
    def set_form_margen_global(self, v: float | str): self.form_margen_global = str(v)

    def set_form_sede_nombre(self, v: str):       self.form_sede_nombre = v
    def set_form_sede_dir(self, v: str):          self.form_sede_dir = v
    def set_form_sede_tel(self, v: str):          self.form_sede_tel = v
    def set_form_sede_email(self, v: str):        self.form_sede_email = v
    def set_form_sede_principal(self, v: bool):   self.form_sede_principal = v

    def set_form_u_nombre(self, v: str):    self.form_u_nombre = v
    def set_form_u_email(self, v: str):     self.form_u_email = v
    def set_form_u_rol(self, v: str):       self.form_u_rol = v
    def set_form_u_password(self, v: str):  self.form_u_password = v
    def set_form_u_password2(self, v: str): self.form_u_password2 = v

    def toggle_u_sede(self, sede_id: int):
        if sede_id in self.form_u_sede_ids:
            self.form_u_sede_ids = [s for s in self.form_u_sede_ids if s != sede_id]
        else:
            self.form_u_sede_ids = self.form_u_sede_ids + [sede_id]
    def set_form_pw_nueva(self, v: str):    self.form_pw_nueva = v
    def set_form_pw_nueva2(self, v: str):   self.form_pw_nueva2 = v

    def set_form_moneda_codigo(self, v: str):   self.form_moneda_codigo = v
    def set_form_moneda_nombre(self, v: str):   self.form_moneda_nombre = v
    def set_form_moneda_simbolo(self, v: str):  self.form_moneda_simbolo = v

    def set_form_unidad_nombre(self, v: str):     self.form_unidad_nombre = v
    def set_form_unidad_decimales(self, v: bool): self.form_unidad_decimales = v
    def toggle_form_unidad_decimales(self):       self.form_unidad_decimales = not self.form_unidad_decimales

    def set_form_mp_nombre(self, v: str):       self.form_mp_nombre = v
    def set_form_mp_descripcion(self, v: str):  self.form_mp_descripcion = v
    def set_form_mp_tipo(self, v: str):         self.form_mp_tipo = v

    def set_form_it_tipo(self, v: str):             self.form_it_tipo = v
    def set_form_it_nombre(self, v: str):           self.form_it_nombre = v
    def set_form_it_porcentaje(self, v: float | str): self.form_it_porcentaje = str(v)
    def set_form_it_es_default(self, v: bool):      self.form_it_es_default = v

    # ══════════════════════════════════════════════════════════════════
    # EMPRESA
    # ══════════════════════════════════════════════════════════════════

    async def guardar_empresa(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.is_saving_empresa = True
        self.empresa_error     = ""
        self.empresa_success   = ""
        yield

        ancho = None
        if self.form_ancho_recibo.strip():
            try:
                ancho = int(self.form_ancho_recibo)
            except ValueError:
                self.empresa_error     = "El ancho de recibo debe ser un número entero"
                self.is_saving_empresa = False
                return

        payload = {
            "nombre":           self.form_nombre.strip(),
            "razon_social":     self.form_razon_social.strip()     or None,
            "documento_fiscal": self.form_documento_fiscal.strip() or None,
            "email":            self.form_email_clinica.strip()    or None,
            "telefono":         self.form_telefono.strip()         or None,
            "direccion_fiscal": self.form_direccion_fiscal.strip() or None,
            "zona_horaria":     self.form_zona_horaria.strip()     or None,
            "rubro":            self.form_rubro.strip()            or None,
            "mensaje_recibo":   self.form_mensaje_recibo.strip()   or None,
            "papel_impresion":  self.form_papel_impresion          or "80mm",
            "ancho_recibo":     ancho,
        }
        try:
            async with get_async_session() as session:
                await svc.actualizar_clinica(session, self.clinica_id, payload)
        except ServiceError as exc:
            self.empresa_error     = str(exc)
            self.is_saving_empresa = False
            return

        self.is_saving_empresa = False
        self.empresa_success   = "Configuración guardada correctamente"
        # Refresca el perfil de especialidad (D1) para que el gating de módulos se
        # actualice de inmediato, sin necesidad de volver a iniciar sesión.
        self.clinica_rubro = self.form_rubro.strip()

    async def sembrar_catalogo(self):
        """Crea los servicios precargados de la especialidad del rubro (D1)."""
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.semilla_msg = ""
        async with get_async_session() as session:
            try:
                res = await _especialidad.sembrar_servicios(
                    session, self.clinica_id, self.form_rubro.strip(),
                    usuario_id=self.user_id, sede_id=self.sede_actual_id,
                )
            except ServiceError as exc:
                self.semilla_msg = str(exc)
                return
        if res["creados"]:
            self.semilla_msg = f"Se agregaron {res['creados']} servicios de la especialidad al catálogo."
        elif res["omitidos"]:
            self.semilla_msg = "El catálogo ya tenía los servicios de la especialidad."
        else:
            self.semilla_msg = "Elegí un rubro con especialidad (odontología o estética) para sembrar su catálogo."

    async def guardar_margenes(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.is_saving_margenes = True
        self.margenes_error     = ""
        self.margenes_success   = ""
        yield
        try:
            margen = float(self.form_margen_global)
        except ValueError:
            self.margenes_error     = "El margen debe ser un número"
            self.is_saving_margenes = False
            return
        try:
            async with get_async_session() as session:
                await svc.guardar_margenes(session, self.clinica_id, margen)
        except ServiceError as exc:
            self.margenes_error     = str(exc)
            self.is_saving_margenes = False
            return
        self.is_saving_margenes = False
        self.margenes_success   = f"Margen global actualizado a {margen:.2f}%"

    # ══════════════════════════════════════════════════════════════════
    # SUCURSALES
    # ══════════════════════════════════════════════════════════════════

    async def _cargar_sedes(self):
        from clinica_app.services import sedes as svc_sedes
        async with get_async_session() as session:
            self.sedes = await svc_sedes.listar(session, self.clinica_id)

    def abrir_nueva_sede(self):
        self.sede_editar_id     = 0
        self.form_sede_nombre   = ""
        self.form_sede_dir      = ""
        self.form_sede_tel      = ""
        self.form_sede_email    = ""
        self.form_sede_principal = False
        self.form_sede_error    = ""
        self.modal_sede         = True

    def abrir_editar_sede(self, sede: dict):
        self.sede_editar_id      = sede.get("id") or 0
        self.form_sede_nombre    = sede.get("nombre") or ""
        self.form_sede_dir       = sede.get("direccion") or ""
        self.form_sede_tel       = sede.get("telefono") or ""
        self.form_sede_email     = sede.get("email") or ""
        self.form_sede_principal = sede.get("es_principal", False)
        self.form_sede_error     = ""
        self.modal_sede          = True

    def cerrar_modal_sede(self):
        self.modal_sede = False

    async def guardar_sede(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.is_saving_sede  = True
        self.form_sede_error = ""
        yield
        from clinica_app.services import sedes as svc_sedes
        payload = {
            "nombre":       self.form_sede_nombre,
            "direccion":    self.form_sede_dir   or None,
            "telefono":     self.form_sede_tel   or None,
            "email":        self.form_sede_email or None,
            "es_principal": self.form_sede_principal,
        }
        try:
            async with get_async_session() as session:
                if self.sede_editar_id:
                    await svc_sedes.actualizar(session, self.clinica_id, self.sede_editar_id, payload)
                else:
                    await svc_sedes.crear(session, self.clinica_id, payload)
        except ServiceError as exc:
            self.form_sede_error = str(exc)
            self.is_saving_sede  = False
            return
        self.is_saving_sede = False
        self.modal_sede     = False
        await self._cargar_sedes()

    async def eliminar_sede(self, sede_id: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para eliminar sucursales")
            return
        from clinica_app.services import sedes as svc_sedes
        async with get_async_session() as session:
            try:
                await svc_sedes.eliminar(session, self.clinica_id, sede_id)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        yield rx.toast.success("Sucursal eliminada")
        await self._cargar_sedes()

    # ══════════════════════════════════════════════════════════════════
    # USUARIOS
    # ══════════════════════════════════════════════════════════════════

    async def abrir_modal_usuario(self):
        from clinica_app.services import sedes as svc_sedes
        async with get_async_session() as session:
            self.sedes_form = await svc_sedes.listar(session, self.clinica_id)
        self.form_u_nombre    = ""
        self.form_u_email     = ""
        self.form_u_rol       = "recepcionista"
        self.form_u_password  = ""
        self.form_u_password2 = ""
        self.form_u_sede_ids  = []
        self.form_u_error     = ""
        self.modal_usuario    = True

    def cerrar_modal_usuario(self):
        self.modal_usuario = False

    async def guardar_usuario(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.is_saving_usuario = True
        self.form_u_error      = ""
        yield
        if self.form_u_password != self.form_u_password2:
            self.form_u_error      = "Las contraseñas no coinciden"
            self.is_saving_usuario = False
            return
        try:
            async with get_async_session() as session:
                nuevo = await svc.crear_usuario(session, self.clinica_id, {
                    "nombre":   self.form_u_nombre,
                    "email":    self.form_u_email,
                    "rol":      self.form_u_rol,
                    "password": self.form_u_password,
                })
                # Asignar sucursales si no es admin y se seleccionaron
                if self.form_u_rol != "administracion" and self.form_u_sede_ids:
                    await svc.asignar_sedes_usuario(
                        session, self.clinica_id, nuevo["id"], self.form_u_sede_ids
                    )
        except ServiceError as exc:
            self.form_u_error      = str(exc)
            self.is_saving_usuario = False
            return
        self.is_saving_usuario = False
        self.modal_usuario     = False
        await self._recargar_usuarios()

    def abrir_modal_password(self, usuario: dict):
        self.pw_user_id      = usuario.get("id") or 0
        self.pw_user_nombre  = usuario.get("nombre") or ""
        self.form_pw_nueva   = ""
        self.form_pw_nueva2  = ""
        self.form_pw_error   = ""
        self.form_pw_success = ""
        self.modal_password  = True

    def cerrar_modal_password(self):
        self.modal_password = False

    async def guardar_password(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.is_saving_pw    = True
        self.form_pw_error   = ""
        self.form_pw_success = ""
        yield
        if self.form_pw_nueva != self.form_pw_nueva2:
            self.form_pw_error = "Las contraseñas no coinciden"
            self.is_saving_pw  = False
            return
        try:
            async with get_async_session() as session:
                await svc.cambiar_password(session, self.clinica_id, self.pw_user_id, self.form_pw_nueva)
        except ServiceError as exc:
            self.form_pw_error = str(exc)
            self.is_saving_pw  = False
            return
        self.is_saving_pw    = False
        self.form_pw_success = "Contraseña actualizada"

    async def toggle_activo_usuario(self, user_id: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para modificar usuarios")
            return
        async with get_async_session() as session:
            try:
                await svc.toggle_activo(session, self.clinica_id, user_id, self.user_id)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        await self._recargar_usuarios()

    async def _recargar_usuarios(self):
        async with get_async_session() as session:
            self.usuarios = await svc.listar_usuarios(session, self.clinica_id)

    # ══════════════════════════════════════════════════════════════════
    # MONEDAS
    # ══════════════════════════════════════════════════════════════════

    async def _cargar_monedas(self):
        from clinica_app.services import monedas as svc_m
        async with get_async_session() as session:
            self.monedas = await svc_m.listar(session, self.clinica_id)

    async def agregar_moneda(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.moneda_error = ""
        from clinica_app.services import monedas as svc_m
        try:
            async with get_async_session() as session:
                await svc_m.crear(session, self.clinica_id, {
                    "codigo":  self.form_moneda_codigo,
                    "nombre":  self.form_moneda_nombre,
                    "simbolo": self.form_moneda_simbolo,
                })
        except ServiceError as exc:
            self.moneda_error = str(exc)
            return
        self.form_moneda_codigo  = ""
        self.form_moneda_nombre  = ""
        self.form_moneda_simbolo = ""
        await self._cargar_monedas()

    async def seleccionar_moneda(self, moneda_id: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para cambiar la moneda")
            return
        from clinica_app.services import monedas as svc_m
        async with get_async_session() as session:
            try:
                await svc_m.set_activa(session, self.clinica_id, moneda_id)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        await self._cargar_monedas()

    async def eliminar_moneda(self, moneda_id: int):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.moneda_error = ""
        from clinica_app.services import monedas as svc_m
        async with get_async_session() as session:
            try:
                await svc_m.eliminar(session, self.clinica_id, moneda_id)
            except ServiceError as exc:
                self.moneda_error = str(exc)
                return
        await self._cargar_monedas()

    # ══════════════════════════════════════════════════════════════════
    # UNIDADES DE MEDIDA
    # ══════════════════════════════════════════════════════════════════

    async def _cargar_unidades(self):
        from clinica_app.services import unidades_medida as svc_u
        async with get_async_session() as session:
            self.unidades = await svc_u.listar(session, self.clinica_id)

    async def agregar_unidad(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.unidad_error = ""
        from clinica_app.services import unidades_medida as svc_u
        async with get_async_session() as session:
            try:
                await svc_u.crear(session, self.clinica_id, {
                    "nombre":            self.form_unidad_nombre,
                    "permite_decimales": self.form_unidad_decimales,
                })
            except ServiceError as exc:
                self.unidad_error = str(exc)
                return
        self.form_unidad_nombre    = ""
        self.form_unidad_decimales = False
        await self._cargar_unidades()

    async def toggle_unidad_decimales(self, uid: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para modificar unidades")
            return
        from clinica_app.services import unidades_medida as svc_u
        async with get_async_session() as session:
            try:
                await svc_u.toggle_decimales(session, self.clinica_id, uid)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        await self._cargar_unidades()

    async def eliminar_unidad(self, uid: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para eliminar unidades")
            return
        from clinica_app.services import unidades_medida as svc_u
        async with get_async_session() as session:
            try:
                await svc_u.eliminar(session, self.clinica_id, uid)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        yield rx.toast.success("Unidad eliminada")
        await self._cargar_unidades()

    # ══════════════════════════════════════════════════════════════════
    # MÉTODOS DE PAGO
    # ══════════════════════════════════════════════════════════════════

    async def _cargar_metodos_pago(self):
        from clinica_app.services import metodos_pago_config as svc_mp
        async with get_async_session() as session:
            self.metodos_pago = await svc_mp.listar(session, self.clinica_id)

    async def agregar_metodo_pago(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.mp_error = ""
        from clinica_app.services import metodos_pago_config as svc_mp
        async with get_async_session() as session:
            try:
                await svc_mp.crear(session, self.clinica_id, {
                    "nombre":      self.form_mp_nombre,
                    "descripcion": self.form_mp_descripcion,
                    "tipo":        self.form_mp_tipo,
                })
            except ServiceError as exc:
                self.mp_error = str(exc)
                return
        self.form_mp_nombre      = ""
        self.form_mp_descripcion = ""
        self.form_mp_tipo        = "otro"
        await self._cargar_metodos_pago()

    async def toggle_visible_metodo(self, mid: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para modificar métodos de pago")
            return
        from clinica_app.services import metodos_pago_config as svc_mp
        async with get_async_session() as session:
            try:
                await svc_mp.toggle_visible(session, self.clinica_id, mid)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        await self._cargar_metodos_pago()

    async def toggle_activo_metodo(self, mid: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para modificar métodos de pago")
            return
        from clinica_app.services import metodos_pago_config as svc_mp
        async with get_async_session() as session:
            try:
                await svc_mp.toggle_activo(session, self.clinica_id, mid)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        await self._cargar_metodos_pago()

    async def eliminar_metodo_pago(self, mid: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para eliminar métodos de pago")
            return
        from clinica_app.services import metodos_pago_config as svc_mp
        async with get_async_session() as session:
            try:
                await svc_mp.eliminar(session, self.clinica_id, mid)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        yield rx.toast.success("Método de pago eliminado")
        await self._cargar_metodos_pago()

    # ══════════════════════════════════════════════════════════════════
    # IMPUESTOS
    # ══════════════════════════════════════════════════════════════════

    async def _cargar_impuestos(self):
        from clinica_app.services import impuestos as svc_i
        async with get_async_session() as session:
            self.impuesto_tasas = await svc_i.listar(session, self.clinica_id)

    def abrir_modal_impuesto(self):
        self.impuesto_editar_id = 0
        self.form_it_tipo       = "IVA"
        self.form_it_nombre     = ""
        self.form_it_porcentaje = ""
        self.form_it_es_default = False
        self.it_error           = ""
        self.modal_impuesto     = True

    def cerrar_modal_impuesto(self):
        self.modal_impuesto = False

    async def guardar_impuesto(self):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.is_saving_it = True
        self.it_error     = ""
        yield
        from clinica_app.services import impuestos as svc_i
        payload = {
            "tipo_impuesto": self.form_it_tipo,
            "nombre":        self.form_it_nombre,
            "porcentaje":    self.form_it_porcentaje,
            "is_default":    self.form_it_es_default,
        }
        try:
            async with get_async_session() as session:
                if self.impuesto_editar_id:
                    await svc_i.actualizar(session, self.clinica_id, self.impuesto_editar_id, payload)
                else:
                    await svc_i.crear(session, self.clinica_id, payload)
        except ServiceError as exc:
            self.it_error     = str(exc)
            self.is_saving_it = False
            return
        self.is_saving_it   = False
        self.modal_impuesto = False
        await self._cargar_impuestos()

    async def eliminar_impuesto(self, tid: int):
        if not self.tiene_permiso("configuracion", write=True):
            return
        self.it_error = ""
        from clinica_app.services import impuestos as svc_i
        async with get_async_session() as session:
            try:
                await svc_i.eliminar(session, self.clinica_id, tid)
            except ServiceError as exc:
                self.it_error = str(exc)
                return
        await self._cargar_impuestos()

    async def set_default_impuesto(self, tid: int):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para modificar impuestos")
            return
        from clinica_app.services import impuestos as svc_i
        async with get_async_session() as session:
            try:
                await svc_i.set_default(session, self.clinica_id, tid)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        await self._cargar_impuestos()

    async def cargar_impuestos_pais(self, pais: str):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para cargar impuestos")
            return
        from clinica_app.services import impuestos as svc_i
        async with get_async_session() as session:
            try:
                await svc_i.cargar_pais(session, self.clinica_id, pais)
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return
        yield rx.toast.success("Impuestos del país cargados")
        await self._cargar_impuestos()

    async def toggle_mostrar_impuesto_recibo(self):
        if not self.tiene_permiso("configuracion", write=True):
            yield rx.toast.error("No tenés permiso para modificar esta opción")
            return
        async with get_async_session() as session:
            try:
                nuevo_val = await svc.toggle_mostrar_impuesto(session, self.clinica_id)
                self.mostrar_impuesto_recibo = nuevo_val
            except ServiceError as exc:
                yield rx.toast.error(str(exc))
                return

    # ══════════════════════════════════════════════════════════════════
    # PERMISOS
    # ══════════════════════════════════════════════════════════════════

    async def abrir_modal_permisos(self, usuario: dict):
        self.permisos_rol_activo = usuario.get("rol", "")
        self.permisos_rol_label  = usuario.get("rol_label", "")
        await self._cargar_permisos_rol()
        self.modal_permisos = True

    def cerrar_modal_permisos(self):
        self.modal_permisos = False

    async def _cargar_permisos_rol(self):
        rol = self.permisos_rol_activo
        if not rol:
            return
        from clinica_app.models.user import PermisoRol, RoleEnum
        from sqlmodel import select

        async with get_async_session() as session:
            registros = (
                await session.execute(
                    select(PermisoRol).where(
                        PermisoRol.clinica_id == self.clinica_id,
                        PermisoRol.role == RoleEnum(rol),
                    )
                )
            ).scalars().all()
        idx     = {r.module: r for r in registros}
        default = (rol == "administracion")
        self.permisos_rol_modulos = [
            {
                "module":    k,
                "label":     label,
                "can_read":  idx[k].can_read  if k in idx else default,
                "can_write": idx[k].can_write if k in idx else default,
            }
            for k, label in self._MODULOS
        ]

    async def toggle_permiso_rol(self, module: str, tipo: str):
        if not self.tiene_permiso("configuracion", write=True):
            return
        rol = self.permisos_rol_activo
        if not rol:
            return
        from clinica_app.models.user import PermisoRol, RoleEnum
        from sqlmodel import select

        async with get_async_session() as session:
            p = (
                await session.execute(
                    select(PermisoRol).where(
                        PermisoRol.clinica_id == self.clinica_id,
                        PermisoRol.role   == RoleEnum(rol),
                        PermisoRol.module == module,
                    )
                )
            ).scalars().first()
            if p is None:
                p = PermisoRol(
                    clinica_id=self.clinica_id,
                    role=RoleEnum(rol), module=module,
                    can_read=(rol == "administracion"),
                    can_write=(rol == "administracion"),
                )
                session.add(p)
                await session.flush()
            if tipo == "read":
                p.can_read  = not p.can_read
                nuevo_valor = p.can_read
            else:
                p.can_write = not p.can_write
                nuevo_valor = p.can_write
            await session.flush()
            from clinica_app.services import auditoria
            await auditoria.registrar(
                session, self.clinica_id,
                usuario_id=self.user_id,
                accion="cambiar_permisos", entidad="permiso_rol", entidad_id=p.id,
                detalle={"rol": rol, "modulo": module, "tipo": tipo, "valor": nuevo_valor},
            )
        await self._cargar_permisos_rol()

    async def _cargar_permisos(self):
        from clinica_app.models.user import PermisoRol
        from sqlmodel import select

        async with get_async_session() as session:
            registros = (
                await session.execute(
                    select(PermisoRol).where(PermisoRol.clinica_id == self.clinica_id)
                )
            ).scalars().all()
        idx = {(r.role.value, r.module): r for r in registros}
        matrix = []
        for mod_key, mod_label in self._MODULOS:
            row: dict = {"module": mod_key, "module_label": mod_label}
            for role in self._ROLES:
                p = idx.get((role, mod_key))
                row[f"{role}_read"]  = p.can_read  if p else (role == "administracion")
                row[f"{role}_write"] = p.can_write if p else (role == "administracion")
            matrix.append(row)
        self.permisos_matrix = matrix

    async def toggle_permiso(self, module: str, role: str, tipo: str):
        if not self.tiene_permiso("configuracion", write=True):
            return
        from clinica_app.models.user import PermisoRol, RoleEnum
        from sqlmodel import select

        async with get_async_session() as session:
            p = (
                await session.execute(
                    select(PermisoRol).where(
                        PermisoRol.clinica_id == self.clinica_id,
                        PermisoRol.role   == RoleEnum(role),
                        PermisoRol.module == module,
                    )
                )
            ).scalars().first()
            if p is None:
                p = PermisoRol(
                    clinica_id=self.clinica_id,
                    role=RoleEnum(role), module=module,
                    can_read=True, can_write=(role == "administracion"),
                )
                session.add(p)
                await session.flush()
            if tipo == "read":
                p.can_read  = not p.can_read
            else:
                p.can_write = not p.can_write
        await self._cargar_permisos()

    # ── Atajos de teclado ──────────────────────────────────────────────────────

    async def handle_modal_sede_key(self, key: str):
        if key == "Escape":
            self.cerrar_modal_sede()
        elif key == "Enter" and self.modal_sede and not self.is_saving_sede:
            async for s in self.guardar_sede():
                yield s

    async def handle_modal_usuario_key(self, key: str):
        if key == "Escape":
            self.cerrar_modal_usuario()
        elif key == "Enter" and self.modal_usuario and not self.is_saving_usuario:
            async for s in self.guardar_usuario():
                yield s

    async def handle_modal_password_key(self, key: str):
        if key == "Escape":
            self.cerrar_modal_password()
        elif key == "Enter" and self.modal_password and not self.is_saving_pw:
            async for s in self.guardar_password():
                yield s

    async def handle_modal_impuesto_key(self, key: str):
        if key == "Escape":
            self.cerrar_modal_impuesto()
        elif key == "Enter" and self.modal_impuesto and not self.is_saving_it:
            async for s in self.guardar_impuesto():
                yield s

    def handle_modal_permisos_key(self, key: str):
        if key == "Escape":
            self.cerrar_modal_permisos()

    _MODULOS = [
        ("dashboard",     "Panel"),
        ("pacientes",     "Pacientes"),
        ("historia",      "Historia Clínica"),
        ("profesionales", "Profesionales"),
        ("calendario",    "Calendario"),
        ("turnos",        "Turnos"),
        ("servicios",     "Servicios"),
        ("cobro",         "Cobro / POS"),
        ("caja",          "Caja"),
        ("cuentas",       "Cuentas Ctes."),
        ("compras",       "Compras"),
        ("inventario",    "Inventario"),
        ("promociones",   "Promociones"),
        ("reportes",      "Reportes"),
        ("configuracion", "Configuración"),
    ]
    _ROLES = ["administracion", "recepcionista", "profesional", "contador"]
