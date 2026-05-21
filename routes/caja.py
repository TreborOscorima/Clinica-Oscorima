from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from flask import Blueprint, Response, request
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from extensions import db
from utils.audit import log_action
from utils.decorators import role_required
from utils.tenant import get_current_clinica_id

from models.caja import (
    CajaMovimiento,
    CierreCaja,
    Comprobante,
    ComprobanteItem,
    DeudaPaciente,
    MetodoPago,
    TipoMovimiento,
)
from models.paciente import Paciente
from schemas.caja import (
    CajaMovimientoSchema,
    CierreCajaSchema,
    ComprobanteSchema,
)

from services.billing import get_billing_strategy
from services.caja import CajaService, dec2
from services.exceptions import ServiceError

bp = Blueprint("caja", __name__, url_prefix="/api/caja")

mov_schema = CajaMovimientoSchema()
comp_schema = ComprobanteSchema()
cier_schema = CierreCajaSchema()


def _json_payload() -> dict:
    return request.get_json(silent=True) or {}


def _mp_from_str(value: str) -> MetodoPago:
    normalized = (value or "").strip().lower()
    mapping = {
        "efectivo": MetodoPago.EFECTIVO,
        "tarjeta": MetodoPago.TARJETA,
        "transferencia": MetodoPago.TRANSFERENCIA,
    }
    return mapping.get(normalized, MetodoPago.OTRO)


def _get_idem_key() -> str | None:
    raw = request.headers.get("Idempotency-Key") or _json_payload().get("idempotency_key")
    key = (raw or "").strip()
    return key or None


def _clinica_id() -> int:
    return get_current_clinica_id()


def _service() -> CajaService:
    return CajaService(_clinica_id())


def _service_error_response(exc: ServiceError):
    return {"message": exc.message}, exc.status_code


# ──────────────────────────────────────────────────────────────────────────────
# Movimientos manuales
# ──────────────────────────────────────────────────────────────────────────────

@bp.get("/movimientos")
@jwt_required()
def listar_mov():
    try:
        return _service().listar_movimientos(request.args)
    except ServiceError as exc:
        return _service_error_response(exc)


@bp.post("/movimientos")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear_mov():
    try:
        movimiento = _service().crear_movimiento(_json_payload())
    except ServiceError as exc:
        return _service_error_response(exc)
    log_action(
        get_jwt().get("sub"),
        "crear_movimiento_caja",
        f"Movimiento {movimiento.id} {movimiento.tipo} {movimiento.monto}",
    )
    return mov_schema.dump(movimiento), 201


@bp.delete("/movimientos/<int:mid>")
@jwt_required()
@role_required("administracion")
def eliminar_mov(mid: int):
    try:
        _service().eliminar_movimiento(mid)
    except ServiceError as exc:
        return _service_error_response(exc)
    log_action(get_jwt().get("sub"), "eliminar_movimiento_caja", f"Movimiento {mid}")
    return {"message": "Eliminado"}


# ──────────────────────────────────────────────────────────────────────────────
# Comprobantes simples (ruta legacy)
# ──────────────────────────────────────────────────────────────────────────────

@bp.post("/comprobantes")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear_comprobante():
    clinica_id = _clinica_id()
    payload = _json_payload()

    total = dec2(payload.get("total", "0"))
    paciente_id = payload.get("paciente_id")
    forma_pago = _mp_from_str(payload.get("forma_pago", MetodoPago.EFECTIVO.value))
    observacion = payload.get("observacion", "")
    tipo = payload.get("tipo", "recibo")
    servicio_id = payload.get("servicio_id")
    profesional_id = payload.get("profesional_id")
    turno_id = payload.get("turno_id")

    idem = _get_idem_key()
    if idem and hasattr(Comprobante, "idempotency_key"):
        previo = db.session.execute(
            select(Comprobante).where(
                Comprobante.clinica_id == clinica_id,
                Comprobante.idempotency_key == idem,
            )
        ).scalar_one_or_none()
        if previo:
            return comp_schema.dump(previo), 200

    comprobante = Comprobante(
        clinica_id=clinica_id,
        tipo=tipo,
        total=total,
        total_bruto=total,
        descuento_global=dec2(0),
        paciente_id=paciente_id,
        forma_pago=forma_pago,
        observacion=observacion,
        **({"idempotency_key": idem} if (idem and hasattr(Comprobante, "idempotency_key")) else {}),
    )
    db.session.add(comprobante)
    db.session.flush()
    comprobante.numero = f"{tipo[:1].upper()}-{comprobante.id:06d}"

    movimiento_kwargs = dict(
        clinica_id=clinica_id,
        tipo=TipoMovimiento.INGRESO,
        monto=total,
        metodo_pago=forma_pago,
        paciente_id=paciente_id,
        comprobante_id=comprobante.id,
        servicio_id=servicio_id,
        profesional_id=profesional_id,
        observacion=f"{tipo} {comprobante.numero}",
    )
    if hasattr(CajaMovimiento, "turno_id"):
        movimiento_kwargs["turno_id"] = turno_id

    db.session.add(CajaMovimiento(**movimiento_kwargs))

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if idem and hasattr(Comprobante, "idempotency_key"):
            previo = db.session.execute(
                select(Comprobante).where(
                    Comprobante.clinica_id == clinica_id,
                    Comprobante.idempotency_key == idem,
                )
            ).scalar_one_or_none()
            if previo:
                return comp_schema.dump(previo), 200
        raise

    log_action(
        get_jwt().get("sub"),
        "crear_comprobante",
        f"Comprobante {comprobante.numero} - turno {turno_id}",
    )
    return comp_schema.dump(comprobante), 201


