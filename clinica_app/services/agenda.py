"""Agenda profesional real — disponibilidad, bloqueos y detección de solapamientos.

Tres piezas:
  - **Disponibilidad**: franjas horarias semanales por profesional (cuándo atiende).
  - **Bloqueos**: rangos en los que el profesional NO está disponible (vacaciones).
  - **verificar**: al crear/reprogramar un turno, detecta solapamiento con otro
    turno del mismo profesional, choque con un bloqueo y turnos fuera de horario.

Reutiliza tenant + auditoría. No reimplementa turnos: `turnos.crear`/`reprogramar`
llaman a `verificar` y, si hay conflictos, cortan con `ConflictError`.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from clinica_app.models.agenda import BloqueoAgenda, DisponibilidadProfesional
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.services import auditoria
from clinica_app.services.exceptions import NotFoundError, ValidationError

DIAS_SEMANA: list[dict[str, Any]] = [
    {"valor": 0, "label": "Lunes"},
    {"valor": 1, "label": "Martes"},
    {"valor": 2, "label": "Miércoles"},
    {"valor": 3, "label": "Jueves"},
    {"valor": 4, "label": "Viernes"},
    {"valor": 5, "label": "Sábado"},
    {"valor": 6, "label": "Domingo"},
]
_DIA_LABEL = {d["valor"]: d["label"] for d in DIAS_SEMANA}

_DURACION_DEFAULT = 30


def dias_catalogo() -> list[dict[str, Any]]:
    return [dict(d) for d in DIAS_SEMANA]


def _parse_hhmm(valor: str | None) -> int | None:
    """"HH:MM" → minutos desde medianoche; None si es inválido."""
    if not valor or ":" not in valor:
        return None
    try:
        h, m = valor.split(":", 1)
        hh, mm = int(h), int(m)
    except (ValueError, TypeError):
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return hh * 60 + mm


def _fmt_hhmm(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


# ── Disponibilidad ────────────────────────────────────────────────────────────

def _dump_disp(d: DisponibilidadProfesional) -> dict[str, Any]:
    return {
        "id":          d.id,
        "dia_semana":  d.dia_semana,
        "dia_label":   _DIA_LABEL.get(d.dia_semana, str(d.dia_semana)),
        "hora_inicio": d.hora_inicio,
        "hora_fin":    d.hora_fin,
    }


async def listar_disponibilidad(
    session: AsyncSession, clinica_id: int, profesional_id: int, sede_id: int = 0
) -> list[dict[str, Any]]:
    stmt = select(DisponibilidadProfesional).where(
        DisponibilidadProfesional.clinica_id == clinica_id,
        DisponibilidadProfesional.profesional_id == profesional_id,
        DisponibilidadProfesional.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(DisponibilidadProfesional.sede_id == sede_id)
    filas = (await session.execute(stmt)).scalars().all()
    filas = sorted(filas, key=lambda d: (d.dia_semana, _parse_hhmm(d.hora_inicio) or 0))
    return [_dump_disp(d) for d in filas]


async def agregar_disponibilidad(
    session: AsyncSession,
    clinica_id: int,
    profesional_id: int,
    *,
    dia_semana: int,
    hora_inicio: str,
    hora_fin: str,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    if dia_semana not in _DIA_LABEL:
        raise ValidationError("Día de la semana inválido")
    ini = _parse_hhmm(hora_inicio)
    fin = _parse_hhmm(hora_fin)
    if ini is None or fin is None:
        raise ValidationError("Horas inválidas (usá HH:MM)")
    if ini >= fin:
        raise ValidationError("La hora de inicio debe ser anterior a la de fin")

    d = DisponibilidadProfesional(
        clinica_id=clinica_id,
        profesional_id=profesional_id,
        sede_id=sede_id or None,
        dia_semana=dia_semana,
        hora_inicio=_fmt_hhmm(ini),
        hora_fin=_fmt_hhmm(fin),
    )
    session.add(d)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id, usuario_id=usuario_id,
        accion="crear", entidad="disponibilidad", entidad_id=d.id,
        detalle={"profesional_id": profesional_id, "dia": dia_semana, "rango": f"{d.hora_inicio}-{d.hora_fin}"},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_disp(d)


async def eliminar_disponibilidad(
    session: AsyncSession, clinica_id: int, disp_id: int, *, usuario_id: int | None = None, sede_id: int = 0
) -> None:
    d = (await session.execute(
        select(DisponibilidadProfesional).where(
            DisponibilidadProfesional.id == disp_id,
            DisponibilidadProfesional.clinica_id == clinica_id,
            DisponibilidadProfesional.is_active.is_(True),
        )
    )).scalars().first()
    if d is None:
        raise NotFoundError("Franja no encontrada")
    d.soft_delete()
    await auditoria.registrar(
        session, clinica_id, usuario_id=usuario_id,
        accion="eliminar", entidad="disponibilidad", entidad_id=d.id,
        detalle={"profesional_id": d.profesional_id},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Bloqueos ──────────────────────────────────────────────────────────────────

def _dump_bloqueo(b: BloqueoAgenda) -> dict[str, Any]:
    return {
        "id":     b.id,
        "inicio": b.inicio.strftime("%Y-%m-%d %H:%M") if b.inicio else "",
        "fin":    b.fin.strftime("%Y-%m-%d %H:%M") if b.fin else "",
        "motivo": b.motivo or "",
    }


async def listar_bloqueos(
    session: AsyncSession, clinica_id: int, profesional_id: int, sede_id: int = 0
) -> list[dict[str, Any]]:
    stmt = select(BloqueoAgenda).where(
        BloqueoAgenda.clinica_id == clinica_id,
        BloqueoAgenda.profesional_id == profesional_id,
        BloqueoAgenda.is_active.is_(True),
    )
    if sede_id:
        stmt = stmt.where(BloqueoAgenda.sede_id == sede_id)
    stmt = stmt.order_by(BloqueoAgenda.inicio.desc())
    filas = (await session.execute(stmt)).scalars().all()
    return [_dump_bloqueo(b) for b in filas]


def _parse_dt(valor: str) -> datetime:
    try:
        return datetime.fromisoformat(str(valor))
    except (ValueError, TypeError) as exc:
        raise ValidationError("Fecha/hora inválida") from exc


async def agregar_bloqueo(
    session: AsyncSession,
    clinica_id: int,
    profesional_id: int,
    *,
    inicio: str,
    fin: str,
    motivo: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    dt_ini = _parse_dt(inicio)
    dt_fin = _parse_dt(fin)
    if dt_ini >= dt_fin:
        raise ValidationError("El inicio debe ser anterior al fin")

    b = BloqueoAgenda(
        clinica_id=clinica_id,
        profesional_id=profesional_id,
        sede_id=sede_id or None,
        inicio=dt_ini,
        fin=dt_fin,
        motivo=(motivo or "").strip()[:200] or None,
    )
    session.add(b)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id, usuario_id=usuario_id,
        accion="crear", entidad="bloqueo_agenda", entidad_id=b.id,
        detalle={"profesional_id": profesional_id, "inicio": b.inicio.isoformat(), "fin": b.fin.isoformat()},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_bloqueo(b)


async def eliminar_bloqueo(
    session: AsyncSession, clinica_id: int, bloqueo_id: int, *, usuario_id: int | None = None, sede_id: int = 0
) -> None:
    b = (await session.execute(
        select(BloqueoAgenda).where(
            BloqueoAgenda.id == bloqueo_id,
            BloqueoAgenda.clinica_id == clinica_id,
            BloqueoAgenda.is_active.is_(True),
        )
    )).scalars().first()
    if b is None:
        raise NotFoundError("Bloqueo no encontrado")
    b.soft_delete()
    await auditoria.registrar(
        session, clinica_id, usuario_id=usuario_id,
        accion="eliminar", entidad="bloqueo_agenda", entidad_id=b.id,
        detalle={"profesional_id": b.profesional_id},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Verificación de disponibilidad ────────────────────────────────────────────

def _solapan(a_ini: datetime, a_fin: datetime, b_ini: datetime, b_fin: datetime) -> bool:
    return a_ini < b_fin and b_ini < a_fin


async def verificar(
    session: AsyncSession,
    clinica_id: int,
    profesional_id: int | None,
    fecha_hora: datetime,
    *,
    duracion_min: int = _DURACION_DEFAULT,
    sede_id: int = 0,
    excluir_turno_id: int = 0,
) -> dict[str, Any]:
    """Devuelve {"conflictos": [str]} para un turno propuesto. Sin profesional no
    hay nada que validar (los turnos sin profesional no chocan agenda)."""
    conflictos: list[str] = []
    if not profesional_id:
        return {"conflictos": conflictos}

    dur = duracion_min if duracion_min and duracion_min > 0 else _DURACION_DEFAULT
    inicio = fecha_hora
    fin = fecha_hora + timedelta(minutes=dur)

    # 1) Bloqueos (vacaciones / ausencia)
    bloqueos = (await session.execute(
        select(BloqueoAgenda).where(
            BloqueoAgenda.clinica_id == clinica_id,
            BloqueoAgenda.profesional_id == profesional_id,
            BloqueoAgenda.is_active.is_(True),
            BloqueoAgenda.inicio < fin,
            BloqueoAgenda.fin > inicio,
        )
    )).scalars().all()
    for b in bloqueos:
        etiqueta = f" ({b.motivo})" if b.motivo else ""
        conflictos.append(
            f"El profesional no está disponible{etiqueta}: bloqueo del "
            f"{b.inicio:%d/%m %H:%M} al {b.fin:%d/%m %H:%M}."
        )

    # 2) Solapamiento con otro turno del mismo profesional
    margen = timedelta(hours=12)
    otros = (await session.execute(
        select(Turno)
        .options(selectinload(Turno.servicio), selectinload(Turno.paciente))
        .where(
            Turno.clinica_id == clinica_id,
            Turno.profesional_id == profesional_id,
            Turno.is_active.is_(True),
            Turno.estado != EstadoTurno.CANCELADO,
            Turno.fecha_hora >= inicio - margen,
            Turno.fecha_hora <= fin + margen,
        )
    )).scalars().all()
    for t in otros:
        if excluir_turno_id and t.id == excluir_turno_id:
            continue
        t_dur = getattr(t.servicio, "duracion_min", None) or _DURACION_DEFAULT
        t_ini = t.fecha_hora
        t_fin = t_ini + timedelta(minutes=t_dur)
        if _solapan(inicio, fin, t_ini, t_fin):
            pac = getattr(t.paciente, "nombre", None) or "otro paciente"
            conflictos.append(
                f"Se superpone con el turno de {pac} el {t_ini:%d/%m %H:%M}."
            )

    # 3) Fuera del horario de atención (solo si el profesional tiene horario cargado)
    disp = (await session.execute(
        select(DisponibilidadProfesional).where(
            DisponibilidadProfesional.clinica_id == clinica_id,
            DisponibilidadProfesional.profesional_id == profesional_id,
            DisponibilidadProfesional.is_active.is_(True),
        )
    )).scalars().all()
    if disp:
        dia = fecha_hora.weekday()  # 0=lunes … 6=domingo
        min_ini = fecha_hora.hour * 60 + fecha_hora.minute
        min_fin = min_ini + dur
        dentro = any(
            d.dia_semana == dia
            and (_parse_hhmm(d.hora_inicio) or 0) <= min_ini
            and min_fin <= (_parse_hhmm(d.hora_fin) or 0)
            for d in disp
        )
        if not dentro:
            conflictos.append(
                f"Fuera del horario de atención del profesional ({_DIA_LABEL.get(dia, '')})."
            )

    return {"conflictos": conflictos}
