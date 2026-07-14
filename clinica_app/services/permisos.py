from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.user import PermisoRol, RoleEnum


MODULOS = [
    "dashboard", "pacientes", "historia", "profesionales", "calendario",
    "turnos", "servicios", "cobro", "caja", "cuentas", "compras",
    "inventario", "promociones", "reportes", "configuracion",
]

_DEFAULTS: dict[str, dict[str, tuple[bool, bool]]] = {
    "administracion": {m: (True, True) for m in MODULOS},
    "recepcionista": {
        "dashboard":     (True, False),
        "pacientes":     (True, True),
        "turnos":        (True, True),
        "calendario":    (True, False),
        "cobro":         (True, True),
        "caja":          (True, False),
        "cuentas":       (True, False),
        "servicios":     (True, False),
    },
    "profesional": {
        "dashboard":     (True, False),
        "pacientes":     (True, False),
        "historia":      (True, True),
        "turnos":        (True, False),
        "calendario":    (True, False),
        "servicios":     (True, False),
        "cobro":         (True, False),
    },
    "contador": {
        "dashboard":     (True, False),
        "caja":          (True, False),
        "cuentas":       (True, False),
        "reportes":      (True, True),
        "compras":       (True, False),
        "inventario":    (True, False),
        "cobro":         (True, False),
    },
}


async def cargar_permisos(
    session: AsyncSession, clinica_id: int, role: str
) -> dict[str, dict[str, bool]]:
    registros = (
        await session.execute(
            select(PermisoRol).where(
                PermisoRol.clinica_id == clinica_id,
                PermisoRol.role == RoleEnum(role),
            )
        )
    ).scalars().all()

    if not registros:
        await seedear_permisos_rol(session, clinica_id, role)
        registros = (
            await session.execute(
                select(PermisoRol).where(
                    PermisoRol.clinica_id == clinica_id,
                    PermisoRol.role == RoleEnum(role),
                )
            )
        ).scalars().all()
    else:
        existing = {r.module for r in registros}
        missing = set(MODULOS) - existing
        if missing:
            await _seedear_modulos_faltantes(
                session, clinica_id, role, missing
            )
            registros = (
                await session.execute(
                    select(PermisoRol).where(
                        PermisoRol.clinica_id == clinica_id,
                        PermisoRol.role == RoleEnum(role),
                    )
                )
            ).scalars().all()

    return {
        r.module: {"read": r.can_read, "write": r.can_write}
        for r in registros
    }


async def _seedear_modulos_faltantes(
    session: AsyncSession, clinica_id: int, role: str, missing: set[str]
) -> None:
    defaults = _DEFAULTS.get(role, {})
    for module in missing:
        can_read, can_write = defaults.get(module, (False, False))
        session.add(PermisoRol(
            clinica_id=clinica_id,
            role=RoleEnum(role),
            module=module,
            can_read=can_read,
            can_write=can_write,
        ))
    await session.flush()


async def seedear_permisos_rol(
    session: AsyncSession, clinica_id: int, role: str
) -> None:
    defaults = _DEFAULTS.get(role, {})
    for module in MODULOS:
        can_read, can_write = defaults.get(module, (False, False))
        session.add(PermisoRol(
            clinica_id=clinica_id,
            role=RoleEnum(role),
            module=module,
            can_read=can_read,
            can_write=can_write,
        ))
    await session.flush()


async def seedear_todos(session: AsyncSession, clinica_id: int) -> None:
    for role in _DEFAULTS:
        existing = (
            await session.execute(
                select(PermisoRol.id).where(
                    PermisoRol.clinica_id == clinica_id,
                    PermisoRol.role == RoleEnum(role),
                ).limit(1)
            )
        ).scalar_one_or_none()
        if existing is None:
            await seedear_permisos_rol(session, clinica_id, role)
