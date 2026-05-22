from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select as sa_select
from sqlmodel import Session, select

from clinica_app.models.login_intento import LoginIntento
from clinica_app.models.user import User
from clinica_app.services.exceptions import ServiceError


def _registrar_intento_fallido(email: str) -> None:
    """Guarda un intento fallido en una sesión independiente (nunca hace rollback)."""
    from clinica_app.database import get_session
    try:
        with get_session() as s:
            s.add(LoginIntento(email=email))
    except Exception:
        pass  # No debe bloquear el flujo de auth


def autenticar(session: Session, email: str, password: str) -> User:
    """
    Valida credenciales y devuelve el User.
    - Aplica rate limiting persistente (LOGIN_MAX_ATTEMPTS / LOGIN_WINDOW_SECS).
    - Siempre lanza ServiceError con mensaje genérico para prevenir user-enumeration.
    """
    from clinica_app.config import LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECS

    email = email.strip().lower()

    # ── Rate limiting ─────────────────────────────────────────────────────────
    ventana = datetime.now(timezone.utc) - timedelta(seconds=LOGIN_WINDOW_SECS)
    # Comparar sin timezone porque MySQL almacena DATETIME sin tz
    ventana_naive = ventana.replace(tzinfo=None)

    intentos_recientes: int = session.execute(
        sa_select(func.count(LoginIntento.id)).where(
            LoginIntento.email == email,
            LoginIntento.created_at >= ventana_naive,
        )
    ).scalar_one()

    if intentos_recientes >= LOGIN_MAX_ATTEMPTS:
        mins = max(1, LOGIN_WINDOW_SECS // 60)
        raise ServiceError(
            f"Demasiados intentos fallidos. Espere {mins} min. e intente de nuevo.",
            429,
        )

    # ── Validación de credenciales ────────────────────────────────────────────
    user: User | None = session.exec(
        select(User).where(User.email == email)
    ).first()

    if not user or not user.check_password(password) or not user.is_active:
        _registrar_intento_fallido(email)
        raise ServiceError("Credenciales inválidas", 401)

    return user


def datos_usuario(user: User) -> dict[str, Any]:
    return {
        "id":         user.id,
        "nombre":     user.nombre,
        "email":      user.email,
        "rol":        user.rol.value,
        "clinica_id": user.clinica_id,
    }
