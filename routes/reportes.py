from io import StringIO
import csv
import os
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, current_app, request, Response, send_file
from flask_jwt_extended import jwt_required, get_jwt
from redis.exceptions import RedisError
from rq.job import Job
from rq.exceptions import NoSuchJobError

from services.reportes import EXPORT_MIMETYPES, VALID_EXPORT_REPORT_TYPES, ReportesService, build_report_export_file
from utils.tenant import get_current_clinica_id
from tasks.queue import get_queue, get_redis_connection

bp = Blueprint("reportes", __name__, url_prefix="/api/reportes")


def _clinica_id() -> int:
    return get_current_clinica_id()


def _service() -> ReportesService:
    return ReportesService(_clinica_id())


# ---------- ATENCIONES ----------
@bp.get("/atenciones")
@jwt_required()
def atenciones():
    """
    Reporte de atenciones (turnos en estado 'atendido') agrupadas por
    profesional | servicio | día
    """
    return _service().atenciones(request.args)

# ---------- FACTURACIÓN / CAJA ----------
@bp.get("/facturacion")
@jwt_required()
def facturacion():
    return _service().facturacion(request.args)

# ---------- STOCK ----------
@bp.get("/stock_bajo")
@jwt_required()
def stock_bajo():
    """
    Productos cuyo stock_actual <= stock_minimo
    """
    return _service().stock_bajo()

# ---------- PACIENTES ----------
@bp.get("/pacientes")
@jwt_required()
def rep_pacientes():
    """
    Pacientes nuevos (creados en rango), frecuentes (>=N turnos en rango), inactivos (sin turnos últimos M días)
    """
    return _service().pacientes_resumen(request.args)


# ---------- EXPORTES ESPECÍFICOS ----------
@bp.get("/facturacion/export/excel")
@jwt_required()
def exportar_facturacion_excel():
    params = request.args or {}
    file_path = _build_export_file("facturacion", "excel", params, _current_user_label())
    return _send_export_file(file_path, "excel")


@bp.get("/facturacion/export/pdf")
@jwt_required()
def exportar_facturacion_pdf():
    params = request.args or {}
    file_path = _build_export_file("facturacion", "pdf", params, _current_user_label())
    return _send_export_file(file_path, "pdf")


def _current_user_label() -> str:
    claims = get_jwt() or {}
    return claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")


def _build_export_file(report_type: str, formato: str, params: Dict[str, Any], user_label: str) -> str:
    return build_report_export_file(report_type, formato, params, user_label, _clinica_id())


def _send_export_file(file_path: str, formato: str):
    return send_file(
        file_path,
        mimetype=EXPORT_MIMETYPES[formato],
        as_attachment=True,
        download_name=os.path.basename(file_path),
    )


def _export_dir() -> Path:
    return Path(current_app.config.get("REPORT_EXPORT_DIR", "exports")).resolve()


def _job_payload(job: Job) -> Dict[str, Any]:
    payload = {
        "job_id": job.id,
        "status": job.get_status(refresh=True),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
    }
    if job.is_finished:
        result = job.result or {}
        payload["result"] = result
        if result.get("file_path"):
            payload["download_url"] = f"/api/reportes/exportar/jobs/{job.id}/download"
    if job.is_failed:
        payload["error"] = (job.exc_info or "").splitlines()[-1:] or ["Job fallido"]
        payload["error"] = payload["error"][0]
    return payload


@bp.post("/exportar/async")
@jwt_required()
def exportar_async():
    payload = request.get_json(silent=True) or {}
    report_type = (payload.get("tipo") or payload.get("reporte") or "").strip().lower()
    formato = (payload.get("formato") or "excel").strip().lower()
    filtros = payload.get("filtros") or {}
    if not isinstance(filtros, dict):
        return {"message": "filtros debe ser un objeto"}, 400
    if formato not in EXPORT_MIMETYPES:
        return {"message": "formato inválido"}, 400
    if report_type not in VALID_EXPORT_REPORT_TYPES:
        return {"message": "tipo de reporte inválido"}, 400

    try:
        queue = get_queue()
        queue.connection.ping()
        job = queue.enqueue(
            "tasks.reportes.export_report_job",
            report_type,
            formato,
            filtros,
            _clinica_id(),
            _current_user_label(),
            job_timeout=current_app.config.get("REPORT_EXPORT_JOB_TIMEOUT", 600),
        )
    except RedisError as exc:
        return {
            "message": "Redis no está disponible. El exportador síncrono sigue funcionando para desarrollo local.",
            "detail": str(exc),
        }, 503

    return {
        "job_id": job.id,
        "status": job.get_status(refresh=True),
        "queue": queue.name,
    }, 202


