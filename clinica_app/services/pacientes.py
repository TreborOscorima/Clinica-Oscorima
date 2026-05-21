from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlmodel import Session

from clinica_app.models.paciente import Paciente
from clinica_app.services.exceptions import ConflictError, NotFoundError


def _dump(p: Paciente) -> dict[str, Any]:
    return {
        "id":                  p.id,
        "nombre":              p.nombre,
        "documento":           p.documento,
        "email":               p.email,
        "telefono":            p.telefono,
        "direccion":           p.direccion,
        "fecha_nacimiento":    p.fecha_nacimiento.isoformat() if p.fecha_nacimiento else None,
        "contacto_emergencia": p.contacto_emergencia,
        "edad":                p.edad,
        "created_at":          p.created_at.isoformat() if p.created_at else None,
    }


def _base_query(clinica_id: int):
    return select(Paciente).where(
        Paciente.clinica_id == clinica_id,
        Paciente.is_active.is_(True),
    )


def listar(
    session: Session,
    clinica_id: int,
    q: str = "",
    desde: datetime | None = None,
    hasta: datetime | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = _base_query(clinica_id)

    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Paciente.nombre.ilike(like),
                cast(Paciente.documento, String).ilike(like),
            )
        )
    if desde:
        stmt = stmt.where(Paciente.created_at >= desde)
    if hasta:
        if hasta.hour == 0 and hasta.minute == 0:
            hasta = hasta + timedelta(days=1)
        stmt = stmt.where(Paciente.created_at < hasta)

    total: int = session.exec(
        select(func.count()).select_from(stmt.subquery())
    ).one()
    items = session.exec(
        stmt.order_by(Paciente.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    return {
        "data":     [_dump(p) for p in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, -(-total // per_page)),
    }


def crear(session: Session, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    payload = {k: v for k, v in payload.items() if v not in (None, "")}
    payload["clinica_id"] = clinica_id

    if payload.get("documento"):
        _assert_documento_libre(session, clinica_id, payload["documento"])
    if payload.get("email"):
        _assert_email_libre(session, clinica_id, payload["email"])

    p = Paciente(**payload)
    session.add(p)
    session.flush()
    return _dump(p)


def obtener(session: Session, clinica_id: int, paciente_id: int) -> Paciente:
    p = session.exec(
        _base_query(clinica_id).where(Paciente.id == paciente_id)
    ).first()
    if p is None:
        raise NotFoundError("Paciente no encontrado")
    return p


def actualizar(session: Session, clinica_id: int, paciente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    p = obtener(session, clinica_id, paciente_id)
    payload = {k: v for k, v in payload.items() if v is not None}

    nuevo_doc = payload.get("documento")
    if nuevo_doc and nuevo_doc != p.documento:
        _assert_documento_libre(session, clinica_id, nuevo_doc, exclude_id=p.id)

    nuevo_mail = payload.get("email")
    if nuevo_mail and nuevo_mail != p.email:
        _assert_email_libre(session, clinica_id, nuevo_mail, exclude_id=p.id)

    for k, v in payload.items():
        if hasattr(p, k):
            setattr(p, k, v)
    session.flush()
    return _dump(p)


def eliminar(session: Session, clinica_id: int, paciente_id: int) -> None:
    p = obtener(session, clinica_id, paciente_id)
    p.soft_delete()
    session.flush()


def _assert_documento_libre(session: Session, clinica_id: int, documento: str, exclude_id: int | None = None) -> None:
    stmt = select(Paciente).where(
        Paciente.clinica_id == clinica_id,
        Paciente.documento == documento,
        Paciente.is_active.is_(True),
    )
    if exclude_id:
        stmt = stmt.where(Paciente.id != exclude_id)
    if session.exec(stmt).first():
        raise ConflictError("Documento ya registrado en esta clínica")


def _assert_email_libre(session: Session, clinica_id: int, email: str, exclude_id: int | None = None) -> None:
    stmt = select(Paciente).where(
        Paciente.clinica_id == clinica_id,
        Paciente.email == email,
        Paciente.is_active.is_(True),
    )
    if exclude_id:
        stmt = stmt.where(Paciente.id != exclude_id)
    if session.exec(stmt).first():
        raise ConflictError("Email ya registrado en esta clínica")
