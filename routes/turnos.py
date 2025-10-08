from datetime import datetime
from decimal import Decimal

from flask import Blueprint, request
from flask_jwt_extended import get_jwt, jwt_required

from extensions import db
from models.caja import CajaMovimiento, MetodoPago, TipoMovimiento
from models.servicio import Servicio
from models.turno import EstadoTurno, Turno
from schemas.turno import TurnoSchema
from utils.audit import log_action
from utils.decorators import role_required
from utils.inventario_ops import consumir_insumos_por_servicio

bp = Blueprint("turnos", __name__, url_prefix="/api/turnos")
schema = TurnoSchema()
schema_many = TurnoSchema(many=True)



@bp.get("/<int:tid>")
@jwt_required()
def obtener(tid):
    turno = Turno.query.get_or_404(tid)
    return schema.dump(turno), 200


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

    query = Turno.query
    if estado:
        try:
            estado_enum = EstadoTurno(estado)
        except Exception:
            return {"message": "Estado invalido"}, 400
        query = query.filter(Turno.estado == estado_enum)

    query = query.order_by(Turno.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    if pagination.pages and page > pagination.pages:
        pagination = query.paginate(page=pagination.pages, per_page=per_page, error_out=False)

    return {
        "data": schema_many.dump(pagination.items),
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
        "total": pagination.total,
    }


@bp.post("")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear():
    payload = request.get_json(silent=True) or {}

    profesional_id = payload.get("profesional_id")
    profesional_dni = str(payload.get("profesional_dni") or "").strip()
    if not profesional_id and profesional_dni:
        from models.profesional import Profesional

        profesional = Profesional.query.filter_by(dni=profesional_dni).first()
        if not profesional:
            return {"message": "Profesional no encontrado por DNI"}, 404
        payload["profesional_id"] = profesional.id

    tiene_items = bool(payload.get("items"))
    servicio_id = payload.get("servicio_id")
    servicio_nombre = (payload.get("servicio_nombre") or "").strip()
    if not tiene_items and not servicio_id and servicio_nombre:
        servicio = Servicio.query.filter(Servicio.nombre.ilike(servicio_nombre)).first()
        if not servicio:
            return {"message": "Servicio no encontrado por nombre"}, 404
        payload["servicio_id"] = servicio.id

    turno: Turno = schema.load(payload, session=db.session)
    claims = get_jwt() or {}
    created_by = claims.get("sub")
    try:
        turno.created_by_id = int(created_by) if created_by is not None else None
    except Exception:
        turno.created_by_id = created_by

    for item in turno.items or []:
        if item.cantidad is None:
            item.cantidad = Decimal("1.00")
        if item.descuento is None:
            item.descuento = Decimal("0.00")

    db.session.add(turno)
    db.session.commit()
    log_action(get_jwt().get("sub"), "crear_turno", f"Turno {turno.id}")
    return schema.dump(turno), 201


@bp.put("/<int:tid>/estado")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def cambiar_estado(tid):
    turno: Turno = Turno.query.get_or_404(tid)
    payload = request.get_json(silent=True) or {}

    estado_str = (payload.get("estado") or "").strip().lower()
    motivo = payload.get("motivo_cancelacion")

    try:
        estado_enum = EstadoTurno(estado_str)
    except Exception:
        return {"message": "Estado invalido"}, 400

    if turno.estado == EstadoTurno.ATENDIDO and estado_enum == EstadoTurno.ATENDIDO:
        return {"message": "El turno ya esta atendido"}, 409

    turno.estado = estado_enum
    if estado_enum == EstadoTurno.CANCELADO and motivo:
        turno.motivo_cancelacion = motivo

    movimientos_stock = []
    movimiento_caja_id = None

    def _append_consumo(consumo):
        if isinstance(consumo, list):
            movimientos_stock.extend(consumo)
        elif isinstance(consumo, dict):
            movimientos_stock.append(consumo)

    if estado_enum == EstadoTurno.ATENDIDO:
        tiene_items = bool(turno.items)
        referencia = f"TUR-{turno.id:06d}"

        if tiene_items:
            for item in turno.items:
                try:
                    multiplicador = float(item.cantidad or 1)
                except Exception:
                    multiplicador = 1.0

                consumo = consumir_insumos_por_servicio(
                    item.servicio_id,
                    multiplicador=multiplicador,
                    motivo=f"Consumo por turno {turno.id} (item {item.id})",
                    referencia=referencia,
                )
                _append_consumo(consumo)
        elif turno.servicio_id:
            consumo = consumir_insumos_por_servicio(
                turno.servicio_id,
                multiplicador=1.0,
                motivo=f"Consumo por turno {turno.id}",
                referencia=referencia,
            )
            _append_consumo(consumo)

        if payload.get("cobrar"):
            monto_req = payload.get("monto")
            if monto_req is None:
                total = Decimal("0.00")
                if tiene_items:
                    for item in turno.items:
                        precio_item = item.precio if item.precio is not None else item.servicio.precio
                        cantidad = Decimal(str(item.cantidad or 1))
                        descuento_item = Decimal(str(item.descuento or 0))
                        total += (Decimal(str(precio_item or 0)) * cantidad) - descuento_item
                elif turno.servicio_id and turno.servicio:
                    total = Decimal(str(getattr(turno.servicio, "precio", 0) or "0"))
                monto = total
            else:
                try:
                    monto = Decimal(str(monto_req))
                except Exception:
                    return {"message": "Monto invalido"}, 400

            if monto <= 0:
                return {"message": "Monto invalido"}, 400

            metodo = (payload.get("metodo_pago") or MetodoPago.EFECTIVO.value).lower()
            metodos_validos = [metodo_enum.value for metodo_enum in MetodoPago]
            if metodo not in metodos_validos:
                return {"message": f"Metodo de pago invalido. Use: {', '.join(metodos_validos)}"}, 400

            observacion_suffix = " (multi-servicio)" if tiene_items else ""
            movimiento = CajaMovimiento(
                tipo=TipoMovimiento.INGRESO,
                monto=monto,
                metodo_pago=metodo,
                paciente_id=turno.paciente_id,
                profesional_id=turno.profesional_id,
                servicio_id=None if tiene_items else turno.servicio_id,
                observacion=f"Cobro por turno {turno.id}{observacion_suffix}",
            )
            db.session.add(movimiento)
            db.session.flush()
            movimiento_caja_id = movimiento.id

    db.session.commit()
    log_action(get_jwt().get("sub"), "actualizar_turno", f"Turno {turno.id} -> {turno.estado.value}")

    response = schema.dump(turno)
    response["movimientos_stock"] = movimientos_stock
    response["movimiento_caja_id"] = movimiento_caja_id
    return response


@bp.put("/<int:tid>/reprogramar")
@jwt_required()
@role_required("administracion", "recepcionista", "profesional")
def reprogramar(tid):
    turno: Turno = Turno.query.get_or_404(tid)
    payload = request.get_json(silent=True) or {}

    nueva_fecha = payload.get("fecha_hora")
    nuevo_estado = (payload.get("estado") or "").strip().lower()

    if not nueva_fecha:
        return {"message": "fecha_hora requerida"}, 400

    try:
        turno.fecha_hora = datetime.fromisoformat(nueva_fecha)
    except Exception:
        return {"message": "fecha_hora invalida"}, 400

    if nuevo_estado:
        try:
            turno.estado = EstadoTurno(nuevo_estado)
        except Exception:
            return {"message": "estado invalido"}, 400

    db.session.commit()
    log_action(get_jwt().get("sub"), "reprogramar_turno", f"Turno {turno.id} -> {turno.fecha_hora} {turno.estado}")
    return schema.dump(turno), 200
