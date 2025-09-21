# routes/profesionales.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import or_, cast, String
from extensions import db
from utils.decorators import role_required
from utils.audit import log_action

from models.profesional import Profesional
from schemas.profesional import ProfesionalSchema

bp = Blueprint("profesionales", __name__, url_prefix="/api/profesionales")
schema = ProfesionalSchema()
list_schema = ProfesionalSchema(many=True)

@bp.get("")
@jwt_required()
def listar():
    """
    GET /api/profesionales?q=ana&especialidad=Esteticista&activo=true&page=1&per_page=20
    """
    q = (request.args.get("q") or "").strip()
    especialidad = (request.args.get("especialidad") or "").strip()
    activo = request.args.get("activo")
    page = int(request.args.get("page") or 1)
    per_page = min(int(request.args.get("per_page") or 50), 200)

    query = Profesional.query

    if q:
        # Buscar por nombres, apellidos o DNI (string o numérico)
        # Si tu campo dni es Integer en el modelo, cast a String para usar ilike
        query = query.filter(
            or_(
                Profesional.nombres.ilike(f"%{q}%"),
                Profesional.apellidos.ilike(f"%{q}%"),
                cast(Profesional.dni, String).ilike(f"%{q}%"),
            )
        )

    if especialidad:
        query = query.filter(Profesional.especialidad.ilike(f"%{especialidad}%"))

    if activo is not None:
        if activo.lower() in ("true", "1", "t", "yes", "si", "sí"):
            query = query.filter(Profesional.activo.is_(True))
        elif activo.lower() in ("false", "0", "f", "no"):
            query = query.filter(Profesional.activo.is_(False))

    pag = query.order_by(Profesional.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return {
        "data": list_schema.dump(pag.items),
        "page": pag.page,
        "per_page": pag.per_page,
        "total": pag.total,
        "pages": pag.pages,
    }

@bp.get("/<int:pid>")
@jwt_required()
def obtener(pid):
    p = Profesional.query.get_or_404(pid)
    return schema.dump(p)

@bp.post("")
@jwt_required()
@role_required("administracion")
def crear():
    obj = schema.load(request.json or {}, session=db.session)

    # Unicidad por DNI
    if obj.dni and Profesional.query.filter(Profesional.dni == obj.dni).first():
        return {"message": "DNI ya registrado en otro profesional"}, 409

    # Unicidad por Matrícula (si viene)
    if obj.matricula and Profesional.query.filter(Profesional.matricula == obj.matricula).first():
        return {"message": "Matrícula ya registrada en otro profesional"}, 409

    db.session.add(obj)
    db.session.commit()

    log_action(get_jwt().get("sub"), "crear_profesional", f"Profesional {obj.id}")
    return schema.dump(obj), 201

@bp.put("/<int:pid>")
@jwt_required()
@role_required("administracion")
def actualizar(pid):
    p = Profesional.query.get_or_404(pid)
    payload = request.json or {}

    # Si cambian DNI / Matrícula, validar que no estén usados por otro
    new_dni = payload.get("dni")
    if new_dni and new_dni != (p.dni or None):
        if Profesional.query.filter(Profesional.dni == new_dni, Profesional.id != p.id).first():
            return {"message": "DNI ya registrado en otro profesional"}, 409

    new_mat = payload.get("matricula")
    if new_mat and new_mat != (p.matricula or None):
        if Profesional.query.filter(Profesional.matricula == new_mat, Profesional.id != p.id).first():
            return {"message": "Matrícula ya registrada en otro profesional"}, 409

    _ = schema.load(payload, instance=p, partial=True, session=db.session)
    db.session.commit()

    log_action(get_jwt().get("sub"), "actualizar_profesional", f"Profesional {p.id}")
    return schema.dump(p)

@bp.delete("/<int:pid>")
@jwt_required()
@role_required("administracion")
def eliminar(pid):
    p = Profesional.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    user_id = get_jwt().get("sub")
    log_action(user_id, "eliminar_profesional", f"Profesional {pid}")
    return {"message": "Eliminado"}
