from __future__ import annotations

from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, jwt_required

from services.exceptions import ServiceError
from services.pacientes import PacienteService
from utils.audit import log_action
from utils.decorators import role_required
from utils.tenant import get_current_clinica_id


bp = Blueprint("pacientes", __name__, url_prefix="/api/pacientes")


def _service() -> PacienteService:
    return PacienteService(get_current_clinica_id())


def _parse_dt(val: str | None):
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            pass
    return None


def _error_response(err: ServiceError):
    return {"message": err.message}, err.status_code


@bp.get("")
@jwt_required()
def listar():
    q = (request.args.get("q") or "").strip()
    desde = _parse_dt(request.args.get("desde"))
    hasta = _parse_dt(request.args.get("hasta"))
    page = int(request.args.get("page") or 1)
    per_page = min(max(int(request.args.get("per_page") or 20), 1), 200)

    return _service().listar(q=q, desde=desde, hasta=hasta, page=page, per_page=per_page)


@bp.post("")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def crear():
    try:
        paciente = _service().crear(request.json or {})
    except ServiceError as err:
        return _error_response(err)

    log_action(get_jwt().get("sub"), "crear_paciente", f"Paciente {paciente.id}")
    return _service().dump(paciente), 201


@bp.get("/<int:pid>")
@jwt_required()
def detalle(pid):
    try:
        paciente = _service().obtener(pid)
    except ServiceError as err:
        return _error_response(err)
    return _service().dump(paciente)


@bp.get("/<int:pid>/historial")
@jwt_required()
def historial(pid):
    try:
        return _service().historial(pid)
    except ServiceError as err:
        return _error_response(err)


@bp.put("/<int:pid>")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def actualizar(pid):
    try:
        paciente = _service().actualizar(pid, request.json or {})
    except ServiceError as err:
        return _error_response(err)

    log_action(get_jwt().get("sub"), "actualizar_paciente", f"Paciente {paciente.id}")
    return _service().dump(paciente)


@bp.delete("/<int:pid>")
@jwt_required()
@role_required("administracion")
def eliminar(pid):
    try:
        _service().eliminar(pid)
    except ServiceError as err:
        return _error_response(err)

    log_action(get_jwt().get("sub"), "eliminar_paciente", f"Paciente {pid}")
    return {"message": "Eliminado"}
