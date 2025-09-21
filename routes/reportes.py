from datetime import datetime, timedelta, date
from io import StringIO
import csv

from flask import Blueprint, request, Response
from flask_jwt_extended import jwt_required
from sqlalchemy import func, and_, desc

from extensions import db
from models.turno import Turno, EstadoTurno
from models.servicio import Servicio
from models.profesional import Profesional
from models.paciente import Paciente
from models.caja import CajaMovimiento, Comprobante
from models.inventario import Producto, MovimientoStock

bp = Blueprint("reportes", __name__, url_prefix="/api/reportes")

def _parse_dt(s, default_start=True):
    if not s:
        return None
    try:
        # admite "YYYY-MM-DD" o ISO parcial
        dt = datetime.fromisoformat(s)
        return dt
    except Exception:
        try:
            d = datetime.strptime(s, "%Y-%m-%d")
            return d if not default_start else d
        except Exception:
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
    """
    Totales de caja por rango. group_by = metodo | dia | profesional | servicio
    Basado en CajaMovimiento (ingresos/egresos). Para profesional/servicio mira referencia en comprobante cuando exista.
    """
    desde = _parse_dt(request.args.get("desde"))
    hasta = _parse_dt(request.args.get("hasta"))
    group_by = (request.args.get("group_by") or "metodo").lower()
    tipo = request.args.get("tipo")  # ingreso/egreso/ambos

    q = db.session.query(CajaMovimiento)
    if desde: q = q.filter(CajaMovimiento.fecha >= desde)
    if hasta: q = q.filter(CajaMovimiento.fecha <= hasta)
    if tipo in ("ingreso", "egreso"):
        q = q.filter(CajaMovimiento.tipo == tipo)

    if group_by == "dia":
        data = (db.session.query(func.date(CajaMovimiento.fecha), func.coalesce(func.sum(CajaMovimiento.monto), 0))
                .filter(CajaMovimiento.id.in_(q.with_entities(CajaMovimiento.id)))
                .group_by(func.date(CajaMovimiento.fecha))
                .order_by(func.date(CajaMovimiento.fecha))
                .all())
        rows = [{"clave": str(d), "monto": float(t)} for d, t in data]
    elif group_by == "metodo":
        data = (db.session.query(CajaMovimiento.metodo_pago, func.coalesce(func.sum(CajaMovimiento.monto), 0))
                .filter(CajaMovimiento.id.in_(q.with_entities(CajaMovimiento.id)))
                .group_by(CajaMovimiento.metodo_pago)
                .order_by(desc(func.coalesce(func.sum(CajaMovimiento.monto), 0)))
                .all())
        rows = [{"clave": (m or "-"), "monto": float(t)} for m, t in data]
    elif group_by == "profesional":
        data = (db.session.query(Profesional.nombres, Profesional.apellidos, func.coalesce(func.sum(CajaMovimiento.monto), 0))
                .join(Profesional, Profesional.id == CajaMovimiento.profesional_id, isouter=True)
                .filter(CajaMovimiento.id.in_(q.with_entities(CajaMovimiento.id)))
                .group_by(Profesional.nombres, Profesional.apellidos)
                .order_by(desc(func.coalesce(func.sum(CajaMovimiento.monto), 0)))
                .all())
        rows = [{"clave": f"{n or ''} {a or ''}".strip() or "Sin profesional", "monto": float(t)} for n,a,t in data]
    else:  # servicio
        data = (db.session.query(Servicio.nombre, func.coalesce(func.sum(CajaMovimiento.monto), 0))
                .join(Servicio, Servicio.id == CajaMovimiento.servicio_id, isouter=True)
                .filter(CajaMovimiento.id.in_(q.with_entities(CajaMovimiento.id)))
                .group_by(Servicio.nombre)
                .order_by(desc(func.coalesce(func.sum(CajaMovimiento.monto), 0)))
                .all())
        rows = [{"clave": (n or "Sin servicio"), "monto": float(t)} for n, t in data]

    # totales globales
    tot = (db.session.query(func.coalesce(func.sum(CajaMovimiento.monto), 0))
           .filter(CajaMovimiento.id.in_(q.with_entities(CajaMovimiento.id)))
           .scalar() or 0)
    return {"data": rows, "total": float(tot)}

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
        "id": p.id, "sku": p.sku, "nombre": p.nombre, "categoria": p.categoria,
        "stock_actual": float(p.stock_actual or 0), "stock_minimo": float(p.stock_minimo or 0), "unidad": p.unidad
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
        payload = stock_bajo().get_json()
        rows = payload["data"]
        headers = ["id","sku","nombre","categoria","stock_actual","stock_minimo","unidad"]
    elif tipo == "atenciones":
        payload = atenciones().get_json()
        rows = payload["data"]
        headers = ["clave","cantidad"]
    else:  # facturacion
        payload = facturacion().get_json()
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
