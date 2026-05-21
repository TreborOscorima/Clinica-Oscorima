from __future__ import annotations

import reflex as rx

from clinica_app.database import get_session
from clinica_app.services import configuracion as svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class ConfiguracionState(BaseState):
    """
    Estado del módulo Configuración.
    Solo accesible para administradores (require_admin en on_mount).
    """

    # ── Tab activo ─────────────────────────────────────────────────────────────
    tab_activo: str = "clinica"   # "clinica" | "usuarios"

    # ── Formulario de datos de la clínica ──────────────────────────────────────
    form_nombre:           str  = ""
    form_razon_social:     str  = ""
    form_documento_fiscal: str  = ""
    form_email_clinica:    str  = ""
    form_telefono:         str  = ""
    clinica_error:         str  = ""
    clinica_success:       str  = ""
    is_saving_clinica:     bool = False

    # ── Lista de usuarios ──────────────────────────────────────────────────────
    usuarios: list[dict] = []

    # ── Modal: crear usuario ───────────────────────────────────────────────────
    modal_usuario:     bool = False
    form_u_nombre:     str  = ""
    form_u_email:      str  = ""
    form_u_rol:        str  = "recepcionista"
    form_u_password:   str  = ""
    form_u_password2:  str  = ""
    form_u_error:      str  = ""
    is_saving_usuario: bool = False

    # ── Modal: cambiar contraseña ──────────────────────────────────────────────
    modal_password:    bool = False
    pw_user_id:        int  = 0
    pw_user_nombre:    str  = ""
    form_pw_nueva:     str  = ""
    form_pw_nueva2:    str  = ""
    form_pw_error:     str  = ""
    form_pw_success:   str  = ""
    is_saving_pw:      bool = False

    # ── Carga ─────────────────────────────────────────────────────────────────

    def on_mount(self):
        return self.require_auth() or self.require_admin() or self._cargar()

    def _cargar(self):
        with get_session() as session:
            clinica  = svc.obtener_clinica(session, self.clinica_id)
            usuarios = svc.listar_usuarios(session, self.clinica_id)

        self.form_nombre           = clinica["nombre"]
        self.form_razon_social     = clinica["razon_social"]
        self.form_documento_fiscal = clinica["documento_fiscal"]
        self.form_email_clinica    = clinica["email"]
        self.form_telefono         = clinica["telefono"]
        self.usuarios              = usuarios
        self.clinica_error         = ""
        self.clinica_success       = ""

    def set_tab(self, tab: str):
        self.tab_activo = tab

    # ── Guardar datos de la clínica ────────────────────────────────────────────

    async def guardar_clinica(self):
        self.is_saving_clinica = True
        self.clinica_error     = ""
        self.clinica_success   = ""
        yield

        payload = {
            "nombre":           self.form_nombre.strip(),
            "razon_social":     self.form_razon_social.strip() or None,
            "documento_fiscal": self.form_documento_fiscal.strip() or None,
            "email":            self.form_email_clinica.strip() or None,
            "telefono":         self.form_telefono.strip() or None,
        }

        try:
            with get_session() as session:
                svc.actualizar_clinica(session, self.clinica_id, payload)
        except ServiceError as exc:
            self.clinica_error     = str(exc)
            self.is_saving_clinica = False
            return

        self.is_saving_clinica = False
        self.clinica_success   = "Datos actualizados correctamente"

    # ── Crear usuario ──────────────────────────────────────────────────────────

    def abrir_modal_usuario(self):
        self.form_u_nombre    = ""
        self.form_u_email     = ""
        self.form_u_rol       = "recepcionista"
        self.form_u_password  = ""
        self.form_u_password2 = ""
        self.form_u_error     = ""
        self.modal_usuario    = True

    def cerrar_modal_usuario(self):
        self.modal_usuario = False

    async def guardar_usuario(self):
        self.is_saving_usuario = True
        self.form_u_error      = ""
        yield

        if self.form_u_password != self.form_u_password2:
            self.form_u_error      = "Las contraseñas no coinciden"
            self.is_saving_usuario = False
            return

        try:
            with get_session() as session:
                svc.crear_usuario(
                    session,
                    self.clinica_id,
                    {
                        "nombre":   self.form_u_nombre,
                        "email":    self.form_u_email,
                        "rol":      self.form_u_rol,
                        "password": self.form_u_password,
                    },
                )
        except ServiceError as exc:
            self.form_u_error      = str(exc)
            self.is_saving_usuario = False
            return

        self.is_saving_usuario = False
        self.modal_usuario     = False
        return self._recargar_usuarios()

    # ── Cambiar contraseña ─────────────────────────────────────────────────────

    def abrir_modal_password(self, usuario: dict):
        self.pw_user_id     = usuario.get("id") or 0
        self.pw_user_nombre = usuario.get("nombre") or ""
        self.form_pw_nueva  = ""
        self.form_pw_nueva2 = ""
        self.form_pw_error  = ""
        self.form_pw_success = ""
        self.modal_password = True

    def cerrar_modal_password(self):
        self.modal_password = False

    async def guardar_password(self):
        self.is_saving_pw    = True
        self.form_pw_error   = ""
        self.form_pw_success = ""
        yield

        if self.form_pw_nueva != self.form_pw_nueva2:
            self.form_pw_error = "Las contraseñas no coinciden"
            self.is_saving_pw  = False
            return

        try:
            with get_session() as session:
                svc.cambiar_password(
                    session, self.clinica_id, self.pw_user_id, self.form_pw_nueva
                )
        except ServiceError as exc:
            self.form_pw_error = str(exc)
            self.is_saving_pw  = False
            return

        self.is_saving_pw    = False
        self.form_pw_success = "Contraseña actualizada"

    # ── Activar / desactivar usuario ──────────────────────────────────────────

    def toggle_activo_usuario(self, user_id: int):
        try:
            with get_session() as session:
                svc.toggle_activo(session, self.clinica_id, user_id, self.user_id)
        except ServiceError:
            pass
        return self._recargar_usuarios()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _recargar_usuarios(self):
        with get_session() as session:
            self.usuarios = svc.listar_usuarios(session, self.clinica_id)
