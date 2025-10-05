from datetime import datetime
from decimal import Decimal
import os
from typing import Any, Dict, List, Tuple

from flask import Blueprint, request, send_file
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from extensions import db
from models.caja import CajaMovimiento, MetodoPago, TipoMovimiento
from models.servicio import Servicio
from models.turno import EstadoTurno, Turno
from models.turno_servicio import TurnoServicio
from schemas.turno import TurnoSchema
from utils.audit import log_action
from utils.decorators import role_required
from utils.inventario_ops import consumir_insumos_por_servicio
from utils.exporter import export_to_excel, export_to_pdf

bp = Blueprint("turnos", __name__, url_prefix="/api/turnos")
schema = TurnoSchema()
schema_many = TurnoSchema(many=True)



def _parse_dt_param(value: str | None):
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _collect_turnos_report(desde: str | None, hasta: str | None, estado: str | None, profesional_id: str | None, servicio_id: str | None):
    desde_dt = _parse_dt_param(desde)
    hasta_dt = _parse_dt_param(hasta)
    estado = (estado or "").strip().lower()
    prof_id = int(profesional_id) if profesional_id and str(profesional_id).isdigit() else None
    serv_id = int(servicio_id) if servicio_id and str(servicio_id).isdigit() else None

    query = (Turno.query.options(
        joinedload(Turno.paciente),
        joinedload(Turno.profesional),
        joinedload(Turno.items).joinedload(TurnoServicio.servicio),
        joinedload(Turno.servicio),
        joinedload(Turno.created_by)
    ))

    if desde_dt:
        query = query.filter(Turno.fecha_hora >= desde_dt)
    if hasta_dt:
        query = query.filter(Turno.fecha_hora <= hasta_dt)
    if estado:
        try:
            estado_enum = EstadoTurno(estado)
            query = query.filter(Turno.estado == estado_enum)
        except Exception:
            pass
    if prof_id:
        query = query.filter(Turno.profesional_id == prof_id)
    if serv_id:
        query = query.filter(or_(Turno.servicio_id == serv_id, Turno.items.any(TurnoServicio.servicio_id == serv_id)))

    turnos = query.order_by(Turno.fecha_hora.asc()).all()

    rows: List[Dict[str, Any]] = []
    total_facturado_estimado = 0.0
    total_atendidos = 0
    total_cancelados = 0

    for turno in turnos:
        paciente = turno.paciente
        profesional = turno.profesional
        estado_txt = (turno.estado.value if turno.estado else "pendiente").upper()
        if estado_txt == "ATENDIDO":
            total_atendidos += 1
        if estado_txt == "CANCELADO":
            total_cancelados += 1

        servicios: List[Tuple[str, float, float]] = []
        if turno.items:
            for item in turno.items:
                servicio = item.servicio
                nombre = getattr(servicio, "nombre", "Sin servicio")
                precio = float((item.precio or 0) or getattr(servicio, "precio", 0) or 0)
                duracion = float(getattr(servicio, "duracion_min", 0) or 0)
                servicios.append((nombre, precio, duracion))
        else:
            servicio = turno.servicio
            nombre = getattr(servicio, "nombre", "Sin servicio")
            precio = float(getattr(servicio, "precio", 0) or 0)
            duracion = float(getattr(servicio, "duracion_min", 0) or 0)
            servicios.append((nombre, precio, duracion))

        monto_estimado = sum(s[1] for s in servicios)
        total_facturado_estimado += monto_estimado
        duracion_total = sum(s[2] for s in servicios)

        fecha = turno.fecha_hora or datetime.utcnow()
        paciente_nombre = getattr(paciente, "nombre", "Sin nombre")
        paciente_doc = getattr(paciente, "documento", "") or "-"
        profesional_nombre = ""
        if profesional:
            profesional_nombre = f"{getattr(profesional, 'nombres', '')} {getattr(profesional, 'apellidos', '')}".strip()
        profesional_nombre = profesional_nombre or "Sin profesional"
        usuario_nombre = getattr(turno.created_by, "nombre", None) or "No disponible"
        observacion = turno.motivo_cancelacion or "No disponible"

        rows.append({
            "ID Turno": turno.id,
            "Fecha": fecha.strftime("%d/%m/%Y"),
            "Hora": fecha.strftime("%H:%M"),
            "Paciente": paciente_nombre,
            "DNI": paciente_doc,
            "Profesional": profesional_nombre,
            "Servicio": " / ".join({s[0] for s in servicios}) or "Sin servicio",
            "Estado": estado_txt,
            "Duracion": f"{int(duracion_total)} min" if duracion_total else "-",
            "Monto estimado": round(monto_estimado, 2),
            "Observaciones": observacion,
            "Usuario registro": usuario_nombre,
        })

    summary: List[Tuple[str, Any]] = [
        ("Total turnos atendidos", total_atendidos),
        ("Total turnos cancelados", total_cancelados),
        ("Total monto estimado", f"PEN {total_facturado_estimado:0.2f}"),
    ]

    if not rows:
        rows = [{
            "ID Turno": "-",
            "Fecha": "-",
            "Hora": "-",
            "Paciente": "Sin resultados",
            "DNI": "-",
            "Profesional": "-",
            "Servicio": "-",
            "Estado": "-",
            "Duracion": "-",
            "Monto estimado": 0.0,
            "Observaciones": "Sin resultados en este periodo",
            "Usuario registro": "-",
        }]
        summary = [
            ("Total turnos atendidos", 0),
            ("Total turnos cancelados", 0),
            ("Total monto estimado", "PEN 0.00"),
        ]

    return rows, summary


def _build_turno_export_metadata(total: int, summary: List[Tuple[str, Any]], generated_by: str, filtros: Dict[str, Any]):
    desde = filtros.get("desde") or "-"
    hasta = filtros.get("hasta") or "-"
    date_range = f"{desde} - {hasta}" if (desde != "-" or hasta != "-") else "Sin rango"
    return {
        "title": "Turnos - Agenda",
        "generated_by": generated_by,
        "generated_at": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        "total_records": total,
        "date_range": date_range,
        "filters": filtros,
        "summary": summary,
    }


@bp.get("/export/excel")
@jwt_required()
def exportar_turnos_excel():
    params = request.args or {}
    rows, summary = _collect_turnos_report(
        params.get("desde"),
        params.get("hasta"),
        params.get("estado"),
        params.get("profesional_id"),
        params.get("servicio_id"),
    )
    claims = get_jwt() or {}
    user_label = claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")
    meta = _build_turno_export_metadata(len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
        "estado": params.get("estado") or "",
        "profesional_id": params.get("profesional_id") or "",
        "servicio_id": params.get("servicio_id") or "",
    })
    file_path = export_to_excel("turnos", rows, meta)
    return send_file(file_path, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=os.path.basename(file_path))


@bp.get("/export/pdf")
@jwt_required()
def exportar_turnos_pdf():
    params = request.args or {}
    rows, summary = _collect_turnos_report(
        params.get("desde"),
        params.get("hasta"),
        params.get("estado"),
        params.get("profesional_id"),
        params.get("servicio_id"),
    )
    claims = get_jwt() or {}
    user_label = claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")
    meta = _build_turno_export_metadata(len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
        "estado": params.get("estado") or "",
        "profesional_id": params.get("profesional_id") or "",
        "servicio_id": params.get("servicio_id") or "",
    })
    file_path = export_to_pdf("turnos", rows, meta)
    return send_file(file_path, mimetype="application/pdf", as_attachment=True, download_name=os.path.basename(file_path))

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
