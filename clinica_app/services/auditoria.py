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

from sqlalchemy.ext.asyncio import AsyncSession

from clinica_app.models.audit_log import AuditLog


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
