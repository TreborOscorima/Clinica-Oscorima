"""Odontograma — estado dental por paciente (B1).

Modelo de datos: una fila por pieza *con datos* (numeración FDI). Las piezas sin
intervención no ocupan fila; el servicio las presenta como "sano" al listar, de
modo que el odontograma siempre devuelve la arcada completa. El detalle por cara
(vestibular, lingual, mesial, distal, oclusal) se guarda como JSON en `caras`.

Es diferenciador odontológico: no toca el resto del sistema y reutiliza tenant +
auditoría. El plan de tratamiento (B2) se apoyará en estas piezas.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.pieza_dental import PiezaDental
from clinica_app.services import auditoria
from clinica_app.services.exceptions import NotFoundError, ValidationError

# ── Numeración FDI (dentición permanente) ────────────────────────────────────
# Fila superior (maxilar): cuadrante 1 (18→11) + cuadrante 2 (21→28)
# Fila inferior (mandíbula): cuadrante 4 (48→41) + cuadrante 3 (31→38)
ARCADA_SUPERIOR: list[str] = [
    "18", "17", "16", "15", "14", "13", "12", "11",
    "21", "22", "23", "24", "25", "26", "27", "28",
]
ARCADA_INFERIOR: list[str] = [
    "48", "47", "46", "45", "44", "43", "42", "41",
    "31", "32", "33", "34", "35", "36", "37", "38",
]
PIEZAS_VALIDAS: frozenset[str] = frozenset(ARCADA_SUPERIOR + ARCADA_INFERIOR)

# ── Estados por pieza (clave → etiqueta + color para la UI) ───────────────────
ESTADOS: dict[str, dict[str, str]] = {
    "sano":       {"label": "Sano",                "color": "#e5e7eb", "text": "#374151"},
    "caries":     {"label": "Caries",              "color": "#ef4444", "text": "#ffffff"},
    "obturado":   {"label": "Obturado",            "color": "#3b82f6", "text": "#ffffff"},
    "corona":     {"label": "Corona",              "color": "#f59e0b", "text": "#ffffff"},
    "endodoncia": {"label": "Endodoncia",          "color": "#fb923c", "text": "#ffffff"},
    "extraccion": {"label": "Extracción indicada", "color": "#b91c1c", "text": "#ffffff"},
    "ausente":    {"label": "Ausente",             "color": "#9ca3af", "text": "#ffffff"},
    "implante":   {"label": "Implante",            "color": "#14b8a6", "text": "#ffffff"},
    "protesis":   {"label": "Prótesis",            "color": "#a855f7", "text": "#ffffff"},
    "fractura":   {"label": "Fractura",            "color": "#ec4899", "text": "#ffffff"},
    "sellante":   {"label": "Sellante",            "color": "#22c55e", "text": "#ffffff"},
}

# Caras de la pieza (para el detalle por superficie)
CARAS: tuple[str, ...] = ("vestibular", "palatina", "mesial", "distal", "oclusal")


def estados_catalogo() -> list[dict[str, str]]:
    """Catálogo de estados para la leyenda/selector de la UI."""
    return [{"clave": k, **v} for k, v in ESTADOS.items()]


def layout() -> dict[str, list[str]]:
    """Disposición de la arcada para dibujar el odontograma."""
    return {"superior": list(ARCADA_SUPERIOR), "inferior": list(ARCADA_INFERIOR)}


def _validar_estado(estado: str) -> str:
    if estado not in ESTADOS:
        raise ValidationError(f"Estado dental inválido: {estado}")
    return estado


def _validar_numero(numero: str) -> str:
    numero = (numero or "").strip()
    if numero not in PIEZAS_VALIDAS:
        raise ValidationError(f"Pieza dental inválida: {numero}")
    return numero


def _parse_caras(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Solo caras y estados conocidos.
    return {
        c: e for c, e in data.items()
        if c in CARAS and isinstance(e, str) and e in ESTADOS
    }


def _serializar_caras(caras: dict[str, str] | None) -> str | None:
    if not caras:
        return None
    limpio = {
        c: e for c, e in caras.items()
        if c in CARAS and isinstance(e, str) and e in ESTADOS
    }
    return json.dumps(limpio, ensure_ascii=False) if limpio else None


def _dump(p: PiezaDental) -> dict[str, Any]:
    info = ESTADOS.get(p.estado or "sano", ESTADOS["sano"])
    return {
        "numero":     p.numero,
        "estado":     p.estado or "sano",
        "caras":      _parse_caras(p.caras),
        "nota":       p.nota or "",
        "estado_label": info["label"],
        "color":      info["color"],
        "text_color": info["text"],
    }


def _pieza_default(numero: str) -> dict[str, Any]:
    return {
        "numero":       numero,
        "estado":       "sano",
        "caras":        {},
        "nota":         "",
        "estado_label": ESTADOS["sano"]["label"],
        "color":        ESTADOS["sano"]["color"],
        "text_color":   ESTADOS["sano"]["text"],
    }


async def listar(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Devuelve la arcada completa (con o sin datos) + resumen por estado."""
    stmt = select(PiezaDental).where(
        PiezaDental.clinica_id == clinica_id,
        PiezaDental.paciente_id == paciente_id,
        PiezaDental.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(PiezaDental.sede_id == sede_id)
    filas = (await session.execute(stmt)).scalars().all()
    guardadas = {p.numero: _dump(p) for p in filas}

    piezas = {n: guardadas.get(n, _pieza_default(n)) for n in PIEZAS_VALIDAS}

    resumen: dict[str, int] = {}
    for p in guardadas.values():
        if p["estado"] != "sano":
            resumen[p["estado"]] = resumen.get(p["estado"], 0) + 1

    return {
        "superior": [piezas[n] for n in ARCADA_SUPERIOR],
        "inferior": [piezas[n] for n in ARCADA_INFERIOR],
        "resumen":  resumen,
        "con_datos": sum(1 for p in guardadas.values() if p["estado"] != "sano" or p["caras"] or p["nota"]),
    }


async def obtener_pieza(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    numero: str,
    sede_id: int = 0,
) -> dict[str, Any]:
    numero = _validar_numero(numero)
    stmt = select(PiezaDental).where(
        PiezaDental.clinica_id == clinica_id,
        PiezaDental.paciente_id == paciente_id,
        PiezaDental.numero == numero,
        PiezaDental.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(PiezaDental.sede_id == sede_id)
    p = (await session.execute(stmt)).scalars().first()
    return _dump(p) if p else _pieza_default(numero)


async def guardar_pieza(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    numero: str,
    *,
    estado: str = "sano",
    caras: dict[str, str] | None = None,
    nota: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Upsert del estado de una pieza. Registra auditoría."""
    numero = _validar_numero(numero)
    estado = _validar_estado(estado)
    caras_json = _serializar_caras(caras)
    nota = (nota or "").strip()[:255] or None

    stmt = select(PiezaDental).where(
        PiezaDental.clinica_id == clinica_id,
        PiezaDental.paciente_id == paciente_id,
        PiezaDental.numero == numero,
        PiezaDental.is_active.is_(True),
    )
    p = (await session.execute(stmt)).scalars().first()

    if p is None:
        p = PiezaDental(
            clinica_id=clinica_id,
            paciente_id=paciente_id,
            sede_id=sede_id or None,
            numero=numero,
            estado=estado,
            caras=caras_json,
            nota=nota,
            created_by_id=usuario_id,
        )
        session.add(p)
    else:
        p.estado = estado
        p.caras = caras_json
        p.nota = nota

    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="editar", entidad="pieza_dental", entidad_id=p.id,
        detalle={"paciente_id": paciente_id, "numero": numero, "estado": estado},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump(p)


async def resetear_pieza(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    numero: str,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Vuelve una pieza a 'sano' eliminando su fila (baja física de la marca)."""
    numero = _validar_numero(numero)
    stmt = select(PiezaDental).where(
        PiezaDental.clinica_id == clinica_id,
        PiezaDental.paciente_id == paciente_id,
        PiezaDental.numero == numero,
        PiezaDental.is_active.is_(True),
    )
    p = (await session.execute(stmt)).scalars().first()
    if p is None:
        raise NotFoundError("La pieza no tiene datos")
    p.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="resetear", entidad="pieza_dental", entidad_id=p.id,
        detalle={"paciente_id": paciente_id, "numero": numero},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _pieza_default(numero)
