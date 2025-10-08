from datetime import datetime, timedelta, date
from io import StringIO
import csv
import os
from typing import Any, Dict, List, Tuple

from flask import Blueprint, request, Response, send_file
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, and_, desc, or_
from sqlalchemy.orm import joinedload

from extensions import db
from models.turno import Turno, EstadoTurno
from models.turno_servicio import TurnoServicio
from models.servicio import Servicio
from models.profesional import Profesional
from models.paciente import Paciente
from models.caja import CajaMovimiento, Comprobante, ComprobanteItem, MetodoPago, TipoMovimiento
from models.inventario import Producto, MovimientoStock
from utils.exporter import export_to_excel, export_to_pdf, COMPANY_NAME, COMPANY_RUC, COMPANY_ADDRESS, COMPANY_PHONE

bp = Blueprint("reportes", __name__, url_prefix="/api/reportes")

def _parse_dt(s, default_start=True):
    if not s:
        return None
    try:
        # admite "YYYY-MM-DD" o ISO parcial
        dt = datetime.fromisoformat(s)
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt if not default_start else dt
        except Exception:
            continue
    return None

# ---------- ATENCIONES ----------
@bp.get("/atenciones")
@jwt_required()
def atenciones():
    """
    Reporte de atenciones (turnos en estado 'atendido') agrupadas por
    profesional | servicio | día
    """
    desde = _parse_dt(request.args.get("desde"))
    hasta = _parse_dt(request.args.get("hasta"))
    group_by = (request.args.get("group_by") or "dia").lower()

    q = db.session.query(Turno)
    if desde: q = q.filter(Turno.fecha_hora >= desde)
    if hasta: q = q.filter(Turno.fecha_hora <= hasta)
    q = q.filter(Turno.estado == EstadoTurno.ATENDIDO)

    if group_by == "profesional":
        data = (db.session.query(Profesional.nombres, Profesional.apellidos, func.count(Turno.id))
                .join(Profesional, Profesional.id == Turno.profesional_id, isouter=True)
                .filter(Turno.id.in_(q.with_entities(Turno.id)))
                .group_by(Profesional.nombres, Profesional.apellidos)
                .order_by(desc(func.count(Turno.id)))
                .all())
        rows = [{"clave": f"{n or ''} {a or ''}".strip() or "Sin asignar", "cantidad": c} for n, a, c in data]
    elif group_by == "servicio":
        data = (db.session.query(Servicio.nombre, func.count(Turno.id))
                .join(Servicio, Servicio.id == Turno.servicio_id, isouter=True)
                .filter(Turno.id.in_(q.with_entities(Turno.id)))
                .group_by(Servicio.nombre)
                .order_by(desc(func.count(Turno.id)))
                .all())
        rows = [{"clave": n or "Sin servicio", "cantidad": c} for n, c in data]
    else:  # día
        data = (db.session.query(func.date(Turno.fecha_hora), func.count(Turno.id))
                .filter(Turno.id.in_(q.with_entities(Turno.id)))
                .group_by(func.date(Turno.fecha_hora))
                .order_by(func.date(Turno.fecha_hora))
                .all())
        rows = [{"clave": str(d), "cantidad": c} for d, c in data]

    return {"data": rows}

# ---------- FACTURACIÓN / CAJA ----------
@bp.get("/facturacion")
@jwt_required()
def facturacion():
    rows, total, group_by, extra = _facturacion_dataset(request.args)
    resumen = {
        "ingresos": extra.get("total_ingresos", 0.0),
        "egresos": extra.get("total_egresos", 0.0),
        "neto": extra.get("total_neto", 0.0),
    }
    filtros = {"tipo": extra.get("tipo", ""), "metodo": extra.get("metodo", "")}
    return {"data": rows, "total": total, "group_by": group_by, "resumen": resumen, "filters": filtros}

# ---------- STOCK ----------
@bp.get("/stock_bajo")
@jwt_required()
def stock_bajo():
    """
    Productos cuyo stock_actual <= stock_minimo
    """
    data = (db.session.query(Producto)
            .filter(Producto.stock_actual <= Producto.stock_minimo)
            .order_by(Producto.nombre.asc())
            .limit(500).all())
    rows = [{
        "id": p.id,
        "sku": p.sku,
        "nombre": p.nombre,
        "categoria": getattr(p, "categoria", ""),
        "stock_actual": float(p.stock_actual or 0),
        "stock_minimo": float(p.stock_minimo or 0),
        "unidad": getattr(p, "unidad", ""),
    } for p in data]
    return {"data": rows}

