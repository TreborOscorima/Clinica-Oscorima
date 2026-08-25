from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import auth as auth_svc
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState


class CuentaState(BaseState):
    """Autoservicio de cuenta del usuario (cambio de la propia contraseña).

    Disponible para cualquier usuario autenticado, sin requerir el permiso de
    configuración (que es administrativo).
    """

    form_actual:  str = ""
    form_nueva:   str = ""
    form_nueva2:  str = ""
    error:        str = ""
    success:      str = ""
    is_saving:    bool = False

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")

    def set_form_actual(self, v: str): self.form_actual = v
    def set_form_nueva(self, v: str):  self.form_nueva = v
    def set_form_nueva2(self, v: str): self.form_nueva2 = v

    def _limpiar(self):
        self.form_actual = ""
        self.form_nueva  = ""
        self.form_nueva2 = ""

    async def cambiar_password(self):
        self.error   = ""
        self.success = ""
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.form_actual or not self.form_nueva:
            self.error = "Completá todos los campos"
            return
        if self.form_nueva != self.form_nueva2:
            self.error = "Las contraseñas nuevas no coinciden"
            return

        self.is_saving = True
        yield
        try:
            async with get_async_session() as session:
                await auth_svc.cambiar_mi_password(
                    session, self.user_id, self.form_actual, self.form_nueva
                )
        except ServiceError as exc:
            self.error = str(exc)
            self.is_saving = False
            return
        except Exception:
            self.error = "No se pudo cambiar la contraseña. Intentá de nuevo."
            self.is_saving = False
            return

        self.is_saving = False
        self._limpiar()
        self.success = "Contraseña actualizada correctamente"

    def handle_key(self, key: str):
        if key == "Enter" and not self.is_saving:
            return CuentaState.cambiar_password
