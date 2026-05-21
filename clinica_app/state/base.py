from __future__ import annotations

import reflex as rx


class BaseState(rx.State):
    """
    Raíz del árbol de estados.
    Contiene la sesión autenticada y el contexto de tenant (clinica_id).

    SEGURIDAD: clinica_id nunca se expone al cliente — vive exclusivamente
    en el servidor Python de Reflex y se propaga a todos los SubStates.
    """

    user_id:    int  = 0
    clinica_id: int  = 0   # ← eje central del multi-tenant
    user_email: str  = ""
    user_nombre: str = ""
    user_role:  str  = ""  # RoleEnum.value: "administracion" | "recepcionista" | ...
    is_authenticated: bool = False

    # ── Computed vars (derivados, read-only en el cliente) ─────────────────────

    @rx.var
    def is_admin(self) -> bool:
        return self.user_role == "administracion"

    @rx.var
    def is_staff(self) -> bool:
        return self.user_role in ("administracion", "recepcionista")

    @rx.var
    def is_profesional(self) -> bool:
        return self.user_role == "profesional"

    @rx.var
    def rol_display(self) -> str:
        mapping = {
            "administracion": "Administrador",
            "recepcionista":  "Recepcionista",
            "profesional":    "Profesional",
            "contador":       "Contador",
        }
        return mapping.get(self.user_role, self.user_role)

    # ── Guards ─────────────────────────────────────────────────────────────────

    def require_auth(self):
        """Redirige al login si el usuario no está autenticado."""
        if not self.is_authenticated:
            return rx.redirect("/login")

    def require_admin(self):
        """Redirige si el usuario no tiene rol de admin."""
        if not self.is_admin:
            return rx.redirect("/")

    # ── Logout ─────────────────────────────────────────────────────────────────

    def logout(self):
        self.reset()
        return rx.redirect("/login")
