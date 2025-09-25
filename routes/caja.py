from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from flask import Blueprint, Response, request
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from extensions import db
from utils.audit import log_action
from utils.decorators import role_required

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except ModuleNotFoundError:  # pragma: no cover
    A4 = None
    canvas = None


def reportlab_available() -> bool:
    return canvas is not None and A4 is not None


from models.caja import (
    CajaMovimiento,
    CierreCaja,
    Comprobante,
    ComprobanteItem,
    DeudaPaciente,
    MetodoPago,
    TipoMovimiento,
)
from models.inventario import MovimientoStock, Producto, TipoMov, aplicar_movimiento
from models.paciente import Paciente
from models.servicio import Servicio
from models.turno import EstadoTurno, Turno

from schemas.caja import (
    CajaMovimientoSchema,
    CierreCajaSchema,
    ComprobanteSchema,
    DeudaPacienteSchema,
)

from utils.inventario_ops import consumir_insumos_por_servicio
from utils.numeros import numero_a_letras

bp = Blueprint("caja", __name__, url_prefix="/api/caja")

mov_schema = CajaMovimientoSchema()
mov_many = CajaMovimientoSchema(many=True)
comp_schema = ComprobanteSchema()
cier_schema = CierreCajaSchema()

D2 = Decimal("0.01")
ZERO = Decimal("0")


def dec2(value) -> Decimal:
    if value is None:
        value = 0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(D2, rounding=ROUND_HALF_UP)


def _json_payload() -> dict:
    return request.get_json(silent=True) or {}


def _mp_from_str(value: str) -> MetodoPago:
    normalized = (value or "").strip().lower()
    mapping = {
        "efectivo": MetodoPago.EFECTIVO,
        "tarjeta": MetodoPago.TARJETA,
        "transferencia": MetodoPago.TRANSFERENCIA,
    }
    try:
        return mapping.get(normalized, MetodoPago.OTRO)
    except Exception:
        return getattr(MetodoPago, "OTRO", list(MetodoPago)[-1])


def _get_idem_key() -> str | None:
    raw = request.headers.get("Idempotency-Key") or _json_payload().get("idempotency_key")
    key = (raw or "").strip()
    return key or None


@bp.get("/movimientos")
@jwt_required()
def listar_mov():
    args = request.args
    query = CajaMovimiento.query

    desde_raw = args.get("desde")
    if desde_raw:
        try:
            start = datetime.fromisoformat(desde_raw)
        except ValueError:
            return {"message": "desde invalido (use ISO 8601)"}, 400
        query = query.filter(CajaMovimiento.fecha >= start)

    hasta_raw = args.get("hasta")
    if hasta_raw:
        try:
            end = datetime.fromisoformat(hasta_raw)
        except ValueError:
            return {"message": "hasta invalido (use ISO 8601)"}, 400
        query = query.filter(CajaMovimiento.fecha <= end)

    tipo = args.get("tipo")
    if tipo:
        query = query.filter(CajaMovimiento.tipo == tipo)

    metodo = args.get("metodo")
    if metodo:
        query = query.filter(CajaMovimiento.metodo_pago == metodo)

    movimientos = query.order_by(CajaMovimiento.fecha.desc()).limit(500).all()
    return {"data": mov_many.dump(movimientos)}


@bp.post("/movimientos")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear_mov():
    payload = _json_payload()
    loaded = mov_schema.load(payload)
    data = {key: value for key, value in vars(loaded).items() if not key.startswith("_")}
    movimiento = CajaMovimiento(**data)
    db.session.add(movimiento)
    db.session.commit()
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
    movimiento = CajaMovimiento.query.get_or_404(mid)
    db.session.delete(movimiento)
    db.session.commit()
    log_action(get_jwt().get("sub"), "eliminar_movimiento_caja", f"Movimiento {mid}")
    return {"message": "Eliminado"}