# ---------- PACIENTES ----------
@bp.get("/pacientes")
@jwt_required()
def rep_pacientes():
    """
    Pacientes nuevos (creados en rango), frecuentes (>=N turnos en rango), inactivos (sin turnos últimos M días)
    """
    desde = _parse_dt(request.args.get("desde"))
    hasta = _parse_dt(request.args.get("hasta"))
    n_frec = int(request.args.get("frecuentes_n") or 2)
    inact_dias = int(request.args.get("inactivos_dias") or 60)

    # nuevos
    qn = db.session.query(Paciente)
    if desde: qn = qn.filter(Paciente.created_at >= desde)
    if hasta: qn = qn.filter(Paciente.created_at <= hasta)
    nuevos = qn.count()

    # frecuentes (por cantidad de turnos en rango)
    qt = db.session.query(Turno.paciente_id, func.count(Turno.id)).group_by(Turno.paciente_id)
    if desde: qt = qt.filter(Turno.fecha_hora >= desde)
    if hasta: qt = qt.filter(Turno.fecha_hora <= hasta)
    frec = db.session.query(func.count()).from_statement(
        qt.having(func.count(Turno.id) >= n_frec).with_only_columns(func.count())
    ).scalar() or 0

    # inactivos (último turno más viejo que X días)
    limite = datetime.utcnow() - timedelta(days=inact_dias)
    sub = (db.session.query(Turno.paciente_id, func.max(Turno.fecha_hora).label("ult"))
           .group_by(Turno.paciente_id)).subquery()
    inactivos = (db.session.query(Paciente)
                 .outerjoin(sub, sub.c.paciente_id == Paciente.id)
                 .filter((sub.c.ult == None) | (sub.c.ult < limite))
                 .count())

    return {"nuevos": int(nuevos), "frecuentes": int(frec), "inactivos": int(inactivos)}


