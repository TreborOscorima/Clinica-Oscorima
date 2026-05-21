from __future__ import annotations

import os
from typing import Any

import redis
import rq

from clinica_app.config import REDIS_URL, REPORT_EXPORT_DIR


def _get_queue() -> rq.Queue:
    conn = redis.from_url(REDIS_URL)
    return rq.Queue("reportes", connection=conn)


def encolar_reporte(clinica_id: int, tipo: str, params: dict[str, Any]) -> str:
    """Encola un job de reporte en Redis/RQ. Retorna el job_id."""
    from clinica_app.tasks.reportes import generar_reporte  # import diferido
    q = _get_queue()
    job = q.enqueue(
        generar_reporte,
        clinica_id=clinica_id,
        tipo=tipo,
        params=params,
        job_timeout=600,
    )
    return job.id


def estado_job(job_id: str) -> dict[str, Any]:
    """Consulta el estado de un job RQ."""
    conn = redis.from_url(REDIS_URL)
    try:
        job = rq.job.Job.fetch(job_id, connection=conn)
        return {
            "job_id":   job_id,
            "status":   job.get_status().value,
            "result":   job.result,
            "error":    job.exc_info if job.is_failed else None,
        }
    except Exception:
        return {"job_id": job_id, "status": "not_found", "result": None, "error": None}
