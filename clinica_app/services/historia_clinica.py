"""Línea de tiempo unificada del paciente (auditoría #6).

La historia clínica está repartida en varias pantallas (notas, odontograma,
plan de tratamiento, galería/sesiones estéticas, mapa estético, adjuntos,
consentimientos, recetas) y además cruza con agenda (turnos) y caja (cobros).
Este servicio NO crea datos ni esquema: sólo **lee** cada fuente y las funde en
una sola lista cronológica de eventos para una vista de agregación.

Cada evento es un dict plano listo para la UI: fecha ordenable + etiqueta,
tipo, título, detalle, estado (para el color del badge) y un `href` al detalle.
El ordenamiento y el conteo por tipo se calculan acá; el filtro por tipo lo hace
el estado en el cliente sobre la lista completa (los conteos quedan estables).

Rendimiento: una consulta por fuente (todas filtradas por paciente + clínica +
sede), sin N+1. Los nombres de profesional/servicio se precargan en un mapa por
id para no tocar relaciones lazy (que romperían en async).
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.adjunto import Adjunto
from clinica_app.models.caja import Comprobante
from clinica_app.models.evaluacion_estetica import EvaluacionEstetica
from clinica_app.models.nota_clinica import NotaClinica
from clinica_app.models.odontograma_version import OdontogramaVersion
from clinica_app.models.plan_tratamiento import PlanTratamiento
from clinica_app.models.profesional import Profesional
from clinica_app.models.servicio import Servicio
from clinica_app.models.sesion_estetica import SesionEstetica
from clinica_app.models.turno import Turno

# Orden y presentación de cada tipo de evento. La clave se usa para filtrar y
# para el color/ícono; el label es el rótulo del filtro.
TIPOS: list[dict[str, str]] = [
    {"key": "turno",          "label": "Turnos",          "icono": "calendar-clock"},
    {"key": "nota",           "label": "Notas",           "icono": "clipboard-list"},
    {"key": "receta",         "label": "Recetas",         "icono": "pill"},
    {"key": "consentimiento", "label": "Consentimientos", "icono": "signature"},
    {"key": "adjunto",        "label": "Adjuntos",        "icono": "paperclip"},
    {"key": "odontograma",    "label": "Odontograma",     "icono": "smile"},
    {"key": "plan",           "label": "Planes",          "icono": "clipboard-check"},
    {"key": "sesion",         "label": "Sesiones",        "icono": "brush"},
    {"key": "evaluacion",     "label": "Evaluaciones",    "icono": "scan-face"},
    {"key": "cobro",          "label": "Cobros",          "icono": "credit-card"},
]

# Tope defensivo: una historia muy larga no debe volcar miles de filas al front.
_LIMITE = 400


def _norm(x: date | datetime | None) -> datetime:
    """Normaliza a datetime *naive* comparable (una fecha sin hora → medianoche)."""
    if isinstance(x, datetime):
        return x.replace(tzinfo=None)
    if isinstance(x, date):
        return datetime.combine(x, time.min)
    return datetime.min


def _fmt(x: date | datetime | None, *, con_hora: bool = True) -> str:
    if isinstance(x, datetime):
        return x.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")
    if isinstance(x, date):
        return x.strftime("%d/%m/%Y")
    return ""


def _corto(texto: str | None, n: int = 140) -> str:
    t = " ".join((texto or "").split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


async def _mapa(session: AsyncSession, model: Any, ids: set[int], etiqueta) -> dict[int, str]:
    """{id: etiqueta(row)} para los ids dados; una sola consulta, sin lazy-load."""
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = (await session.execute(select(model).where(model.id.in_(ids)))).scalars().all()
    return {r.id: etiqueta(r) for r in rows}


async def timeline(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    sede_id: int = 0,
    limite: int = _LIMITE,
) -> dict[str, Any]:
    """Funde todas las fuentes en una línea de tiempo del paciente.

    Devuelve ``{"eventos": [...], "conteos": {tipo: n}, "total": n}`` con los
    eventos ordenados del más reciente al más antiguo.
    """
    eventos: list[dict[str, Any]] = []
    hc_href = f"/historia-clinica?paciente_id={paciente_id}"

    def _tenant(model):
        stmt = select(model).where(
            model.clinica_id == clinica_id,
            model.paciente_id == paciente_id,
            model.is_active.is_(True),
        )
        if sede_id:
            stmt = stmt.where(model.sede_id == sede_id)
        return stmt

    # ── Turnos (fecha clínica = fecha_hora del turno) ────────────────────────
    turnos = (await session.execute(_tenant(Turno))).scalars().all()
    prof_ids = {t.profesional_id for t in turnos}
    serv_ids = {t.servicio_id for t in turnos}

    # ── Notas clínicas ───────────────────────────────────────────────────────
    notas = (await session.execute(_tenant(NotaClinica))).scalars().all()
    prof_ids |= {n.profesional_id for n in notas}

    prof_map = await _mapa(
        session, Profesional, prof_ids,
        lambda p: f"{p.nombres} {p.apellidos}".strip(),
    )
    serv_map = await _mapa(session, Servicio, serv_ids, lambda s: s.nombre)

    for t in turnos:
        estado = t.estado.value if t.estado else "pendiente"
        serv = serv_map.get(t.servicio_id, "")
        prof = prof_map.get(t.profesional_id, "")
        detalle = " · ".join([p for p in (serv, prof) if p]) or "Turno agendado"
        eventos.append({
            "tipo": "turno", "orden": _norm(t.fecha_hora),
            "fecha": _fmt(t.fecha_hora), "titulo": "Turno",
            "detalle": detalle, "estado": estado, "href": "/turnos",
        })

    for n in notas:
        tipo_nota = n.tipo.value if n.tipo else "otro"
        eventos.append({
            "tipo": "nota", "orden": _norm(n.created_at),
            "fecha": _fmt(n.created_at),
            "titulo": f"Nota · {tipo_nota.capitalize()}",
            "detalle": _corto(n.contenido),
            "estado": "firmada" if n.firmada else tipo_nota,
            "href": hc_href,
        })

    # ── Adjuntos (incluye consentimientos y recetas, por categoría) ──────────
    adjuntos = (await session.execute(_tenant(Adjunto))).scalars().all()
    for a in adjuntos:
        cat = (a.categoria or "otro").lower()
        if cat == "consentimiento":
            tipo, titulo = "consentimiento", "Consentimiento informado"
        elif cat == "receta":
            tipo, titulo = "receta", "Receta / indicación"
        else:
            tipo, titulo = "adjunto", f"Adjunto · {cat.capitalize()}"
        eventos.append({
            "tipo": tipo, "orden": _norm(a.created_at),
            "fecha": _fmt(a.created_at), "titulo": titulo,
            "detalle": a.nombre or "", "estado": cat, "href": hc_href,
        })

    # ── Odontograma (versiones) ──────────────────────────────────────────────
    versiones = (await session.execute(_tenant(OdontogramaVersion))).scalars().all()
    for v in versiones:
        n_piezas = int(v.con_datos or 0)
        detalle = v.nota or (f"{n_piezas} piezas con datos" if n_piezas else "Snapshot")
        eventos.append({
            "tipo": "odontograma", "orden": _norm(v.created_at),
            "fecha": _fmt(v.created_at),
            "titulo": f"Odontograma · {v.titulo}",
            "detalle": _corto(detalle), "estado": "odontograma",
            "href": f"/odontograma?paciente_id={paciente_id}",
        })

    # ── Planes de tratamiento ────────────────────────────────────────────────
    planes = (await session.execute(_tenant(PlanTratamiento))).scalars().all()
    for pl in planes:
        eventos.append({
            "tipo": "plan", "orden": _norm(pl.created_at),
            "fecha": _fmt(pl.created_at),
            "titulo": f"Plan · {pl.titulo}",
            "detalle": _corto(pl.notas) if pl.notas else "Plan de tratamiento",
            "estado": pl.estado or "borrador",
            "href": f"/plan-tratamiento?paciente_id={paciente_id}",
        })

    # ── Sesiones estéticas (fecha clínica = fecha de la sesión) ──────────────
    sesiones = (await session.execute(_tenant(SesionEstetica))).scalars().all()
    for s in sesiones:
        partes = [p for p in (s.zona, s.notas) if p]
        eventos.append({
            "tipo": "sesion", "orden": _norm(s.fecha),
            "fecha": _fmt(s.fecha, con_hora=False),
            "titulo": f"Sesión estética · {s.titulo}",
            "detalle": _corto(" · ".join(partes)) if partes else "Sesión estética",
            "estado": "sesion",
            "href": f"/galeria-estetica?paciente_id={paciente_id}",
        })

    # ── Evaluaciones estéticas (mapa) ────────────────────────────────────────
    evals = (await session.execute(_tenant(EvaluacionEstetica))).scalars().all()
    for e in evals:
        sev = "" if e.severidad is None else f" · severidad {e.severidad}/4"
        eventos.append({
            "tipo": "evaluacion", "orden": _norm(e.created_at),
            "fecha": _fmt(e.created_at),
            "titulo": f"Evaluación · {e.categoria.capitalize()}",
            "detalle": _corto(f"Zona {e.zona_codigo}{sev}. {e.observacion or ''}"),
            "estado": "evaluacion",
            "href": f"/mapa-estetico?paciente_id={paciente_id}",
        })

    # ── Cobros / comprobantes (fecha = fecha del comprobante) ────────────────
    comp_stmt = select(Comprobante).where(
        Comprobante.clinica_id == clinica_id,
        Comprobante.paciente_id == paciente_id,
        Comprobante.is_active.is_(True),
    )
    if sede_id:
        comp_stmt = comp_stmt.where(Comprobante.sede_id == sede_id)
    comprobantes = (await session.execute(comp_stmt)).scalars().all()
    for c in comprobantes:
        total = c.total if isinstance(c.total, Decimal) else Decimal(str(c.total or 0))
        forma = c.forma_pago.value if c.forma_pago else ""
        num = c.numero or (c.tipo or "recibo").capitalize()
        detalle = f"$ {total:.2f}" + (f" · {forma}" if forma else "")
        eventos.append({
            "tipo": "cobro", "orden": _norm(c.fecha),
            "fecha": _fmt(c.fecha), "titulo": f"Cobro · {num}",
            "detalle": detalle,
            "estado": "anulado" if c.anulado else "cobro",
            "href": f"/cuentas?paciente_id={paciente_id}",
        })

    # ── Fusión, conteos y ordenamiento ───────────────────────────────────────
    conteos = {t["key"]: 0 for t in TIPOS}
    for ev in eventos:
        conteos[ev["tipo"]] = conteos.get(ev["tipo"], 0) + 1

    eventos.sort(key=lambda ev: ev["orden"], reverse=True)
    total = len(eventos)
    eventos = eventos[:limite]
    # `orden` (datetime) no es serializable a JSON para el estado de Reflex.
    for ev in eventos:
        ev.pop("orden", None)

    return {"eventos": eventos, "conteos": conteos, "total": total}