# ---------- EXPORTES ESPECÍFICOS ----------
def _collect_pacientes_report(desde: str | None, hasta: str | None):
    desde_dt = _parse_dt(desde)
    hasta_dt = _parse_dt(hasta)
    estados_historial = [EstadoTurno.ATENDIDO.value]
    estado_cobrado = getattr(EstadoTurno, "COBRADO", None)
    if estado_cobrado:
        estados_historial.append(estado_cobrado.value)

    turnos_q = (
        Turno.query.options(
            joinedload(Turno.paciente),
            joinedload(Turno.profesional),
            joinedload(Turno.items).joinedload(TurnoServicio.servicio),
            joinedload(Turno.servicio),
        )
        .filter(Turno.estado.in_(estados_historial))
    )
    if desde_dt:
        turnos_q = turnos_q.filter(Turno.fecha_hora >= desde_dt)
    if hasta_dt:
        turnos_q = turnos_q.filter(Turno.fecha_hora <= hasta_dt)

    turnos = turnos_q.all()
    if not turnos:
        summary = [
            ("Total sesiones", 0),
            ("Total facturado", "PEN 0.00"),
            ("Promedio por sesion", "PEN 0.00"),
        ]
        rows = [{
            "Paciente ID": "-",
            "DNI": "-",
            "Nombre": "Sin resultados",
            "Fecha servicio": "-",
            "Hora": "-",
            "Servicio": "-",
            "Profesional": "-",
            "Detalle": "Sin resultados en este periodo",
            "Estado": "-",
            "Monto facturado": 0.0,
            "Metodo pago": "-",
            "Usuario registro": "-",
        }]
        return rows, summary

    turno_ids = [t.id for t in turnos]
    movimientos = (
        CajaMovimiento.query
        .filter(CajaMovimiento.turno_id.in_(turno_ids))
        .all()
    )

    mov_map: Dict[int, Dict[str, Any]] = {}
    for mov in movimientos:
        bucket = mov_map.setdefault(mov.turno_id, {"monto": 0.0, "metodos": []})
        try:
            bucket["monto"] += float(mov.monto or 0)
        except Exception:
            bucket["monto"] += 0.0
        metodo_val = getattr(mov.metodo_pago, "value", None) or getattr(mov.metodo_pago, "name", None) or str(mov.metodo_pago or "-")
        if metodo_val not in bucket["metodos"]:
            bucket["metodos"].append(metodo_val)

    rows: List[Dict[str, Any]] = []
    total_facturado = 0.0
    for turno in turnos:
        paciente = turno.paciente
        profesional = turno.profesional
        servicios = []

        if turno.items:
            for item in turno.items:
                servicios.append({
                    "nombre": getattr(item.servicio, "nombre", "Sin servicio"),
                    "detalle": item.nota or getattr(item.servicio, "descripcion", ""),
                    "precio": float((item.precio or 0) or getattr(item.servicio, "precio", 0) or 0),
                })
        else:
            servicios.append({
                "nombre": getattr(turno.servicio, "nombre", "Sin servicio"),
                "detalle": getattr(turno.servicio, "descripcion", ""),
                "precio": float(getattr(turno.servicio, "precio", 0) or 0),
            })

        movimiento = mov_map.get(turno.id, {"monto": 0.0, "metodos": []})
        metodos_txt = ", ".join(movimiento["metodos"]) if movimiento["metodos"] else "-"
        monto_total_turno = movimiento["monto"] or sum(s["precio"] for s in servicios)
        partes = len(servicios) or 1
        monto_unit = monto_total_turno / partes
        total_facturado += monto_total_turno

        fecha_hora = turno.fecha_hora or datetime.utcnow()
        fecha_txt = fecha_hora.strftime("%d/%m/%Y")
        hora_txt = fecha_hora.strftime("%H:%M")
        paciente_doc = getattr(paciente, "documento", "") or "-"
        paciente_nombre = getattr(paciente, "nombre", "") or "Sin nombre"
        profesional_nombre = ""
        if profesional:
            profesional_nombre = f"{getattr(profesional, 'nombres', '')} {getattr(profesional, 'apellidos', '')}".strip()
        profesional_nombre = profesional_nombre or "Sin profesional"

        for servicio in servicios:
            rows.append({
                "Paciente ID": getattr(paciente, "id", ""),
                "DNI": paciente_doc,
                "Nombre": paciente_nombre,
                "Fecha servicio": fecha_txt,
                "Hora": hora_txt,
                "Servicio": servicio["nombre"],
                "Profesional": profesional_nombre,
                "Detalle": servicio["detalle"],
                "Estado": (turno.estado.value if turno.estado else "").upper(),
                "Monto facturado": round(monto_unit, 2),
                "Metodo pago": metodos_txt,
                "Usuario registro": "No disponible",
            })

    total_sesiones = len(rows)
    promedio = total_facturado / total_sesiones if total_sesiones else 0.0
    summary = [
        ("Total sesiones", total_sesiones),
        ("Total facturado", f"PEN {total_facturado:0.2f}"),
        ("Promedio por sesion", f"PEN {promedio:0.2f}"),
    ]
    return rows, summary


def _collect_movimientos_report(desde: str | None, hasta: str | None, tipo: str | None, producto_id: str | None):
    desde_dt = _parse_dt(desde)
    hasta_dt = _parse_dt(hasta)
    tipo = (tipo or "").strip().lower()
    prod_id = int(producto_id) if producto_id and str(producto_id).isdigit() else None

    q = db.session.query(MovimientoStock, Producto).join(Producto, MovimientoStock.producto_id == Producto.id)
    if desde_dt:
        q = q.filter(MovimientoStock.fecha >= desde_dt)
    if hasta_dt:
        q = q.filter(MovimientoStock.fecha <= hasta_dt)
    if tipo in {"ingreso", "egreso", "ajuste"}:
        q = q.filter(func.lower(MovimientoStock.tipo) == tipo)
    if prod_id:
        q = q.filter(MovimientoStock.producto_id == prod_id)

    movimientos = q.order_by(MovimientoStock.fecha.asc()).all()
    rows: List[Dict[str, Any]] = []
    total_ingresos = 0.0
    total_egresos = 0.0

    for mov, producto in movimientos:
        cantidad = float(mov.cantidad or 0)
        if cantidad >= 0:
            total_ingresos += cantidad
        else:
            total_egresos += abs(cantidad)
        saldo_anterior = float(mov.saldo or 0) - cantidad
        fecha = mov.fecha or datetime.utcnow()
        rows.append({
            "Codigo producto": producto.sku or producto.id,
            "Descripcion": producto.nombre,
            "Tipo": (mov.tipo or "").upper(),
            "Cantidad": round(cantidad, 3),
            "Unidad": "No disponible",
            "Stock anterior": round(saldo_anterior, 3),
            "Stock posterior": round(float(mov.saldo or 0), 3),
            "Fecha": fecha.strftime("%d/%m/%Y"),
            "Hora": fecha.strftime("%H:%M"),
            "Responsable": "No disponible",
            "Observacion": mov.motivo or mov.referencia or "-",
        })

    diferencia = total_ingresos - total_egresos
    summary: List[Tuple[str, Any]] = [
        ("Total ingresos", total_ingresos),
        ("Total egresos", total_egresos),
        ("Diferencia neta", diferencia),
    ]

    if not rows:
        rows = [{
            "Codigo producto": "-",
            "Descripcion": "Sin resultados",
            "Tipo": "-",
            "Cantidad": 0.0,
            "Unidad": "-",
            "Stock anterior": 0.0,
            "Stock posterior": 0.0,
            "Fecha": "-",
            "Hora": "-",
            "Responsable": "-",
            "Observacion": "Sin resultados en este periodo",
        }]
        summary = [
            ("Total ingresos", 0.0),
            ("Total egresos", 0.0),
            ("Diferencia neta", 0.0),
        ]
    return rows, summary


