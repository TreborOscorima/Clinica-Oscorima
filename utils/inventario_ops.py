# utils/inventario_ops.py
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from extensions import db
from models.inventario import MovimientoStock, TipoMov, Producto
from models.servicio_insumo import ServicioInsumo

def _D(x) -> Decimal:
    if isinstance(x, Decimal): 
        return x
    if x is None: 
        return Decimal("0")
    try: 
        return Decimal(str(x))
    except (InvalidOperation, ValueError): 
        return Decimal("0")

def consumir_insumos_por_servicio(
    servicio_id: int,
    multiplicador=1,
    motivo="",
    referencia="",
    session: Session = None,
    estricta: bool = False,
    clinica_id: int | None = None,
):
    """
    Compatibilidad: delega en la versión por lotes.
    """
    return consumir_insumos_por_servicios_en_lote(
        [(servicio_id, multiplicador)],
        motivo=motivo,
        referencia=referencia,
        session=session or db.session,
        estricta=estricta,
        clinica_id=clinica_id,
    )

def consumir_insumos_por_servicios_en_lote(
    servicios: list,  # [(servicio_id, multiplicador), ...]
    *, motivo: str = "", referencia: str = "",
    session: Session = None, estricta: bool = False,
    clinica_id: int | None = None,
):
    """
    Suma insumos de TODOS los servicios del POS y descuenta por producto.
    Devuelve una lista de movimientos resumidos: [{producto_id, cantidad, saldo}].
    - Filtra SIEMPRE cantidades <= 0 (no crea renglones “0.000”).
    - Si 'estricta' es True, valida stock suficiente y existencia de productos.
    """
    session = session or db.session
    totales = defaultdict(Decimal)

    # 1) Acumular requerimientos por producto (filtrando cantidades <= 0)
    for sid, mult in servicios:
        mult = _D(mult)
        items = session.execute(
            select(ServicioInsumo).where(ServicioInsumo.servicio_id == sid)
        ).scalars().all()

        for it in items:
            req = _D(it.cantidad_por_sesion) * mult
            # 🔧 FIX: ignorar cualquier requerimiento no positivo
            if req is None or req <= 0:
                continue
            totales[it.producto_id] += req

    # 2) (opcional) validar stock total en modo 'estricta'
    if estricta:
        falt = []
        for pid, cant in totales.items():
            # si por alguna razón quedó 0 después de acumular, ignorar en la validación también
            if cant <= 0:
                continue
            stmt = select(Producto).where(Producto.id == pid)
            if clinica_id is not None:
                stmt = stmt.where(Producto.clinica_id == clinica_id, Producto.is_active.is_(True))
            prod = session.execute(stmt.with_for_update(read=True)).scalar_one_or_none()
            disp = _D(getattr(prod, "stock_actual", 0)) if prod else Decimal("0")
            if disp < cant:
                falt.append({"producto_id": pid, "requerido": str(cant), "disponible": str(disp)})
        if falt:
            raise ValueError(f"Stock insuficiente de insumos: {falt}")

    # 3) Descontar por producto en una sola pasada (sin crear movimientos de 0)
    movimientos = []
    for pid, cant in totales.items():
        # 🔧 FIX: no intentes crear movimientos con cantidad <= 0
        if cant is None or cant <= 0:
            continue

        stmt = select(Producto).where(Producto.id == pid)
        if clinica_id is not None:
            stmt = stmt.where(Producto.clinica_id == clinica_id, Producto.is_active.is_(True))
        prod = session.execute(stmt.with_for_update()).scalar_one_or_none()
        if not prod:
            if estricta:
                raise ValueError(f"Producto {pid} no existe")
            else:
                continue

        disp = _D(prod.stock_actual)
        # en modo no estricto, descontamos hasta donde alcance
        desc = cant if estricta or disp >= cant else disp

        # 🔧 FIX: si el resultante a descontar es 0 o negativo, no generes movimiento
        if desc is None or desc <= 0:
            continue

        nuevo = disp - desc
        mov = MovimientoStock(
            clinica_id=prod.clinica_id,
            producto_id=pid,
            tipo=TipoMov.EGRESO.value if hasattr(TipoMov, "EGRESO") else "egreso",
            cantidad=desc,
            saldo=nuevo,
            motivo=motivo,
            referencia=referencia,
            fecha=datetime.now(timezone.utc),
        )
        session.add(mov)

        prod.stock_actual = nuevo
        movimientos.append({
            "producto_id": pid,
            "cantidad": str(desc),
            "saldo": str(nuevo)
        })

    session.flush()
    return movimientos
