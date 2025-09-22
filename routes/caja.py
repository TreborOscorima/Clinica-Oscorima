from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from flask import Blueprint, request, Response, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from extensions import db
from utils.decorators import role_required
from utils.audit import log_action

# ReportLab para PDFs
try:  # pragma: no cover - fallback para entornos sin ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except ModuleNotFoundError:  # pragma: no cover - solo usado en pruebas/entornos mínimos
    A4 = None
    canvas = None

# Modelos / Schemas
from models.caja import (
    CajaMovimiento,
    Comprobante,
    CierreCaja,
    TipoMovimiento,
    MetodoPago,
    ComprobanteItem,
    DeudaPaciente,
)
from models.inventario import Producto, TipoMov, MovimientoStock, aplicar_movimiento
from models.servicio import Servicio
from models.turno import Turno, EstadoTurno
from models.paciente import Paciente

from schemas.caja import (
    CajaMovimientoSchema,
    ComprobanteSchema,
    CierreCajaSchema,
    DeudaPacienteSchema,
)

from utils.inventario_ops import consumir_insumos_por_servicio

bp = Blueprint("caja", __name__, url_prefix="/api/caja")

mov_schema = CajaMovimientoSchema()
mov_many = CajaMovimientoSchema(many=True)
comp_schema = ComprobanteSchema()
cier_schema = CierreCajaSchema()

D2 = Decimal("0.01")
def dec2(x):
    if x is None:
        x = 0
    if not isinstance(x, Decimal):
        x = Decimal(str(x))
    return x.quantize(D2, rounding=ROUND_HALF_UP)

def _mp_from_str(s: str) -> MetodoPago:
    val = (s or "").strip().lower()
    try:
        if val == "efectivo":
            return MetodoPago.EFECTIVO
        if val == "tarjeta":
            return MetodoPago.TARJETA
        if val == "transferencia":
            return MetodoPago.TRANSFERENCIA
        return MetodoPago.OTRO
    except Exception:
        return getattr(MetodoPago, "OTRO", list(MetodoPago)[-1])
    
# --- NUEVO: helper de idempotencia (lee header o payload) ---
def _get_idem_key() -> str | None:
    idem = (request.headers.get("Idempotency-Key") or (request.json or {}).get("idempotency_key") or "").strip()
    return idem or None

# -------------------------
# Movimientos
# -------------------------
@bp.get("/movimientos")
@jwt_required()
def listar_mov():
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")
    tipo = request.args.get("tipo")
    metodo = request.args.get("metodo")

    q = CajaMovimiento.query
    if desde:
        try:
            start = datetime.fromisoformat(desde)
            q = q.filter(CajaMovimiento.fecha >= start)
        except ValueError:
            return {"message": "desde inválido (use ISO 8601)"}, 400
    if hasta:
        try:
            end = datetime.fromisoformat(hasta)
            q = q.filter(CajaMovimiento.fecha <= end)
        except ValueError:
            return {"message": "hasta inválido (use ISO 8601)"}, 400
    if tipo:
        q = q.filter(CajaMovimiento.tipo == tipo)
    if metodo:
        q = q.filter(CajaMovimiento.metodo_pago == metodo)

    items = q.order_by(CajaMovimiento.fecha.desc()).limit(500).all()
    return {"data": mov_many.dump(items)}

@bp.post("/movimientos")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear_mov():
    data = mov_schema.load(request.json or {})
    m = CajaMovimiento(**{k: v for k, v in data.__dict__.items() if not k.startswith("_sa_instance_state")})
    db.session.add(m)
    db.session.commit()
    uid = get_jwt().get("sub")
    log_action(uid, "crear_movimiento_caja", f"Movimiento {m.id} {m.tipo} {m.monto}")
    return mov_schema.dump(m), 201

@bp.delete("/movimientos/<int:mid>")
@jwt_required()
@role_required("administracion")
def eliminar_mov(mid):
    m = CajaMovimiento.query.get_or_404(mid)
    db.session.delete(m)
    db.session.commit()
    uid = get_jwt().get("sub")
    log_action(uid, "eliminar_movimiento_caja", f"Movimiento {mid}")
    return {"message": "Eliminado"}

