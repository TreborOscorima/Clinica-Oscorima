from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from clinica_app.models.clinica import Clinica
from clinica_app.models.user import RoleEnum, User
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


# ── Clínica ────────────────────────────────────────────────────────────────────

_CAMPOS_CLINICA = ("nombre", "razon_social", "documento_fiscal", "email", "telefono")


def _dump_clinica(c: Clinica) -> dict[str, Any]:
    return {
        "id":               c.id,
        "nombre":           c.nombre,
        "slug":             c.slug,
        "razon_social":     c.razon_social or "",
        "documento_fiscal": c.documento_fiscal or "",
        "email":            c.email or "",
        "telefono":         c.telefono or "",
    }


def obtener_clinica(session: Session, clinica_id: int) -> dict[str, Any]:
    c = session.get(Clinica, clinica_id)
    if c is None or not c.is_active:
        raise NotFoundError("Clínica no encontrada")
    return _dump_clinica(c)


def actualizar_clinica(session: Session, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    c = session.get(Clinica, clinica_id)
    if c is None or not c.is_active:
        raise NotFoundError("Clínica no encontrada")
    if not (payload.get("nombre") or "").strip():
        raise ServiceError("El nombre de la clínica es obligatorio")
    for campo in _CAMPOS_CLINICA:
        if campo in payload:
            val = payload[campo]
            setattr(c, campo, val.strip() if isinstance(val, str) else val)
    session.flush()
    return _dump_clinica(c)


# ── Usuarios ───────────────────────────────────────────────────────────────────

_ROL_LABELS: dict[str, str] = {
    "administracion": "Administrador",
    "recepcionista":  "Recepcionista",
    "profesional":    "Profesional",
    "contador":       "Contador",
}


def _dump_user(u: User) -> dict[str, Any]:
    return {
        "id":         u.id,
        "nombre":     u.nombre,
        "email":      u.email,
        "rol":        u.rol.value,
        "rol_label":  _ROL_LABELS.get(u.rol.value, u.rol.value),
        "is_active":  u.is_active,
        "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
    }


def listar_usuarios(session: Session, clinica_id: int) -> list[dict[str, Any]]:
    users = session.exec(
        select(User)
        .where(User.clinica_id == clinica_id)
        .order_by(User.nombre.asc())
    ).all()
    return [_dump_user(u) for u in users]


def crear_usuario(session: Session, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    nombre   = (payload.get("nombre") or "").strip()
    email    = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "")
    rol_str  = (payload.get("rol") or RoleEnum.RECEP.value)

    if not nombre:
        raise ServiceError("Nombre obligatorio")
    if not email:
        raise ServiceError("Email obligatorio")
    if len(password) < 6:
        raise ServiceError("La contraseña debe tener al menos 6 caracteres")
    try:
        rol = RoleEnum(rol_str)
    except ValueError as exc:
        raise ServiceError("Rol inválido") from exc

    if session.exec(select(User).where(User.email == email)).first():
        raise ConflictError("Email ya registrado en el sistema")

    u = User(clinica_id=clinica_id, nombre=nombre, email=email, rol=rol)
    u.set_password(password)
    session.add(u)
    session.flush()
    return _dump_user(u)


def cambiar_password(session: Session, clinica_id: int, user_id: int, nueva: str) -> None:
    if len(nueva) < 6:
        raise ServiceError("La contraseña debe tener al menos 6 caracteres")
    u = session.exec(
        select(User).where(User.id == user_id, User.clinica_id == clinica_id)
    ).first()
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    u.set_password(nueva)
    session.flush()


def toggle_activo(session: Session, clinica_id: int, user_id: int, solicitante_id: int) -> dict[str, Any]:
    if user_id == solicitante_id:
        raise ServiceError("No puedes desactivar tu propia cuenta")
    u = session.exec(
        select(User).where(User.id == user_id, User.clinica_id == clinica_id)
    ).first()
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    if u.is_active:
        u.soft_delete()
    else:
        u.is_active   = True
        u.deleted_at  = None
    session.flush()
    return _dump_user(u)