def _collect_turnos_report(desde: str | None, hasta: str | None, estado: str | None, profesional_id: str | None, servicio_id: str | None):
    desde_dt = _parse_dt(desde)
    hasta_dt = _parse_dt(hasta)
    estado = (estado or "").strip().lower()
    prof_id = int(profesional_id) if profesional_id and str(profesional_id).isdigit() else None
    serv_id = int(servicio_id) if servicio_id and str(servicio_id).isdigit() else None

    query = (
        Turno.query.options(
            joinedload(Turno.paciente),
            joinedload(Turno.profesional),
            joinedload(Turno.items).joinedload(TurnoServicio.servicio),
            joinedload(Turno.servicio),
            joinedload(Turno.created_by),
        )
    )
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
            "Servicio": " / ".join([s[0] for s in servicios]) or "Sin servicio",
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


def _parse_facturacion_filters(params: Dict[str, Any] | None) -> Dict[str, Any]:
    params = params or {}
    desde = _parse_dt(params.get("desde"))
    hasta = _parse_dt(params.get("hasta"))

    tipo_raw = (params.get("tipo") or "").strip().lower()
    tipo_enum = None
    if tipo_raw in {t.value for t in TipoMovimiento}:
        tipo_enum = TipoMovimiento(tipo_raw)
    else:
        tipo_raw = ""

    metodo_raw = (params.get("metodo") or "").strip().lower()
    metodo_enum = None
    if metodo_raw in {m.value for m in MetodoPago}:
        metodo_enum = MetodoPago(metodo_raw)
    else:
        metodo_raw = ""

    group_by = (params.get("group_by") or "metodo").strip().lower() or "metodo"
    return {
        "desde": desde,
        "hasta": hasta,
        "tipo": tipo_enum,
        "tipo_raw": tipo_raw,
        "metodo": metodo_enum,
        "metodo_raw": metodo_raw,
        "group_by": group_by,
    }


