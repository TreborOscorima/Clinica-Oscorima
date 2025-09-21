from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from extensions import db
from decimal import Decimal

from models.turno import Turno, EstadoTurno
from models.turno_servicio import TurnoServicio
from models.servicio import Servicio
from schemas.turno import TurnoSchema
from utils.decorators import role_required
from utils.audit import log_action

# caja + inventario
from models.caja import CajaMovimiento, TipoMovimiento, MetodoPago
from utils.inventario_ops import consumir_insumos_por_servicio

bp = Blueprint("turnos", __name__, url_prefix="/api/turnos")
schema = TurnoSchema()
schema_many = TurnoSchema(many=True)

@bp.get("/<int:tid>")
@jwt_required()
def obtener(tid):
    t = Turno.query.get_or_404(tid)
    return schema.dump(t), 200

@bp.get("")
@jwt_required()
def listar():
    estado = (request.args.get("estado") or "").strip().lower()
    q = Turno.query
    if estado:
        try:
            est = EstadoTurno(estado)
        except Exception:
            return {"message": "Estado inválido"}, 400
        q = q.filter(Turno.estado == est)
    items = q.order_by(Turno.fecha_hora.desc()).limit(200).all()
    return {"data": schema_many.dump(items)}

@bp.post("")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear():
    payload = request.json or {}

    # Profesional por DNI (opcional, para UX rápida)
    if not payload.get("profesional_id") and payload.get("profesional_dni"):
        from models.profesional import Profesional
        pr = Profesional.query.filter_by(dni=str(payload["profesional_dni"]).strip()).first()
        if not pr:
            return {"message": "Profesional no encontrado por DNI"}, 404
        payload["profesional_id"] = pr.id

    # Compat: si no hay items y llega servicio_nombre, resolverlo
    if not payload.get("items") and not payload.get("servicio_id") and payload.get("servicio_nombre"):
        s = Servicio.query.filter(Servicio.nombre.ilike(str(payload["servicio_nombre"]).strip())).first()
        if not s:
            return {"message": "Servicio no encontrado por nombre"}, 404
        payload["servicio_id"] = s.id

    # Cargar Turno con schema (valida items vs servicio_id)
    obj: Turno = schema.load(payload, session=db.session)

    # Normalizar valores de items (defaults)
    for it in (obj.items or []):
        if it.cantidad is None:
            it.cantidad = Decimal("1.00")
        if it.descuento is None:
            it.descuento = Decimal("0.00")

    db.session.add(obj)
    db.session.commit()
    log_action(get_jwt().get("sub"), "crear_turno", f"Turno {obj.id}")
    return schema.dump(obj), 201

@bp.put("/<int:tid>/estado")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def cambiar_estado(tid):
    t: Turno = Turno.query.get_or_404(tid)
    payload = request.json or {}
    estado_str = (payload.get("estado") or "").lower()
    motivo = payload.get("motivo_cancelacion")

    try:
        estado_enum = EstadoTurno(estado_str)
    except Exception:
        return {"message": "Estado inválido"}, 400

    # idempotencia
    if t.estado == EstadoTurno.ATENDIDO and estado_enum == EstadoTurno.ATENDIDO:
        return {"message": "El turno ya está atendido"}, 409

    t.estado = estado_enum
    if estado_enum == EstadoTurno.CANCELADO and motivo:
        t.motivo_cancelacion = motivo

    movimientos_stock = []
    mov_caja_id = None

    if estado_enum == EstadoTurno.ATENDIDO:
        # 1) Consumir insumos por item (o compat por servicio_id)
        if t.items and len(t.items) > 0:
            for item in t.items:
                try:
                    mult = float(item.cantidad or 1)
                except Exception:
                    mult = 1.0
                ms = consumir_insumos_por_servicio(
                    item.servicio_id,
                    multiplicador=mult,
                    motivo=f"Consumo por turno {t.id} (item {item.id})",
                    referencia=f"TUR-{t.id:06d}"
                )
                if isinstance(ms, list):
                    movimientos_stock.extend(ms)
                elif isinstance(ms, dict):
                    movimientos_stock.append(ms)
        elif t.servicio_id:
            ms = consumir_insumos_por_servicio(
                t.servicio_id,
                multiplicador=1.0,
                motivo=f"Consumo por turno {t.id}",
                referencia=f"TUR-{t.id:06d}"
            )
            if isinstance(ms, list):
                movimientos_stock.extend(ms)
            elif isinstance(ms, dict):
                movimientos_stock.append(ms)

        # 2) Cobro opcional
        if payload.get("cobrar"):
            monto_req = payload.get("monto", None)
            if monto_req is None:
                total = Decimal("0.00")
                if t.items and len(t.items) > 0:
                    for item in t.items:
                        precio_item = item.precio if item.precio is not None else item.servicio.precio
                        cant = Decimal(str(item.cantidad or 1))
                        desc = Decimal(str(item.descuento or 0))
                        total += (Decimal(str(precio_item or 0)) * cant) - desc
                elif t.servicio_id and t.servicio:
                    total = Decimal(str(getattr(t.servicio, "precio", 0) or "0"))
                monto = total
            else:
                try:
                    monto = Decimal(str(monto_req))
                except Exception:
                    return {"message": "Monto inválido"}, 400

            if monto <= 0:
                return {"message": "Monto inválido"}, 400

            metodo = (payload.get("metodo_pago") or MetodoPago.EFECTIVO.value).lower()
            validos = [e.value for e in MetodoPago]
            if metodo not in validos:
                return {"message": f"Método de pago inválido. Use: {', '.join(validos)}"}, 400

            mov = CajaMovimiento(
                tipo=TipoMovimiento.INGRESO,
                monto=monto,
                metodo_pago=metodo,
                paciente_id=t.paciente_id,
                profesional_id=t.profesional_id,
                servicio_id=t.servicio_id if not (t.items and len(t.items) > 0) else None,
                observacion=f"Cobro por turno {t.id}" + (" (multi-servicio)" if t.items and len(t.items) > 0 else "")
            )
            db.session.add(mov)
            db.session.flush()
            mov_caja_id = mov.id

    db.session.commit()
    log_action(get_jwt().get("sub"), "actualizar_turno", f"Turno {t.id} -> {t.estado.value}")

    out = schema.dump(t)
    out["movimientos_stock"] = movimientos_stock
    out["movimiento_caja_id"] = mov_caja_id
    return out

@bp.put("/<int:tid>/reprogramar")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def reprogramar(tid):
    from datetime import datetime
    t: Turno = Turno.query.get_or_404(tid)
    data = request.get_json() or {}
    nueva = data.get("fecha_hora")
    nuevo_estado = (data.get("estado") or "").lower()

    if not nueva:
        return {"message": "fecha_hora requerida"}, 400

    try:
      t.fecha_hora = datetime.fromisoformat(nueva)
    except Exception:
      return {"message": "fecha_hora inválida"}, 400

    if nuevo_estado:
      try:
        t.estado = EstadoTurno(nuevo_estado)
      except Exception:
        return {"message": "estado inválido"}, 400

    db.session.commit()
    log_action(get_jwt().get("sub"), "reprogramar_turno", f"Turno {t.id} -> {t.fecha_hora} {t.estado}")
    return schema.dump(t), 200