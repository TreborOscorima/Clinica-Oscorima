from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from clinica_app.config import RECORDATORIOS_TZ
from clinica_app.models.caja import CajaMovimiento, MetodoPago, TipoMovimiento
from clinica_app.models.clinica import Clinica
from clinica_app.models.paciente import Paciente
from clinica_app.models.servicio import Servicio
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.models.turno_servicio import TurnoServicio
from clinica_app.services.exceptions import ConflictError, NotFoundError, ServiceError
from clinica_app.services import agenda as _agenda
from clinica_app.services import notificaciones as notif


# Transiciones de estado permitidas (máquina de estados del turno). `atendido`
# es terminal (puede tener cobro asociado); `cancelado` sólo se puede reactivar
# volviéndolo a `pendiente`.
_TRANSICIONES: dict[EstadoTurno, set[EstadoTurno]] = {
    EstadoTurno.PENDIENTE:  {EstadoTurno.CONFIRMADO, EstadoTurno.CANCELADO, EstadoTurno.ATENDIDO},
    EstadoTurno.CONFIRMADO: {EstadoTurno.PENDIENTE, EstadoTurno.CANCELADO, EstadoTurno.ATENDIDO},
    EstadoTurno.ATENDIDO:   set(),
    EstadoTurno.CANCELADO:  {EstadoTurno.PENDIENTE},
}


def transiciones_validas(estado_actual: str) -> list[str]:
    """Estados a los que se puede pasar desde `estado_actual` (para la UI)."""
    try:
        actual = EstadoTurno(estado_actual)
    except ValueError:
        return []
    return [e.value for e in EstadoTurno if e in _TRANSICIONES.get(actual, set())]


# Tolerancia para el bloqueo de fecha pasada: el input datetime-local trunca a
# minuto y puede haber skew de reloj, así que no rechazamos turnos "de este
# mismo minuto". Sí rechaza cualquier fecha/hora claramente anterior.
_GRACIA_PASADO = timedelta(minutes=2)


def _ahora_local(tz_nombre: str | None = None) -> datetime:
    """Ahora en la zona horaria de la clínica, naive, para comparar con la
    fecha/hora (wall-clock local) que el usuario elige en el formulario.

    Si falta la base de datos de zonas horarias (host sin `tzdata`), cae a UTC
    con la stdlib, que nunca falla."""
    try:
        tz: Any = ZoneInfo(tz_nombre or RECORDATORIOS_TZ)
    except Exception:
        tz = timezone.utc
    return datetime.now(tz).replace(tzinfo=None)


def _es_pasado(fecha: datetime, tz_nombre: str | None = None) -> bool:
    return fecha < _ahora_local(tz_nombre) - _GRACIA_PASADO


async def _tz_clinica(session: AsyncSession, clinica_id: int) -> str | None:
    c = await session.get(Clinica, clinica_id)
    return getattr(c, "zona_horaria", None) if c else None


async def _duracion_servicio(session: AsyncSession, clinica_id: int, servicio_id: int | None) -> int:
    """Duración (min) del servicio del turno; 30 por defecto si no hay servicio."""
    if not servicio_id:
        return 30
    s = (await session.execute(
        select(Servicio).where(Servicio.id == servicio_id, Servicio.clinica_id == clinica_id)
    )).scalars().first()
    return getattr(s, "duracion_min", None) or 30


async def _validar_agenda(
    session: AsyncSession,
    clinica_id: int,
    *,
    profesional_id: int | None,
    servicio_id: int | None,
    fecha_hora: datetime,
    sede_id: int,
    excluir_turno_id: int = 0,
) -> None:
    """Corta con ConflictError si el turno choca con la agenda del profesional."""
    if not profesional_id:
        return
    dur = await _duracion_servicio(session, clinica_id, servicio_id)
    res = await _agenda.verificar(
        session, clinica_id, profesional_id, fecha_hora,
        duracion_min=dur, sede_id=sede_id, excluir_turno_id=excluir_turno_id,
    )
    if res["conflictos"]:
        raise ConflictError(" ".join(res["conflictos"]))


