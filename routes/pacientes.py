# routes/pacientes.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import or_, cast, String
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from extensions import db
from models.paciente import Paciente
from models.turno import Turno, EstadoTurno
from models.turno_servicio import TurnoServicio
from models.servicio import Servicio
from models.profesional import Profesional
from schemas.paciente import PacienteSchema
from schemas.historial import HistorialResponseSchema
from utils.decorators import role_required
from utils.audit import log_action

bp = Blueprint("pacientes", __name__, url_prefix="/api/pacientes")
schema = PacienteSchema()
schema_many = PacienteSchema(many=True)
historial_schema = HistorialResponseSchema()

def _parse_bool(val: str | None):
    if val is None:
        return None
    val = val.strip().lower()
    return val in ("true", "1", "t", "yes", "si", "sí") if val else None

def _parse_dt(val: str | None):
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            pass
    return None

@bp.get("")
@jwt_required()
def listar():
    """
    GET /api/pacientes?q=juan&desde=2025-08-01&hasta=2025-08-31&page=1&per_page=20
    Filtros:
      - q: busca en nombre y documento
      - desde/hasta: por created_at
      - activo: si tu modelo tuviera ese campo (hoy no lo tiene)
    """
    q = (request.args.get("q") or "").strip()
    # activo eliminado porque tu modelo Paciente no tiene ese campo
    desde = _parse_dt(request.args.get("desde"))
    hasta = _parse_dt(request.args.get("hasta"))
    page = int(request.args.get("page") or 1)
    per_page = min(max(int(request.args.get("per_page") or 20), 1), 200)

    query = Paciente.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Paciente.nombre.ilike(like),
                cast(Paciente.documento, String).ilike(like),
            )
        )

    if desde:
        query = query.filter(Paciente.created_at >= desde)
    if hasta:
        if hasta.hour == 0 and hasta.minute == 0:
            hasta = hasta + timedelta(days=1)
        query = query.filter(Paciente.created_at < hasta)

    pag = query.order_by(Paciente.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return {
        "data": schema_many.dump(pag.items),
        "page": pag.page,
        "per_page": pag.per_page,
        "total": pag.total,
        "pages": pag.pages,
    }

@bp.post("")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def crear():
    data = schema.load(request.json or {}, session=db.session)  # hace compat: dni→documento
    # Chequeos anti-duplicado
    if data.documento:
        dup = Paciente.query.filter(Paciente.documento == data.documento).first()
        if dup:
            return {"message": "Paciente ya registrado (DNI duplicado)"}, 409
    if data.email:
        dup_mail = Paciente.query.filter(Paciente.email == data.email).first()
        if dup_mail:
            return {"message": "Email ya registrado en otro paciente"}, 409

    db.session.add(data)
    db.session.commit()
    log_action(get_jwt().get("sub"), "crear_paciente", f"Paciente {data.id}")
    return schema.dump(data), 201

@bp.get("/<int:pid>")
@jwt_required()
def detalle(pid):
    p = Paciente.query.get_or_404(pid)
    return schema.dump(p)

@bp.get("/<int:pid>/historial")
@jwt_required()
def historial(pid):
    paciente = Paciente.query.get_or_404(pid)

    estados_historial = [EstadoTurno.ATENDIDO.value]
    estado_cobrado = getattr(EstadoTurno, "COBRADO", None)
    if estado_cobrado:
        estados_historial.append(estado_cobrado.value)
    else:
        estados_historial.append("cobrado")
    estados_historial = list(dict.fromkeys(estados_historial))

    turnos = (
        Turno.query.options(
            joinedload(Turno.profesional),
            joinedload(Turno.items).joinedload(TurnoServicio.servicio),
            joinedload(Turno.servicio),
        )
        .filter(
            Turno.paciente_id == paciente.id,
            Turno.estado.in_(estados_historial),
        )
        .order_by(Turno.fecha_hora.desc())
        .all()
    )

    registros: list[dict[str, str | int | None]] = []
    for turno in turnos:
        profesional: Profesional | None = turno.profesional
        profesional_nombre = (
            f"{(profesional.nombres or '').strip()} {(profesional.apellidos or '').strip()}".strip()
            if profesional else None
        )
        fecha_hora = turno.fecha_hora
        fecha = fecha_hora.strftime("%Y-%m-%d") if fecha_hora else ""
        hora = fecha_hora.strftime("%H:%M") if fecha_hora else ""

        if turno.items:
            for item in turno.items:
                servicio: Servicio | None = item.servicio
                servicio_nombre = getattr(servicio, "nombre", None) or ""
                detalle = item.nota or getattr(servicio, "descripcion", None)
                registros.append(
                    {
                        "turno_id": turno.id,
                        "fecha": fecha,
                        "hora": hora,
                        "servicio": servicio_nombre,
                        "profesional": profesional_nombre,
                        "detalle": detalle,
                    }
                )
        else:
            servicio: Servicio | None = turno.servicio
            servicio_nombre = getattr(servicio, "nombre", None) or ""
            detalle = getattr(servicio, "descripcion", None)
            registros.append(
                {
                    "turno_id": turno.id,
                    "fecha": fecha,
                    "hora": hora,
                    "servicio": servicio_nombre,
                    "profesional": profesional_nombre,
                    "detalle": detalle,
                }
            )

    data = {
        "paciente_id": paciente.id,
        "paciente_nombre": paciente.nombre,
        "historial": registros,
        "total": len(registros),
    }
    return historial_schema.dump(data)

@bp.put("/<int:pid>")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def actualizar(pid):
    p = Paciente.query.get_or_404(pid)
    payload = request.json or {}

    # Si viene un DNI nuevo, validar que no lo tenga otro paciente
    nuevo_doc = payload.get("documento") or payload.get("dni")
    if nuevo_doc and nuevo_doc != (p.documento or None):
        if Paciente.query.filter(Paciente.documento == nuevo_doc, Paciente.id != p.id).first():
            return {"message": "DNI ya utilizado por otro paciente"}, 409

    # Si viene un email nuevo, validar que no lo tenga otro paciente
    nuevo_mail = payload.get("email")
    if nuevo_mail and nuevo_mail != (p.email or None):
        if Paciente.query.filter(Paciente.email == nuevo_mail, Paciente.id != p.id).first():
            return {"message": "Email ya utilizado por otro paciente"}, 409

    # Cargar cambios (acepta todos los campos)
    _ = schema.load(payload, instance=p, partial=True, session=db.session)
    db.session.commit()
    log_action(get_jwt().get("sub"), "actualizar_paciente", f"Paciente {p.id}")
    return schema.dump(p)

@bp.delete("/<int:pid>")
@jwt_required()
@role_required("administracion")
def eliminar(pid):
    p = Paciente.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    log_action(get_jwt().get("sub"), "eliminar_paciente", f"Paciente {pid}")
    return {"message": "Eliminado"}
