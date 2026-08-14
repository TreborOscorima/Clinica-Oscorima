"""Consentimientos informados (A4).

Orquesta la generación de un consentimiento: arma el PDF (bytes), lo persiste
en disco vía `storage`, lo registra como `Adjunto` (categoría "consentimiento",
reutilizando toda la infraestructura de A2) y deja rastro de auditoría. El
resultado queda descargable/imprimible desde la Historia Clínica del paciente.

No genera fila propia en una tabla nueva: el consentimiento ES un adjunto, así
que hereda descarga con token, borrado con soft-delete y aislamiento por clínica.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.paciente import Paciente
from clinica_app.services import adjuntos as adj_svc
from clinica_app.services import auditoria
from clinica_app.services import plantillas_consentimiento as plantillas
from clinica_app.services.exceptions import NotFoundError
from clinica_app.services.pdf_consentimiento import generar_consentimiento_pdf
from clinica_app.services.storage import guardar as _guardar_archivo


def tipos() -> list[dict[str, str]]:
    """Tipos de consentimiento disponibles para el selector de la UI."""
    return plantillas.opciones()


def _slug(texto: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (texto or "").lower()).strip("-")
    return s[:40] or "consentimiento"


async def generar(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    tipo: str = "general",
    procedimiento: str = "",
    profesional_nombre: str = "",
    observaciones: str = "",
    usuario_id: int | None = None,
    sede_id: int = 0,
    clinica_nombre: str = "TUWAYKILIFE",
) -> dict[str, Any]:
    """Genera el consentimiento y lo archiva como adjunto. Devuelve el adjunto.

    Lanza NotFoundError si el paciente no existe en la clínica, y RuntimeError si
    reportlab no está disponible (propagado desde el generador de PDF).
    """
    pac = (await session.execute(
        select(Paciente).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
            Paciente.is_active.is_(True),
        )
    )).scalars().first()
    if pac is None:
        raise NotFoundError("Paciente no encontrado")

    titulo = plantillas.titulo(tipo)
    cuerpo = plantillas.cuerpo(tipo, procedimiento)

    # La construcción del PDF y la escritura a disco son bloqueantes: fuera del loop.
    pdf_bytes = await asyncio.to_thread(
        generar_consentimiento_pdf,
        clinica_nombre=clinica_nombre,
        titulo=titulo,
        cuerpo=cuerpo,
        paciente_nombre=pac.nombre,
        paciente_documento=pac.documento or "",
        procedimiento=procedimiento,
        profesional_nombre=profesional_nombre,
        observaciones=observaciones,
    )

    nombre_archivo = f"consentimiento-{_slug(tipo)}-{_slug(pac.nombre)}.pdf"
    stored_name = await asyncio.to_thread(
        _guardar_archivo, clinica_id, nombre_archivo, pdf_bytes
    )

    dump = await adj_svc.crear(
        session, clinica_id, paciente_id,
        nombre=nombre_archivo,
        stored_name=stored_name,
        mime="application/pdf",
        tamano=len(pdf_bytes),
        categoria="consentimiento",
        created_by_id=usuario_id,
        sede_id=sede_id,
    )

    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="generar", entidad="consentimiento", entidad_id=dump["id"],
        detalle={"tipo": tipo, "paciente_id": paciente_id, "procedimiento": procedimiento},
        sede_id=sede_id or None,
    )
    await session.flush()
    return dump
