from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services.auth import autenticar, datos_usuario, sedes_para_usuario
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class AuthState(BaseState):
    """Gestiona el formulario de login y la autenticación."""

    error_msg:  str  = ""
    is_loading: bool = False

    # Selector de sucursal post-login / cambio en sesión
    sedes_disponibles:    list[dict] = []
    mostrar_selector_sede: bool      = False

    @rx.var
    def tiene_multiples_sedes(self) -> bool:
        return len(self.sedes_disponibles) > 1

    # ── Login ──────────────────────────────────────────────────────────────────

    async def handle_login(self, form_data: dict):
        self.is_loading = True
        self.error_msg  = ""
        yield

        email    = (form_data.get("email") or "").strip().lower()
        password = form_data.get("password") or ""

        if not email or not password:
            self.error_msg  = "Ingresa email y contraseña"
            self.is_loading = False
            return

        try:
            async with get_async_session() as session:
                user  = await autenticar(session, email, password)
                datos = datos_usuario(user)
                is_admin = (datos["rol"] == "administracion")
                sedes = await sedes_para_usuario(
                    session, datos["clinica_id"], datos["id"], is_admin
                )
        except ServiceError as exc:
            self.error_msg  = str(exc)
            self.is_loading = False
            return

        # Poblar BaseState — tenant resuelto desde la DB, nunca desde el cliente
        self.user_id          = datos["id"]
        self.clinica_id       = datos["clinica_id"]
        self.user_email       = datos["email"]
        self.user_nombre      = datos["nombre"]
        self.user_role        = datos["rol"]
        self.profesional_id   = datos["profesional_id"]
        self.is_authenticated = True
        self.is_loading       = False
        self.sedes_disponibles = sedes

        if len(sedes) == 1:
            # Auto-selección cuando hay una sola sede
            self.sede_actual_id     = sedes[0]["id"]
            self.sede_actual_nombre = sedes[0]["nombre"]
            yield rx.redirect("/")
        elif len(sedes) == 0:
            # Sin sedes configuradas — entrar sin filtro de sede
            self.sede_actual_id     = 0
            self.sede_actual_nombre = "Sin sucursal"
            yield rx.redirect("/")
        else:
            # Múltiples sedes — redirigir al dashboard donde el modal vive dentro del shell()
            self.mostrar_selector_sede = True
            yield rx.redirect("/")

    def seleccionar_sede(self, sede_id: int):
        try:
            sede_id_int = int(sede_id)
        except (TypeError, ValueError):
            return
        sede = next((s for s in self.sedes_disponibles if int(s["id"]) == sede_id_int), None)
        if not sede:
            return
        self.sede_actual_id        = sede["id"]
        self.sede_actual_nombre    = sede["nombre"]
        self.mostrar_selector_sede = False
        # Recargar la página para que el estado del módulo activo consulte
        # los datos de la nueva sede (re-ejecuta on_mount).
        return rx.call_script("window.location.reload()")

    # ── Cambio de sucursal en sesión ───────────────────────────────────────────

    async def abrir_selector_sede(self):
        """Recarga las sedes disponibles y muestra el modal selector."""
        is_admin = (self.user_role == "administracion")
        async with get_async_session() as session:
            sedes = await sedes_para_usuario(
                session, self.clinica_id, self.user_id, is_admin
            )
        self.sedes_disponibles    = sedes
        self.mostrar_selector_sede = True

    # ── Logout ─────────────────────────────────────────────────────────────────

    def handle_logout(self):
        return self.logout()