def _facturacion_dataset(params) -> Tuple[List[Dict[str, Any]], float, str, Dict[str, Any]]:
    filtros = _parse_facturacion_filters(params)

    base_query = db.session.query(CajaMovimiento)
    if filtros["desde"]:
        base_query = base_query.filter(CajaMovimiento.fecha >= filtros["desde"])
    if filtros["hasta"]:
        base_query = base_query.filter(CajaMovimiento.fecha <= filtros["hasta"])
    if filtros["tipo"]:
        base_query = base_query.filter(CajaMovimiento.tipo == filtros["tipo"])
    if filtros["metodo"]:
        base_query = base_query.filter(CajaMovimiento.metodo_pago == filtros["metodo"])

    base_ids = base_query.with_entities(CajaMovimiento.id)
    group_by = filtros["group_by"]
    rows: List[Dict[str, Any]] = []

    if group_by == "dia":
        data = (
            db.session.query(func.date(CajaMovimiento.fecha), func.coalesce(func.sum(CajaMovimiento.monto), 0))
            .filter(CajaMovimiento.id.in_(base_ids))
            .group_by(func.date(CajaMovimiento.fecha))
            .order_by(func.date(CajaMovimiento.fecha))
            .all()
        )
        rows = [{"clave": str(d), "monto": float(t)} for d, t in data]
    elif group_by == "metodo":
        data = (
            db.session.query(CajaMovimiento.metodo_pago, func.coalesce(func.sum(CajaMovimiento.monto), 0))
            .filter(CajaMovimiento.id.in_(base_ids))
            .group_by(CajaMovimiento.metodo_pago)
            .order_by(desc(func.coalesce(func.sum(CajaMovimiento.monto), 0)))
            .all()
        )
        rows = []
        for metodo_val, total_val in data:
            if hasattr(metodo_val, "value"):
                label = metodo_val.value
            else:
                label = (metodo_val or "").strip() or "-"
            rows.append({"clave": label, "monto": float(total_val or 0)})
    elif group_by == "profesional":
        data = (
            db.session.query(Profesional.nombres, Profesional.apellidos, func.coalesce(func.sum(CajaMovimiento.monto), 0))
            .join(Profesional, Profesional.id == CajaMovimiento.profesional_id, isouter=True)
            .filter(CajaMovimiento.id.in_(base_ids))
            .group_by(Profesional.nombres, Profesional.apellidos)
            .order_by(desc(func.coalesce(func.sum(CajaMovimiento.monto), 0)))
            .all()
        )
        rows = [{"clave": f"{n or ''} {a or ''}".strip() or "Sin profesional", "monto": float(t or 0)} for n, a, t in data]
    elif group_by == "paciente":
        data = (
            db.session.query(Paciente.nombre, Paciente.documento, func.coalesce(func.sum(CajaMovimiento.monto), 0))
            .join(Paciente, Paciente.id == CajaMovimiento.paciente_id, isouter=True)
            .filter(CajaMovimiento.id.in_(base_ids))
            .group_by(Paciente.nombre, Paciente.documento)
            .order_by(desc(func.coalesce(func.sum(CajaMovimiento.monto), 0)))
            .all()
        )
        rows = []
        for nombre, documento, total_val in data:
            etiqueta = (nombre or "").strip() or "Sin paciente"
            doc_txt = (documento or "").strip() or "s/DNI"
            rows.append({"clave": f"{etiqueta} ({doc_txt})", "monto": float(total_val or 0)})
    elif group_by == "producto":
        data = (
            db.session.query(ComprobanteItem.nombre, func.coalesce(func.sum(ComprobanteItem.subtotal), 0))
            .join(Comprobante, Comprobante.id == ComprobanteItem.comprobante_id)
            .join(CajaMovimiento, CajaMovimiento.comprobante_id == Comprobante.id)
            .filter(CajaMovimiento.id.in_(base_ids))
            .filter(func.lower(ComprobanteItem.tipo) == "producto")
            .group_by(ComprobanteItem.nombre)
            .order_by(desc(func.coalesce(func.sum(ComprobanteItem.subtotal), 0)))
            .all()
        )
        rows = [{"clave": (nombre or "Sin producto"), "monto": float(total or 0)} for nombre, total in data]
    else:  # servicio (default)
        if group_by != "servicio":
            group_by = "servicio"
        totales: Dict[str, float] = {}
        data_serv = (
            db.session.query(Servicio.nombre, func.coalesce(func.sum(CajaMovimiento.monto), 0))
            .join(Servicio, Servicio.id == CajaMovimiento.servicio_id, isouter=True)
            .filter(CajaMovimiento.id.in_(base_ids))
            .group_by(Servicio.nombre)
            .all()
        )
        for nombre, total_val in data_serv:
            clave = (nombre or "Sin servicio")
            totales[clave] = totales.get(clave, 0.0) + float(total_val or 0)

        data_items = (
            db.session.query(ComprobanteItem.nombre, func.coalesce(func.sum(ComprobanteItem.subtotal), 0))
            .join(Comprobante, Comprobante.id == ComprobanteItem.comprobante_id)
            .join(CajaMovimiento, CajaMovimiento.comprobante_id == Comprobante.id)
            .filter(CajaMovimiento.id.in_(base_ids))
            .filter(func.lower(ComprobanteItem.tipo) == "servicio")
            .group_by(ComprobanteItem.nombre)
            .all()
        )
        for nombre, total_val in data_items:
            clave = (nombre or "Sin servicio")
            totales[clave] = totales.get(clave, 0.0) + float(total_val or 0)

        rows = [{"clave": clave, "monto": monto} for clave, monto in totales.items() if monto]
        rows.sort(key=lambda item: item["monto"], reverse=True)

    total = float(base_query.with_entities(func.coalesce(func.sum(CajaMovimiento.monto), 0)).scalar() or 0.0)
    totales_tipo = (
        base_query.with_entities(CajaMovimiento.tipo, func.coalesce(func.sum(CajaMovimiento.monto), 0))
        .group_by(CajaMovimiento.tipo)
        .all()
    )
    total_ingresos = 0.0
    total_egresos = 0.0
    for tipo_valor, monto_valor in totales_tipo:
        tipo_txt = tipo_valor.value if isinstance(tipo_valor, TipoMovimiento) else str(tipo_valor or "").lower()
        monto_float = float(monto_valor or 0)
        if tipo_txt == TipoMovimiento.EGRESO.value:
            total_egresos += monto_float
        else:
            total_ingresos += monto_float

    extra = {
        "tipo": filtros["tipo_raw"],
        "metodo": filtros["metodo_raw"],
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "total_neto": total_ingresos - total_egresos,
    }
    return rows, total, group_by, extra


