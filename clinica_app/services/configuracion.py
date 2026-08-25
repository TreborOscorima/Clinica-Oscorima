from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.clinica import Clinica
from clinica_app.models.user import RoleEnum, User
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError
from clinica_app.services.password import validar_password


# ── Clínica ────────────────────────────────────────────────────────────────────

_CAMPOS_CLINICA = (
    "nombre", "razon_social", "documento_fiscal", "email", "telefono",
    "direccion_fiscal", "zona_horaria", "rubro",
    "mensaje_recibo", "papel_impresion", "ancho_recibo",
    "margen_global", "mostrar_impuesto_recibo", "impuesto_modo",
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
        "impuesto_modo":           c.impuesto_modo or "incluido",
    }


async def obtener_clinica(session: AsyncSession, clinica_id: int) -> dict[str, Any]:
    c = await session.get(Clinica, clinica_id)
    if c is None or not c.is_active:
        raise NotFoundError("Clínica no encontrada")
    return _dump_clinica(c)


async def actualizar_clinica(session: AsyncSession, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    c = await session.get(Clinica, clinica_id)
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
    await session.flush()
    return _dump_clinica(c)


async def guardar_margenes(session: AsyncSession, clinica_id: int, margen_global: float) -> dict[str, Any]:
    c = await session.get(Clinica, clinica_id)
    if c is None or not c.is_active:
        raise NotFoundError("Clínica no encontrada")
    if margen_global < 0:
        raise ServiceError("El margen no puede ser negativo")
    c.margen_global = margen_global
    await session.flush()
    return _dump_clinica(c)


async def toggle_mostrar_impuesto(session: AsyncSession, clinica_id: int) -> bool:
    c = await session.get(Clinica, clinica_id)
    if c is None or not c.is_active:
        raise NotFoundError("Clínica no encontrada")
    c.mostrar_impuesto_recibo = not c.mostrar_impuesto_recibo
    await session.flush()
    return bool(c.mostrar_impuesto_recibo)


async def set_impuesto_modo(session: AsyncSession, clinica_id: int, modo: str) -> str:
    """Fija cómo se aplica el impuesto: 'incluido' (el precio ya lo incluye) o
    'agregado' (se suma al precio). Cualquier otro valor cae en 'incluido'."""
    modo = (modo or "").strip().lower()
    if modo not in ("incluido", "agregado"):
        raise ServiceError("Modo de impuesto inválido")
    c = await session.get(Clinica, clinica_id)
    if c is None or not c.is_active:
        raise NotFoundError("Clínica no encontrada")
    c.impuesto_modo = modo
    await session.flush()
    return modo


# ── Usuarios ───────────────────────────────────────────────────────────────────

_ROL_LABELS: dict[str, str] = {
    "administracion": "Administrador",
    "recepcionista":  "Recepcionista",
    "profesional":    "Profesional",
    "contador":       "Contador",
}

_SYSTEM_MODULES: list[tuple[str, str]] = [
    ("dashboard",     "Panel"),
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


async def listar_usuarios(session: AsyncSession, clinica_id: int) -> list[dict[str, Any]]:
    from clinica_app.models.user import UsuarioSede
    users = (await session.execute(
        select(User)
        .where(User.clinica_id == clinica_id)
        .order_by(User.nombre.asc())
    )).scalars().all()

    if not users:
        return []

    user_ids = [u.id for u in users]
    asignaciones = (await session.execute(
        select(UsuarioSede).where(UsuarioSede.user_id.in_(user_ids))
    )).scalars().all()
    sede_map: dict[int, list[int]] = {}
    for a in asignaciones:
        sede_map.setdefault(a.user_id, []).append(a.sede_id)

    result = []
    for u in users:
        d = _dump_user(u)
        d["sede_ids"] = sede_map.get(u.id, [])
        result.append(d)
    return result


async def listar_sede_ids_usuario(session: AsyncSession, user_id: int) -> list[int]:
    from clinica_app.models.user import UsuarioSede
    rows = (await session.execute(
        select(UsuarioSede).where(UsuarioSede.user_id == user_id)
    )).scalars().all()
    return [r.sede_id for r in rows]


async def asignar_sedes_usuario(
    session: AsyncSession,
    clinica_id: int,
    user_id: int,
    sede_ids: list[int],
) -> None:
    from clinica_app.models.user import UsuarioSede
    from clinica_app.models.sede import Sede

    existing = (await session.execute(
        select(UsuarioSede).where(UsuarioSede.user_id == user_id)
    )).scalars().all()
    for row in existing:
        await session.delete(row)

    sedes_validas = {
        s.id for s in (await session.execute(
            select(Sede).where(Sede.clinica_id == clinica_id, Sede.is_active.is_(True))
        )).scalars().all()
    }
    for sid in sede_ids:
        if sid in sedes_validas:
            session.add(UsuarioSede(user_id=user_id, sede_id=sid))
    await session.flush()


async def crear_usuario(session: AsyncSession, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    nombre   = (payload.get("nombre")   or "").strip()
    email    = (payload.get("email")    or "").strip().lower()
    password = (payload.get("password") or "")
    rol_str  = (payload.get("rol")      or RoleEnum.RECEP.value)

    if not nombre:
        raise ServiceError("Nombre obligatorio")
    if not email:
        raise ServiceError("Email obligatorio")
    validar_password(password)
    try:
        rol = RoleEnum(rol_str)
    except ValueError as exc:
        raise ServiceError("Rol inválido") from exc

    if (await session.execute(select(User).where(User.email == email))).scalars().first():
        raise ConflictError("Email ya registrado en el sistema")

    # Límite de usuarios por clínica (override del owner; NULL = ilimitado).
    clinica = await session.get(Clinica, clinica_id)
    maximo = getattr(clinica, "max_usuarios", None) if clinica else None
    if maximo:
        total = (await session.execute(
            select(func.count()).select_from(User).where(
                User.clinica_id == clinica_id, User.is_active.is_(True)
            )
        )).scalar_one()
        if total >= maximo:
            raise ServiceError(
                f"Límite alcanzado: máximo {maximo} usuarios. "
                f"Contacte a TUWAYKI para ampliar su plan."
            )

    u = User(clinica_id=clinica_id, nombre=nombre, email=email, rol=rol)
    u.set_password(password)
    session.add(u)
    await session.flush()
    return _dump_user(u)


async def cambiar_password(session: AsyncSession, clinica_id: int, user_id: int, nueva: str) -> None:
    validar_password(nueva)
    u = (await session.execute(
        select(User).where(User.id == user_id, User.clinica_id == clinica_id)
    )).scalars().first()
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    u.set_password(nueva)
    await session.flush()


async def toggle_activo(session: AsyncSession, clinica_id: int, user_id: int, solicitante_id: int) -> dict[str, Any]:
    if user_id == solicitante_id:
        raise ServiceError("No puedes desactivar tu propia cuenta")
    u = (await session.execute(
        select(User).where(User.id == user_id, User.clinica_id == clinica_id)
    )).scalars().first()
    if u is None:
        raise NotFoundError("Usuario no encontrado")
    if u.is_active:
        u.soft_delete()
    else:
        u.is_active  = True
        u.deleted_at = None
    await session.flush()
    return _dump_user(u)