# -------------------------
# Comprobante simple
# -------------------------
@bp.post("/comprobantes")
@jwt_required()
@role_required("administracion", "recepcionista")
def crear_comprobante():
    payload = request.get_json() or {}
    total = dec2(payload.get("total", "0"))
    paciente_id = payload.get("paciente_id")
    forma = _mp_from_str(payload.get("forma_pago", MetodoPago.EFECTIVO.value))
    observacion = payload.get("observacion", "")
    tipo = payload.get("tipo", "recibo")
    servicio_id = payload.get("servicio_id")
    profesional_id = payload.get("profesional_id")
    descontar_insumos = bool(payload.get("descontar_insumos", True))
    turno_id = payload.get("turno_id")

    # --- NUEVO: idempotencia (si existe columna en el modelo) ---
    idem = _get_idem_key()
    if idem and hasattr(Comprobante, "idempotency_key"):
        prev = Comprobante.query.filter_by(idempotency_key=idem).first()
        if prev:
            return comp_schema.dump(prev), 200

    c = Comprobante(
        tipo=tipo,
        total=total,
        total_bruto=total,
        descuento_global=dec2(0),
        paciente_id=paciente_id,
        forma_pago=forma,
        observacion=observacion,
        **({"idempotency_key": idem} if (idem and hasattr(Comprobante, "idempotency_key")) else {}),
    )
    db.session.add(c)
    db.session.flush()
    c.numero = f"{tipo[:1].upper()}-{c.id:06d}"

    mov_kwargs = dict(
        tipo=TipoMovimiento.INGRESO,
        monto=total,
        metodo_pago=forma,
        paciente_id=paciente_id,
        comprobante_id=c.id,
        servicio_id=servicio_id,
        profesional_id=profesional_id,
        observacion=f"{tipo} {c.numero}",
    )
    if hasattr(CajaMovimiento, "turno_id"):
        mov_kwargs["turno_id"] = turno_id

    mov = CajaMovimiento(**mov_kwargs)
    db.session.add(mov)

    movimientos_stock = []
    if descontar_insumos and servicio_id:
        movimientos_stock = consumir_insumos_por_servicio(
            servicio_id,
            multiplicador=1.0,
            motivo="Consumo por comprobante",
            referencia=c.numero,
            session=db.session,
            estricta=False, 
        )

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if idem and hasattr(Comprobante, "idempotency_key"):
            prev = Comprobante.query.filter_by(idempotency_key=idem).first()
            if prev:
                return comp_schema.dump(prev), 200
        raise

    uid = get_jwt().get("sub")
    log_action(uid, "crear_comprobante", f"Comprobante {c.numero} - turno {turno_id} - stock_movs {len(movimientos_stock)}")

    out = comp_schema.dump(c)
    out["movimientos_stock"] = movimientos_stock
    return out, 201

# -------------------------
# PDF comprobante
# -------------------------
@bp.get("/comprobantes/<int:cid>/pdf")
@jwt_required()
def comprobante_pdf(cid):
    if canvas is None or A4 is None:
        return {"message": "ReportLab no disponible"}, 501
    c = Comprobante.query.get_or_404(cid)
    subtotal = dec2(getattr(c, "total_bruto", None) or sum((it.subtotal or 0) for it in (c.items or [])))
    desc = dec2(getattr(c, "descuento_global", None) or 0)
    total = dec2(getattr(c, "total", 0) or (subtotal - desc))

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, f"Comprobante: {c.tipo.upper()}  N° {c.numero}")
    y -= 30
    p.setFont("Helvetica", 11)
    fecha_safe = getattr(c, "fecha", None) or datetime.utcnow()
    p.drawString(50, y, f"Fecha: {fecha_safe.strftime('%Y-%m-%d %H:%M')}")
    y -= 18
    p.drawString(50, y, f"Paciente ID: {c.paciente_id or '-'}")
    y -= 18
    fp = getattr(c.forma_pago, "value", str(c.forma_pago))
    p.drawString(50, y, f"Forma de pago: {fp}")
    y -= 18
    p.drawString(50, y, f"Subtotal: S/ {float(subtotal):.2f}")
    y -= 18
    p.drawString(50, y, f"Descuento: S/ {float(desc):.2f}")
    y -= 18
    p.drawString(50, y, f"Total: S/ {float(total):.2f}")
    y -= 18
    if c.observacion:
        p.drawString(50, y, f"Obs: {c.observacion}")
        y -= 18

    if getattr(c, "items", None):
        y -= 10
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, "Items:")
        y -= 18
        p.setFont("Helvetica", 10)
        for it in c.items:
            linea = f"- {it.tipo} {it.nombre} x{float(it.cantidad):.2f} @ S/{float(it.precio_unit):.2f}  = S/{float(it.subtotal):.2f}"
            p.drawString(50, y, linea[:110])
            y -= 14
            if y < 80:
                p.showPage(); y = height - 50; p.setFont("Helvetica", 10)

    p.line(50, y, width - 50, y)
    y -= 24
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, y, "Documento generado automáticamente por el sistema de gestión de Clínica Estética.")
    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    resp = Response(pdf, mimetype="application/pdf")
    resp.headers["Content-Disposition"] = f"attachment; filename={c.tipo}_{c.numero}.pdf"
    return resp