def _collect_facturacion_report(
    desde: str | None,
    hasta: str | None,
    tipo: str | None,
    metodo: str | None,
    group_by: str | None,
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, Any]]]:
    filtros = _parse_facturacion_filters(
        {"desde": desde, "hasta": hasta, "tipo": tipo, "metodo": metodo, "group_by": group_by}
    )

    query = (
        db.session.query(CajaMovimiento, Paciente, Profesional, Servicio, Comprobante)
        .join(Paciente, Paciente.id == CajaMovimiento.paciente_id, isouter=True)
        .join(Profesional, Profesional.id == CajaMovimiento.profesional_id, isouter=True)
        .join(Servicio, Servicio.id == CajaMovimiento.servicio_id, isouter=True)
        .join(Comprobante, Comprobante.id == CajaMovimiento.comprobante_id, isouter=True)
    )
    if filtros["desde"]:
        query = query.filter(CajaMovimiento.fecha >= filtros["desde"])
    if filtros["hasta"]:
        query = query.filter(CajaMovimiento.fecha <= filtros["hasta"])
    if filtros["tipo"]:
        query = query.filter(CajaMovimiento.tipo == filtros["tipo"])
    if filtros["metodo"]:
        query = query.filter(CajaMovimiento.metodo_pago == filtros["metodo"])

    movimientos = query.order_by(CajaMovimiento.fecha.asc(), CajaMovimiento.id.asc()).all()
    comprobante_ids = [comp.id for _, _, _, _, comp in movimientos if comp and getattr(comp, "id", None)]
    items_por_comprobante: Dict[int, List[ComprobanteItem]] = {}
    if comprobante_ids:
        items = (
            db.session.query(ComprobanteItem)
            .filter(ComprobanteItem.comprobante_id.in_(comprobante_ids))
            .order_by(ComprobanteItem.id.asc())
            .all()
        )
        for item in items:
            items_por_comprobante.setdefault(item.comprobante_id, []).append(item)

    rows: List[Dict[str, Any]] = []
    total_ingresos = 0.0
    total_egresos = 0.0

    for mov, paciente, profesional, servicio, comprobante in movimientos:
        fecha = mov.fecha or datetime.utcnow()
        fecha_txt = fecha.strftime("%d/%m/%Y")
        hora_txt = fecha.strftime("%H:%M")
        tipo_txt = mov.tipo.value.upper() if isinstance(mov.tipo, TipoMovimiento) else str(mov.tipo or "").upper()
        metodo_txt = (
            mov.metodo_pago.value.upper() if hasattr(mov.metodo_pago, "value") else str(mov.metodo_pago or "").upper()
        )

        monto_raw = float(mov.monto or 0)
        if tipo_txt.lower() == TipoMovimiento.EGRESO.value:
            total_egresos += monto_raw
            monto_signed = -monto_raw
        else:
            total_ingresos += monto_raw
            monto_signed = monto_raw

        paciente_nombre = getattr(paciente, "nombre", None) or "Sin paciente"
        paciente_doc = getattr(paciente, "documento", None) or "s/DNI"

        profesional_nombre = ""
        if profesional:
            profesional_nombre = f"{getattr(profesional, 'nombres', '')} {getattr(profesional, 'apellidos', '')}".strip()
        profesional_nombre = profesional_nombre or "Sin profesional"

        servicio_nombre = getattr(servicio, "nombre", None) or ""
        detalle_items_list: List[str] = []
        items_rel = []
        if comprobante and comprobante.id in items_por_comprobante:
            items_rel = items_por_comprobante.get(comprobante.id, [])
        if items_rel:
            conceptos = []
            for item in items_rel:
                cant = float(item.cantidad or 0)
                subtotal = float(item.subtotal or 0)
                tipo_item = (item.tipo or "-").lower()
                conceptos.append(item.nombre or "-")
                detalle_items_list.append(
                    f"{item.nombre} x{cant:g} ({tipo_item}) PEN {subtotal:0.2f}"
                )
            if not servicio_nombre:
                servicio_nombre = " / ".join(dict.fromkeys(conceptos))  # mantiene orden sin duplicados

        if not servicio_nombre:
            servicio_nombre = mov.observacion or getattr(comprobante, "observacion", None) or "-"

        comprobante_label = "-"
        if comprobante:
            numero = getattr(comprobante, "numero", "") or ""
            tipo_comp = getattr(comprobante, "tipo", "") or ""
            comprobante_label = f"{tipo_comp} {numero}".strip() or numero or tipo_comp or "-"

        observacion = mov.observacion or getattr(comprobante, "observacion", None) or "-"
        detalle_items = "; ".join(detalle_items_list) if detalle_items_list else "-"

        rows.append({
            "Movimiento ID": mov.id,
            "Fecha": fecha_txt,
            "Hora": hora_txt,
            "Tipo": tipo_txt or "-",
            "Metodo pago": metodo_txt or "-",
            "Monto": round(monto_signed, 2),
            "Monto bruto": round(monto_raw, 2),
            "Paciente": paciente_nombre,
            "Documento": paciente_doc,
            "Profesional": profesional_nombre,
            "Servicio/Producto": servicio_nombre,
            "Comprobante": comprobante_label,
            "Turno ID": getattr(mov, "turno_id", None) or "-",
            "Observacion": observacion,
            "Detalle items": detalle_items,
        })

    if not rows:
        rows = [{
            "Movimiento ID": "-",
            "Fecha": "-",
            "Hora": "-",
            "Tipo": "-",
            "Metodo pago": "-",
            "Monto": 0.0,
            "Monto bruto": 0.0,
            "Paciente": "Sin resultados",
            "Documento": "-",
            "Profesional": "-",
            "Servicio/Producto": "-",
            "Comprobante": "-",
            "Turno ID": "-",
            "Observacion": "Sin resultados en este periodo",
            "Detalle items": "-",
        }]
        summary = [
            ("Total movimientos", 0),
            ("Total ingresos", "PEN 0.00"),
            ("Total egresos", "PEN 0.00"),
            ("Balance neto", "PEN 0.00"),
        ]
        return rows, summary

    balance = total_ingresos - total_egresos
    summary = [
        ("Total movimientos", len(rows)),
        ("Total ingresos", f"PEN {total_ingresos:0.2f}"),
        ("Total egresos", f"PEN {total_egresos:0.2f}"),
        ("Balance neto", f"PEN {balance:0.2f}"),
    ]
    return rows, summary


