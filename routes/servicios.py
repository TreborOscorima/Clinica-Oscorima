# routes/servicios.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from extensions import db
from models.servicio import Servicio
from models.servicio_insumo import ServicioInsumo  # ← asegurate de tener este modelo
from schemas.servicio import ServicioSchema
from utils.decorators import role_required
from utils.audit import log_action

bp = Blueprint("servicios", __name__, url_prefix="/api/servicios")
schema = ServicioSchema()
schema_many = ServicioSchema(many=True)

@bp.get("")
@jwt_required()
def listar():
    q = (request.args.get("q") or "").strip()
    query = Servicio.query
    if q:
        like = f"%{q}%"
        query = query.filter(Servicio.nombre.ilike(like))
    items = query.order_by(Servicio.created_at.desc()).limit(200).all()
    return {"data": schema_many.dump(items)}

@bp.post("")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def crear():
    obj = schema.load(request.json or {}, session=db.session)  # ← usa sesión
    db.session.add(obj)
    db.session.commit()
    log_action(get_jwt().get("sub"), "crear_servicio", f"Servicio {obj.id}")
    return schema.dump(obj), 201

@bp.get("/<int:sid>")
@jwt_required()
def detalle(sid):
    s = Servicio.query.get_or_404(sid)
    return schema.dump(s)

@bp.put("/<int:sid>")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def actualizar(sid):
    s = Servicio.query.get_or_404(sid)
    _ = schema.load(request.json or {}, instance=s, partial=True, session=db.session)
    db.session.commit()
    log_action(get_jwt().get("sub"), "actualizar_servicio", f"Servicio {s.id}")
    return schema.dump(s)

@bp.delete("/<int:sid>")
@jwt_required()
@role_required("administracion")
def eliminar(sid):
    s = Servicio.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    log_action(get_jwt().get("sub"), "eliminar_servicio", f"Servicio {sid}")
    return {"message": "Eliminado"}

# ---------- NUEVO: vincular insumos ----------
@bp.post("/<int:sid>/insumos")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def agregar_insumo(sid):
    s = Servicio.query.get_or_404(sid)
    payload = request.json or {}
    producto_id = payload.get("producto_id")
    cantidad = payload.get("cantidad_por_sesion")

    if not producto_id or not cantidad:
        return {"message": "producto_id y cantidad_por_sesion son obligatorios"}, 400

    si = ServicioInsumo(servicio_id=s.id, producto_id=producto_id, cantidad_por_sesion=cantidad)
    db.session.add(si); db.session.commit()
    log_action(get_jwt().get("sub"), "servicio_agregar_insumo", f"Servicio {sid} -> prod {producto_id} x {cantidad}")
    return {"message": "OK", "id": si.id}, 201
