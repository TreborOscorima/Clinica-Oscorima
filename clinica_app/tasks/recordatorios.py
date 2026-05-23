"""
Worker de recordatorios de turnos.

Envía notificaciones (email + WhatsApp) a pacientes con turno en las próximas 24 horas.

Uso manual:
    python -m clinica_app.tasks.recordatorios

Para automatizar (Windows Task Scheduler o cron Linux):
    # Ejecutar una vez por día a las 18:00 hs
    0 18 * * * /ruta/venv/bin/python -m clinica_app.tasks.recordatorios
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from clinica_app.database import _engine
from clinica_app.models.paciente import Paciente
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.services import notificaciones as notif
from clinica_app.services.turnos import _dump

log = logging.getLogger(__name__)


def enviar_recordatorios() -> int:
    """
    Busca todos los turnos pendientes/confirmados que ocurren entre
    las próximas 20 y 28 horas y envía recordatorios.
    Devuelve la cantidad de recordatorios enviados.
    """
    ahora    = datetime.now(timezone.utc)
    desde    = ahora + timedelta(hours=20)
    hasta    = ahora + timedelta(hours=28)
    enviados = 0

    with Session(_engine) as session:
        turnos = session.exec(
            select(Turno)
            .where(
                Turno.is_active.is_(True),
                Turno.fecha_hora >= desde,
                Turno.fecha_hora <= hasta,
                Turno.estado.in_([EstadoTurno.PENDIENTE, EstadoTurno.CONFIRMADO]),
            )
        ).all()

        for turno in turnos:
            # Cargar paciente manualmente para tener email/telefono
            paciente = session.exec(
                select(Paciente).where(Paciente.id == turno.paciente_id)
            ).first()
            if paciente is None:
                continue

            turno_dict = _dump(turno)
            turno_dict["paciente_nombre"] = paciente.nombre

            try:
                notif.notificar_recordatorio(
                    turno_dict,
                    paciente_email=paciente.email or "",
                    paciente_tel=paciente.telefono or "",
                )
                enviados += 1
                log.info(
                    "Recordatorio enviado: turno %d paciente %s",
                    turno.id,
                    paciente.nombre,
                )
            except Exception as exc:
                log.error("Error enviando recordatorio turno %d: %s", turno.id, exc)

    return enviados


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    total = enviar_recordatorios()
    print(f"Recordatorios enviados: {total}")
