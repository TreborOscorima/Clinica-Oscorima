from datetime import datetime, timezone

from flask import Blueprint, current_app, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    jwt_required,
)
from models.user import User
from schemas.auth import LoginSchema
from utils.audit import log_action

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
login_schema = LoginSchema()


def _compute_expires(delta):
    if not delta:
        return None
    now = datetime.now(timezone.utc)
    try:
        return (now + delta).isoformat()
    except TypeError:
        return None


@bp.post("/login")
def login():
    data = login_schema.load(request.json or {})
    user = User.query.filter_by(email=data["email"]).first()
    if not user or not user.check_password(data["password"]) or not user.activo:
        return {"message": "Credenciales invalidas"}, 401
    claims = {"role": user.rol.value, "name": user.nombre}
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)
    log_action(user.id, "login", f"Usuario {user.email} inicio sesion")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": _compute_expires(current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")),
        "refresh_expires_at": _compute_expires(current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES")),
        "user": {"id": user.id, "nombre": user.nombre, "rol": user.rol.value},
    }


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    claims = get_jwt() or {}
    identity = claims.get("sub")

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        user_id = identity

    user = User.query.get(user_id) if user_id is not None else None
    if not user or not user.activo:
        return {"message": "Usuario no autorizado"}, 401

    new_claims = {"role": user.rol.value, "name": user.nombre}
    access_token = create_access_token(identity=str(user.id), additional_claims=new_claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=new_claims)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": _compute_expires(current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")),
        "refresh_expires_at": _compute_expires(current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES")),
    }
