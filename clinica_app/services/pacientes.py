from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.paciente import Paciente
from clinica_app.services.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

# Paridad con el CHECK constraint de BD `chk_documento_digits` (^[0-9]+$).
_DOCUMENTO_RE = re.compile(r"^[0-9]+$")


def _validar_documento(documento: Any) -> None:
    """El documento, si viene, debe contener solo dígitos (igual que el constraint)."""
    if documento in (None, ""):
        return
    if not _DOCUMENTO_RE.match(str(documento)):
        raise ValidationError("El documento debe contener solo números")


def _dump(p: Paciente) -> dict[str, Any]:
    return {
        "id":                  p.id,
        "nombre":              p.nombre,
        "documento":           p.documento,
        "email":               p.email,
        "telefono":            p.telefono,
        "direccion":           p.direccion,
        "fecha_nacimiento":    p.fecha_nacimiento.isoformat() if isinstance(p.fecha_nacimiento, (date, datetime)) else p.fecha_nacimiento,
        "contacto_emergencia": p.contacto_emergencia,
        "edad":                p.edad,
        "created_at":          p.created_at.isoformat() if isinstance(p.created_at, (date, datetime)) else p.created_at,
    }


def _base_query(clinica_id: int, sede_id: int = 0):
    stmt = select(Paciente).where(
        Paciente.clinica_id == clinica_id,
        Paciente.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(Paciente.sede_id == sede_id)
    return stmt


async def listar(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    q: str = "",
    desde: datetime | None = None,
    hasta: datetime | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = _base_query(clinica_id, sede_id)

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

    total: int = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    items = (
        await session.execute(
            stmt.order_by(Paciente.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    return {
        "data":     [_dump(p) for p in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, -(-total // per_page)),
    }


def _parse_fecha(payload: dict[str, Any]) -> None:
    fn = payload.get("fecha_nacimiento")
    if isinstance(fn, str) and fn:
        payload["fecha_nacimiento"] = date.fromisoformat(fn)


async def crear(session: AsyncSession, clinica_id: int, sede_id: int = 0, payload: dict[str, Any] = None) -> dict[str, Any]:
    payload = {k: v for k, v in (payload or {}).items() if v not in (None, "")}
    payload["clinica_id"] = clinica_id
    if sede_id:
        payload["sede_id"] = sede_id
    _parse_fecha(payload)

    _validar_documento(payload.get("documento"))
    if payload.get("documento"):
        await _assert_documento_libre(session, clinica_id, payload["documento"])
    if payload.get("email"):
        await _assert_email_libre(session, clinica_id, payload["email"])

    p = Paciente(**payload)
    session.add(p)
    await session.flush()
    return _dump(p)


async def obtener(session: AsyncSession, clinica_id: int, paciente_id: int, sede_id: int = 0) -> Paciente:
    p = (
        await session.execute(
            _base_query(clinica_id, sede_id).where(Paciente.id == paciente_id)
        )
    ).scalars().first()
    if p is None:
        raise NotFoundError("Paciente no encontrado")
    return p


async def actualizar(
    session: AsyncSession, clinica_id: int, paciente_id: int, payload: dict[str, Any], sede_id: int = 0
) -> dict[str, Any]:
    p = await obtener(session, clinica_id, paciente_id, sede_id)
    payload = {k: v for k, v in payload.items() if v is not None}
    _parse_fecha(payload)

    nuevo_doc = payload.get("documento")
    if nuevo_doc and nuevo_doc != p.documento:
        _validar_documento(nuevo_doc)
        await _assert_documento_libre(session, clinica_id, nuevo_doc, exclude_id=p.id)

    nuevo_mail = payload.get("email")
    if nuevo_mail and nuevo_mail != p.email:
        await _assert_email_libre(session, clinica_id, nuevo_mail, exclude_id=p.id)

    for k, v in payload.items():
        if hasattr(p, k):
            setattr(p, k, v)
    await session.flush()
    return _dump(p)


async def eliminar(session: AsyncSession, clinica_id: int, paciente_id: int, sede_id: int = 0) -> None:
    p = await obtener(session, clinica_id, paciente_id, sede_id)
    p.soft_delete()
    await session.flush()


async def _assert_documento_libre(
    session: AsyncSession,
    clinica_id: int,
    documento: str,
    exclude_id: int | None = None,
) -> None:
    stmt = select(Paciente).where(
        Paciente.clinica_id == clinica_id,
        Paciente.documento == documento,
        Paciente.is_active.is_(True),
    )
    if exclude_id:
        stmt = stmt.where(Paciente.id != exclude_id)
    if (await session.execute(stmt)).scalars().first():
        raise ConflictError("Documento ya registrado en esta clínica")


async def _assert_email_libre(
    session: AsyncSession,
    clinica_id: int,
    email: str,
    exclude_id: int | None = None,
) -> None:
    stmt = select(Paciente).where(
        Paciente.clinica_id == clinica_id,
        Paciente.email == email,
        Paciente.is_active.is_(True),
    )
    if exclude_id:
        stmt = stmt.where(Paciente.id != exclude_id)
    if (await session.execute(stmt)).scalars().first():
        raise ConflictError("Email ya registrado en esta clínica")
