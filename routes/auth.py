"""
routes/auth.py — Autenticación JWT

Endpoints:
    POST /api/auth/login    — Iniciar sesión (rate limited: 5/min por IP)
    POST /api/auth/refresh  — Renovar access token con refresh token
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, current_app, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    jwt_required,
)

from extensions import limiter
from models.user import User
from schemas.auth import LoginSchema
from utils.audit import log_action

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
login_schema = LoginSchema()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _compute_expires(delta: Any) -> str | None:
    """
    Calcula la fecha de expiración ISO 8601 para un timedelta dado.
    Retorna None si el delta es inválido o None.
    """
    if not delta:
        return None
    try:
        return (datetime.now(timezone.utc) + delta).isoformat()
    except (TypeError, AttributeError):
        return None


def _build_token_pair(user: User) -> dict[str, Any]:
    """
    Genera un par access/refresh token para el usuario dado y arma el payload
    de respuesta estándar.
    """
    claims: dict[str, str] = {"role": user.rol.value, "name": user.nombre}
    access_token: str = create_access_token(
        identity=str(user.id), additional_claims=claims
    )
    refresh_token: str = create_refresh_token(
        identity=str(user.id), additional_claims=claims
    )
    cfg = current_app.config
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": _compute_expires(cfg.get("JWT_ACCESS_TOKEN_EXPIRES")),
        "refresh_expires_at": _compute_expires(cfg.get("JWT_REFRESH_TOKEN_EXPIRES")),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@bp.post("/login")
@limiter.limit("5 per minute")  # Protección contra fuerza bruta por IP
def login() -> tuple[dict[str, Any], int]:
    """
    Autentica al usuario con email/password y devuelve el par de tokens.

    Rate limiting: máximo 5 intentos por minuto por IP.
    Anti User-Enumeration: siempre devuelve el mismo mensaje genérico en caso
    de fallo, sin revelar si el email existe o no.
    """
    data: dict[str, Any] = login_schema.load(request.json or {})

    # Consulta única — no revelamos si el email existe o no
    user: User | None = User.query.filter_by(email=data["email"]).first()

    # Validación unificada: devolvemos el MISMO mensaje para email no existente,
    # password incorrecta y cuenta inactiva → previene User Enumeration
    if not user or not user.check_password(data["password"]) or not user.activo:
        return {"message": "Credenciales inválidas"}, 401

    log_action(user.id, "login", f"Usuario {user.email} inició sesión")

    payload = _build_token_pair(user)
    payload["user"] = {
        "id": user.id,
        "nombre": user.nombre,
        "rol": user.rol.value,
    }
    return payload, 200


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh() -> tuple[dict[str, Any], int]:
    """
    Renueva el access token usando un refresh token válido.
    También rota el refresh token (refresh token rotation).
    """
    claims: dict[str, Any] = get_jwt() or {}
    raw_identity: Any = claims.get("sub")

    # Convertir identidad a int de forma segura
    try:
        user_id: int | None = int(raw_identity)
    except (TypeError, ValueError):
        return {"message": "Token inválido"}, 401

    user: User | None = User.query.get(user_id)

    # Anti User-Enumeration: mismo mensaje para usuario inexistente e inactivo
    if not user or not user.activo:
        return {"message": "Credenciales inválidas"}, 401

    return _build_token_pair(user), 200
