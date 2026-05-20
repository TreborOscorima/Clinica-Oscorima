from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from flask import current_app
from flask_jwt_extended import get_jwt
from sqlalchemy import select

from extensions import db
from models.clinica import Clinica

_tenant_context: ContextVar[int | None] = ContextVar("tenant_context", default=None)


@contextmanager
def tenant_context(clinica_id: int):
    token = _tenant_context.set(int(clinica_id))
    try:
        yield
    finally:
        _tenant_context.reset(token)


def get_current_clinica_id() -> int:
    """Resuelve el tenant actual desde JWT o usa el tenant local por defecto."""
    context_value = _tenant_context.get()
    if context_value:
        return int(context_value)

    try:
        claims = get_jwt() or {}
    except Exception:
        claims = {}
    claim_value = claims.get("clinica_id")
    if claim_value:
        return int(claim_value)

    default_id = current_app.config.get("DEFAULT_CLINICA_ID")
    if default_id:
        return int(default_id)

    slug = current_app.config["DEFAULT_CLINICA_SLUG"]
    clinica = db.session.execute(
        select(Clinica).where(Clinica.slug == slug, Clinica.is_active.is_(True))
    ).scalar_one_or_none()
    if clinica is None:
        clinica = Clinica(nombre="Clinica Default", slug=slug)
        db.session.add(clinica)
        db.session.commit()
    return int(clinica.id)
