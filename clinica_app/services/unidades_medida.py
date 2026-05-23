from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from clinica_app.models.base import tenant_select
from clinica_app.models.unidad_medida import UnidadMedida
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


def _dump(u: UnidadMedida) -> dict[str, Any]:
    return {
        "id":                u.id,
        "nombre":            u.nombre,
        "permite_decimales": u.permite_decimales,
    }


def listar(session: Session, clinica_id: int) -> list[dict]:
    rows = session.exec(
        tenant_select(UnidadMedida, clinica_id).order_by(UnidadMedida.nombre)
    ).all()
    return [_dump(u) for u in rows]


def crear(session: Session, clinica_id: int, payload: dict) -> dict:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre de la unidad es obligatorio")

    existente = session.exec(
        select(UnidadMedida).where(
            UnidadMedida.clinica_id == clinica_id,
            UnidadMedida.nombre     == nombre,
            UnidadMedida.is_active.is_(True),
        )
    ).first()
    if existente:
        raise ConflictError(f"Ya existe la unidad '{nombre}'")

    u = UnidadMedida(
        clinica_id=clinica_id,
        nombre=nombre,
        permite_decimales=bool(payload.get("permite_decimales", False)),
    )
    session.add(u)
    session.flush()
    return _dump(u)


def toggle_decimales(session: Session, clinica_id: int, uid: int) -> dict:
    u = session.exec(
        select(UnidadMedida).where(
            UnidadMedida.id         == uid,
            UnidadMedida.clinica_id == clinica_id,
            UnidadMedida.is_active.is_(True),
        )
    ).first()
    if not u:
        raise NotFoundError("Unidad no encontrada")
    u.permite_decimales = not u.permite_decimales
    session.flush()
    return _dump(u)


def eliminar(session: Session, clinica_id: int, uid: int) -> None:
    u = session.exec(
        select(UnidadMedida).where(
            UnidadMedida.id         == uid,
            UnidadMedida.clinica_id == clinica_id,
            UnidadMedida.is_active.is_(True),
        )
    ).first()
    if not u:
        raise NotFoundError("Unidad no encontrada")
    u.soft_delete()
    session.flush()
