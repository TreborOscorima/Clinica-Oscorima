from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete as sa_delete, func, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.login_intento import LoginIntento
from clinica_app.models.user import User
from clinica_app.services.exceptions import ServiceError


async def _registrar_intento_fallido(email: str) -> None:
    """Guarda un intento fallido en una sesión independiente (nunca hace rollback)."""
    from clinica_app.database import get_async_session
    try:
        async with get_async_session() as s:
            s.add(LoginIntento(email=email))
    except Exception:
        pass


async def _purgar_intentos_antiguos() -> None:
    """Elimina registros > 24h en sesión independiente. No bloquea auth si falla."""
    from clinica_app.database import get_async_session
    try:
        limite = (datetime.now(timezone.utc) - timedelta(hours=24)).replace(tzinfo=None)
        async with get_async_session() as s:
            await s.execute(
                sa_delete(LoginIntento).where(LoginIntento.created_at < limite)
            )
    except Exception:
        pass


async def autenticar(session: AsyncSession, email: str, password: str) -> User:
    """
    Valida credenciales y devuelve el User.
    - Aplica rate limiting persistente (LOGIN_MAX_ATTEMPTS / LOGIN_WINDOW_SECS).
    - Siempre lanza ServiceError con mensaje genérico para prevenir user-enumeration.
    """
    from clinica_app.config import LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECS

    email = email.strip().lower()

    # ── Purge oportunista: limpia registros > 24h ─────────────────────────────
    await _purgar_intentos_antiguos()

    # ── Rate limiting ─────────────────────────────────────────────────────────
    ventana = datetime.now(timezone.utc) - timedelta(seconds=LOGIN_WINDOW_SECS)
    # Comparar sin timezone porque MySQL almacena DATETIME sin tz
    ventana_naive = ventana.replace(tzinfo=None)

    intentos_recientes: int = (await session.execute(
        sa_select(func.count(LoginIntento.id)).where(
            LoginIntento.email == email,
            LoginIntento.created_at >= ventana_naive,
        )
    )).scalar_one()

    if intentos_recientes >= LOGIN_MAX_ATTEMPTS:
        mins = max(1, LOGIN_WINDOW_SECS // 60)
        raise ServiceError(
            f"Demasiados intentos fallidos. Espere {mins} min. e intente de nuevo.",
            429,
        )

    # ── Validación de credenciales ────────────────────────────────────────────
    user: User | None = (await session.execute(
        select(User).where(User.email == email)
    )).scalars().first()

    if not user or not user.is_active:
        await _registrar_intento_fallido(email)
        raise ServiceError("Credenciales inválidas", 401)

    # Wrap bcrypt in a thread to avoid blocking the event loop
    password_ok = await asyncio.to_thread(user.check_password, password)

    if not password_ok:
        await _registrar_intento_fallido(email)
        raise ServiceError("Credenciales inválidas", 401)

    return user


async def sedes_para_usuario(
    session: AsyncSession,
    clinica_id: int,
    user_id: int,
    is_admin: bool,
) -> list[dict[str, Any]]:
    """
    Devuelve las sedes accesibles para un usuario.
    - Admin: todas las sedes activas de la clínica.
    - Otros: solo las sedes asignadas en usuario_sedes.
      Si no tiene ninguna asignada, retorna la sede principal.
    """
    from clinica_app.services.sedes import listar as _listar_sedes
    from clinica_app.models.user import UsuarioSede

    todas = await _listar_sedes(session, clinica_id)

    if is_admin:
        return todas

    asignadas = (await session.execute(
        select(UsuarioSede).where(UsuarioSede.user_id == user_id)
    )).scalars().all()

    if not asignadas:
        # Sin asignaciones explícitas: solo la sede principal
        principal = next((s for s in todas if s["es_principal"]), None)
        return [principal] if principal else todas[:1]

    ids = {a.sede_id for a in asignadas}
    return [s for s in todas if s["id"] in ids]


def datos_usuario(user: User) -> dict[str, Any]:
    return {
        "id":             user.id,
        "nombre":         user.nombre,
        "email":          user.email,
        "rol":            user.rol.value,
        "clinica_id":     user.clinica_id,
        "profesional_id": user.profesional_id or 0,
    }
