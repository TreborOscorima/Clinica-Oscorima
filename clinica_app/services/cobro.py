from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func
from sqlmodel import select
from sqlmodel import Session

from clinica_app.models.caja import (
    CajaMovimiento,
    Comprobante,
    ComprobanteItem,
    DeudaPaciente,
    MetodoPago,
    TipoMovimiento,
)
from clinica_app.models.inventario import MovimientoStock, Producto
from clinica_app.models.paciente import Paciente
from clinica_app.services.exceptions import NotFoundError, ServiceError

D2 = Decimal("0.01")


def _dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _dump_item(i: ComprobanteItem) -> dict[str, Any]:
    return {
        "id":          i.id,
        "tipo":        i.tipo,
        "ref_id":      i.ref_id,
        "nombre":      i.nombre,
        "cantidad":    str(i.cantidad),
        "precio_unit": str(i.precio_unit),
        "subtotal":    str(i.subtotal),
    }


def _dump(c: Comprobante, items: list[ComprobanteItem] | None = None) -> dict[str, Any]:
    return {
        "id":               c.id,
        "numero":           c.numero or "",
        "tipo":             c.tipo or "recibo",
        "fecha":            c.fecha.strftime("%Y-%m-%d %H:%M") if c.fecha else "",
        "paciente_id":      c.paciente_id,
        "total_bruto":      str(c.total_bruto or 0),
        "descuento_global": str(c.descuento_global or 0),
        "total":            str(c.total or 0),
        "forma_pago":       c.forma_pago.value if c.forma_pago else "efectivo",
        "observacion":      c.observacion or "",
        "items":            [_dump_item(i) for i in (items or [])],
    }


def _numero(session: Session, clinica_id: int) -> str:
    """Genera un número de comprobante único: REC-{clinica_id}-{YYYYMMDD}-{seq:04d}."""
    hoy = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"REC-{clinica_id}-{hoy}-"
    count: int = session.execute(
        select(func.count()).select_from(
            select(Comprobante).where(
                Comprobante.clinica_id == clinica_id,
                Comprobante.numero.like(f"{prefix}%"),
            ).subquery()
        )
    ).scalar_one()
    return f"{prefix}{count + 1:04d}"


def crear(session: Session, clinica_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    paciente_id = payload.get("paciente_id")
    if not paciente_id:
        raise ServiceError("paciente_id requerido")

    paciente = session.exec(
        select(Paciente).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
            Paciente.is_active.is_(True),
        )
    ).first()
    if not paciente:
        raise NotFoundError("Paciente no encontrado")

    items_payload = payload.get("items") or []
    if not items_payload:
        raise ServiceError("El comprobante debe tener al menos un ítem")

    metodo_str = (payload.get("forma_pago") or "efectivo").lower()
    try:
        forma_pago = MetodoPago(metodo_str)
    except ValueError:
        forma_pago = MetodoPago.OTRO

    total_bruto = Decimal("0")
    processed: list[dict] = []
    for item_data in items_payload:
        try:
            cantidad    = _dec(item_data.get("cantidad", "1"))
            precio_unit = _dec(item_data.get("precio_unit", "0"))
        except Exception as exc:
            raise ServiceError("Cantidad o precio inválido") from exc
        if cantidad <= 0:
            raise ServiceError("La cantidad debe ser mayor a cero")
        subtotal = (cantidad * precio_unit).quantize(D2, rounding=ROUND_HALF_UP)
        total_bruto += subtotal
        processed.append({
            "tipo":        (item_data.get("tipo") or "servicio"),
            "ref_id":      int(item_data.get("ref_id") or 0),
            "nombre":      (item_data.get("nombre") or ""),
            "cantidad":    cantidad,
            "precio_unit": precio_unit,
            "subtotal":    subtotal,
        })

    descuento_global = _dec(payload.get("descuento_global", "0"))
    if descuento_global < 0:
        raise ServiceError("El descuento no puede ser negativo")
    total_neto = max(Decimal("0"), total_bruto - descuento_global)

    numero = _numero(session, clinica_id)

    comp = Comprobante(
        clinica_id=clinica_id,
        tipo=payload.get("tipo") or "recibo",
        numero=numero,
        paciente_id=paciente_id,
        total_bruto=total_bruto,
        descuento_global=descuento_global,
        total=total_neto,
        forma_pago=forma_pago,
        observacion=payload.get("observacion"),
    )
    session.add(comp)
    session.flush()

    items_db: list[ComprobanteItem] = []
    for p in processed:
        ci = ComprobanteItem(
            comprobante_id=comp.id,
            tipo=p["tipo"],
            ref_id=p["ref_id"],
            nombre=p["nombre"],
            cantidad=p["cantidad"],
            precio_unit=p["precio_unit"],
            subtotal=p["subtotal"],
        )
        session.add(ci)
        items_db.append(ci)
        if p["tipo"] == "producto" and p["ref_id"]:
            _descontar_stock(session, clinica_id, p["ref_id"], p["cantidad"], comp.id)

    session.flush()

    es_cuotas  = bool(payload.get("es_cuotas"))
    num_cuotas = max(1, int(payload.get("num_cuotas") or 1))
    anticipo   = _dec(payload.get("cuota_inicial") or "0")

    if es_cuotas and num_cuotas > 1:
        deuda = DeudaPaciente(
            clinica_id=clinica_id,
            paciente_id=paciente_id,
            comprobante_id=comp.id,
            total=total_neto,
            pagado=Decimal("0"),
            saldo=total_neto,
            estado="pendiente",
        )
        session.add(deuda)
        if anticipo > 0:
            _ingreso(session, clinica_id, anticipo, forma_pago, paciente_id, comp.id,
                     f"Anticipo cuotas {numero}")
            deuda.pagado = anticipo
            deuda.saldo  = max(Decimal("0"), total_neto - anticipo)
            if deuda.saldo == 0:
                deuda.estado = "cancelado"
    else:
        _ingreso(session, clinica_id, total_neto, forma_pago, paciente_id, comp.id,
                 f"Cobro {numero}")

    session.flush()
    return _dump(comp, items_db)


