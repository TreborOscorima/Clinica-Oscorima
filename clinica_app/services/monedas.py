from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from clinica_app.models.base import tenant_select
from clinica_app.models.moneda import Moneda
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError


def _dump(m: Moneda) -> dict[str, Any]:
    return {
        "id":        m.id,
        "codigo":    m.codigo,
        "nombre":    m.nombre,
        "simbolo":   m.simbolo,
        "es_activa": m.es_activa,
    }


def listar(session: Session, clinica_id: int) -> list[dict]:
    rows = session.exec(
        tenant_select(Moneda, clinica_id).order_by(Moneda.nombre)
    ).all()
    return [_dump(m) for m in rows]


def crear(session: Session, clinica_id: int, payload: dict) -> dict:
    codigo  = (payload.get("codigo")  or "").strip().upper()
    nombre  = (payload.get("nombre")  or "").strip()
    simbolo = (payload.get("simbolo") or "").strip()
    if not codigo or not nombre or not simbolo:
        raise ServiceError("Código, nombre y símbolo son obligatorios")

    existente = session.exec(
        select(Moneda).where(
            Moneda.clinica_id == clinica_id,
            Moneda.codigo     == codigo,
            Moneda.is_active.is_(True),
        )
    ).first()
    if existente:
        raise ConflictError(f"Ya existe la moneda '{codigo}'")

    m = Moneda(clinica_id=clinica_id, codigo=codigo, nombre=nombre, simbolo=simbolo)
    session.add(m)
    session.flush()
    return _dump(m)


def set_activa(session: Session, clinica_id: int, moneda_id: int) -> None:
    for m in session.exec(
        select(Moneda).where(Moneda.clinica_id == clinica_id, Moneda.is_active.is_(True))
    ).all():
        m.es_activa = False

    m = session.exec(
        select(Moneda).where(Moneda.id == moneda_id, Moneda.clinica_id == clinica_id)
    ).first()
    if not m:
        raise NotFoundError("Moneda no encontrada")
    m.es_activa = True
    session.flush()


def eliminar(session: Session, clinica_id: int, moneda_id: int) -> None:
    m = session.exec(
        select(Moneda).where(
            Moneda.id         == moneda_id,
            Moneda.clinica_id == clinica_id,
            Moneda.is_active.is_(True),
        )
    ).first()
    if not m:
        raise NotFoundError("Moneda no encontrada")
    if m.es_activa:
        raise ServiceError("No se puede eliminar la moneda activa. Seleccioná otra primero.")
    m.soft_delete()
    session.flush()
