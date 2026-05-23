from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from clinica_app.models.nota_clinica import NotaClinica, TipoNota
from clinica_app.services.exceptions import NotFoundError, ServiceError


def _dump(n: NotaClinica) -> dict[str, Any]:
    prof = n.profesional
    prof_nombre = (
        f"{(prof.nombres or '').strip()} {(prof.apellidos or '').strip()}".strip()
        if prof else None
    )
    return {
        "id":              n.id,
        "paciente_id":     n.paciente_id,
        "turno_id":        n.turno_id,
        "profesional_id":  n.profesional_id,
        "profesional_nombre": prof_nombre,
        "tipo":            n.tipo.value if n.tipo else "evolucion",
        "contenido":       n.contenido,
        "created_at":      n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "",
    }


def listar_por_paciente(
    session: Session,
    clinica_id: int,
    paciente_id: int,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    base = (
        select(NotaClinica)
        .where(
            NotaClinica.clinica_id == clinica_id,
            NotaClinica.paciente_id == paciente_id,
            NotaClinica.is_active.is_(True),
        )
        .order_by(NotaClinica.created_at.desc())
    )
    total: int = session.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()
    items = session.exec(base.offset((page - 1) * per_page).limit(per_page)).all()
    return {
        "data":     [_dump(n) for n in items],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    max(1, -(-total // per_page)),
    }


def crear(
    session: Session,
    clinica_id: int,
    payload: dict[str, Any],
    created_by_id: int | None = None,
) -> dict[str, Any]:
    paciente_id = payload.get("paciente_id")
    if not paciente_id:
        raise ServiceError("paciente_id requerido")
    contenido = (payload.get("contenido") or "").strip()
    if not contenido:
        raise ServiceError("El contenido de la nota no puede estar vacío")

    tipo_str = payload.get("tipo", "evolucion")
    try:
        tipo = TipoNota(tipo_str)
    except ValueError:
        tipo = TipoNota.EVOLUCION

    nota = NotaClinica(
        clinica_id=clinica_id,
        paciente_id=paciente_id,
        turno_id=payload.get("turno_id"),
        profesional_id=payload.get("profesional_id"),
        created_by_id=created_by_id,
        tipo=tipo,
        contenido=contenido,
    )
    session.add(nota)
    session.flush()
    session.refresh(nota)
    return _dump(nota)


def actualizar(
    session: Session,
    clinica_id: int,
    nota_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    nota = session.exec(
        select(NotaClinica).where(
            NotaClinica.id == nota_id,
            NotaClinica.clinica_id == clinica_id,
            NotaClinica.is_active.is_(True),
        )
    ).first()
    if nota is None:
        raise NotFoundError("Nota no encontrada")

    contenido = (payload.get("contenido") or "").strip()
    if not contenido:
        raise ServiceError("El contenido no puede estar vacío")

    nota.contenido = contenido
    if payload.get("tipo"):
        try:
            nota.tipo = TipoNota(payload["tipo"])
        except ValueError:
            pass
    session.flush()
    return _dump(nota)


def eliminar(session: Session, clinica_id: int, nota_id: int) -> None:
    nota = session.exec(
        select(NotaClinica).where(
            NotaClinica.id == nota_id,
            NotaClinica.clinica_id == clinica_id,
            NotaClinica.is_active.is_(True),
        )
    ).first()
    if nota is None:
        raise NotFoundError("Nota no encontrada")
    nota.soft_delete()
    session.flush()
