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

from clinica_app.models.base import utcnow
from clinica_app.models.odontograma_version import OdontogramaVersion
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

# Disposición de las 5 caras para dibujar el diente como cruz (V arriba, M/O/D en
# el medio, P abajo). El orden de esta tupla es el que consume `superficies` y el
# que la grilla 2D espera por índice: 0=V, 1=M, 2=O, 3=D, 4=P.
_CARA_LAYOUT: tuple[tuple[str, str, str], ...] = (
    ("vestibular", "V", "Vestibular"),
    ("mesial",     "M", "Mesial"),
    ("oclusal",    "O", "Oclusal / Incisal"),
    ("distal",     "D", "Distal"),
    ("palatina",   "P", "Palatina / Lingual"),
)


def _superficies(caras: dict[str, str] | None) -> list[dict[str, Any]]:
    """Las 5 caras en orden de layout, cada una ya resuelta con su color/estado.
    Cara sin detalle → color blanco y `tiene=False`. Lo dibuja la grilla 2D
    (una celda por cara) sin necesidad de lookups reactivos en la UI."""
    caras = caras or {}
    salida: list[dict[str, Any]] = []
    for cara, corto, label in _CARA_LAYOUT:
        est = caras.get(cara, "")
        info = ESTADOS.get(est) if est else None
        salida.append({
            "cara":   cara,
            "corto":  corto,
            "label":  label,
            "estado": est,
            "color":  info["color"] if info else "#ffffff",
            "text":   info["text"] if info else "#9ca3af",
            "tiene":  bool(info),
        })
    return salida


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
    caras = _parse_caras(p.caras)
    return {
        "numero":     p.numero,
        "estado":     p.estado or "sano",
        "caras":      caras,
        "superficies": _superficies(caras),
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
        "superficies":  _superficies({}),
        "nota":         "",
        "estado_label": ESTADOS["sano"]["label"],
        "color":        ESTADOS["sano"]["color"],
        "text_color":   ESTADOS["sano"]["text"],
    }


