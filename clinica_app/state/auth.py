from __future__ import annotations

import reflex as rx
import redis as redis_lib

from clinica_app.config import REDIS_URL, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECS
from clinica_app.database import get_session
from clinica_app.services.auth import autenticar, datos_usuario
from clinica_app.services.exceptions import ServiceError
from clinica_app.state.base import BaseState

_redis = redis_lib.from_url(REDIS_URL, decode_responses=True)


def _check_rate_limit(key: str) -> bool:
    """Retorna True si el intento está dentro del límite permitido."""
    pipe = _redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, LOGIN_WINDOW_SECS)
    count, _ = pipe.execute()
    return int(count) <= LOGIN_MAX_ATTEMPTS


class AuthState(BaseState):
    """Gestiona el formulario de login y la autenticación."""

    email:      str  = ""
    password:   str  = ""
    error_msg:  str  = ""
    is_loading: bool = False

    # ── Event handlers ─────────────────────────────────────────────────────────

    def set_email(self, value: str):
        self.email = value
        self.error_msg = ""

    def set_password(self, value: str):
        self.password = value
        self.error_msg = ""

    async def handle_login(self):
        self.is_loading = True
        self.error_msg  = ""
        yield

        # Rate limiting por IP
        ip = self.router.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()
        rate_key = f"login_attempts:{ip}"
        if not _check_rate_limit(rate_key):
            self.error_msg  = "Demasiados intentos. Espera 1 minuto."
            self.is_loading = False
            return

        email    = self.email.strip().lower()
        password = self.password

        if not email or not password:
            self.error_msg  = "Ingresa email y contraseña"
            self.is_loading = False
            return

        try:
            with get_session() as session:
                user = autenticar(session, email, password)
                datos = datos_usuario(user)
        except ServiceError as exc:
            self.error_msg  = str(exc)
            self.is_loading = False
            return

        # Poblar BaseState (tenant resuelto desde la DB, nunca desde el cliente)
        self.user_id         = datos["id"]
        self.clinica_id      = datos["clinica_id"]
        self.user_email      = datos["email"]
        self.user_nombre     = datos["nombre"]
        self.user_role       = datos["rol"]
        self.is_authenticated = True
        self.is_loading      = False

        # Limpiar formulario
        self.email    = ""
        self.password = ""

        yield rx.redirect("/")

    def handle_logout(self):
        return self.logout()
