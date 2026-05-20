from __future__ import annotations

from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select

from extensions import db
from models.user import User, RoleEnum, PermisoRol
from schemas.user import UserSchema, PermisoRolSchema
from utils.decorators import role_required
from utils.tenant import get_current_clinica_id

bp = Blueprint("configuracion", __name__, url_prefix="/api/config")

user_schema = UserSchema()
user_many = UserSchema(many=True)
perm_schema = PermisoRolSchema()
perm_many = PermisoRolSchema(many=True)

MANAGED_MODULES = [
    {"key": "dashboard", "label": "Dashboard"},
    {"key": "pacientes", "label": "Pacientes"},
    {"key": "turnos", "label": "Turnos"},
    {"key": "servicios", "label": "Servicios"},
    {"key": "profesionales", "label": "Profesionales"},
    {"key": "inventario", "label": "Inventario"},
    {"key": "caja", "label": "Caja"},
    {"key": "reportes", "label": "Reportes"},
    {"key": "config", "label": "Configuración"},
]


def _ensure_permissions() -> None:
    with db.engine.begin() as conn:
        PermisoRol.__table__.create(conn, checkfirst=True)

    created = False
    for role in RoleEnum:
        for module in MANAGED_MODULES:
            exists = db.session.execute(
                select(PermisoRol).where(
                    PermisoRol.role == role,
                    PermisoRol.module == module["key"],
                )
            ).scalar_one_or_none()
            if not exists:
                db.session.add(
                    PermisoRol(
                        role=role,
                        module=module["key"],
                        can_read=True,
                        can_write=role == RoleEnum.ADMIN,
                    )
                )
                created = True
    if created:
        db.session.commit()


@bp.get("/users")
@jwt_required()
@role_required("administracion")
def listar_usuarios():
    clinica_id = get_current_clinica_id()
    usuarios = db.session.execute(
        select(User)
        .where(User.clinica_id == clinica_id)
        .order_by(User.created_at.desc())
    ).scalars().all()
    return {
        "data": user_many.dump(usuarios),
        "roles": [role.value for role in RoleEnum],
    }


@bp.post("/users")
@jwt_required()
@role_required("administracion")
def crear_usuario():
    payload = request.get_json(silent=True) or {}
    clinica_id = get_current_clinica_id()
    email = (payload.get("email") or "").strip().lower()
    nombre = (payload.get("nombre") or "").strip()
    rol_raw = payload.get("rol") or ""
    password = payload.get("password") or ""

    if not email or not nombre or not rol_raw or not password:
        return {"message": "email, nombre, rol y password son requeridos"}, 400
    if db.session.execute(select(User).where(User.email == email)).scalar_one_or_none():
        return {"message": "Email ya registrado"}, 409

    try:
        rol_enum = RoleEnum(rol_raw)
    except ValueError:
        return {"message": "Rol inválido"}, 400

    usuario = User(
        clinica_id=clinica_id,
        email=email,
        nombre=nombre,
        rol=rol_enum,
        is_active=bool(payload.get("activo", True)),
    )
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()

    return user_schema.dump(usuario), 201


@bp.put("/users/<int:uid>")
@jwt_required()
@role_required("administracion")
def actualizar_usuario(uid: int):
    usuario = db.session.execute(
        select(User).where(User.id == uid, User.clinica_id == get_current_clinica_id())
    ).scalar_one_or_none()
    if not usuario:
        abort(404)

    payload = request.get_json(silent=True) or {}

    nombre = payload.get("nombre")
    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            return {"message": "Nombre inválido"}, 400
        usuario.nombre = nombre

    rol_raw = payload.get("rol")
    if rol_raw is not None:
        try:
            usuario.rol = RoleEnum(rol_raw)
        except ValueError:
            return {"message": "Rol inválido"}, 400

    if "activo" in payload:
        usuario.is_active = bool(payload.get("activo"))

    password = payload.get("password")
    if password:
        usuario.set_password(password)

    db.session.commit()
    return user_schema.dump(usuario)


@bp.get("/permissions")
@jwt_required()
@role_required("administracion")
def listar_permisos():
    _ensure_permissions()
    permisos = db.session.execute(
        select(PermisoRol).order_by(PermisoRol.role.asc(), PermisoRol.module.asc())
    ).scalars().all()
    return {
        "data": perm_many.dump(permisos),
        "modules": MANAGED_MODULES,
        "roles": [role.value for role in RoleEnum],
    }


@bp.put("/permissions/<int:pid>")
@jwt_required()
@role_required("administracion")
def actualizar_permiso(pid: int):
    permiso = db.session.get(PermisoRol, pid)
    if not permiso:
        abort(404)

    payload = request.get_json(silent=True) or {}

    if "can_read" in payload:
        permiso.can_read = bool(payload.get("can_read"))
    if "can_write" in payload:
        permiso.can_write = bool(payload.get("can_write"))
        if permiso.can_write:
            permiso.can_read = True

    db.session.commit()
    return perm_schema.dump(permiso)
