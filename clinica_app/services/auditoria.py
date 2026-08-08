"""Auditoría de acciones sensibles. Se escribe DENTRO de la misma sesión/
transacción que la acción auditada, así el registro es atómico: si la acción
hace rollback, su rastro de auditoría también.

Uso típico desde un servicio (o desde un state, en su bloque de sesión):

    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="anular", entidad="compra", entidad_id=compra_id,
        detalle={"numero": numero, "total": str(total)},
    )
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.audit_log import AuditLog
from clinica_app.models.user import User


def _serializar_detalle(detalle: Any) -> str | None:
    if detalle is None:
        return None
    if isinstance(detalle, str):
        return detalle
    return json.dumps(detalle, ensure_ascii=False, default=str)


async def registrar(
    session: AsyncSession,
    clinica_id: int,
    *,
    accion: str,
    entidad: str,
    usuario_id: int | None = None,
    entidad_id: int | None = None,
    detalle: Any = None,
    sede_id: int | None = None,
) -> None:
    """Agrega una fila de auditoría a la sesión actual (sin commit propio)."""
    session.add(AuditLog(
        clinica_id=clinica_id,
        usuario_id=usuario_id or None,
        sede_id=sede_id or None,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=_serializar_detalle(detalle),
    ))
    await session.flush()


def _dump(a: AuditLog, usuario_nombre: str | None) -> dict[str, Any]:
    return {
        "id":         a.id or 0,
        "fecha":      a.creado_en.strftime("%Y-%m-%d %H:%M") if a.creado_en else "",
        "usuario":    usuario_nombre or "—",
        "accion":     a.accion,
        "entidad":    a.entidad,
        "entidad_id": a.entidad_id or 0,
        "detalle":    a.detalle or "",
    }


async def listar(
    session: AsyncSession,
    clinica_id: int,
    *,
    accion: str = "",
    entidad: str = "",
    page: int = 1,
    per_page: int = 30,
) -> dict[str, Any]:
    """Lista la bitácora (más reciente primero) con filtros opcionales."""
    base = (
        select(AuditLog, User.nombre)
        .outerjoin(User, User.id == AuditLog.usuario_id)
        .where(AuditLog.clinica_id == clinica_id)
    )
    if accion:
        base = base.where(AuditLog.accion == accion)
    if entidad:
        base = base.where(AuditLog.entidad == entidad)

    total: int = (
        await session.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    base = base.order_by(AuditLog.creado_en.desc(), AuditLog.id.desc())
    rows = (
        await session.execute(base.offset((page - 1) * per_page).limit(per_page))
    ).all()

    return {
        "data":     [_dump(a, nombre) for a, nombre in rows],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    max(1, -(-total // per_page)),
    }
