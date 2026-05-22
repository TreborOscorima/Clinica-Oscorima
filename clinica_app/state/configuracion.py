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

    # ── Permisos por módulo ────────────────────────────────────────────────────
    # Lista de dicts con keys: module, module_label,
    # administracion_read, administracion_write, recepcionista_read, ...
    permisos_matrix: list[dict] = []

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
        if tab == "permisos":
            return self._cargar_permisos()

    # ── Setters de formulario (Reflex 0.9.x no auto-genera setters en sub-states)
    def set_form_nombre(self, v: str):           self.form_nombre = v
    def set_form_razon_social(self, v: str):     self.form_razon_social = v
    def set_form_documento_fiscal(self, v: str): self.form_documento_fiscal = v
    def set_form_email_clinica(self, v: str):    self.form_email_clinica = v
    def set_form_telefono(self, v: str):         self.form_telefono = v
    def set_form_u_nombre(self, v: str):         self.form_u_nombre = v
    def set_form_u_email(self, v: str):          self.form_u_email = v
    def set_form_u_rol(self, v: str):            self.form_u_rol = v
    def set_form_u_password(self, v: str):       self.form_u_password = v
    def set_form_u_password2(self, v: str):      self.form_u_password2 = v
    def set_form_pw_nueva(self, v: str):         self.form_pw_nueva = v
    def set_form_pw_nueva2(self, v: str):        self.form_pw_nueva2 = v

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
        self._recargar_usuarios()

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

    # ── Permisos ────────────────────────────────────────────────────────────────

    _MODULOS = [
        ("pacientes",     "Pacientes"),
        ("turnos",        "Turnos"),
        ("cobro",         "Cobro / POS"),
        ("inventario",    "Inventario"),
        ("compras",       "Compras"),
        ("cuentas",       "Cuentas"),
        ("reportes",      "Reportes"),
        ("configuracion", "Configuración"),
    ]
    _ROLES = ["administracion", "recepcionista", "profesional", "contador"]

    def _cargar_permisos(self):
        from clinica_app.models.user import PermisoRol, RoleEnum
        from sqlmodel import select

        with get_session() as session:
            registros = session.exec(select(PermisoRol)).all()

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

    def toggle_permiso(self, module: str, role: str, tipo: str):
        from clinica_app.models.user import PermisoRol, RoleEnum
        from sqlmodel import select

        with get_session() as session:
            p = session.exec(
                select(PermisoRol).where(
                    PermisoRol.role == RoleEnum(role),
                    PermisoRol.module == module,
                )
            ).first()
            if p is None:
                p = PermisoRol(
                    role=RoleEnum(role),
                    module=module,
                    can_read=True,
                    can_write=(role == "administracion"),
                )
                session.add(p)
                session.flush()
            if tipo == "read":
                p.can_read = not p.can_read
            else:
                p.can_write = not p.can_write
        return self._cargar_permisos()
