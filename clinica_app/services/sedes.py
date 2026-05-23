from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from clinica_app.models.base import tenant_select
from clinica_app.models.sede import Sede
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


def _dump(s: Sede) -> dict[str, Any]:
    return {
        "id":           s.id,
        "nombre":       s.nombre,
        "direccion":    s.direccion or "",
        "telefono":     s.telefono or "",
        "email":        s.email or "",
        "es_principal": s.es_principal,
        "is_active":    s.is_active,
    }


def listar(session: Session, clinica_id: int) -> list[dict]:
    rows = session.exec(
        tenant_select(Sede, clinica_id).order_by(Sede.es_principal.desc(), Sede.nombre)
    ).all()
    return [_dump(s) for s in rows]


def crear(session: Session, clinica_id: int, payload: dict) -> dict:
    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre de la sede es obligatorio")

    existente = session.exec(
        select(Sede).where(
            Sede.clinica_id == clinica_id,
            Sede.nombre == nombre,
            Sede.is_active.is_(True),
        )
    ).first()
    if existente:
        raise ConflictError(f"Ya existe una sede con el nombre '{nombre}'")

    es_principal = bool(payload.get("es_principal", False))
    # Solo una sede puede ser principal: desmarcar las demás
    if es_principal:
        session.exec(
            select(Sede).where(
                Sede.clinica_id == clinica_id,
                Sede.es_principal.is_(True),
            )
        )
        for s in session.exec(
            select(Sede).where(Sede.clinica_id == clinica_id, Sede.is_active.is_(True))
        ).all():
            s.es_principal = False

    sede = Sede(
        clinica_id=clinica_id,
        nombre=nombre,
        direccion=payload.get("direccion") or None,
        telefono=payload.get("telefono") or None,
        email=payload.get("email") or None,
        es_principal=es_principal,
    )
    session.add(sede)
    session.flush()
    return _dump(sede)


def actualizar(session: Session, clinica_id: int, sede_id: int, payload: dict) -> dict:
    sede = session.exec(
        select(Sede).where(
            Sede.id == sede_id,
            Sede.clinica_id == clinica_id,
            Sede.is_active.is_(True),
        )
    ).first()
    if not sede:
        raise NotFoundError("Sede no encontrada")

    nombre = (payload.get("nombre") or "").strip()
    if not nombre:
        raise ServiceError("El nombre de la sede es obligatorio")

    sede.nombre    = nombre
    sede.direccion = payload.get("direccion") or None
    sede.telefono  = payload.get("telefono") or None
    sede.email     = payload.get("email") or None

    es_principal = bool(payload.get("es_principal", False))
    if es_principal and not sede.es_principal:
        for s in session.exec(
            select(Sede).where(Sede.clinica_id == clinica_id, Sede.is_active.is_(True))
        ).all():
            s.es_principal = False
        sede.es_principal = True
    elif not es_principal:
        sede.es_principal = False

    session.flush()
    return _dump(sede)


def eliminar(session: Session, clinica_id: int, sede_id: int) -> None:
    sede = session.exec(
        select(Sede).where(
            Sede.id == sede_id,
            Sede.clinica_id == clinica_id,
            Sede.is_active.is_(True),
        )
    ).first()
    if not sede:
        raise NotFoundError("Sede no encontrada")
    if sede.es_principal:
        raise ConflictError("No se puede eliminar la sede principal. Establecé otra como principal primero.")
    sede.soft_delete()
    session.flush()