# -------------------------
# POS (ATÓMICO + deuda y consumo)
# -------------------------
@bp.post("/pos")
@jwt_required()
@role_required("administracion", "recepcionista")
def pos_emitir():
    """
    Crea comprobante con items (producto/servicio), registra pagos (CajaMovimiento),
    descuenta stock por productos y genera deuda si el pago es parcial.
    Soporta descuento global: {descuento_tipo: 'porcentaje'|'monto'|None, descuento_valor: number}
    """
    payload = request.json or {}
    tipo = (payload.get("tipo") or "boleta").lower()
    paciente_id = payload.get("paciente_id")
    turno_id = payload.get("turno_id")
    observacion = payload.get("observacion") or ""
    items = payload.get("items") or []
    pagos = payload.get("pagos") or []

    dsc_tipo = payload.get("descuento_tipo")  # "porcentaje" | "monto" | None
    dsc_valor = payload.get("descuento_valor")  # numero
    insumos_estricto = bool(payload.get("registrar_insumos_estricto", False))

    # --- NUEVO: idempotencia POS ---
    idem = _get_idem_key()
    if idem and hasattr(Comprobante, "idempotency_key"):
        prev = Comprobante.query.filter_by(idempotency_key=idem).first()
        if prev:
            return comp_schema.dump(prev), 200

    if not items:
        return {"message": "items requeridos"}, 400
    if not pagos:
        return {"message": "Debe registrar al menos un pago (puede ser parcial)"}, 400

    try:
        # 1) Normalizar ítems y subtotal
        total_bruto = Decimal("0")
        items_norm = []
        for it in items:
            t = (it.get("tipo") or "").lower()
            if t not in ("producto", "servicio"):
                return {"message": f"tipo de item inválido: {t}"}, 400
            ref_id = it.get("id")
            if not ref_id:
                return {"message": "id de item requerido"}, 400
            cantidad = dec2(it.get("cantidad") or 0)
            if cantidad <= 0:
                return {"message": "cantidad > 0 requerida"}, 400

            precio = it.get("precio")
            if precio is None:
                if t == "servicio":
                    s = Servicio.query.get(ref_id)
                    if not s:
                        return {"message": f"servicio {ref_id} no existe"}, 404
                    precio = s.precio or 0
                else:
                    p = Producto.query.get(ref_id)
                    if not p:
                        return {"message": f"producto {ref_id} no existe"}, 404
                    if it.get("precio") is not None:
                        precio = it.get("precio")
                    elif getattr(p, "precio_venta", None) is not None:
                        precio = p.precio_venta
                    else:
                        return {
                            "message": f"El producto '{getattr(p, 'nombre', ref_id)}' no tiene precio de venta configurado."
                        }, 400

            precio = dec2(precio)
            sub = dec2(precio * cantidad)
            total_bruto = dec2(total_bruto + sub)

            nombre = it.get("nombre") or (
                Servicio.query.get(ref_id).nombre if t == "servicio" else Producto.query.get(ref_id).nombre
            )

            items_norm.append(
                {"tipo": t, "ref_id": ref_id, "nombre": nombre, "cantidad": cantidad, "precio_unit": precio, "subtotal": sub}
            )

        # 2) Descuento global
        descuento_global = Decimal("0.00")
        if dsc_tipo in ("porcentaje", "monto"):
            try:
                val = dec2(dsc_valor or 0)
            except Exception:
                val = Decimal("0")
            if dsc_tipo == "porcentaje":
                if val < 0: val = Decimal("0")
                if val > 100: val = Decimal("100")
                descuento_global = dec2(total_bruto * (val / Decimal("100")))
            else:
                if val < 0: val = Decimal("0")
                if val > total_bruto: val = total_bruto
                descuento_global = dec2(val)

        total_neto = dec2(total_bruto - descuento_global)

        total_pagado = dec2(sum(dec2(p.get("monto")) for p in pagos))
        forma_pago_str = (pagos[0].get("metodo") if pagos else "efectivo") or "efectivo"
        if len(pagos) > 1:
            forma_pago_str = "otro"
        forma_pago_enum = _mp_from_str(forma_pago_str)

        # 3) Comprobante
        c = Comprobante(
            tipo=tipo,
            paciente_id=paciente_id,
            forma_pago=forma_pago_enum,
            observacion=observacion,
            total=total_neto,
            total_bruto=total_bruto,
            descuento_global=descuento_global,
            **({"idempotency_key": idem} if (idem and hasattr(Comprobante, "idempotency_key")) else {}),
        )
        db.session.add(c)
        db.session.flush()
        pref = "B" if tipo.startswith("boleta") else ("F" if tipo.startswith("factura") else "C")
        c.numero = f"{pref}-{c.id:06d}"

        # 4) Items
        for it in items_norm:
            db.session.add(
                ComprobanteItem(
                    comprobante_id=c.id,
                    tipo=it["tipo"],
                    ref_id=it["ref_id"],
                    nombre=it["nombre"],
                    cantidad=it["cantidad"],
                    precio_unit=it["precio_unit"],
                    subtotal=it["subtotal"],
                )
            )

        # 5) Egresos de productos (VENTA)
        ref = c.numero
        ref_srv = f"{ref}-SRV"
        for it in items_norm:
            if it["tipo"] != "producto":
                continue
            p = Producto.query.get(it["ref_id"])
            if not p:
                db.session.rollback()
                return {"message": f"Producto {it['ref_id']} no encontrado"}, 404
            try:
                aplicar_movimiento(
                    p,
                    TipoMov.EGRESO.value if hasattr(TipoMov, "EGRESO") else "egreso",
                    it["cantidad"],
                    motivo="VENTA",
                    ref=ref
                )
            except ValueError as ve:
                db.session.rollback()
                return {"message": str(ve)}, 400

        # 6) Insumos por servicios
        for it in items_norm:
            if it["tipo"] == "servicio":
                try:
                    consumir_insumos_por_servicio(
                        it["ref_id"],
                        multiplicador=float(it["cantidad"]),
                        motivo="SERVICIO",
                        referencia=ref
                    )
                except Exception:
                    # best-effort si hay servicios sin insumos configurados
                    pass

        # 7) Pagos (CajaMovimiento)
        pagos_rows = []
        for p in pagos:
            metodo = _mp_from_str(p.get("metodo"))
            monto = dec2(p.get("monto") or 0)
            if monto <= 0:
                continue
            cm = CajaMovimiento(
                tipo=TipoMovimiento.INGRESO,
                monto=monto,
                metodo_pago=metodo,
                paciente_id=paciente_id,
                comprobante_id=c.id,
                turno_id=turno_id if hasattr(CajaMovimiento, "turno_id") else None,
                observacion=f"Pago {getattr(metodo,'value',str(metodo))} {c.numero}",
            )
            db.session.add(cm)
            pagos_rows.append(cm)

        # 8) Deuda si pago parcial
        saldo = dec2(total_neto - total_pagado)
        deuda_obj = None
        if saldo > 0 and paciente_id:
            deuda_obj = DeudaPaciente(
                paciente_id=paciente_id,
                comprobante_id=c.id,
                total=total_neto,
                pagado=dec2(total_pagado),
                saldo=saldo,
                estado="pendiente",
            )
            db.session.add(deuda_obj)

        # 9) Estado del turno
        if turno_id:
            t = Turno.query.get(turno_id)
            if t and hasattr(EstadoTurno, "ATENDIDO"):
                t.estado = EstadoTurno.ATENDIDO

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if idem and hasattr(Comprobante, "idempotency_key"):
                prev = Comprobante.query.filter_by(idempotency_key=idem).first()
                if prev:
                    return comp_schema.dump(prev), 200
            raise

        log_action(get_jwt().get("sub"), "pos_emitir", f"Comprobante {c.numero} total {total_neto} pagos {total_pagado}")
        return {
            "comprobante": {
                "id": c.id,
                "numero": c.numero,
                "tipo": c.tipo,
                "total_bruto": float(total_bruto),
                "descuento_global": float(descuento_global),
                "total": float(c.total or 0),
                "paciente_id": c.paciente_id,
                "fecha": getattr(c, "fecha", datetime.utcnow()).isoformat(),
                "forma_pago": getattr(c.forma_pago, "value", str(c.forma_pago)),
                "items": [
                    {
                        "tipo": it["tipo"],
                        "ref_id": it["ref_id"],
                        "nombre": it["nombre"],
                        "cantidad": float(it["cantidad"]),
                        "precio_unit": float(it["precio_unit"]),
                        "subtotal": float(it["subtotal"]),
                    }
                    for it in items_norm
                ],
            },
            "pagos": [{"metodo": getattr(p.metodo_pago, "value", str(p.metodo_pago)), "monto": float(p.monto)} for p in pagos_rows],
            "saldo_pendiente": float(saldo),
            "deuda": (DeudaPacienteSchema().dump(deuda_obj) if deuda_obj else None),
            "pdf_url": f"/api/caja/comprobantes/{c.id}/pdf",
        }, 201

    except ValueError as ve:
        db.session.rollback()
        return {"message": str(ve)}, 400
    except Exception as e:
        db.session.rollback()
        return {"message": f"Error al emitir comprobante: {str(e)}"}, 500