@bp.post("/comprobantes")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear_comprobante():
    payload = _json_payload()

    total = dec2(payload.get("total", "0"))
    paciente_id = payload.get("paciente_id")
    forma_pago = _mp_from_str(payload.get("forma_pago", MetodoPago.EFECTIVO.value))
    observacion = payload.get("observacion", "")
    tipo = payload.get("tipo", "recibo")
    servicio_id = payload.get("servicio_id")
    profesional_id = payload.get("profesional_id")
    descontar_insumos = bool(payload.get("descontar_insumos"))
    turno_id = payload.get("turno_id")

    idem = _get_idem_key()
    if idem and hasattr(Comprobante, "idempotency_key"):
        previo = Comprobante.query.filter_by(idempotency_key=idem).first()
        if previo:
            return comp_schema.dump(previo), 200

    comprobante = Comprobante(
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

    movimiento = CajaMovimiento(**movimiento_kwargs)
    db.session.add(movimiento)

    movimientos_stock: list[MovimientoStock] | list[dict] = []
    if descontar_insumos and servicio_id:
        movimientos_stock = consumir_insumos_por_servicio(
            servicio_id,
            multiplicador=1.0,
            motivo="Consumo por comprobante",
            referencia=comprobante.numero,
            session=db.session,
            estricta=False,
        ) or []

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if idem and hasattr(Comprobante, "idempotency_key"):
            previo = Comprobante.query.filter_by(idempotency_key=idem).first()
            if previo:
                return comp_schema.dump(previo), 200
        raise

    log_action(
        get_jwt().get("sub"),
        "crear_comprobante",
        f"Comprobante {comprobante.numero} - turno {turno_id} - stock_movs {len(movimientos_stock)}",
    )

    resultado = comp_schema.dump(comprobante)
    resultado["movimientos_stock"] = movimientos_stock
    return resultado, 201


@bp.get("/comprobantes/<int:cid>/pdf")
@jwt_required()
def comprobante_pdf(cid: int):
    if not reportlab_available():
        return {"message": "ReportLab no disponible"}, 501

    comprobante = Comprobante.query.get_or_404(cid)
    subtotal = dec2(getattr(comprobante, "total_bruto", None) or sum((it.subtotal or 0) for it in (comprobante.items or [])))
    descuento = dec2(getattr(comprobante, "descuento_global", None) or 0)
    total = dec2(getattr(comprobante, "total", 0) or (subtotal - descuento))

    paciente_nombre = ""
    paciente_doc = ""
    if getattr(comprobante, "paciente_id", None):
        paciente = Paciente.query.get(comprobante.paciente_id)
        if paciente:
            paciente_nombre = (paciente.nombre or "").strip()
            paciente_doc = (paciente.documento or "").strip()
    if not paciente_nombre:
        paciente_nombre = "-"

    buffer = BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    cursor_y = height - 50

    lienzo.setFont("Helvetica-Bold", 14)
    lienzo.drawString(50, cursor_y, f"Comprobante: {comprobante.tipo.upper()}  No. {comprobante.numero}")
    cursor_y -= 30

    lienzo.setFont("Helvetica", 11)
    fecha_segura = getattr(comprobante, "fecha", None) or datetime.utcnow()
    lienzo.drawString(50, cursor_y, f"Fecha: {fecha_segura.strftime('%Y-%m-%d %H:%M')}")
    cursor_y -= 18

    lienzo.drawString(50, cursor_y, f"Paciente: {paciente_nombre}")
    cursor_y -= 18

    if paciente_doc:
        lienzo.drawString(50, cursor_y, f"Documento: {paciente_doc}")
        cursor_y -= 18

    forma_pago = getattr(comprobante.forma_pago, "value", str(comprobante.forma_pago))
    lienzo.drawString(50, cursor_y, f"Forma de pago: {forma_pago}")
    cursor_y -= 18

    if comprobante.observacion:
        lienzo.drawString(50, cursor_y, f"Obs: {comprobante.observacion}")
        cursor_y -= 18

    if getattr(comprobante, "items", None):
        cursor_y -= 12
        lienzo.setFont("Helvetica-Bold", 11)
        lienzo.drawString(50, cursor_y, "Detalle de items")
        cursor_y -= 18

        lienzo.setFont("Helvetica-Bold", 10)
        lienzo.drawString(50, cursor_y, "Descripcion")
        lienzo.drawRightString(350, cursor_y, "Cant.")
        lienzo.drawRightString(430, cursor_y, "Precio unit.")
        lienzo.drawRightString(510, cursor_y, "Importe")
        cursor_y -= 14
        lienzo.setFont("Helvetica", 10)

        for item in comprobante.items:
            if cursor_y < 80:
                lienzo.showPage()
                cursor_y = height - 50
                lienzo.setFont("Helvetica-Bold", 10)
                lienzo.drawString(50, cursor_y, "Descripcion")
                lienzo.drawRightString(350, cursor_y, "Cant.")
                lienzo.drawRightString(430, cursor_y, "Precio unit.")
                lienzo.drawRightString(510, cursor_y, "Importe")
                cursor_y -= 14
                lienzo.setFont("Helvetica", 10)

            descripcion = (item.nombre or "").strip()
            tipo_linea = (item.tipo or "").strip()
            if tipo_linea:
                descripcion = f"{tipo_linea.capitalize()} - {descripcion}" if descripcion else tipo_linea.capitalize()

            lienzo.drawString(50, cursor_y, descripcion[:80])
            lienzo.drawRightString(350, cursor_y, f"{float(item.cantidad or 0):.2f}")
            lienzo.drawRightString(430, cursor_y, f"S/ {float(item.precio_unit or 0):.2f}")
            lienzo.drawRightString(510, cursor_y, f"S/ {float(item.subtotal or 0):.2f}")
            cursor_y -= 14

    cursor_y -= 8
    lienzo.setFont("Helvetica", 10)
    lienzo.drawRightString(520, cursor_y, f"Subtotal: S/ {float(subtotal):.2f}")
    cursor_y -= 16
    lienzo.drawRightString(520, cursor_y, f"Descuento aplicado: S/ {float(descuento):.2f}")
    cursor_y -= 16
    lienzo.setFont("Helvetica-Bold", 11)
    lienzo.drawRightString(510, cursor_y, f"Total: S/ {float(total):.2f}")
    cursor_y -= 24

    try:
        total_letras = numero_a_letras(float(total), moneda="soles")
    except Exception:
        total_letras = f"{float(total):.2f}"
    lienzo.drawString(50, cursor_y, f"Importe: {total_letras}")
    cursor_y -= 24

    lienzo.line(50, cursor_y, width - 50, cursor_y)
    cursor_y -= 24

    lienzo.setFont("Helvetica-Oblique", 10)
    lienzo.drawString(50, cursor_y, "Documento generado automaticamente por el sistema de gestion.")
    lienzo.showPage()
    lienzo.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = Response(pdf, mimetype="application/pdf")
    response.headers["Content-Disposition"] = f"attachment; filename={comprobante.tipo}_{comprobante.numero}.pdf"
    return response


@bp.post("/pos")
@jwt_required()
@role_required("administracion", "recepcionista")
def pos_emitir():
    payload = _json_payload()

    tipo = (payload.get("tipo") or "boleta").lower()
    paciente_id = payload.get("paciente_id")
    turno_id = payload.get("turno_id")
    observacion = payload.get("observacion") or ""
    items_raw = payload.get("items") or []
    pagos_raw = payload.get("pagos") or []
    descontar_insumos = bool(payload.get("descontar_insumos"))

    dsc_tipo = payload.get("descuento_tipo")
    dsc_valor = payload.get("descuento_valor")

    idem = _get_idem_key()
    if idem and hasattr(Comprobante, "idempotency_key"):
        previo = Comprobante.query.filter_by(idempotency_key=idem).first()
        if previo:
            return comp_schema.dump(previo), 200

    if not items_raw:
        return {"message": "items requeridos"}, 400
    if not pagos_raw:
        return {"message": "Debe registrar al menos un pago (puede ser parcial)"}, 400

    try:
        total_bruto = Decimal("0")
        items_norm: list[dict] = []

        for item in items_raw:
            item_type = (item.get("tipo") or "").lower()
            if item_type not in ("producto", "servicio"):
                raise ValueError(f"tipo de item invalido: {item_type}")

            ref_id = item.get("id")
            if not ref_id:
                raise ValueError("id de item requerido")

            cantidad = dec2(item.get("cantidad") or 0)
            if cantidad <= 0:
                raise ValueError("cantidad > 0 requerida")

            precio = item.get("precio")
            servicio = None
            producto = None
            if item_type == "servicio":
                servicio = Servicio.query.get(ref_id)
                if not servicio:
                    return {"message": f"servicio {ref_id} no existe"}, 404
                if precio is None:
                    precio = servicio.precio or 0
            else:
                producto = Producto.query.get(ref_id)
                if not producto:
                    return {"message": f"producto {ref_id} no existe"}, 404
                if precio is None:
                    if getattr(producto, "precio_venta", None) is not None:
                        precio = producto.precio_venta
                    else:
                        return {
                            "message": f"El producto '{getattr(producto, 'nombre', ref_id)}' no tiene precio de venta configurado."
                        }, 400

            precio = dec2(precio)
            subtotal = dec2(precio * cantidad)
            total_bruto = dec2(total_bruto + subtotal)

            base_nombre = servicio.nombre if servicio else (producto.nombre if producto else "")
            nombre = item.get("nombre") or base_nombre or ""

            items_norm.append(
                {
                    "tipo": item_type,
                    "ref_id": ref_id,
                    "nombre": nombre,
                    "cantidad": cantidad,
                    "precio_unit": precio,
                    "subtotal": subtotal,
                }
            )

        descuento_global = Decimal("0.00")
        if dsc_tipo in ("porcentaje", "monto"):
            try:
                valor_descuento = dec2(dsc_valor or 0)
            except Exception:
                valor_descuento = Decimal("0")

            if dsc_tipo == "porcentaje":
                valor_descuento = min(max(valor_descuento, Decimal("0")), Decimal("100"))
                descuento_global = dec2(total_bruto * (valor_descuento / Decimal("100")))
            else:
                valor_descuento = min(max(valor_descuento, Decimal("0")), total_bruto)
                descuento_global = dec2(valor_descuento)

        total_neto = dec2(total_bruto - descuento_global)
        total_pagado = dec2(sum(dec2(pago.get("monto")) for pago in pagos_raw))

        metodo_principal = (pagos_raw[0].get("metodo") if pagos_raw else "efectivo") or "efectivo"
        if len(pagos_raw) > 1:
            metodo_principal = "otro"
        forma_pago_enum = _mp_from_str(metodo_principal)

        comprobante = Comprobante(
            tipo=tipo,
            paciente_id=paciente_id,
            forma_pago=forma_pago_enum,
            observacion=observacion,
            total=total_neto,
            total_bruto=total_bruto,
            descuento_global=descuento_global,
            **({"idempotency_key": idem} if (idem and hasattr(Comprobante, "idempotency_key")) else {}),
        )
        db.session.add(comprobante)
        db.session.flush()
        prefijo = "B" if tipo.startswith("boleta") else ("F" if tipo.startswith("factura") else "C")
        comprobante.numero = f"{prefijo}-{comprobante.id:06d}"

        for item in items_norm:
            db.session.add(
                ComprobanteItem(
                    comprobante_id=comprobante.id,
                    tipo=item["tipo"],
                    ref_id=item["ref_id"],
                    nombre=item["nombre"],
                    cantidad=item["cantidad"],
                    precio_unit=item["precio_unit"],
                    subtotal=item["subtotal"],
                )
            )

        referencia = comprobante.numero
        for item in items_norm:
            if item["tipo"] != "producto":
                continue

            producto = Producto.query.get(item["ref_id"])
            if not producto:
                db.session.rollback()
                return {"message": f"Producto {item['ref_id']} no encontrado"}, 404

            try:
                aplicar_movimiento(
                    producto,
                    TipoMov.EGRESO.value if hasattr(TipoMov, "EGRESO") else "egreso",
                    item["cantidad"],
                    motivo="VENTA",
                    ref=referencia,
                )
            except ValueError as error:
                db.session.rollback()
                return {"message": str(error)}, 400

        if descontar_insumos:
            for item in items_norm:
                if item["tipo"] != "servicio":
                    continue
                try:
                    consumir_insumos_por_servicio(
                        item["ref_id"],
                        multiplicador=float(item["cantidad"]),
                        motivo="SERVICIO",
                        referencia=referencia,
                    )
                except Exception:
                    pass

        pagos_creados: list[CajaMovimiento] = []
        for pago in pagos_raw:
            metodo = _mp_from_str(pago.get("metodo"))
            monto = dec2(pago.get("monto") or 0)
            if monto <= 0:
                continue

            pago_mov = CajaMovimiento(
                tipo=TipoMovimiento.INGRESO,
                monto=monto,
                metodo_pago=metodo,
                paciente_id=paciente_id,
                comprobante_id=comprobante.id,
                turno_id=turno_id if hasattr(CajaMovimiento, "turno_id") else None,
                observacion=f"Pago {getattr(metodo, 'value', str(metodo))} {comprobante.numero}",
            )
            db.session.add(pago_mov)
            pagos_creados.append(pago_mov)

        saldo = dec2(total_neto - total_pagado)
        deuda_obj = None
        if saldo > 0 and paciente_id:
            deuda_obj = DeudaPaciente(
                paciente_id=paciente_id,
                comprobante_id=comprobante.id,
                total=total_neto,
                pagado=dec2(total_pagado),
                saldo=saldo,
                estado="pendiente",
            )
            db.session.add(deuda_obj)

        if turno_id:
            turno = Turno.query.get(turno_id)
            if turno and hasattr(EstadoTurno, "ATENDIDO"):
                turno.estado = EstadoTurno.ATENDIDO

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if idem and hasattr(Comprobante, "idempotency_key"):
                previo = Comprobante.query.filter_by(idempotency_key=idem).first()
                if previo:
                    return comp_schema.dump(previo), 200
            raise

        log_action(
            get_jwt().get("sub"),
            "pos_emitir",
            f"Comprobante {comprobante.numero} total {total_neto} pagos {total_pagado}",
        )

        return {
            "comprobante": {
                "id": comprobante.id,
                "numero": comprobante.numero,
                "tipo": comprobante.tipo,
                "total_bruto": float(total_bruto),
                "descuento_global": float(descuento_global),
                "total": float(comprobante.total or 0),
                "paciente_id": comprobante.paciente_id,
                "fecha": getattr(comprobante, "fecha", datetime.utcnow()).isoformat(),
                "forma_pago": getattr(comprobante.forma_pago, "value", str(comprobante.forma_pago)),
                "items": [
                    {
                        "tipo": item["tipo"],
                        "ref_id": item["ref_id"],
                        "nombre": item["nombre"],
                        "cantidad": float(item["cantidad"]),
                        "precio_unit": float(item["precio_unit"]),
                        "subtotal": float(item["subtotal"]),
                    }
                    for item in items_norm
                ],
            },
            "pagos": [
                {
                    "metodo": getattr(pago.metodo_pago, "value", str(pago.metodo_pago)),
                    "monto": float(pago.monto),
                }
                for pago in pagos_creados
            ],
            "saldo_pendiente": float(saldo),
            "deuda": DeudaPacienteSchema().dump(deuda_obj) if deuda_obj else None,
            "pdf_url": f"/api/caja/comprobantes/{comprobante.id}/pdf",
        }, 201

    except ValueError as error:
        db.session.rollback()
        return {"message": str(error)}, 400
    except Exception as error:
        db.session.rollback()
        return {"message": f"Error al emitir comprobante: {error}"}, 500


@bp.get("/deudas/paciente/<int:pid>")
@jwt_required()
def deudas_por_paciente(pid: int):
    query = DeudaPaciente.query.filter(
        DeudaPaciente.paciente_id == pid,
        DeudaPaciente.estado == "pendiente",
    )
    items = query.order_by(DeudaPaciente.creado_en.desc()).all()
    total_saldo = sum((deuda.saldo or 0) for deuda in items)
    return {
        "data": DeudaPacienteSchema(many=True).dump(items),
        "saldo_total": float(dec2(total_saldo)),
    }


@bp.post("/deudas/abonar")
@jwt_required()
@role_required("administracion", "recepcionista")
def deudas_abonar():
    payload = _json_payload()
    paciente_id = payload.get("paciente_id")
    monto_raw = payload.get("monto")
    metodo = _mp_from_str(payload.get("metodo", MetodoPago.EFECTIVO.value))
    nota = payload.get("nota") or ""

    if not paciente_id:
        return {"message": "paciente_id requerido"}, 400
    try:
        monto = dec2(monto_raw)
        if monto <= 0:
            return {"message": "Monto invalido."}, 400
    except Exception:
        return {"message": "Monto invalido."}, 400

    deudas = (
        DeudaPaciente.query.filter(
            DeudaPaciente.paciente_id == paciente_id,
            DeudaPaciente.estado == "pendiente",
            (DeudaPaciente.saldo > 0),
        )
        .order_by(DeudaPaciente.creado_en.asc())
        .all()
    )
    if not deudas:
        return {"message": "El paciente no tiene deudas pendientes."}, 404

    restante = monto
    abonado_total = Decimal("0.00")
    for deuda in deudas:
        if restante <= 0:
            break
        saldo_deuda = dec2(deuda.saldo or 0)
        cubrir = saldo_deuda if saldo_deuda <= restante else restante
        if cubrir <= 0:
            continue

        deuda.pagado = dec2(Decimal(str(deuda.pagado or 0)) + cubrir)
        deuda.saldo = dec2(Decimal(str(deuda.total or 0)) - deuda.pagado)
        if deuda.saldo <= 0:
            deuda.estado = "cancelada"

        abonado_total = dec2(abonado_total + cubrir)
        restante = dec2(restante - cubrir)

        observacion = f"Abono deuda comp {deuda.comprobante_id}"
        if nota:
            observacion = f"{observacion} - {nota}"

        movimiento = CajaMovimiento(
            tipo=TipoMovimiento.INGRESO,
            monto=cubrir,
            metodo_pago=metodo,
            paciente_id=paciente_id,
            comprobante_id=deuda.comprobante_id,
            observacion=observacion,
        )
        db.session.add(movimiento)

    db.session.commit()

    pendientes = (
        db.session.query(func.coalesce(func.sum(DeudaPaciente.saldo), 0))
        .filter(
            DeudaPaciente.paciente_id == paciente_id,
            DeudaPaciente.estado == "pendiente",
            (DeudaPaciente.saldo > 0),
        )
        .scalar()
        or Decimal("0")
    )
    return {
        "ok": True,
        "abonado": float(dec2(abonado_total)),
        "saldo": float(dec2(pendientes)),
    }


def _preview_for_date(fecha: date):
    inicio = datetime.combine(fecha, time.min)
    fin = datetime.combine(fecha, time.max)
    movimientos = CajaMovimiento.query.filter(
        CajaMovimiento.fecha >= inicio,
        CajaMovimiento.fecha <= fin,
    ).all()

    total = Decimal("0")
    por_metodo: dict[str, Decimal] = {k: Decimal("0") for k in ("efectivo", "tarjeta", "transferencia", "otro")}
    for movimiento in movimientos:
        if movimiento.tipo == TipoMovimiento.INGRESO:
            monto = dec2(movimiento.monto or 0)
            total += monto
            metodo_key = (getattr(movimiento.metodo_pago, "value", str(movimiento.metodo_pago)) or "otro").lower()
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
    fecha_raw = request.args.get("fecha") or date.today().isoformat()
    try:
        fecha = date.fromisoformat(fecha_raw)
    except Exception:
        return {"message": "fecha invalida (YYYY-MM-DD)"}, 400
    return _preview_for_date(fecha)


@bp.post("/cierres/diario")
@jwt_required()
@role_required("administracion")
def cierre_confirmar():
    fecha_raw = _json_payload().get("fecha") or date.today().isoformat()
    try:
        fecha = date.fromisoformat(fecha_raw)
    except Exception:
        return {"message": "fecha invalida"}, 400

    existente = CierreCaja.query.filter_by(fecha=fecha).first()
    if existente:
        return cier_schema.dump(existente), 200

    preview = _preview_for_date(fecha)
    cierre = CierreCaja(
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
    if not reportlab_available():
        return {"message": "ReportLab no disponible"}, 501
    try:
        fecha_obj = date.fromisoformat(fecha)
    except Exception:
        return {"message": "fecha invalida (YYYY-MM-DD)"}, 400

    preview = _preview_for_date(fecha_obj)

    buffer = BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    cursor_y = height - 50

    lienzo.setFont("Helvetica-Bold", 14)
    lienzo.drawString(50, cursor_y, f"Cierre diario - {fecha_obj.isoformat()}")
    cursor_y -= 24

    lienzo.setFont("Helvetica", 11)
    lienzo.drawString(50, cursor_y, f"Total ingresos: S/ {preview.get('total_ingresos', 0):.2f}")
    cursor_y -= 18

    por_metodo = preview.get("por_metodo", {}) or {}
    lienzo.drawString(50, cursor_y, f"  - Efectivo: S/ {float(por_metodo.get('efectivo', 0)):.2f}")
    cursor_y -= 16
    lienzo.drawString(50, cursor_y, f"  - Tarjeta: S/ {float(por_metodo.get('tarjeta', 0)):.2f}")
    cursor_y -= 16
    lienzo.drawString(50, cursor_y, f"  - Transferencia: S/ {float(por_metodo.get('transferencia', 0)):.2f}")
    cursor_y -= 16
    lienzo.drawString(50, cursor_y, f"  - Otro: S/ {float(por_metodo.get('otro', 0)):.2f}")
    cursor_y -= 24

    lienzo.drawString(50, cursor_y, f"Movimientos del dia: {preview.get('conteo_movs', 0)}")
    cursor_y -= 24

    lienzo.setFont("Helvetica-Oblique", 9)
    lienzo.drawString(50, cursor_y, "Documento generado automaticamente por el sistema de gestion.")
    lienzo.showPage()
    lienzo.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = Response(pdf, mimetype="application/pdf")
    response.headers["Content-Disposition"] = f"attachment; filename=cierre_diario_{fecha_obj.isoformat()}.pdf"
    return response


@bp.get("/resumen")
@jwt_required()
def resumen():
    args = request.args
    desde_raw = args.get("desde")
    hasta_raw = args.get("hasta")

    start = datetime.fromisoformat(desde_raw) if desde_raw else datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.fromisoformat(hasta_raw) if hasta_raw else datetime.utcnow()

    query = (
        db.session.query(CajaMovimiento.tipo, func.coalesce(func.sum(CajaMovimiento.monto), 0))
        .filter(CajaMovimiento.fecha >= start, CajaMovimiento.fecha <= end)
        .group_by(CajaMovimiento.tipo)
    )
    totales = {tipo: float(total) for tipo, total in query.all()}
    return {"desde": start.isoformat(), "hasta": end.isoformat(), "totales": totales}