def _armar_arcada(guardadas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Construye la arcada completa (superior/inferior) + resumen a partir de un
    mapa {numero: pieza_dump}. Las piezas sin dato se completan como 'sano'."""
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
    return _armar_arcada(guardadas)


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

    # Buscamos SIN filtrar por is_active: el UniqueConstraint (clinica, paciente,
    # numero) no distingue soft-delete, así que una pieza reseteada (is_active=0)
    # sigue ocupando la clave. Si insertáramos una nueva chocaría con esa fila
    # muerta; en su lugar la revivimos. (Sin esto, resetear una pieza y volver a
    # marcarla lanzaba IntegrityError 1062.)
    stmt = select(PiezaDental).where(
        PiezaDental.clinica_id == clinica_id,
        PiezaDental.paciente_id == paciente_id,
        PiezaDental.numero == numero,
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
        if not p.is_active:                 # revivir una pieza previamente reseteada
            p.is_active = True
            p.deleted_at = None
            p.sede_id = sede_id or p.sede_id
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


# ── Versionado — snapshots del odontograma en el tiempo ───────────────────────
# Cada versión congela el estado de las piezas *con datos* en JSON, para poder
# consultar la evolución dental sin bloquear la edición del odontograma vivo.

def _pieza_desde_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    """Reconstruye el dump completo de una pieza a partir del JSON guardado."""
    numero = item.get("numero") or ""
    estado = item.get("estado") or "sano"
    if estado not in ESTADOS:
        estado = "sano"
    info = ESTADOS[estado]
    caras = item.get("caras")
    caras = caras if isinstance(caras, dict) else {}
    return {
        "numero":       numero,
        "estado":       estado,
        "caras":        caras,
        "superficies":  _superficies(caras),
        "nota":         item.get("nota") or "",
        "estado_label": info["label"],
        "color":        info["color"],
        "text_color":   info["text"],
    }


def _parse_snapshot(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [_pieza_desde_snapshot(x) for x in data if isinstance(x, dict) and x.get("numero") in PIEZAS_VALIDAS]


def _dump_version_meta(v: OdontogramaVersion) -> dict[str, Any]:
    """Metadatos de una versión para el historial (sin reconstruir la arcada)."""
    snapshot = _parse_snapshot(v.piezas)
    resumen: dict[str, int] = {}
    for p in snapshot:
        if p["estado"] != "sano":
            resumen[p["estado"]] = resumen.get(p["estado"], 0) + 1
    return {
        "id":        v.id,
        "titulo":    v.titulo,
        "nota":      v.nota or "",
        "con_datos": v.con_datos,
        "fecha":     v.created_at.strftime("%Y-%m-%d %H:%M") if v.created_at else "",
        "resumen": [
            {
                "estado": est,
                "label":  ESTADOS.get(est, {}).get("label", est),
                "color":  ESTADOS.get(est, {}).get("color", "#e5e7eb"),
                "count":  cnt,
            }
            for est, cnt in sorted(resumen.items(), key=lambda kv: -kv[1])
        ],
    }


async def crear_version(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    titulo: str = "",
    nota: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Congela el estado actual del odontograma como una versión histórica."""
    stmt = select(PiezaDental).where(
        PiezaDental.clinica_id == clinica_id,
        PiezaDental.paciente_id == paciente_id,
        PiezaDental.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(PiezaDental.sede_id == sede_id)
    filas = (await session.execute(stmt)).scalars().all()

    snapshot = [
        {
            "numero": p.numero,
            "estado": p.estado or "sano",
            "caras":  _parse_caras(p.caras),
            "nota":   p.nota or "",
        }
        for p in filas
        if (p.estado or "sano") != "sano" or _parse_caras(p.caras) or (p.nota or "")
    ]

    titulo = (titulo or "").strip()[:120]
    if not titulo:
        titulo = "Versión " + utcnow().strftime("%Y-%m-%d %H:%M")
    nota = (nota or "").strip()[:255] or None

    v = OdontogramaVersion(
        clinica_id=clinica_id,
        paciente_id=paciente_id,
        sede_id=sede_id or None,
        titulo=titulo,
        nota=nota,
        piezas=json.dumps(snapshot, ensure_ascii=False),
        con_datos=len(snapshot),
        created_by_id=usuario_id,
    )
    session.add(v)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="versionar", entidad="odontograma_version", entidad_id=v.id,
        detalle={"paciente_id": paciente_id, "titulo": titulo, "con_datos": len(snapshot)},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_version_meta(v)


async def listar_versiones(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    sede_id: int = 0,
) -> list[dict[str, Any]]:
    """Historial de versiones del paciente, de la más reciente a la más antigua."""
    stmt = select(OdontogramaVersion).where(
        OdontogramaVersion.clinica_id == clinica_id,
        OdontogramaVersion.paciente_id == paciente_id,
        OdontogramaVersion.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(OdontogramaVersion.sede_id == sede_id)
    stmt = stmt.order_by(OdontogramaVersion.created_at.desc())
    filas = (await session.execute(stmt)).scalars().all()
    return [_dump_version_meta(v) for v in filas]


async def obtener_version(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    version_id: int,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Reconstruye la arcada completa de una versión, en el mismo formato que `listar`."""
    stmt = select(OdontogramaVersion).where(
        OdontogramaVersion.id == version_id,
        OdontogramaVersion.clinica_id == clinica_id,
        OdontogramaVersion.paciente_id == paciente_id,
        OdontogramaVersion.is_active.is_(True),
    )
    v = (await session.execute(stmt)).scalars().first()
    if v is None:
        raise NotFoundError("La versión no existe")
    guardadas = {p["numero"]: p for p in _parse_snapshot(v.piezas)}
    arcada = _armar_arcada(guardadas)
    arcada["id"] = v.id
    arcada["titulo"] = v.titulo
    arcada["nota"] = v.nota or ""
    arcada["fecha"] = v.created_at.strftime("%Y-%m-%d %H:%M") if v.created_at else ""
    return arcada


async def eliminar_version(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    version_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> None:
    """Baja lógica de una versión histórica."""
    stmt = select(OdontogramaVersion).where(
        OdontogramaVersion.id == version_id,
        OdontogramaVersion.clinica_id == clinica_id,
        OdontogramaVersion.paciente_id == paciente_id,
        OdontogramaVersion.is_active.is_(True),
    )
    v = (await session.execute(stmt)).scalars().first()
    if v is None:
        raise NotFoundError("La versión no existe")
    v.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar", entidad="odontograma_version", entidad_id=v.id,
        detalle={"paciente_id": paciente_id, "titulo": v.titulo},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Comparación de versiones ──────────────────────────────────────────────────

async def _arcada_para_comparar(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    version_id: int,
    sede_id: int,
) -> dict[str, Any]:
    """Arcada + etiqueta para un lado de la comparación. `version_id`==0 = vivo."""
    if version_id:
        arcada = await obtener_version(session, clinica_id, paciente_id, version_id)
        titulo = arcada.get("titulo", "")
        fecha = arcada.get("fecha", "")
    else:
        arcada = await listar(session, clinica_id, paciente_id, sede_id=sede_id)
        titulo = "Estado actual"
        fecha = ""
    return {"arcada": arcada, "titulo": titulo, "fecha": fecha}


async def comparar(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    a_id: int,
    b_id: int,
    *,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Compara dos odontogramas (versión vs versión, o versión vs estado actual).

    `a_id`/`b_id` son ids de versión; 0 significa el odontograma vivo. Devuelve
    ambas arcadas con cada pieza marcada (`cambio`) si difiere del otro lado, más
    la lista de diferencias pieza por pieza para el panel de detalle.
    """
    lado_a = await _arcada_para_comparar(session, clinica_id, paciente_id, a_id, sede_id)
    lado_b = await _arcada_para_comparar(session, clinica_id, paciente_id, b_id, sede_id)

    map_a = {p["numero"]: p for p in lado_a["arcada"]["superior"] + lado_a["arcada"]["inferior"]}
    map_b = {p["numero"]: p for p in lado_b["arcada"]["superior"] + lado_b["arcada"]["inferior"]}

    def _marcar(piezas: list[dict[str, Any]], otro: dict[str, dict]) -> list[dict[str, Any]]:
        salida = []
        for p in piezas:
            contra = otro.get(p["numero"], _pieza_default(p["numero"]))
            salida.append({**p, "cambio": p["estado"] != contra["estado"]})
        return salida

    cambios = []
    for numero in ARCADA_SUPERIOR + ARCADA_INFERIOR:
        pa = map_a.get(numero, _pieza_default(numero))
        pb = map_b.get(numero, _pieza_default(numero))
        if pa["estado"] != pb["estado"]:
            cambios.append({
                "numero":  numero,
                "a_label": pa["estado_label"], "a_color": pa["color"], "a_text": pa["text_color"],
                "b_label": pb["estado_label"], "b_color": pb["color"], "b_text": pb["text_color"],
            })

    return {
        "superior_a": _marcar(lado_a["arcada"]["superior"], map_b),
        "inferior_a": _marcar(lado_a["arcada"]["inferior"], map_b),
        "superior_b": _marcar(lado_b["arcada"]["superior"], map_a),
        "inferior_b": _marcar(lado_b["arcada"]["inferior"], map_a),
        "titulo_a":   lado_a["titulo"], "fecha_a": lado_a["fecha"],
        "titulo_b":   lado_b["titulo"], "fecha_b": lado_b["fecha"],
        "cambios":    cambios,
        "n_cambios":  len(cambios),
    }


# ── Exportación a PDF ─────────────────────────────────────────────────────────

async def datos_export(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    version_id: int = 0,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Reúne todo lo que el PDF necesita: paciente + arcada (viva o de versión)
    + leyenda de estados. Si `version_id` > 0 exporta esa versión histórica; si
    no, el odontograma vivo. Lanza NotFoundError si el paciente/versión no existe.
    """
    from clinica_app.models.paciente import Paciente

    pac = (await session.execute(
        select(Paciente).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
        )
    )).scalars().first()
    if pac is None:
        raise NotFoundError("El paciente no existe")

    version_titulo = ""
    version_fecha = ""
    if version_id:
        arcada = await obtener_version(session, clinica_id, paciente_id, version_id)
        version_titulo = arcada.get("titulo", "")
        version_fecha = arcada.get("fecha", "")
    else:
        arcada = await listar(session, clinica_id, paciente_id, sede_id=sede_id)

    return {
        "paciente_nombre":    pac.nombre,
        "paciente_documento": pac.documento or "",
        "superior":           arcada["superior"],
        "inferior":           arcada["inferior"],
        "leyenda":            estados_catalogo(),
        "version_titulo":     version_titulo,
        "version_fecha":      version_fecha,
    }
