from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import joinedload

from extensions import db
from models.caja import CajaMovimiento, Comprobante, ComprobanteItem, MetodoPago, TipoMovimiento
from models.inventario import MovimientoStock, Producto
from models.paciente import Paciente
from models.profesional import Profesional
from models.servicio import Servicio
from models.turno import EstadoTurno, Turno
from models.turno_servicio import TurnoServicio
from utils.exporter import (
    COMPANY_ADDRESS,
    COMPANY_NAME,
    COMPANY_PHONE,
    COMPANY_RUC,
    export_to_excel,
    export_to_pdf,
)


def parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


EXPORT_MIMETYPES = {
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}

VALID_EXPORT_REPORT_TYPES = {"facturacion", "pacientes", "inventario", "turnos"}


class ReportesService:
    def __init__(self, clinica_id: int):
        self.clinica_id = clinica_id

    def atenciones(self, params: dict[str, Any]) -> dict[str, Any]:
        desde = parse_dt(params.get("desde"))
        hasta = parse_dt(params.get("hasta"))
        group_by = (params.get("group_by") or "dia").lower()

        query = db.session.query(Turno).filter(
            Turno.clinica_id == self.clinica_id,
            Turno.is_active.is_(True),
            Turno.estado == EstadoTurno.ATENDIDO,
        )
        if desde:
            query = query.filter(Turno.fecha_hora >= desde)
        if hasta:
            query = query.filter(Turno.fecha_hora <= hasta)

        if group_by == "profesional":
            data = (
                db.session.query(Profesional.nombres, Profesional.apellidos, func.count(Turno.id))
                .join(Profesional, Profesional.id == Turno.profesional_id, isouter=True)
                .filter(Turno.id.in_(query.with_entities(Turno.id)))
                .group_by(Profesional.nombres, Profesional.apellidos)
                .order_by(desc(func.count(Turno.id)))
                .all()
            )
            rows = [{"clave": f"{n or ''} {a or ''}".strip() or "Sin asignar", "cantidad": c} for n, a, c in data]
        elif group_by == "servicio":
            data = (
                db.session.query(Servicio.nombre, func.count(Turno.id))
                .join(Servicio, Servicio.id == Turno.servicio_id, isouter=True)
                .filter(Turno.id.in_(query.with_entities(Turno.id)))
                .group_by(Servicio.nombre)
                .order_by(desc(func.count(Turno.id)))
                .all()
            )
            rows = [{"clave": nombre or "Sin servicio", "cantidad": count} for nombre, count in data]
        else:
            data = (
                db.session.query(func.date(Turno.fecha_hora), func.count(Turno.id))
                .filter(Turno.id.in_(query.with_entities(Turno.id)))
                .group_by(func.date(Turno.fecha_hora))
                .order_by(func.date(Turno.fecha_hora))
                .all()
            )
            rows = [{"clave": str(day), "cantidad": count} for day, count in data]

        return {"data": rows}

    def stock_bajo(self) -> dict[str, Any]:
        rows = (
            db.session.query(Producto)
            .filter(
                Producto.clinica_id == self.clinica_id,
                Producto.is_active.is_(True),
                Producto.stock_actual <= Producto.stock_minimo,
            )
            .order_by(Producto.nombre.asc())
            .limit(500)
            .all()
        )
        return {
            "data": [
                {
                    "id": producto.id,
                    "sku": producto.sku,
                    "nombre": producto.nombre,
                    "categoria": getattr(producto, "categoria", ""),
                    "stock_actual": float(producto.stock_actual or 0),
                    "stock_minimo": float(producto.stock_minimo or 0),
                    "unidad": getattr(producto, "unidad", ""),
                }
                for producto in rows
            ]
        }

    def pacientes_resumen(self, params: dict[str, Any]) -> dict[str, Any]:
        desde = parse_dt(params.get("desde"))
        hasta = parse_dt(params.get("hasta"))
        n_frec = int(params.get("frecuentes_n") or 2)
        inact_dias = int(params.get("inactivos_dias") or 60)

        pacientes_query = db.session.query(Paciente).filter(
            Paciente.clinica_id == self.clinica_id,
            Paciente.is_active.is_(True),
        )
        nuevos_query = pacientes_query
        if desde:
            nuevos_query = nuevos_query.filter(Paciente.created_at >= desde)
        if hasta:
            nuevos_query = nuevos_query.filter(Paciente.created_at <= hasta)
        nuevos = nuevos_query.count()

        frecuentes_query = (
            db.session.query(Turno.paciente_id, func.count(Turno.id).label("total"))
            .filter(Turno.clinica_id == self.clinica_id, Turno.is_active.is_(True))
            .group_by(Turno.paciente_id)
        )
        if desde:
            frecuentes_query = frecuentes_query.filter(Turno.fecha_hora >= desde)
        if hasta:
            frecuentes_query = frecuentes_query.filter(Turno.fecha_hora <= hasta)
        frecuentes_subquery = frecuentes_query.having(func.count(Turno.id) >= n_frec).subquery()
        frecuentes = db.session.query(func.count()).select_from(frecuentes_subquery).scalar() or 0

        limite = datetime.utcnow() - timedelta(days=inact_dias)
        ultimos_turnos = (
            db.session.query(Turno.paciente_id, func.max(Turno.fecha_hora).label("ult"))
            .filter(Turno.clinica_id == self.clinica_id, Turno.is_active.is_(True))
            .group_by(Turno.paciente_id)
            .subquery()
        )
        inactivos = (
            pacientes_query.outerjoin(ultimos_turnos, ultimos_turnos.c.paciente_id == Paciente.id)
            .filter(or_(ultimos_turnos.c.ult == None, ultimos_turnos.c.ult < limite))
            .count()
        )

        return {"nuevos": int(nuevos), "frecuentes": int(frecuentes), "inactivos": int(inactivos)}

    def facturacion(self, params: dict[str, Any]) -> dict[str, Any]:
        rows, total, group_by, extra = self.facturacion_dataset(params)
        resumen = {
            "ingresos": extra.get("total_ingresos", 0.0),
            "egresos": extra.get("total_egresos", 0.0),
            "neto": extra.get("total_neto", 0.0),
        }
        filtros = {"tipo": extra.get("tipo", ""), "metodo": extra.get("metodo", "")}
        return {"data": rows, "total": total, "group_by": group_by, "resumen": resumen, "filters": filtros}

    def facturacion_dataset(self, params: dict[str, Any] | None):
        filtros = self._parse_facturacion_filters(params)
        base_query = db.session.query(CajaMovimiento).filter(
            CajaMovimiento.clinica_id == self.clinica_id,
            CajaMovimiento.is_active.is_(True),
        )
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
        rows: list[dict[str, Any]] = []

        if group_by == "dia":
            data = (
                db.session.query(func.date(CajaMovimiento.fecha), func.coalesce(func.sum(CajaMovimiento.monto), 0))
                .filter(CajaMovimiento.id.in_(base_ids))
                .group_by(func.date(CajaMovimiento.fecha))
                .order_by(func.date(CajaMovimiento.fecha))
                .all()
            )
            rows = [{"clave": str(day), "monto": float(total)} for day, total in data]
        elif group_by == "metodo":
            data = (
                db.session.query(CajaMovimiento.metodo_pago, func.coalesce(func.sum(CajaMovimiento.monto), 0))
                .filter(CajaMovimiento.id.in_(base_ids))
                .group_by(CajaMovimiento.metodo_pago)
                .order_by(desc(func.coalesce(func.sum(CajaMovimiento.monto), 0)))
                .all()
            )
            for metodo_val, total_val in data:
                label = metodo_val.value if hasattr(metodo_val, "value") else (metodo_val or "").strip() or "-"
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
            rows = [{"clave": nombre or "Sin producto", "monto": float(total or 0)} for nombre, total in data]
        else:
            if group_by != "servicio":
                group_by = "servicio"
            rows = self._facturacion_por_servicio(base_ids)

        total = float(base_query.with_entities(func.coalesce(func.sum(CajaMovimiento.monto), 0)).scalar() or 0.0)
        total_ingresos, total_egresos = self._totales_por_tipo(base_query)
        return rows, total, group_by, {
            "tipo": filtros["tipo_raw"],
            "metodo": filtros["metodo_raw"],
            "total_ingresos": total_ingresos,
            "total_egresos": total_egresos,
            "total_neto": total_ingresos - total_egresos,
        }

    def collect_pacientes_report(self, desde: str | None, hasta: str | None):
        desde_dt = parse_dt(desde)
        hasta_dt = parse_dt(hasta)
        estados_historial = [EstadoTurno.ATENDIDO.value]
        estado_cobrado = getattr(EstadoTurno, "COBRADO", None)
        if estado_cobrado:
            estados_historial.append(estado_cobrado.value)

        turnos_query = (
            Turno.query.options(
                joinedload(Turno.paciente),
                joinedload(Turno.profesional),
                joinedload(Turno.items).joinedload(TurnoServicio.servicio),
                joinedload(Turno.servicio),
            )
            .filter(
                Turno.clinica_id == self.clinica_id,
                Turno.is_active.is_(True),
                Turno.estado.in_(estados_historial),
            )
        )
        if desde_dt:
            turnos_query = turnos_query.filter(Turno.fecha_hora >= desde_dt)
        if hasta_dt:
            turnos_query = turnos_query.filter(Turno.fecha_hora <= hasta_dt)

        turnos = turnos_query.all()
        if not turnos:
            return [{
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
            }], [
                ("Total sesiones", 0),
                ("Total facturado", "PEN 0.00"),
                ("Promedio por sesion", "PEN 0.00"),
            ]

        turno_ids = [turno.id for turno in turnos]
        movimientos = (
            CajaMovimiento.query.filter(
                CajaMovimiento.clinica_id == self.clinica_id,
                CajaMovimiento.is_active.is_(True),
                CajaMovimiento.turno_id.in_(turno_ids),
            ).all()
        )

        mov_map: dict[int, dict[str, Any]] = {}
        for mov in movimientos:
            bucket = mov_map.setdefault(mov.turno_id, {"monto": 0.0, "metodos": []})
            try:
                bucket["monto"] += float(mov.monto or 0)
            except Exception:
                bucket["monto"] += 0.0
            metodo_val = getattr(mov.metodo_pago, "value", None) or getattr(mov.metodo_pago, "name", None) or str(mov.metodo_pago or "-")
            if metodo_val not in bucket["metodos"]:
                bucket["metodos"].append(metodo_val)

        rows: list[dict[str, Any]] = []
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
            monto_total_turno = movimiento["monto"] or sum(servicio["precio"] for servicio in servicios)
            partes = len(servicios) or 1
            monto_unit = monto_total_turno / partes
            total_facturado += monto_total_turno

            fecha_hora = turno.fecha_hora or datetime.utcnow()
            profesional_nombre = ""
            if profesional:
                profesional_nombre = f"{getattr(profesional, 'nombres', '')} {getattr(profesional, 'apellidos', '')}".strip()
            profesional_nombre = profesional_nombre or "Sin profesional"

            for servicio in servicios:
                rows.append({
                    "Paciente ID": getattr(paciente, "id", ""),
                    "DNI": getattr(paciente, "documento", "") or "-",
                    "Nombre": getattr(paciente, "nombre", "") or "Sin nombre",
                    "Fecha servicio": fecha_hora.strftime("%d/%m/%Y"),
                    "Hora": fecha_hora.strftime("%H:%M"),
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
        return rows, [
            ("Total sesiones", total_sesiones),
            ("Total facturado", f"PEN {total_facturado:0.2f}"),
            ("Promedio por sesion", f"PEN {promedio:0.2f}"),
        ]

    def collect_movimientos_report(
        self,
        desde: str | None,
        hasta: str | None,
        tipo: str | None,
        producto_id: str | None,
    ):
        desde_dt = parse_dt(desde)
        hasta_dt = parse_dt(hasta)
        tipo = (tipo or "").strip().lower()
        prod_id = int(producto_id) if producto_id and str(producto_id).isdigit() else None

        query = (
            db.session.query(MovimientoStock, Producto)
            .join(Producto, MovimientoStock.producto_id == Producto.id)
            .filter(
                MovimientoStock.clinica_id == self.clinica_id,
                MovimientoStock.is_active.is_(True),
                Producto.clinica_id == self.clinica_id,
                Producto.is_active.is_(True),
            )
        )
        if desde_dt:
            query = query.filter(MovimientoStock.fecha >= desde_dt)
        if hasta_dt:
            query = query.filter(MovimientoStock.fecha <= hasta_dt)
        if tipo in {"ingreso", "egreso", "ajuste"}:
            query = query.filter(func.lower(MovimientoStock.tipo) == tipo)
        if prod_id:
            query = query.filter(MovimientoStock.producto_id == prod_id)

        rows: list[dict[str, Any]] = []
        total_ingresos = 0.0
        total_egresos = 0.0
        for mov, producto in query.order_by(MovimientoStock.fecha.asc()).all():
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

        if not rows:
            return [{
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
            }], [
                ("Total ingresos", 0.0),
                ("Total egresos", 0.0),
                ("Diferencia neta", 0.0),
            ]

        return rows, [
            ("Total ingresos", total_ingresos),
            ("Total egresos", total_egresos),
            ("Diferencia neta", total_ingresos - total_egresos),
        ]

    def collect_turnos_report(
        self,
        desde: str | None,
        hasta: str | None,
        estado: str | None,
        profesional_id: str | None,
        servicio_id: str | None,
    ):
        desde_dt = parse_dt(desde)
        hasta_dt = parse_dt(hasta)
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
            .filter(Turno.clinica_id == self.clinica_id, Turno.is_active.is_(True))
        )
        if desde_dt:
            query = query.filter(Turno.fecha_hora >= desde_dt)
        if hasta_dt:
            query = query.filter(Turno.fecha_hora <= hasta_dt)
        if estado:
            try:
                query = query.filter(Turno.estado == EstadoTurno(estado))
            except Exception:
                pass
        if prof_id:
            query = query.filter(Turno.profesional_id == prof_id)
        if serv_id:
            query = query.filter(or_(Turno.servicio_id == serv_id, Turno.items.any(TurnoServicio.servicio_id == serv_id)))

        rows: list[dict[str, Any]] = []
        total_facturado_estimado = 0.0
        total_atendidos = 0
        total_cancelados = 0
        for turno in query.order_by(Turno.fecha_hora.asc()).all():
            paciente = turno.paciente
            profesional = turno.profesional
            estado_txt = (turno.estado.value if turno.estado else "pendiente").upper()
            if estado_txt == "ATENDIDO":
                total_atendidos += 1
            if estado_txt == "CANCELADO":
                total_cancelados += 1

            servicios: list[tuple[str, float, float]] = []
            if turno.items:
                for item in turno.items:
                    servicio = item.servicio
                    servicios.append((
                        getattr(servicio, "nombre", "Sin servicio"),
                        float((item.precio or 0) or getattr(servicio, "precio", 0) or 0),
                        float(getattr(servicio, "duracion_min", 0) or 0),
                    ))
            else:
                servicio = turno.servicio
                servicios.append((
                    getattr(servicio, "nombre", "Sin servicio"),
                    float(getattr(servicio, "precio", 0) or 0),
                    float(getattr(servicio, "duracion_min", 0) or 0),
                ))

            monto_estimado = sum(servicio[1] for servicio in servicios)
            total_facturado_estimado += monto_estimado
            duracion_total = sum(servicio[2] for servicio in servicios)
            fecha = turno.fecha_hora or datetime.utcnow()
            profesional_nombre = ""
            if profesional:
                profesional_nombre = f"{getattr(profesional, 'nombres', '')} {getattr(profesional, 'apellidos', '')}".strip()

            rows.append({
                "ID Turno": turno.id,
                "Fecha": fecha.strftime("%d/%m/%Y"),
                "Hora": fecha.strftime("%H:%M"),
                "Paciente": getattr(paciente, "nombre", "Sin nombre"),
                "DNI": getattr(paciente, "documento", "") or "-",
                "Profesional": profesional_nombre or "Sin profesional",
                "Servicio": " / ".join([servicio[0] for servicio in servicios]) or "Sin servicio",
                "Estado": estado_txt,
                "Duracion": f"{int(duracion_total)} min" if duracion_total else "-",
                "Monto estimado": round(monto_estimado, 2),
                "Observaciones": turno.motivo_cancelacion or "No disponible",
                "Usuario registro": getattr(turno.created_by, "nombre", None) or "No disponible",
            })

        if not rows:
            return [{
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
            }], [
                ("Total turnos atendidos", 0),
                ("Total turnos cancelados", 0),
                ("Total monto estimado", "PEN 0.00"),
            ]

        return rows, [
            ("Total turnos atendidos", total_atendidos),
            ("Total turnos cancelados", total_cancelados),
            ("Total monto estimado", f"PEN {total_facturado_estimado:0.2f}"),
        ]

    def collect_facturacion_report(
        self,
        desde: str | None,
        hasta: str | None,
        tipo: str | None,
        metodo: str | None,
        group_by: str | None,
    ):
        filtros = self._parse_facturacion_filters(
            {"desde": desde, "hasta": hasta, "tipo": tipo, "metodo": metodo, "group_by": group_by}
        )

        query = (
            db.session.query(CajaMovimiento, Paciente, Profesional, Servicio, Comprobante)
            .join(Paciente, Paciente.id == CajaMovimiento.paciente_id, isouter=True)
            .join(Profesional, Profesional.id == CajaMovimiento.profesional_id, isouter=True)
            .join(Servicio, Servicio.id == CajaMovimiento.servicio_id, isouter=True)
            .join(Comprobante, Comprobante.id == CajaMovimiento.comprobante_id, isouter=True)
            .filter(CajaMovimiento.clinica_id == self.clinica_id, CajaMovimiento.is_active.is_(True))
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
        items_por_comprobante: dict[int, list[ComprobanteItem]] = {}
        if comprobante_ids:
            for item in (
                db.session.query(ComprobanteItem)
                .filter(ComprobanteItem.comprobante_id.in_(comprobante_ids))
                .order_by(ComprobanteItem.id.asc())
                .all()
            ):
                items_por_comprobante.setdefault(item.comprobante_id, []).append(item)

        rows: list[dict[str, Any]] = []
        total_ingresos = 0.0
        total_egresos = 0.0
        for mov, paciente, profesional, servicio, comprobante in movimientos:
            fecha = mov.fecha or datetime.utcnow()
            tipo_txt = mov.tipo.value.upper() if isinstance(mov.tipo, TipoMovimiento) else str(mov.tipo or "").upper()
            metodo_txt = mov.metodo_pago.value.upper() if hasattr(mov.metodo_pago, "value") else str(mov.metodo_pago or "").upper()
            monto_raw = float(mov.monto or 0)
            if tipo_txt.lower() == TipoMovimiento.EGRESO.value:
                total_egresos += monto_raw
                monto_signed = -monto_raw
            else:
                total_ingresos += monto_raw
                monto_signed = monto_raw

            profesional_nombre = ""
            if profesional:
                profesional_nombre = f"{getattr(profesional, 'nombres', '')} {getattr(profesional, 'apellidos', '')}".strip()

            servicio_nombre = getattr(servicio, "nombre", None) or ""
            detalle_items_list: list[str] = []
            items_rel = items_por_comprobante.get(comprobante.id, []) if comprobante else []
            if items_rel:
                conceptos = []
                for item in items_rel:
                    cantidad = float(item.cantidad or 0)
                    subtotal = float(item.subtotal or 0)
                    tipo_item = (item.tipo or "-").lower()
                    conceptos.append(item.nombre or "-")
                    detalle_items_list.append(f"{item.nombre} x{cantidad:g} ({tipo_item}) PEN {subtotal:0.2f}")
                if not servicio_nombre:
                    servicio_nombre = " / ".join(dict.fromkeys(conceptos))

            if not servicio_nombre:
                servicio_nombre = mov.observacion or getattr(comprobante, "observacion", None) or "-"

            comprobante_label = "-"
            if comprobante:
                numero = getattr(comprobante, "numero", "") or ""
                tipo_comp = getattr(comprobante, "tipo", "") or ""
                comprobante_label = f"{tipo_comp} {numero}".strip() or numero or tipo_comp or "-"

            rows.append({
                "Movimiento ID": mov.id,
                "Fecha": fecha.strftime("%d/%m/%Y"),
                "Hora": fecha.strftime("%H:%M"),
                "Tipo": tipo_txt or "-",
                "Metodo pago": metodo_txt or "-",
                "Monto": round(monto_signed, 2),
                "Monto bruto": round(monto_raw, 2),
                "Paciente": getattr(paciente, "nombre", None) or "Sin paciente",
                "Documento": getattr(paciente, "documento", None) or "s/DNI",
                "Profesional": profesional_nombre or "Sin profesional",
                "Servicio/Producto": servicio_nombre,
                "Comprobante": comprobante_label,
                "Turno ID": getattr(mov, "turno_id", None) or "-",
                "Observacion": mov.observacion or getattr(comprobante, "observacion", None) or "-",
                "Detalle items": "; ".join(detalle_items_list) if detalle_items_list else "-",
            })

        if not rows:
            return [{
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
            }], [
                ("Total movimientos", 0),
                ("Total ingresos", "PEN 0.00"),
                ("Total egresos", "PEN 0.00"),
                ("Balance neto", "PEN 0.00"),
            ]

        return rows, [
            ("Total movimientos", len(rows)),
            ("Total ingresos", f"PEN {total_ingresos:0.2f}"),
            ("Total egresos", f"PEN {total_egresos:0.2f}"),
            ("Balance neto", f"PEN {total_ingresos - total_egresos:0.2f}"),
        ]

    def _parse_facturacion_filters(self, params: dict[str, Any] | None) -> dict[str, Any]:
        params = params or {}
        tipo_raw = (params.get("tipo") or "").strip().lower()
        tipo_enum = TipoMovimiento(tipo_raw) if tipo_raw in {tipo.value for tipo in TipoMovimiento} else None
        metodo_raw = (params.get("metodo") or "").strip().lower()
        metodo_enum = MetodoPago(metodo_raw) if metodo_raw in {metodo.value for metodo in MetodoPago} else None
        return {
            "desde": parse_dt(params.get("desde")),
            "hasta": parse_dt(params.get("hasta")),
            "tipo": tipo_enum,
            "tipo_raw": tipo_raw if tipo_enum else "",
            "metodo": metodo_enum,
            "metodo_raw": metodo_raw if metodo_enum else "",
            "group_by": (params.get("group_by") or "metodo").strip().lower() or "metodo",
        }

    def _facturacion_por_servicio(self, base_ids) -> list[dict[str, Any]]:
        totals: dict[str, float] = {}
        data_serv = (
            db.session.query(Servicio.nombre, func.coalesce(func.sum(CajaMovimiento.monto), 0))
            .join(Servicio, Servicio.id == CajaMovimiento.servicio_id, isouter=True)
            .filter(CajaMovimiento.id.in_(base_ids))
            .group_by(Servicio.nombre)
            .all()
        )
        for nombre, total_val in data_serv:
            key = nombre or "Sin servicio"
            totals[key] = totals.get(key, 0.0) + float(total_val or 0)

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
            key = nombre or "Sin servicio"
            totals[key] = totals.get(key, 0.0) + float(total_val or 0)

        rows = [{"clave": key, "monto": amount} for key, amount in totals.items() if amount]
        rows.sort(key=lambda item: item["monto"], reverse=True)
        return rows

    @staticmethod
    def _totales_por_tipo(base_query) -> tuple[float, float]:
        total_ingresos = 0.0
        total_egresos = 0.0
        for tipo_valor, monto_valor in (
            base_query.with_entities(CajaMovimiento.tipo, func.coalesce(func.sum(CajaMovimiento.monto), 0))
            .group_by(CajaMovimiento.tipo)
            .all()
        ):
            tipo_txt = tipo_valor.value if isinstance(tipo_valor, TipoMovimiento) else str(tipo_valor or "").lower()
            monto_float = float(monto_valor or 0)
            if tipo_txt == TipoMovimiento.EGRESO.value:
                total_egresos += monto_float
            else:
                total_ingresos += monto_float
        return total_ingresos, total_egresos


def _header_fields(extra: list[tuple[str, Any]] | None = None) -> list[tuple[str, Any]]:
    fields = [
        ("Empresa", COMPANY_NAME),
        ("RUC", COMPANY_RUC or "-"),
        ("Direccion", COMPANY_ADDRESS),
        ("Telefono", COMPANY_PHONE or "-"),
        ("Reporte", "{title}"),
        ("Fecha generacion", "{generated_at}"),
        ("Generado por", "{generated_by}"),
        ("Total registros", "{total_records}"),
    ]
    if extra:
        fields.extend(extra)
    return fields


def build_export_meta(
    base_title: str,
    total: int,
    summary: list[tuple[str, Any]],
    generated_by: str,
    filtros: dict[str, Any],
    *,
    header_fields: list[tuple[str, Any]] | None = None,
    include_logo_note: bool = True,
):
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


def build_report_export_file(
    report_type: str,
    formato: str,
    params: dict[str, Any],
    user_label: str,
    clinica_id: int,
) -> str:
    report_type = (report_type or "").strip().lower()
    formato = (formato or "").strip().lower()
    params = params or {}
    if formato not in EXPORT_MIMETYPES:
        raise ValueError("formato inválido")

    service = ReportesService(clinica_id)
    if report_type == "facturacion":
        rows, summary = service.collect_facturacion_report(
            params.get("desde"),
            params.get("hasta"),
            params.get("tipo"),
            params.get("metodo"),
            params.get("group_by"),
        )
        meta = build_export_meta("Facturación / Caja", len(rows), summary, user_label, {
            "desde": params.get("desde") or "",
            "hasta": params.get("hasta") or "",
            "tipo": params.get("tipo") or "",
            "metodo": params.get("metodo") or "",
            "group_by": params.get("group_by") or "",
        }, header_fields=_header_fields([("Rango", "{date_range}")]), include_logo_note=False)
    elif report_type == "pacientes":
        rows, summary = service.collect_pacientes_report(params.get("desde"), params.get("hasta"))
        meta = build_export_meta("Pacientes - Historial Clinico", len(rows), summary, user_label, {
            "desde": params.get("desde") or "",
            "hasta": params.get("hasta") or "",
        }, header_fields=_header_fields([("Rango", "{date_range}")]), include_logo_note=False)
    elif report_type == "inventario":
        rows, summary = service.collect_movimientos_report(
            params.get("desde"),
            params.get("hasta"),
            params.get("tipo"),
            params.get("producto_id"),
        )
        meta = build_export_meta("Inventario - Movimientos", len(rows), summary, user_label, {
            "desde": params.get("desde") or "",
            "hasta": params.get("hasta") or "",
            "tipo": params.get("tipo") or "",
            "producto_id": params.get("producto_id") or "",
        }, header_fields=_header_fields(), include_logo_note=False)
    elif report_type == "turnos":
        rows, summary = service.collect_turnos_report(
            params.get("desde"),
            params.get("hasta"),
            params.get("estado"),
            params.get("profesional_id"),
            params.get("servicio_id"),
        )
        meta = build_export_meta("Turnos - Agenda", len(rows), summary, user_label, {
            "desde": params.get("desde") or "",
            "hasta": params.get("hasta") or "",
            "estado": params.get("estado") or "",
            "profesional_id": params.get("profesional_id") or "",
            "servicio_id": params.get("servicio_id") or "",
        }, header_fields=_header_fields(), include_logo_note=False)
    else:
        raise ValueError("tipo de reporte inválido")

    exporter = export_to_excel if formato == "excel" else export_to_pdf
    return exporter(report_type, rows, meta)