@bp.get("/facturacion/export/excel")
@jwt_required()
def exportar_facturacion_excel():
    params = request.args or {}
    rows, summary = _collect_facturacion_report(
        params.get("desde"),
        params.get("hasta"),
        params.get("tipo"),
        params.get("metodo"),
        params.get("group_by"),
    )
    claims = get_jwt() or {}
    user_label = claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")
    meta = _build_meta("Facturación / Caja", len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
        "tipo": params.get("tipo") or "",
        "metodo": params.get("metodo") or "",
        "group_by": params.get("group_by") or "",
    }, header_fields=[
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
        ("Rango", "{date_range}"),
    ], include_logo_note=False)
    file_path = export_to_excel("facturacion", rows, meta)
    return send_file(
        file_path,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=os.path.basename(file_path),
    )


@bp.get("/facturacion/export/pdf")
@jwt_required()
def exportar_facturacion_pdf():
    params = request.args or {}
    rows, summary = _collect_facturacion_report(
        params.get("desde"),
        params.get("hasta"),
        params.get("tipo"),
        params.get("metodo"),
        params.get("group_by"),
    )
    claims = get_jwt() or {}
    user_label = claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")
    meta = _build_meta("Facturación / Caja", len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
        "tipo": params.get("tipo") or "",
        "metodo": params.get("metodo") or "",
        "group_by": params.get("group_by") or "",
    }, header_fields=[
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
        ("Rango", "{date_range}"),
    ], include_logo_note=False)
    file_path = export_to_pdf("facturacion", rows, meta)
    return send_file(
        file_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=os.path.basename(file_path),
    )