def _dump(t: Turno) -> dict[str, Any]:
    paciente_nombre = getattr(t.paciente, "nombre", None) if t.paciente else None
    prof = t.profesional
    prof_nombre = (
        f"{(prof.nombres or '').strip()} {(prof.apellidos or '').strip()}".strip()
        if prof else None
    )
    servicio_nombre = getattr(t.servicio, "nombre", None) if t.servicio else None
    items = []
    for item in (t.items or []):
        items.append({
            "id":          item.id,
            "servicio_id": item.servicio_id,
            "servicio":    getattr(item.servicio, "nombre", None),
            "precio":      str(item.precio) if item.precio is not None else None,
            "cantidad":    str(item.cantidad) if item.cantidad is not None else None,
            "descuento":   str(item.descuento) if item.descuento is not None else None,
        })
    return {
        "id":                  t.id,
        "paciente_id":         t.paciente_id,
        "paciente_nombre":     paciente_nombre,
        "profesional_id":      t.profesional_id,
        "profesional_nombre":  prof_nombre,
        "servicio_id":         t.servicio_id,
        "servicio_nombre":     servicio_nombre,
        "fecha_hora":          t.fecha_hora.strftime("%Y-%m-%d %H:%M") if t.fecha_hora else "",
        "estado":              t.estado.value if t.estado else None,
        "motivo_cancelacion":  t.motivo_cancelacion,
        "items":               items,
        "created_at":          t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
    }


def _base_query(clinica_id: int, sede_id: int = 0):
    stmt = (
        select(Turno)
        .options(
            selectinload(Turno.paciente),
            selectinload(Turno.profesional),
            selectinload(Turno.servicio),
            selectinload(Turno.items).selectinload(TurnoServicio.servicio),
        )
        .where(Turno.clinica_id == clinica_id, Turno.is_active.is_(True))
    )
    if sede_id:
        stmt = stmt.where(Turno.sede_id == sede_id)
    return stmt


