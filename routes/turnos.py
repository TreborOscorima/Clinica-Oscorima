from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, jwt_required

from services.exceptions import ServiceError
from services.turnos import TurnoService
from utils.audit import log_action
from utils.decorators import role_required
from utils.tenant import get_current_clinica_id


bp = Blueprint("turnos", __name__, url_prefix="/api/turnos")


def _service() -> TurnoService:
    return TurnoService(get_current_clinica_id())


def _error_response(err: ServiceError):
    return {"message": err.message}, err.status_code


@bp.get("/<int:tid>")
@jwt_required()
def obtener(tid):
    try:
        turno = _service().obtener(tid)
    except ServiceError as err:
        return _error_response(err)
    return _service().dump(turno), 200


@bp.get("")
@jwt_required()
def listar():
    args = request.args
    estado = (args.get("estado") or "").strip().lower()

    try:
        page = max(1, int(args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = int(args.get("per_page", 10))
    except (TypeError, ValueError):
        per_page = 10
    per_page = max(1, min(50, per_page))

    try:
        return _service().listar(estado=estado, page=page, per_page=per_page)
    except ServiceError as err:
        return _error_response(err)


@bp.post("")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear():
    payload = request.get_json(silent=True) or {}
    claims = get_jwt() or {}

    try:
        turno = _service().crear(payload, created_by=claims.get("sub"))
    except ServiceError as err:
        return _error_response(err)

    log_action(claims.get("sub"), "crear_turno", f"Turno {turno.id}")
    return _service().dump(turno), 201


@bp.put("/<int:tid>/estado")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def cambiar_estado(tid):
    payload = request.get_json(silent=True) or {}
    try:
        response = _service().cambiar_estado(tid, payload)
    except ServiceError as err:
        return _error_response(err)

    estado = response.get("estado")
    log_action(get_jwt().get("sub"), "actualizar_turno", f"Turno {tid} -> {estado}")
    return response


@bp.put("/<int:tid>/reprogramar")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def reprogramar(tid):
    payload = request.get_json(silent=True) or {}
    try:
        turno = _service().reprogramar(tid, payload)
    except ServiceError as err:
        return _error_response(err)

    log_action(get_jwt().get("sub"), "reprogramar_turno", f"Turno {turno.id} -> {turno.fecha_hora} {turno.estado}")
    return _service().dump(turno), 200
