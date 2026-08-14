"""Servicio de adjuntos clínicos (A2).

Metadatos en BD; el binario lo maneja services/storage.py. El borrado es
soft-delete + registro de auditoría (requisito de trazabilidad en salud) y
devuelve el `stored_name` para que la capa que llama borre el archivo físico.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.adjunto import Adjunto
from clinica_app.services import auditoria
from clinica_app.services.exceptions import NotFoundError

_CATEGORIAS = frozenset({"foto", "estudio", "radiografia", "consentimiento", "receta", "informe", "otro"})


def _fmt_size(n: int) -> str:
    n = int(n or 0)
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _dump(a: Adjunto) -> dict[str, Any]:
    return {
        "id":         a.id or 0,
        "nombre":     a.nombre,
        "categoria":  a.categoria or "otro",
        "mime":       a.mime or "",
        "tamano":     a.tamano or 0,
        "tamano_fmt": _fmt_size(a.tamano or 0),
        "created_at": a.created_at.strftime("%d/%m/%Y %H:%M") if isinstance(a.created_at, (date, datetime)) else "",
    }


def _base_query(clinica_id: int, sede_id: int = 0):
    stmt = select(Adjunto).where(
        Adjunto.clinica_id == clinica_id,
        Adjunto.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(Adjunto.sede_id == sede_id)
    return stmt


async def listar_por_paciente(
    session: AsyncSession, clinica_id: int, paciente_id: int, sede_id: int = 0
) -> list[dict[str, Any]]:
    stmt = (
        _base_query(clinica_id, sede_id)
        .where(Adjunto.paciente_id == paciente_id)
        .order_by(Adjunto.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_dump(a) for a in rows]


async def crear(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    nombre: str,
    stored_name: str,
    mime: str | None = None,
    tamano: int = 0,
    categoria: str | None = None,
    created_by_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    cat = categoria if categoria in _CATEGORIAS else "otro"
    a = Adjunto(
        clinica_id=clinica_id,
        paciente_id=paciente_id,
        sede_id=sede_id or None,
        nombre=nombre[:255],
        stored_name=stored_name,
        mime=(mime or None) and mime[:120],
        tamano=int(tamano or 0),
        categoria=cat,
        created_by_id=created_by_id or None,
    )
    session.add(a)
    await session.flush()
    return _dump(a)


async def obtener(
    session: AsyncSession, clinica_id: int, adjunto_id: int, sede_id: int = 0
) -> Adjunto:
    a = (
        await session.execute(
            _base_query(clinica_id, sede_id).where(Adjunto.id == adjunto_id)
        )
    ).scalars().first()
    if a is None:
        raise NotFoundError("Adjunto no encontrado")
    return a


async def eliminar(
    session: AsyncSession,
    clinica_id: int,
    adjunto_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> str:
    """Soft-delete + auditoría. Devuelve el `stored_name` para borrar el archivo."""
    a = await obtener(session, clinica_id, adjunto_id, sede_id)
    stored_name = a.stored_name
    a.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar", entidad="adjunto", entidad_id=adjunto_id,
        detalle={"nombre": a.nombre, "paciente_id": a.paciente_id},
        sede_id=sede_id or None,
    )
    await session.flush()
    return stored_name