# ──────────────────────────────────────────────────────────────────────────────
# PDF de comprobante — delega en la estrategia de facturación
# ──────────────────────────────────────────────────────────────────────────────

@bp.get("/comprobantes/<int:cid>/pdf")
@jwt_required()
def comprobante_pdf(cid: int):
    clinica_id = _clinica_id()

    comprobante = db.session.execute(
        select(Comprobante).where(
            Comprobante.id == cid,
            Comprobante.clinica_id == clinica_id,
            Comprobante.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if comprobante is None:
        return {"message": "Comprobante no encontrado"}, 404

    paciente = None
    if getattr(comprobante, "paciente_id", None):
        paciente = db.session.execute(
            select(Paciente).where(
                Paciente.id == comprobante.paciente_id,
                Paciente.clinica_id == clinica_id,
                Paciente.is_active.is_(True),
            )
        ).scalar_one_or_none()

    try:
        strategy = get_billing_strategy(comprobante.tipo)
        pdf = strategy.generate_pdf(comprobante, paciente=paciente)
    except RuntimeError as exc:
        return {"message": str(exc)}, 501
    except NotImplementedError as exc:
        return {"message": str(exc)}, 501

    response = Response(pdf, mimetype="application/pdf")
    response.headers["Content-Disposition"] = (
        f"attachment; filename={comprobante.tipo}_{comprobante.numero}.pdf"
    )
    return response


# ──────────────────────────────────────────────────────────────────────────────
# POS — emisión de comprobantes (Fat Controller → CajaService)
# ──────────────────────────────────────────────────────────────────────────────

@bp.post("/pos")
@jwt_required()
@role_required("administracion", "recepcionista")
def pos_emitir():
    payload = _json_payload()
    idem_key = _get_idem_key()

    try:
        resultado = _service().emitir_pos(payload, idem_key=idem_key)
    except ServiceError as exc:
        return _service_error_response(exc)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    log_action(
        get_jwt().get("sub"),
        "pos_emitir",
        (
            f"Comprobante {resultado['comprobante']['numero']} "
            f"total {resultado['comprobante']['total']} "
            f"saldo {resultado['saldo_pendiente']}"
        ),
    )

    status_code = 200 if resultado.get("idempotent") else 201
    return resultado, status_code


# ──────────────────────────────────────────────────────────────────────────────
# Deudas
# ──────────────────────────────────────────────────────────────────────────────

@bp.get("/deudas/paciente/<int:pid>")
@jwt_required()
def deudas_por_paciente(pid: int):
    return _service().deudas_por_paciente(pid)


@bp.post("/deudas/abonar")
@jwt_required()
@role_required("administracion", "recepcionista")
def deudas_abonar():
    try:
        return _service().abonar_deudas(_json_payload())
    except ServiceError as exc:
        return _service_error_response(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Cierre diario
# ──────────────────────────────────────────────────────────────────────────────

def _preview_for_date(fecha: date, clinica_id: int):
    inicio = datetime.combine(fecha, time.min)
    fin = datetime.combine(fecha, time.max)
    movimientos = db.session.execute(
        select(CajaMovimiento).where(
            CajaMovimiento.clinica_id == clinica_id,
            CajaMovimiento.is_active.is_(True),
            CajaMovimiento.fecha >= inicio,
            CajaMovimiento.fecha <= fin,
        )
    ).scalars().all()

    total = Decimal("0")
    por_metodo: dict[str, Decimal] = {k: Decimal("0") for k in ("efectivo", "tarjeta", "transferencia", "otro")}
    for movimiento in movimientos:
        if movimiento.tipo == TipoMovimiento.INGRESO:
            monto = dec2(movimiento.monto or 0)
            total += monto
            metodo_key = (
                getattr(movimiento.metodo_pago, "value", str(movimiento.metodo_pago)) or "otro"
            ).lower()
            if metodo_key not in por_metodo:
                metodo_key = "otro"
            por_metodo[metodo_key] = dec2(por_metodo[metodo_key] + monto)

    return {
        "fecha": fecha.isoformat(),
        "total_ingresos": float(dec2(total)),
        "por_metodo": {k: float(dec2(v)) for k, v in por_metodo.items()},
        "conteo_movs": len(movimientos),
    }


@bp.get("/cierres/diario/preview")
@jwt_required()
def cierre_preview():
    clinica_id = _clinica_id()
    fecha_raw = request.args.get("fecha") or date.today().isoformat()
    try:
        fecha = date.fromisoformat(fecha_raw)
    except Exception:
        return {"message": "fecha invalida (YYYY-MM-DD)"}, 400
    return _preview_for_date(fecha, clinica_id)


@bp.post("/cierres/diario")
@jwt_required()
@role_required("administracion")
def cierre_confirmar():
    clinica_id = _clinica_id()
    fecha_raw = _json_payload().get("fecha") or date.today().isoformat()
    try:
        fecha = date.fromisoformat(fecha_raw)
    except Exception:
        return {"message": "fecha invalida"}, 400

    existente = db.session.execute(
        select(CierreCaja).where(
            CierreCaja.clinica_id == clinica_id,
            CierreCaja.fecha == fecha,
            CierreCaja.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if existente:
        return cier_schema.dump(existente), 200

    preview = _preview_for_date(fecha, clinica_id)
    cierre = CierreCaja(
        clinica_id=clinica_id,
        fecha=fecha,
        total_ingresos=dec2(preview["total_ingresos"]),
        total_egresos=dec2(0),
        saldo=dec2(preview["total_ingresos"]),
        usuario_id=get_jwt().get("sub"),
    )
    db.session.add(cierre)
    db.session.commit()
    log_action(get_jwt().get("sub"), "cierre_diario", f"Cierre {fecha} ingresos {cierre.total_ingresos}")
    return cier_schema.dump(cierre), 201


@bp.get("/cierres/diario/<fecha>/pdf")
@jwt_required()
def cierre_diario_pdf(fecha: str):
    try:
        fecha_obj = date.fromisoformat(fecha)
    except Exception:
        return {"message": "fecha invalida (YYYY-MM-DD)"}, 400

    preview = _preview_for_date(fecha_obj, _clinica_id())

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError:
        return {"message": "ReportLab no disponible"}, 501

    buffer = BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    _, height = A4
    cursor_y = height - 50

    lienzo.setFont("Helvetica-Bold", 14)
    lienzo.drawString(50, cursor_y, f"Cierre diario - {fecha_obj.isoformat()}")
    cursor_y -= 24

    lienzo.setFont("Helvetica", 11)
    lienzo.drawString(50, cursor_y, f"Total ingresos: S/ {preview.get('total_ingresos', 0):.2f}")
    cursor_y -= 18

    por_metodo = preview.get("por_metodo", {}) or {}
    for label, key in [
        ("Efectivo", "efectivo"),
        ("Tarjeta", "tarjeta"),
        ("Transferencia", "transferencia"),
        ("Otro", "otro"),
    ]:
        lienzo.drawString(50, cursor_y, f"  - {label}: S/ {float(por_metodo.get(key, 0)):.2f}")
        cursor_y -= 16

    cursor_y -= 8
    lienzo.drawString(50, cursor_y, f"Movimientos del dia: {preview.get('conteo_movs', 0)}")
    cursor_y -= 24

    lienzo.setFont("Helvetica-Oblique", 9)
    lienzo.drawString(50, cursor_y, "Documento generado automaticamente por el sistema de gestion.")
    lienzo.showPage()
    lienzo.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = Response(pdf, mimetype="application/pdf")
    response.headers["Content-Disposition"] = (
        f"attachment; filename=cierre_diario_{fecha_obj.isoformat()}.pdf"
    )
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Resumen
# ──────────────────────────────────────────────────────────────────────────────

@bp.get("/resumen")
@jwt_required()
def resumen():
    try:
        return _service().resumen(request.args)
    except ServiceError as exc:
        return _service_error_response(exc)
