# routes/servicio_insumos.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from extensions import db
from utils.decorators import role_required
from models.inventario import Producto
from models.servicio_insumo import ServicioInsumo  # asegúrate de tener este modelo

bp = Blueprint("servicio_insumos", __name__, url_prefix="/api/servicios")

@bp.get("/<int:sid>/insumos")
@jwt_required()
def listar_insumos(sid):
    items = ServicioInsumo.query.filter_by(servicio_id=sid).all()
    out = []
    for it in items:
        prod = db.session.get(Producto, it.producto_id)
        out.append({
            "id": it.id,
            "servicio_id": it.servicio_id,
            "producto_id": it.producto_id,
            "producto_nombre": (prod.nombre if prod else ""),
            "cantidad_por_sesion": float(it.cantidad_por_sesion or 0)
        })
    return {"data": out}

@bp.post("/<int:sid>/insumos")
@jwt_required()
@role_required("administracion")
def agregar_insumo(sid):
    payload = request.json or {}
    producto_id = payload.get("producto_id")
    cantidad = float(payload.get("cantidad_por_sesion") or 0)
    if not producto_id or cantidad <= 0:
        return {"message":"Datos inválidos"}, 400
    it = ServicioInsumo(servicio_id=sid, producto_id=producto_id, cantidad_por_sesion=cantidad)
    db.session.add(it)
    db.session.commit()
    return {"id": it.id}, 201

@bp.delete("/insumos/<int:insumo_id>")
@jwt_required()
@role_required("administracion")
def eliminar_insumo(insumo_id):
    it = ServicioInsumo.query.get_or_404(insumo_id)
    db.session.delete(it)
    db.session.commit()
    return {"message":"Eliminado"}

