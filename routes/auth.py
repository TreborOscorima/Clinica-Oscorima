from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token
from extensions import db
from models.user import User, RoleEnum
from schemas.auth import LoginSchema
from utils.audit import log_action

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
login_schema = LoginSchema()

@bp.post("/login")
def login():
    data = login_schema.load(request.json or {})
    user = User.query.filter_by(email=data["email"]).first()
    if not user or not user.check_password(data["password"]) or not user.activo:
        return {"message": "Credenciales inválidas"}, 401
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.rol.value, "name": user.nombre})
    log_action(user.id, "login", f"Usuario {user.email} inició sesión")
    return {"access_token": token, "user": {"id": user.id, "nombre": user.nombre, "rol": user.rol.value}}