# -------------------------
# Deudas / Cierres / Resumen
# -------------------------

@bp.get("/deudas/paciente/<int:pid>")
@jwt_required()
def deudas_por_paciente(pid):
    qs = DeudaPaciente.query.filter(DeudaPaciente.paciente_id == pid, DeudaPaciente.estado == "pendiente")
    items = qs.order_by(DeudaPaciente.creado_en.desc()).all()
    total_saldo = sum((d.saldo or 0) for d in items)
    return {
        "total_saldo": float(dec2(total_saldo)),
        "items": DeudaPacienteSchema(many=True).dump(items),
    }

@bp.post("/deudas/abonar")
@jwt_required()
def deudas_abonar():
    data = request.get_json(silent=True) or {}
    paciente_id = data.get("paciente_id")
    monto = data.get("monto")
    metodo = _mp_from_str(data.get("metodo") or "efectivo")
    nota = (data.get("nota") or "").strip() or None

    if not paciente_id or monto is None:
        return {"message": "Datos inválidos."}, 400
    try:
        monto = dec2(monto)
        if monto <= 0:
            return {"message": "Monto inválido."}, 400
    except Exception:
        return {"message": "Monto inválido."}, 400

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
    for d in deudas:
        if restante <= 0:
            break
        saldo_d = dec2(d.saldo or 0)
        a_cubrir = saldo_d if saldo_d <= restante else restante
        if a_cubrir <= 0:
            continue

        d.pagado = dec2(Decimal(str(d.pagado or 0)) + a_cubrir)
        d.saldo = dec2(Decimal(str(d.total or 0)) - d.pagado)
        if d.saldo <= 0:
            d.estado = "cancelada"

        abonado_total = dec2(abonado_total + a_cubrir)
        restante = dec2(restante - a_cubrir)

        obs = f"Abono deuda comp {d.comprobante_id}"
        if nota:
            obs = f"{obs} - {nota}"

        cm = CajaMovimiento(
            tipo=TipoMovimiento.INGRESO,
            monto=a_cubrir,
            metodo_pago=metodo,
            paciente_id=paciente_id,
            comprobante_id=d.comprobante_id,
            observacion=obs,
        )
        db.session.add(cm)

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
    return {"ok": True, "abonado": float(dec2(abonado_total)), "saldo": float(dec2(pendientes))}