@bp.get("/exportar/jobs/<job_id>")
@jwt_required()
def exportar_job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=get_redis_connection())
    except NoSuchJobError:
        return {"message": "Job no encontrado"}, 404
    except RedisError as exc:
        return {"message": "Redis no está disponible", "detail": str(exc)}, 503
    return _job_payload(job)


@bp.get("/exportar/jobs/<job_id>/download")
@jwt_required()
def exportar_job_download(job_id: str):
    try:
        job = Job.fetch(job_id, connection=get_redis_connection())
    except NoSuchJobError:
        return {"message": "Job no encontrado"}, 404
    except RedisError as exc:
        return {"message": "Redis no está disponible", "detail": str(exc)}, 503

    if not job.is_finished or not isinstance(job.result, dict):
        return {"message": "El archivo todavía no está disponible"}, 409

    file_path = Path(job.result.get("file_path") or "").resolve()
    export_dir = _export_dir()
    if file_path != export_dir and export_dir not in file_path.parents:
        return {"message": "Archivo fuera del directorio de exportación"}, 403
    if not file_path.exists():
        return {"message": "Archivo no encontrado"}, 404

    return send_file(
        str(file_path),
        mimetype=job.result.get("mimetype") or "application/octet-stream",
        as_attachment=True,
        download_name=job.result.get("download_name") or file_path.name,
    )


@bp.get("/pacientes/export/excel")
@jwt_required()
def exportar_pacientes_excel():
    params = request.args or {}
    file_path = _build_export_file("pacientes", "excel", params, _current_user_label())
    return _send_export_file(file_path, "excel")


@bp.get("/pacientes/export/pdf")
@jwt_required()
def exportar_pacientes_pdf():
    params = request.args or {}
    file_path = _build_export_file("pacientes", "pdf", params, _current_user_label())
    return _send_export_file(file_path, "pdf")


@bp.get("/inventario/export/excel")
@jwt_required()
def exportar_inventario_excel():
    params = request.args or {}
    file_path = _build_export_file("inventario", "excel", params, _current_user_label())
    return _send_export_file(file_path, "excel")


@bp.get("/inventario/export/pdf")
@jwt_required()
def exportar_inventario_pdf():
    params = request.args or {}
    file_path = _build_export_file("inventario", "pdf", params, _current_user_label())
    return _send_export_file(file_path, "pdf")


@bp.get("/turnos/export/excel")
@jwt_required()
def exportar_turnos_excel():
    params = request.args or {}
    file_path = _build_export_file("turnos", "excel", params, _current_user_label())
    return _send_export_file(file_path, "excel")


@bp.get("/turnos/export/pdf")
@jwt_required()
def exportar_turnos_pdf():
    params = request.args or {}
    file_path = _build_export_file("turnos", "pdf", params, _current_user_label())
    return _send_export_file(file_path, "pdf")


# ---------- EXPORTAR CSV ----------
@bp.get("/exportar/csv")
@jwt_required()
def export_csv():
    """
    Exporta a CSV según tipo:
      - tipo=atenciones&group_by=...&desde=...&hasta=...
      - tipo=facturacion&group_by=...&desde=...&hasta=...&tipo=ingreso|egreso|ambos
      - tipo=stock_bajo
    """
    tipo = (request.args.get("tipo") or "").lower()
    if tipo not in ("atenciones","facturacion","stock_bajo"):
        return {"message":"tipo inválido"}, 400

    if tipo == "stock_bajo":
        payload = stock_bajo()
        rows = payload["data"]
        headers = ["id","sku","nombre","categoria","stock_actual","stock_minimo","unidad"]
    elif tipo == "atenciones":
        payload = atenciones()
        rows = payload["data"]
        headers = ["clave","cantidad"]
    else:  # facturacion
        payload = facturacion()
        rows = payload["data"]
        headers = ["clave","monto","total_global"]
        total = payload.get("total", 0)
        for r in rows:
            r["total_global"] = total

    sio = StringIO()
    w = csv.DictWriter(sio, fieldnames=headers)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in headers})
    csv_bytes = sio.getvalue().encode("utf-8-sig")
    return Response(csv_bytes, mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=reporte.csv"})

