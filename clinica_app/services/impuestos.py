from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from clinica_app.models.base import tenant_select
from clinica_app.models.impuesto_tasa import ImpuestoTasa
from clinica_app.services.exceptions import NotFoundError, ServiceError

_PAIS_DEFAULTS: dict[str, list[tuple]] = {
    "peru":      [("IGV", "Estándar",     18.0, True)],
    "argentina": [("IVA", "Estándar",     21.0, True),
                  ("IVA", "Reducida",     10.5, False),
                  ("IVA", "Incrementada", 27.0, False)],
    "colombia":  [("IVA", "Estándar",     19.0, True),
                  ("IVA", "Reducida",      5.0, False)],
    "chile":     [("IVA", "Estándar",     19.0, True)],
    "ecuador":   [("IVA", "Estándar",     12.0, True),
                  ("IVA", "Reducida",      5.0, False)],
    "bolivia":   [("IVA", "Estándar",     13.0, True)],
    "uruguay":   [("IVA", "Estándar",     22.0, True),
                  ("IVA", "Reducida",     10.0, False)],
    "paraguay":  [("IVA", "Estándar",     10.0, True),
                  ("IVA", "Reducida",      5.0, False)],
    "mexico":    [("IVA", "Estándar",     16.0, True)],
}


def _dump(t: ImpuestoTasa) -> dict[str, Any]:
    return {
        "id":            t.id,
        "tipo_impuesto": t.tipo_impuesto,
        "nombre":        t.nombre,
        "porcentaje":    t.porcentaje,
        "is_default":    t.is_default,
    }


def listar(session: Session, clinica_id: int) -> list[dict]:
    rows = session.exec(
        tenant_select(ImpuestoTasa, clinica_id)
        .order_by(ImpuestoTasa.tipo_impuesto, ImpuestoTasa.nombre)
    ).all()
    return [_dump(t) for t in rows]


def crear(session: Session, clinica_id: int, payload: dict) -> dict:
    tipo   = (payload.get("tipo_impuesto") or "IVA").strip().upper()
    nombre = (payload.get("nombre") or "").strip()
    try:
        porcentaje = float(payload.get("porcentaje", 0))
    except (ValueError, TypeError):
        raise ServiceError("Porcentaje inválido")
    if not nombre:
        raise ServiceError("El nombre de la tasa es obligatorio")
    if porcentaje < 0:
        raise ServiceError("El porcentaje no puede ser negativo")

    is_default = bool(payload.get("is_default", False))
    if is_default:
        _quitar_default(session, clinica_id)

    t = ImpuestoTasa(
        clinica_id=clinica_id,
        tipo_impuesto=tipo,
        nombre=nombre,
        porcentaje=porcentaje,
        is_default=is_default,
    )
    session.add(t)
    session.flush()
    return _dump(t)


def actualizar(session: Session, clinica_id: int, tid: int, payload: dict) -> dict:
    t = session.exec(
        select(ImpuestoTasa).where(
            ImpuestoTasa.id         == tid,
            ImpuestoTasa.clinica_id == clinica_id,
            ImpuestoTasa.is_active.is_(True),
        )
    ).first()
    if not t:
        raise NotFoundError("Tasa no encontrada")
    try:
        t.porcentaje = float(payload.get("porcentaje", t.porcentaje))
    except (ValueError, TypeError):
        raise ServiceError("Porcentaje inválido")
    if nombre := (payload.get("nombre") or "").strip():
        t.nombre = nombre
    if tipo := (payload.get("tipo_impuesto") or "").strip():
        t.tipo_impuesto = tipo.upper()
    session.flush()
    return _dump(t)


def set_default(session: Session, clinica_id: int, tid: int) -> None:
    _quitar_default(session, clinica_id)
    t = session.exec(
        select(ImpuestoTasa).where(
            ImpuestoTasa.id         == tid,
            ImpuestoTasa.clinica_id == clinica_id,
        )
    ).first()
    if not t:
        raise NotFoundError("Tasa no encontrada")
    t.is_default = True
    session.flush()


def eliminar(session: Session, clinica_id: int, tid: int) -> None:
    t = session.exec(
        select(ImpuestoTasa).where(
            ImpuestoTasa.id         == tid,
            ImpuestoTasa.clinica_id == clinica_id,
            ImpuestoTasa.is_active.is_(True),
        )
    ).first()
    if not t:
        raise NotFoundError("Tasa no encontrada")
    if t.is_default:
        raise ServiceError("No se puede eliminar la tasa por defecto. Seleccioná otra primero.")
    t.soft_delete()
    session.flush()


def cargar_pais(session: Session, clinica_id: int, pais: str) -> None:
    defaults = _PAIS_DEFAULTS.get(pais.lower())
    if not defaults:
        raise ServiceError(f"País no soportado: {pais}")
    for t in session.exec(
        select(ImpuestoTasa).where(
            ImpuestoTasa.clinica_id == clinica_id,
            ImpuestoTasa.is_active.is_(True),
        )
    ).all():
        t.soft_delete()
    for tipo, nombre, porcentaje, is_default in defaults:
        session.add(ImpuestoTasa(
            clinica_id=clinica_id,
            tipo_impuesto=tipo,
            nombre=nombre,
            porcentaje=porcentaje,
            is_default=is_default,
        ))
    session.flush()


def _quitar_default(session: Session, clinica_id: int) -> None:
    for t in session.exec(
        select(ImpuestoTasa).where(
            ImpuestoTasa.clinica_id  == clinica_id,
            ImpuestoTasa.is_active.is_(True),
            ImpuestoTasa.is_default.is_(True),
        )
    ).all():
        t.is_default = False