def _build_meta(base_title: str, total: int, summary: List[Tuple[str, Any]], generated_by: str, filtros: Dict[str, Any], *, header_fields: List[Tuple[str, Any]] | None = None, include_logo_note: bool = True):
    desde = filtros.get("desde") or "-"
    hasta = filtros.get("hasta") or "-"
    date_range = f"{desde} - {hasta}" if (desde != "-" or hasta != "-") else "Sin rango"
    meta = {
        "title": base_title,
        "generated_by": generated_by,
        "generated_at": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        "total_records": total,
        "date_range": date_range,
        "filters": filtros,
        "summary": summary,
        "include_logo_note": include_logo_note,
    }
    if header_fields is not None:
        meta["header_fields"] = header_fields
    return meta


@bp.get("/pacientes/export/excel")
@jwt_required()
def exportar_pacientes_excel():
    params = request.args or {}
    rows, summary = _collect_pacientes_report(params.get("desde"), params.get("hasta"))
    claims = get_jwt() or {}
    user_label = claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")
    meta = _build_meta("Pacientes - Historial Clinico", len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
    }, header_fields=[
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
        ("Rango", "{date_range}"),
    ], include_logo_note=False)
    file_path = export_to_excel("pacientes", rows, meta)
    return send_file(file_path, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=os.path.basename(file_path))


@bp.get("/pacientes/export/pdf")
@jwt_required()
def exportar_pacientes_pdf():
    params = request.args or {}
    rows, summary = _collect_pacientes_report(params.get("desde"), params.get("hasta"))
    claims = get_jwt() or {}
    user_label = claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")
    meta = _build_meta("Pacientes - Historial Clinico", len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
    }, header_fields=[
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
        ("Rango", "{date_range}"),
    ], include_logo_note=False)
    file_path = export_to_pdf("pacientes", rows, meta)
    return send_file(file_path, mimetype="application/pdf", as_attachment=True, download_name=os.path.basename(file_path))


@bp.get("/inventario/export/excel")
@jwt_required()
def exportar_inventario_excel():
    params = request.args or {}
    rows, summary = _collect_movimientos_report(
        params.get("desde"),
        params.get("hasta"),
        params.get("tipo"),
        params.get("producto_id"),
    )
    claims = get_jwt() or {}
    user_label = claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")
    meta = _build_meta("Inventario - Movimientos", len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
        "tipo": params.get("tipo") or "",
        "producto_id": params.get("producto_id") or "",
    }, header_fields=[
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
    ], include_logo_note=False)
    file_path = export_to_excel("inventario", rows, meta)
    return send_file(file_path, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=os.path.basename(file_path))


@bp.get("/inventario/export/pdf")
@jwt_required()
def exportar_inventario_pdf():
    params = request.args or {}
    rows, summary = _collect_movimientos_report(
        params.get("desde"),
        params.get("hasta"),
        params.get("tipo"),
        params.get("producto_id"),
    )
    claims = get_jwt() or {}
    user_label = claims.get("name") or claims.get("email") or str(claims.get("sub") or "Usuario")
    meta = _build_meta("Inventario - Movimientos", len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
        "tipo": params.get("tipo") or "",
        "producto_id": params.get("producto_id") or "",
    }, header_fields=[
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
    ], include_logo_note=False)
    file_path = export_to_pdf("inventario", rows, meta)
    return send_file(file_path, mimetype="application/pdf", as_attachment=True, download_name=os.path.basename(file_path))


@bp.get("/turnos/export/excel")
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
    meta = _build_meta("Turnos - Agenda", len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
        "estado": params.get("estado") or "",
        "profesional_id": params.get("profesional_id") or "",
        "servicio_id": params.get("servicio_id") or "",
    }, header_fields=[
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
    ], include_logo_note=False)
    file_path = export_to_excel("turnos", rows, meta)
    return send_file(file_path, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=os.path.basename(file_path))


@bp.get("/turnos/export/pdf")
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
    meta = _build_meta("Turnos - Agenda", len(rows), summary, user_label, {
        "desde": params.get("desde") or "",
        "hasta": params.get("hasta") or "",
        "estado": params.get("estado") or "",
        "profesional_id": params.get("profesional_id") or "",
        "servicio_id": params.get("servicio_id") or "",
    }, header_fields=[
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
    ], include_logo_note=False)
    file_path = export_to_pdf("turnos", rows, meta)
    return send_file(file_path, mimetype="application/pdf", as_attachment=True, download_name=os.path.basename(file_path))


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