async def listar(
    session: AsyncSession,
    clinica_id: int,
    sede_id: int = 0,
    estado: str = "",
    fecha_desde: str = "",
    fecha_hasta: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = _base_query(clinica_id, sede_id)
    if estado:
        try:
            stmt = stmt.where(Turno.estado == EstadoTurno(estado))
        except ValueError as exc:
            raise ServiceError("Estado inválido") from exc
    if fecha_desde:
        try:
            stmt = stmt.where(Turno.fecha_hora >= datetime.fromisoformat(fecha_desde))
        except ValueError:
            pass
    if fecha_hasta:
        try:
            stmt = stmt.where(Turno.fecha_hora <= datetime.fromisoformat(fecha_hasta + "T23:59:59"))
        except ValueError:
            pass

    count_stmt = select(Turno).where(Turno.clinica_id == clinica_id, Turno.is_active.is_(True))
    if sede_id:
        count_stmt = count_stmt.where(Turno.sede_id == sede_id)
    if estado:
        try:
            count_stmt = count_stmt.where(Turno.estado == EstadoTurno(estado))
        except ValueError:
            pass
    if fecha_desde:
        try:
            count_stmt = count_stmt.where(Turno.fecha_hora >= datetime.fromisoformat(fecha_desde))
        except ValueError:
            pass
    if fecha_hasta:
        try:
            count_stmt = count_stmt.where(Turno.fecha_hora <= datetime.fromisoformat(fecha_hasta + "T23:59:59"))
        except ValueError:
            pass
    total: int = (
        await session.execute(select(func.count()).select_from(count_stmt.subquery()))
    ).scalar_one()
    items = (
        await session.execute(
            stmt.order_by(Turno.fecha_hora.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    return {
        "data":     [_dump(t) for t in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, -(-total // per_page)),
    }


async def obtener(session: AsyncSession, clinica_id: int, turno_id: int, sede_id: int = 0) -> Turno:
    t = (
        await session.execute(
            _base_query(clinica_id, sede_id).where(Turno.id == turno_id)
        )
    ).scalars().first()
    if t is None:
        raise NotFoundError("Turno no encontrado")
    return t


async def crear(
    session: AsyncSession,
    clinica_id: int,
    payload: dict[str, Any],
    created_by_id: int | None = None,
    sede_id: int = 0,
    validar_agenda: bool = False,
) -> dict[str, Any]:
    paciente_id = payload.get("paciente_id")
    if not paciente_id:
        raise ServiceError("paciente_id requerido")

    paciente = (
        await session.execute(
            select(Paciente).where(
                Paciente.id == paciente_id,
                Paciente.clinica_id == clinica_id,
                Paciente.is_active.is_(True),
            )
        )
    ).scalars().first()
    if paciente is None:
        raise NotFoundError("Paciente no encontrado en esta clínica")

    fecha_hora_str = payload.get("fecha_hora")
    if not fecha_hora_str:
        raise ServiceError("fecha_hora requerida")
    try:
        fecha_hora = datetime.fromisoformat(str(fecha_hora_str))
    except ValueError as exc:
        raise ServiceError("fecha_hora inválida (ISO 8601)") from exc

    if _es_pasado(fecha_hora, await _tz_clinica(session, clinica_id)):
        raise ServiceError("No se puede agendar un turno en una fecha/hora pasada")

    if validar_agenda:
        await _validar_agenda(
            session, clinica_id,
            profesional_id=payload.get("profesional_id"),
            servicio_id=payload.get("servicio_id"),
            fecha_hora=fecha_hora,
            sede_id=sede_id,
        )

    turno = Turno(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        paciente_id=paciente_id,
        profesional_id=payload.get("profesional_id"),
        servicio_id=payload.get("servicio_id"),
        fecha_hora=fecha_hora,
        estado=EstadoTurno.PENDIENTE,
        created_by_id=created_by_id,
    )
    session.add(turno)
    await session.flush()

    for item_data in (payload.get("items") or []):
        item = TurnoServicio(
            turno_id=turno.id,
            servicio_id=item_data["servicio_id"],
            precio=item_data.get("precio"),
            cantidad=Decimal(str(item_data.get("cantidad", "1"))),
            descuento=Decimal(str(item_data.get("descuento", "0"))),
            nota=item_data.get("nota"),
        )
        session.add(item)

    await session.flush()
    turno = (
        await session.execute(_base_query(clinica_id).where(Turno.id == turno.id))
    ).scalars().first()
    turno_dict = _dump(turno)

    try:
        notif.notificar_turno_nuevo(
            turno_dict,
            paciente_email=getattr(paciente, "email", "") or "",
            paciente_tel=getattr(paciente, "telefono", "") or "",
        )
    except Exception:
        pass

    return turno_dict


async def cambiar_estado(
    session: AsyncSession, clinica_id: int, turno_id: int, payload: dict[str, Any], sede_id: int = 0
) -> dict[str, Any]:
    turno = await obtener(session, clinica_id, turno_id, sede_id=sede_id)
    estado_str = (payload.get("estado") or "").strip().lower()
    try:
        nuevo_estado = EstadoTurno(estado_str)
    except ValueError as exc:
        raise ServiceError("Estado inválido") from exc

    actual = turno.estado or EstadoTurno.PENDIENTE
    if nuevo_estado == actual:
        raise ConflictError(f"El turno ya está {actual.value}")
    if nuevo_estado not in _TRANSICIONES.get(actual, set()):
        raise ConflictError(
            f"No se puede pasar de «{actual.value}» a «{nuevo_estado.value}»"
        )

    turno.estado = nuevo_estado
    if nuevo_estado == EstadoTurno.CANCELADO and payload.get("motivo_cancelacion"):
        turno.motivo_cancelacion = payload["motivo_cancelacion"]

    if nuevo_estado == EstadoTurno.ATENDIDO and payload.get("cobrar"):
        _registrar_cobro(session, turno, payload)

    await session.flush()
    turno = (
        await session.execute(_base_query(clinica_id).where(Turno.id == turno.id))
    ).scalars().first()
    turno_dict = _dump(turno)

    try:
        pac = turno.paciente
        p_email = getattr(pac, "email", "") or ""
        p_tel   = getattr(pac, "telefono", "") or ""
        if nuevo_estado == EstadoTurno.CONFIRMADO:
            notif.notificar_turno_confirmado(turno_dict, p_email, p_tel)
        elif nuevo_estado == EstadoTurno.CANCELADO:
            notif.notificar_turno_cancelado(turno_dict, p_email, p_tel)
    except Exception:
        pass

    return turno_dict


async def reprogramar(
    session: AsyncSession, clinica_id: int, turno_id: int, payload: dict[str, Any], sede_id: int = 0,
    validar_agenda: bool = False,
) -> dict[str, Any]:
    turno = await obtener(session, clinica_id, turno_id, sede_id=sede_id)
    nueva_fecha = payload.get("fecha_hora")
    if not nueva_fecha:
        raise ServiceError("fecha_hora requerida")
    try:
        nueva_dt = datetime.fromisoformat(str(nueva_fecha))
    except ValueError as exc:
        raise ServiceError("fecha_hora inválida") from exc

    if _es_pasado(nueva_dt, await _tz_clinica(session, clinica_id)):
        raise ServiceError("No se puede reprogramar a una fecha/hora pasada")

    if validar_agenda:
        await _validar_agenda(
            session, clinica_id,
            profesional_id=turno.profesional_id,
            servicio_id=turno.servicio_id,
            fecha_hora=nueva_dt,
            sede_id=sede_id,
            excluir_turno_id=turno_id,
        )
    turno.fecha_hora = nueva_dt
    if payload.get("estado"):
        try:
            turno.estado = EstadoTurno(payload["estado"])
        except ValueError as exc:
            raise ServiceError("estado inválido") from exc
    await session.flush()
    turno = (
        await session.execute(_base_query(clinica_id).where(Turno.id == turno.id))
    ).scalars().first()
    return _dump(turno)


def _registrar_cobro(session: AsyncSession, turno: Turno, payload: dict[str, Any]) -> None:
    monto_req = payload.get("monto")
    if monto_req is None:
        monto = _calcular_total(turno)
    else:
        try:
            monto = Decimal(str(monto_req))
        except Exception as exc:
            raise ServiceError("Monto inválido") from exc

    if monto <= 0:
        raise ServiceError("Monto inválido")

    metodo_str = (payload.get("metodo_pago") or "efectivo").lower()
    try:
        metodo = MetodoPago(metodo_str)
    except ValueError:
        metodo = MetodoPago.OTRO

    mov = CajaMovimiento(
        clinica_id=turno.clinica_id,
        sede_id=turno.sede_id,
        tipo=TipoMovimiento.INGRESO,
        monto=monto,
        metodo_pago=metodo,
        paciente_id=turno.paciente_id,
        profesional_id=turno.profesional_id,
        turno_id=turno.id,
        observacion=f"Cobro por turno {turno.id}",
    )
    session.add(mov)


def _calcular_total(turno: Turno) -> Decimal:
    total = Decimal("0")
    if turno.items:
        for item in turno.items:
            precio = item.precio if item.precio is not None else getattr(item.servicio, "precio", Decimal("0"))
            cantidad = Decimal(str(item.cantidad or 1))
            descuento = Decimal(str(item.descuento or 0))
            total += (Decimal(str(precio or 0)) * cantidad) - descuento
    elif turno.servicio:
        total = Decimal(str(getattr(turno.servicio, "precio", 0) or 0))
    return total
