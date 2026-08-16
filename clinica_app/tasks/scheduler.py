"""
Scheduler de tareas de fondo — proceso/servicio aparte.

Corre como un contenedor dedicado (`life_scheduler` en docker-compose), NO dentro
del proceso de Reflex: así no toca el event loop de la app y un reinicio de la UI
no interrumpe los envíos (ni al revés). Un único proceso ⇒ no hay disparos
duplicados.

Hoy programa una sola tarea: el worker de recordatorios de turnos, una vez por
día a `RECORDATORIOS_HORA` (hora local `RECORDATORIOS_TZ`).

Implementación: un loop `sleep` que calcula el próximo disparo con `zoneinfo` de
la stdlib (sin dependencias externas; correcto ante cambios de hora/DST porque el
objetivo se resuelve como hora de pared local en cada iteración). Agregar tareas
nuevas con otra cadencia = generalizar `_segundos_hasta` o sumar más loops.

Uso:
    python -m clinica_app.tasks.scheduler
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from clinica_app.config import RECORDATORIOS_HORA, RECORDATORIOS_TZ
from clinica_app.tasks.recordatorios import enviar_recordatorios

log = logging.getLogger(__name__)


def _hora_minuto(hhmm: str) -> tuple[int, int]:
    """Parsea 'HH:MM' → (hora, minuto), con fallback a 18:00 si es inválido."""
    try:
        h, m = hhmm.strip().split(":", 1)
        hora, minuto = int(h), int(m)
        if 0 <= hora <= 23 and 0 <= minuto <= 59:
            return hora, minuto
    except (ValueError, AttributeError):
        pass
    log.warning("RECORDATORIOS_HORA inválida (%r); usando 18:00", hhmm)
    return 18, 0


def _tz(nombre: str) -> ZoneInfo:
    try:
        return ZoneInfo(nombre)
    except Exception:
        log.warning("RECORDATORIOS_TZ inválida (%r); usando UTC", nombre)
        return ZoneInfo("UTC")


def _proximo_disparo(ahora: datetime, hora: int, minuto: int) -> datetime:
    """Próxima ocurrencia (aware) de hora:minuto local a partir de `ahora`."""
    objetivo = ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    if objetivo <= ahora:
        objetivo += timedelta(days=1)
    return objetivo


def _job_recordatorios() -> None:
    """Wrapper con logging: una excepción no debe cortar el loop del scheduler."""
    try:
        resumen = enviar_recordatorios()
        log.info("Recordatorios: %s", resumen)
    except Exception:
        log.exception("Falló la corrida de recordatorios")


def main(*, _una_vuelta: bool = False) -> None:
    """Loop principal. `_una_vuelta` es solo para tests (no bloquea indefinido)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    tz = _tz(RECORDATORIOS_TZ)
    hora, minuto = _hora_minuto(RECORDATORIOS_HORA)
    log.info(
        "Scheduler iniciado — recordatorios diarios a las %02d:%02d (%s)",
        hora, minuto, RECORDATORIOS_TZ,
    )
    while True:
        ahora     = datetime.now(tz)
        proximo   = _proximo_disparo(ahora, hora, minuto)
        segundos  = max(1.0, (proximo - ahora).total_seconds())
        log.info("Próximo disparo: %s (en %.0f s)", proximo.isoformat(), segundos)
        try:
            time.sleep(segundos)
        except (KeyboardInterrupt, SystemExit):
            log.info("Scheduler detenido")
            return
        _job_recordatorios()
        if _una_vuelta:
            return


if __name__ == "__main__":
    main()
