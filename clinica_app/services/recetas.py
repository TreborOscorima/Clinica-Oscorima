"""Recetas / indicaciones imprimibles (A5).

Cierra el circuito asistencial básico: emite un PDF de receta ("Rp/") o de
indicaciones médicas y lo archiva como `Adjunto` (categoría "receta"),
reutilizando toda la infraestructura de A2 (storage, descarga con token, borrado
con auditoría, aislamiento por clínica). Deja rastro en el audit log.

No usa tabla propia: la receta ES un adjunto PDF del paciente.
"""
from __future__ import annotations

import asyncio
import re
import unicodedata
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.paciente import Paciente
from clinica_app.services import adjuntos as adj_svc
from clinica_app.services import auditoria
from clinica_app.services.exceptions import NotFoundError, ServiceError
from clinica_app.services.pdf_receta import generar_receta_pdf
from clinica_app.services.storage import guardar as _guardar_archivo

_TIPOS = {
    "receta":     "Receta",
    "indicacion": "Indicación",
}


def tipos() -> list[dict[str, str]]:
    """Tipos disponibles para el selector de la UI."""
    return [{"clave": k, "label": v} for k, v in _TIPOS.items()]


# ── Cruce receta ↔ alergias ─────────────────────────────────────────────────

_SEP_RE = re.compile(r"[,;/·\n\r\.]+|\by\b|\be\b", re.IGNORECASE)


def _norm(s: str) -> str:
    """Minúsculas sin acentos, para comparar términos de forma robusta."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def detectar_conflictos_alergia(cuerpo: str, alergias: str) -> list[str]:
    """Devuelve los términos de alergia del paciente que aparecen en la receta.

    Coincidencia por substring normalizado (sin acentos, insensible a mayúsculas)
    de cada término declarado en `alergias` contra el cuerpo de la receta. Es una
    ayuda de seguridad, no un sustituto del criterio clínico: matchea el texto
    literal, no clases farmacológicas (p. ej. "AINEs" no matchea "ibuprofeno").
    """
    if not (alergias or "").strip() or not (cuerpo or "").strip():
        return []
    cuerpo_n = _norm(cuerpo)
    conflictos: list[str] = []
    vistos: set[str] = set()
    for termino in _SEP_RE.split(alergias):
        t = (termino or "").strip()
        if len(t) < 3:
            continue
        clave = _norm(t)
        if clave and clave not in vistos and clave in cuerpo_n:
            vistos.add(clave)
            conflictos.append(t)
    return conflictos


def _slug(texto: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (texto or "").lower()).strip("-")
    return s[:40] or "receta"


async def generar(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    tipo: str = "receta",
    cuerpo: str = "",
    diagnostico: str = "",
    profesional_nombre: str = "",
    profesional_matricula: str = "",
    profesional_especialidad: str = "",
    usuario_id: int | None = None,
    sede_id: int = 0,
    clinica_nombre: str = "TUWAYKILIFE",
) -> dict[str, Any]:
    """Genera la receta/indicación y la archiva como adjunto. Devuelve el adjunto.

    Lanza NotFoundError si el paciente no existe en la clínica, ServiceError si el
    cuerpo está vacío, y RuntimeError si reportlab no está disponible.
    """
    if tipo not in _TIPOS:
        tipo = "receta"
    if not (cuerpo or "").strip():
        raise ServiceError("El contenido de la receta no puede estar vacío")

    pac = (await session.execute(
        select(Paciente).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
            Paciente.is_active.is_(True),
        )
    )).scalars().first()
    if pac is None:
        raise NotFoundError("Paciente no encontrado")

    pdf_bytes = await asyncio.to_thread(
        generar_receta_pdf,
        clinica_nombre=clinica_nombre,
        tipo=tipo,
        paciente_nombre=pac.nombre,
        paciente_documento=pac.documento or "",
        profesional_nombre=profesional_nombre,
        profesional_matricula=profesional_matricula,
        profesional_especialidad=profesional_especialidad,
        diagnostico=diagnostico,
        cuerpo=cuerpo,
    )

    nombre_archivo = f"{_slug(tipo)}-{_slug(pac.nombre)}.pdf"
    stored_name = await asyncio.to_thread(
        _guardar_archivo, clinica_id, nombre_archivo, pdf_bytes
    )

    dump = await adj_svc.crear(
        session, clinica_id, paciente_id,
        nombre=nombre_archivo,
        stored_name=stored_name,
        mime="application/pdf",
        tamano=len(pdf_bytes),
        categoria="receta",
        created_by_id=usuario_id,
        sede_id=sede_id,
    )

    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="generar", entidad="receta", entidad_id=dump["id"],
        detalle={"tipo": tipo, "paciente_id": paciente_id, "diagnostico": diagnostico},
        sede_id=sede_id or None,
    )
    await session.flush()
    return dump