# =========================
# Helpers de cierre diario
# =========================
def _preview_for_date(f: date):
    start = datetime.combine(f, datetime.min.time())
    end = datetime.combine(f, datetime.max.time())
    movs = CajaMovimiento.query.filter(CajaMovimiento.fecha >= start, CajaMovimiento.fecha <= end).all()

    tot = Decimal("0")
    tot_m = {k: Decimal("0") for k in ("efectivo", "tarjeta", "transferencia", "otro")}
    for m in movs:
        if m.tipo == TipoMovimiento.INGRESO:
            monto = dec2(m.monto or 0)
            tot += monto
            key = (getattr(m.metodo_pago, "value", str(m.metodo_pago)) or "otro").lower()
            if key not in tot_m:
                key = "otro"
            tot_m[key] = dec2(tot_m[key] + monto)

    return {
        "fecha": f.isoformat(),
        "total_ingresos": float(dec2(tot)),
        "por_metodo": {k: float(dec2(v)) for k, v in tot_m.items()},
        "conteo_movs": len(movs),
    }

# =========================
# Cierre diario
# =========================
@bp.get("/cierres/diario/preview")
@jwt_required()
def cierre_preview():
    fecha = (request.args.get("fecha") or date.today().isoformat())
    try:
        f = date.fromisoformat(fecha)
    except Exception:
        return {"message": "fecha inválida (YYYY-MM-DD)"}, 400
    return _preview_for_date(f)


