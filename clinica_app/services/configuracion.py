from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from clinica_app.models.clinica import Clinica
from clinica_app.models.user import RoleEnum, User
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


# ── Clínica ────────────────────────────────────────────────────────────────────

_CAMPOS_CLINICA = (
    "nombre", "razon_social", "documento_fiscal", "email", "telefono",
    "direccion_fiscal", "zona_horaria", "rubro",
    "mensaje_recibo", "papel_impresion", "ancho_recibo",
    "margen_global", "mostrar_impuesto_recibo",
)


def _dump_clinica(c: Clinica) -> dict[str, Any]:
    return {
        "id":                      c.id,
        "nombre":                  c.nombre,
        "slug":                    c.slug,
        "razon_social":            c.razon_social            or "",
        "documento_fiscal":        c.documento_fiscal        or "",
        "email":                   c.email                   or "",
        "telefono":                c.telefono                or "",
        "direccion_fiscal":        c.direccion_fiscal        or "",
        "zona_horaria":            c.zona_horaria            or "",
        "rubro":                   c.rubro                   or "",
        "mensaje_recibo":          c.mensaje_recibo          or "",
        "papel_impresion":         c.papel_impresion         or "80mm",
        "ancho_recibo":            c.ancho_recibo,
        "margen_global":           float(c.margen_global)    if c.margen_global is not None else 50.0,
        "mostrar_impuesto_recibo": bool(c.mostrar_impuesto_recibo),
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
            if isinstance(val, str):
                val = val.strip() or None if campo not in ("nombre",) else val.strip()
            setattr(c, campo, val)
    session.flush()
    return _dump_clinica(c)


def guardar_margenes(session: Session, clinica_id: int, margen_global: float) -> dict[str, Any]:
    c = session.get(Clinica, clinica_id)
    if c is None or not c.is_active:
        raise NotFoundError("Clínica no encontrada")
    if margen_global < 0:
        raise ServiceError("El margen no puede ser negativo")
    c.margen_global = margen_global
    session.flush()
    return _dump_clinica(c)


def toggle_mostrar_impuesto(session: Session, clinica_id: int) -> bool:
    c = session.get(Clinica, clinica_id)
    if c is None or not c.is_active:
        raise NotFoundError("Clínica no encontrada")
    c.mostrar_impuesto_recibo = not c.mostrar_impuesto_recibo
    session.flush()
    return bool(c.mostrar_impuesto_recibo)


# ── Usuarios ───────────────────────────────────────────────────────────────────

_ROL_LABELS: dict[str, str] = {
    "administracion": "Administrador",
    "recepcionista":  "Recepcionista",
    "profesional":    "Profesional",
    "contador":       "Contador",
}

_SYSTEM_MODULES: list[tuple[str, str]] = [
    ("dashboard",     "Dashboard"),
    ("pacientes",     "Pacientes"),
    ("historia",      "Historia Clínica"),
    ("profesionales", "Profesionales"),
    ("calendario",    "Calendario"),
    ("turnos",        "Turnos"),
    ("servicios",     "Servicios"),
    ("cobro",         "Cobro / POS"),
    ("caja",          "Caja"),
    ("cuentas",       "Cuentas Ctes."),
    ("compras",       "Compras"),
    ("inventario",    "Inventario"),
    ("promociones",   "Promociones"),
    ("reportes",      "Reportes"),
    ("configuracion", "Configuración"),
]

_MODULE_LABELS: dict[str, str] = dict(_SYSTEM_MODULES)

_ACCESOS_ROL: dict[str, list[str]] = {
    "administracion": [k for k, _ in _SYSTEM_MODULES],
    "recepcionista":  ["dashboard", "pacientes", "historia", "calendario",
                       "turnos", "servicios", "cobro", "caja", "cuentas"],
    "profesional":    ["dashboard", "pacientes", "historia", "calendario", "turnos"],
    "contador":       ["dashboard", "caja", "cuentas", "compras", "inventario", "reportes"],
}


def _dump_user(u: User) -> dict[str, Any]:
    rol_val = u.rol.value
    modulos  = _ACCESOS_ROL.get(rol_val, [])
    return {
        "id":         u.id,
        "nombre":     u.nombre,
        "email":      u.email,
        "rol":        rol_val,
        "rol_label":  _ROL_LABELS.get(rol_val, rol_val),
        "is_active":  u.is_active,
        "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
        "modulos":    [_MODULE_LABELS[k] for k in modulos if k in _MODULE_LABELS],
    }


def listar_usuarios(session: Session, clinica_id: int) -> list[dict[str, Any]]:
    users = session.exec(
        select(User)
        .where(User.clinica_id == clinica_id)
        .order_by(User.nombre.asc())
    ).all()
    return [_dump_user(u) for u in users]


def crear_usuario(session: Session, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    nombre   = (payload.get("nombre")   or "").strip()
    email    = (payload.get("email")    or "").strip().lower()
    password = (payload.get("password") or "")
    rol_str  = (payload.get("rol")      or RoleEnum.RECEP.value)

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
        u.is_active  = True
        u.deleted_at = None
    session.flush()
    return _dump_user(u)
