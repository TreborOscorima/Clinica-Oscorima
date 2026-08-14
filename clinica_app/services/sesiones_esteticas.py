"""Galería antes/después estética por sesión (C1).

Cada `SesionEstetica` agrupa fotos (`Adjunto` categoría "foto") por fecha/zona,
etiquetadas con un `momento` (antes/durante/después). Reutiliza el
almacenamiento y el endpoint de descarga de A2; la lista de sesiones ordenada
por fecha es la línea de tiempo de evolución del paciente.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.adjunto import Adjunto
from clinica_app.models.paciente import Paciente
from clinica_app.models.sesion_estetica import SesionEstetica
from clinica_app.services import auditoria
from clinica_app.services.exceptions import NotFoundError, ValidationError

# ── Momentos (etiqueta de la foto dentro de la sesión) ────────────────────────
MOMENTOS: dict[str, str] = {
    "antes":   "Antes",
    "durante": "Durante",
    "despues": "Después",
}


def momentos_catalogo() -> list[dict[str, str]]:
    return [{"clave": k, "label": v} for k, v in MOMENTOS.items()]


def _validar_momento(momento: str) -> str:
    if momento not in MOMENTOS:
        raise ValidationError(f"Momento inválido: {momento}")
    return momento


def _parse_fecha(valor: Any) -> date:
    if isinstance(valor, date):
        return valor
    txt = (str(valor) if valor is not None else "").strip()
    if not txt:
        raise ValidationError("La fecha de la sesión es obligatoria")
    try:
        return datetime.strptime(txt[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Fecha inválida (use AAAA-MM-DD)")


# ── Serialización ─────────────────────────────────────────────────────────────

def _dump_foto(a: Adjunto) -> dict[str, Any]:
    return {
        "id":       a.id or 0,
        "nombre":   a.nombre or "",
        "momento":  a.momento or "antes",
        "mime":     a.mime or "",
    }


def _dump_sesion(s: SesionEstetica) -> dict[str, Any]:
    return {
        "id":          s.id or 0,
        "paciente_id": s.paciente_id,
        "fecha":       s.fecha.strftime("%Y-%m-%d") if s.fecha else "",
        "fecha_fmt":   s.fecha.strftime("%d/%m/%Y") if s.fecha else "",
        "titulo":      s.titulo or "",
        "zona":        s.zona or "",
        "notas":       s.notas or "",
    }


# ── Consultas de fotos ────────────────────────────────────────────────────────

async def _fotos_de(session: AsyncSession, clinica_id: int, sesion_id: int) -> list[Adjunto]:
    stmt = (
        select(Adjunto)
        .where(
            Adjunto.clinica_id == clinica_id,
            Adjunto.sesion_id == sesion_id,
            Adjunto.is_active.is_(True),
        )
        .order_by(Adjunto.created_at.asc(), Adjunto.id.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def _get_sesion(session: AsyncSession, clinica_id: int, sesion_id: int) -> SesionEstetica:
    s = (await session.execute(
        select(SesionEstetica).where(
            SesionEstetica.id == sesion_id,
            SesionEstetica.clinica_id == clinica_id,
            SesionEstetica.is_active.is_(True),
        )
    )).scalars().first()
    if s is None:
        raise NotFoundError("Sesión estética no encontrada")
    return s


# ── Consultas de sesión ───────────────────────────────────────────────────────

async def listar_sesiones(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
) -> list[dict[str, Any]]:
    """Línea de tiempo: sesiones del paciente (más reciente primero) con conteos."""
    stmt = (
        select(SesionEstetica)
        .where(
            SesionEstetica.clinica_id == clinica_id,
            SesionEstetica.paciente_id == paciente_id,
            SesionEstetica.is_active.is_(True),
        )
        .order_by(SesionEstetica.fecha.desc(), SesionEstetica.id.desc())
    )
    sesiones = list((await session.execute(stmt)).scalars().all())
    salida = []
    for s in sesiones:
        fotos = await _fotos_de(session, clinica_id, s.id)
        d = _dump_sesion(s)
        d["n_fotos"]   = len(fotos)
        d["n_antes"]   = sum(1 for f in fotos if (f.momento or "") == "antes")
        d["n_despues"] = sum(1 for f in fotos if (f.momento or "") == "despues")
        salida.append(d)
    return salida


async def obtener_sesion(
    session: AsyncSession,
    clinica_id: int,
    sesion_id: int,
) -> dict[str, Any]:
    """Sesión completa con sus fotos agrupadas por momento."""
    s = await _get_sesion(session, clinica_id, sesion_id)
    fotos = [_dump_foto(f) for f in await _fotos_de(session, clinica_id, sesion_id)]
    d = _dump_sesion(s)
    d["antes"]   = [f for f in fotos if f["momento"] == "antes"]
    d["durante"] = [f for f in fotos if f["momento"] == "durante"]
    d["despues"] = [f for f in fotos if f["momento"] == "despues"]
    d["n_fotos"] = len(fotos)
    return d


# ── Mutaciones de sesión ──────────────────────────────────────────────────────

async def crear_sesion(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    fecha: Any,
    titulo: str,
    zona: str | None = None,
    notas: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    titulo = (titulo or "").strip()
    if not titulo:
        raise ValidationError("El título de la sesión es obligatorio")
    fecha_d = _parse_fecha(fecha)

    pac = (await session.execute(
        select(Paciente.id).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
            Paciente.is_active.is_(True),
        )
    )).first()
    if pac is None:
        raise NotFoundError("Paciente no encontrado")

    s = SesionEstetica(
        clinica_id=clinica_id,
        paciente_id=paciente_id,
        sede_id=sede_id or None,
        fecha=fecha_d,
        titulo=titulo[:160],
        zona=(zona or "").strip()[:120] or None,
        notas=(notas or "").strip() or None,
        created_by_id=usuario_id,
    )
    session.add(s)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="crear", entidad="sesion_estetica", entidad_id=s.id,
        detalle={"paciente_id": paciente_id, "titulo": titulo[:160], "fecha": fecha_d.isoformat()},
        sede_id=sede_id or None,
    )
    d = _dump_sesion(s)
    d.update({"n_fotos": 0, "n_antes": 0, "n_despues": 0})
    return d


async def actualizar_sesion(
    session: AsyncSession,
    clinica_id: int,
    sesion_id: int,
    *,
    fecha: Any = None,
    titulo: str | None = None,
    zona: str | None = None,
    notas: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    s = await _get_sesion(session, clinica_id, sesion_id)
    if fecha is not None and str(fecha).strip():
        s.fecha = _parse_fecha(fecha)
    if titulo is not None:
        t = titulo.strip()
        if not t:
            raise ValidationError("El título de la sesión es obligatorio")
        s.titulo = t[:160]
    if zona is not None:
        s.zona = zona.strip()[:120] or None
    if notas is not None:
        s.notas = notas.strip() or None
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="editar", entidad="sesion_estetica", entidad_id=s.id,
        detalle={"titulo": s.titulo},
        sede_id=sede_id or None,
    )
    return _dump_sesion(s)


async def eliminar_sesion(
    session: AsyncSession,
    clinica_id: int,
    sesion_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> list[str]:
    """Soft-delete de la sesión y de sus fotos. Devuelve los `stored_name` para
    que la capa que llama borre los archivos físicos."""
    s = await _get_sesion(session, clinica_id, sesion_id)
    stored: list[str] = []
    for f in await _fotos_de(session, clinica_id, sesion_id):
        stored.append(f.stored_name)
        f.soft_delete()
    s.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar", entidad="sesion_estetica", entidad_id=s.id,
        detalle={"paciente_id": s.paciente_id, "titulo": s.titulo, "fotos": len(stored)},
        sede_id=sede_id or None,
    )
    await session.flush()
    return stored


# ── Fotos ─────────────────────────────────────────────────────────────────────

async def registrar_foto(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    sesion_id: int,
    *,
    momento: str,
    nombre: str,
    stored_name: str,
    mime: str | None = None,
    tamano: int = 0,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Cuelga una foto ya almacenada (stored_name) de una sesión + momento."""
    momento = _validar_momento(momento)
    s = await _get_sesion(session, clinica_id, sesion_id)  # valida pertenencia

    a = Adjunto(
        clinica_id=clinica_id,
        paciente_id=paciente_id or s.paciente_id,
        sede_id=sede_id or None,
        sesion_id=sesion_id,
        momento=momento,
        nombre=(nombre or "foto")[:255],
        stored_name=stored_name,
        mime=(mime or None) and mime[:120],
        tamano=int(tamano or 0),
        categoria="foto",
        created_by_id=usuario_id or None,
    )
    session.add(a)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="agregar_foto", entidad="sesion_estetica", entidad_id=sesion_id,
        detalle={"foto_id": a.id, "momento": momento, "nombre": a.nombre},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_foto(a)


async def eliminar_foto(
    session: AsyncSession,
    clinica_id: int,
    foto_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> str:
    """Soft-delete de una foto. Devuelve el `stored_name` para borrar el archivo."""
    a = (await session.execute(
        select(Adjunto).where(
            Adjunto.id == foto_id,
            Adjunto.clinica_id == clinica_id,
            Adjunto.is_active.is_(True),
        )
    )).scalars().first()
    if a is None:
        raise NotFoundError("Foto no encontrada")
    stored_name = a.stored_name
    sesion_id = a.sesion_id
    a.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar_foto", entidad="sesion_estetica", entidad_id=sesion_id,
        detalle={"foto_id": foto_id},
        sede_id=sede_id or None,
    )
    await session.flush()
    return stored_name
