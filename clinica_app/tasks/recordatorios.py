"""
Worker de recordatorios de turnos.

Envía notificaciones (email + WhatsApp) a pacientes con turno en las próximas
~24 horas y registra el **estado de envío** por canal en `recordatorios_turno`.
Es **idempotente**: un turno que ya tiene al menos un canal `ENVIADO` no se
vuelve a recordar, así que correrlo dos veces (o que el scheduler dispare de
más) no spamea al paciente. Los turnos cuyo intento falló por completo (ningún
canal enviado) SÍ se reintentan en la corrida siguiente.

Uso manual (una corrida):
    python -m clinica_app.tasks.recordatorios

Automatizado: no llamar a este módulo por cron directamente salvo que quieras
esa mecánica; el camino recomendado es el servicio `life_scheduler`
(APScheduler) — ver `clinica_app/tasks/scheduler.py`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from clinica_app.database import _sync_engine as _engine
from clinica_app.models.paciente import Paciente
from clinica_app.models.recordatorio_turno import (
    CanalRecordatorio, EstadoRecordatorio, RecordatorioTurno,
)
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.services import notificaciones as notif
from clinica_app.services.turnos import _dump

log = logging.getLogger(__name__)

# Ventana de disparo: turnos que ocurren entre 20 y 28 h desde ahora. Con una
# corrida diaria, cada turno cae en la ventana una sola vez (~24 h antes).
_VENTANA_DESDE_H = 20
_VENTANA_HASTA_H = 28


def _ya_recordado(session: Session, turno_id: int) -> bool:
    """True si el turno ya tiene algún recordatorio ENVIADO (idempotencia)."""
    fila = session.exec(
        select(RecordatorioTurno.id).where(
            RecordatorioTurno.turno_id == turno_id,
            RecordatorioTurno.estado == EstadoRecordatorio.ENVIADO.value,
            RecordatorioTurno.is_active.is_(True),
        ).limit(1)
    ).first()
    return fila is not None


def enviar_recordatorios() -> dict[str, int]:
    """Envía los recordatorios pendientes de la ventana y registra su estado.

    Devuelve un resumen ``{turnos, recordados, omitidos, canales_ok,
    canales_fallidos}``:
      - ``turnos``: turnos activos en la ventana;
      - ``recordados``: turnos con al menos un canal enviado en esta corrida;
      - ``omitidos``: turnos salteados por idempotencia (ya recordados);
      - ``canales_ok`` / ``canales_fallidos``: intentos por canal.
    """
    ahora  = datetime.now(timezone.utc)
    desde  = ahora + timedelta(hours=_VENTANA_DESDE_H)
    hasta  = ahora + timedelta(hours=_VENTANA_HASTA_H)

    resumen = {"turnos": 0, "recordados": 0, "omitidos": 0,
               "canales_ok": 0, "canales_fallidos": 0}

    with Session(_engine) as session:
        turnos = session.exec(
            select(Turno).where(
                Turno.is_active.is_(True),
                Turno.fecha_hora >= desde,
                Turno.fecha_hora <= hasta,
                Turno.estado.in_([EstadoTurno.PENDIENTE, EstadoTurno.CONFIRMADO]),
            )
        ).all()
        resumen["turnos"] = len(turnos)

        for turno in turnos:
            if _ya_recordado(session, turno.id):
                resumen["omitidos"] += 1
                continue

            paciente = session.exec(
                select(Paciente).where(Paciente.id == turno.paciente_id)
            ).first()
            if paciente is None:
                continue

            turno_dict = _dump(turno)
            turno_dict["paciente_nombre"] = paciente.nombre
            email = paciente.email or ""
            tel   = paciente.telefono or ""

            try:
                resultados = notif.notificar_recordatorio(
                    turno_dict, paciente_email=email, paciente_tel=tel,
                )
            except Exception as exc:  # falla dura del proveedor → registrar y seguir
                log.error("Error enviando recordatorio turno %d: %s", turno.id, exc)
                resultados = {}

            destino_por_canal = {
                CanalRecordatorio.EMAIL.value:    email,
                CanalRecordatorio.WHATSAPP.value: tel,
            }
            enviado_algun_canal = False
            for canal, ok in resultados.items():
                estado = EstadoRecordatorio.ENVIADO if ok else EstadoRecordatorio.FALLIDO
                session.add(RecordatorioTurno(
                    clinica_id=turno.clinica_id,
                    turno_id=turno.id,
                    canal=canal,
                    estado=estado.value,
                    destino=destino_por_canal.get(canal) or None,
                ))
                if ok:
                    resumen["canales_ok"] += 1
                    enviado_algun_canal = True
                else:
                    resumen["canales_fallidos"] += 1

            if enviado_algun_canal:
                resumen["recordados"] += 1
                log.info("Recordatorio enviado: turno %d paciente %s", turno.id, paciente.nombre)

            # Commit por turno: el progreso persiste aunque un turno posterior falle.
            session.commit()

    return resumen


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = enviar_recordatorios()
    print(
        f"Turnos en ventana: {r['turnos']} | recordados: {r['recordados']} | "
        f"omitidos (ya recordados): {r['omitidos']} | "
        f"canales ok: {r['canales_ok']} | canales fallidos: {r['canales_fallidos']}"
    )