def _ingreso(
    session: Session,
    clinica_id: int,
    monto: Decimal,
    metodo: MetodoPago,
    paciente_id: int,
    comprobante_id: int,
    observacion: str,
) -> None:
    if monto <= 0:
        return
    session.add(CajaMovimiento(
        clinica_id=clinica_id,
        tipo=TipoMovimiento.INGRESO,
        monto=monto,
        metodo_pago=metodo,
        paciente_id=paciente_id,
        comprobante_id=comprobante_id,
        observacion=observacion,
    ))


def _descontar_stock(
    session: Session,
    clinica_id: int,
    producto_id: int,
    cantidad: Decimal,
    comprobante_id: int,
) -> None:
    prod = session.exec(
        select(Producto).where(
            Producto.id == producto_id,
            Producto.clinica_id == clinica_id,
            Producto.is_active.is_(True),
        )
    ).first()
    if not prod:
        return
    nuevo_stock = (prod.stock_actual or Decimal("0")) - cantidad
    prod.stock_actual = nuevo_stock
    session.add(MovimientoStock(
        clinica_id=clinica_id,
        producto_id=producto_id,
        tipo="egreso",
        cantidad=cantidad,
        saldo=nuevo_stock,
        motivo="Venta",
        referencia=f"comp:{comprobante_id}",
    ))


def listar(
    session: Session,
    clinica_id: int,
    paciente_id: int | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = select(Comprobante).where(
        Comprobante.clinica_id == clinica_id,
        Comprobante.is_active.is_(True),
    )
    if paciente_id:
        stmt = stmt.where(Comprobante.paciente_id == paciente_id)

    total: int = session.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    items = session.exec(
        stmt.order_by(Comprobante.fecha.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return {
        "data":     [_dump(c) for c in items],
        "page":     page,
        "per_page": per_page,
        "total":    total,
        "pages":    max(1, -(-total // per_page)),
    }


def obtener(session: Session, clinica_id: int, comp_id: int) -> dict[str, Any]:
    comp = session.exec(
        select(Comprobante).where(
            Comprobante.clinica_id == clinica_id,
            Comprobante.id == comp_id,
        )
    ).first()
    if not comp:
        raise NotFoundError("Comprobante no encontrado")
    items = session.exec(
        select(ComprobanteItem).where(ComprobanteItem.comprobante_id == comp_id)
    ).all()
    return _dump(comp, list(items))


def anular(session: Session, clinica_id: int, comp_id: int) -> None:
    comp = session.exec(
        select(Comprobante).where(
            Comprobante.clinica_id == clinica_id,
            Comprobante.id == comp_id,
            Comprobante.is_active.is_(True),
        )
    ).first()
    if not comp:
        raise NotFoundError("Comprobante no encontrado")
    comp.soft_delete()
    session.flush()