@bp.post("/cierres/diario")
@jwt_required()
@role_required("administracion")
def cierre_confirmar():
    fecha = (request.json or {}).get("fecha") or date.today().isoformat()
    try:
        f = date.fromisoformat(fecha)
    except Exception:
        return {"message": "fecha inválida"}, 400

    ya = CierreCaja.query.filter_by(fecha=f).first()
    if ya:
        return CierreCajaSchema().dump(ya), 200

    prev = _preview_for_date(f)

    c = CierreCaja(
        fecha=f,
        total_ingresos=dec2(prev["total_ingresos"]),
        total_egresos=dec2(0),
        saldo=dec2(prev["total_ingresos"]),
        usuario_id=get_jwt().get("sub"),
    )
    db.session.add(c)
    db.session.commit()
    log_action(get_jwt().get("sub"), "cierre_diario", f"Cierre {f} ingresos {c.total_ingresos}")
    return CierreCajaSchema().dump(c), 201


@bp.get("/cierres/diario/<fecha>/pdf")
@jwt_required()
def cierre_diario_pdf(fecha):
    if canvas is None or A4 is None:
        return {"message": "ReportLab no disponible"}, 501
    try:
        f = date.fromisoformat(fecha)
    except Exception:
        return {"message": "fecha inválida (YYYY-MM-DD)"}, 400

    prev = _preview_for_date(f)

    # PDF simple
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, f"Cierre diario — {f.isoformat()}")
    y -= 24
    p.setFont("Helvetica", 11)
    p.drawString(50, y, f"Total ingresos: S/ {prev.get('total_ingresos', 0):.2f}")
    y -= 18
    pm = prev.get("por_metodo", {}) or {}
    p.drawString(50, y, f"  • Efectivo: S/ {float(pm.get('efectivo', 0)):.2f}")
    y -= 16
    p.drawString(50, y, f"  • Tarjeta: S/ {float(pm.get('tarjeta', 0)):.2f}")
    y -= 16
    p.drawString(50, y, f"  • Transferencia: S/ {float(pm.get('transferencia', 0)):.2f}")
    y -= 16
    p.drawString(50, y, f"  • Otro: S/ {float(pm.get('otro', 0)):.2f}")
    y -= 24
    p.drawString(50, y, f"Movimientos del día: {prev.get('conteo_movs', 0)}")
    y -= 24

    p.setFont("Helvetica-Oblique", 9)
    p.drawString(50, y, "Documento generado automáticamente por el sistema de gestión de Clínica Estética.")
    p.showPage()
    p.save()
    pdf = buf.getvalue()
    buf.close()

    resp = Response(pdf, mimetype="application/pdf")
    resp.headers["Content-Disposition"] = f"attachment; filename=cierre_diario_{f.isoformat()}.pdf"
    return resp

# =========================
# Resumen (rango)
# =========================
@bp.get("/resumen")
@jwt_required()
def resumen():
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")
    start = datetime.fromisoformat(desde) if desde else datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.fromisoformat(hasta) if hasta else datetime.utcnow()
    q = (
        db.session.query(CajaMovimiento.tipo, func.coalesce(func.sum(CajaMovimiento.monto), 0))
        .filter(CajaMovimiento.fecha >= start, CajaMovimiento.fecha <= end)
        .group_by(CajaMovimiento.tipo)
    )
    totals = {tipo: float(total) for tipo, total in q.all()}
    return {"desde": start.isoformat(), "hasta": end.isoformat(), "totales": totals}
