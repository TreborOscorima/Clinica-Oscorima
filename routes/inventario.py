# routes/inventario.py
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, text
from extensions import db

def _base_ref(ref: str) -> str:
    ref = (ref or "").strip()
    return ref[:-4] if ref.endswith("-SRV") else ref

def _try_fetch_comprobante_by_ref(ref: str):
    """Devuelve dict {'id','numero','total','paciente_nombre','items':[{'producto':{'id'},'cantidad','precio_unitario','subtotal'}]} o None."""
    try:
        from models.caja import Comprobante, ComprobanteItem
        try:
            from models.paciente import Paciente
        except Exception:
            Paciente = None
    except Exception:
        return None

    if not ref:
        return None
    numero = _base_ref(ref)

    # Buscar por numero completo
    c = None
    if hasattr(Comprobante, "numero"):
        c = Comprobante.query.filter(func.lower(Comprobante.numero) == numero.lower()).first()

    # Buscar por serie/correlativo si aplica
    if (not c) and "-" in numero:
        pref, suf = numero.split("-", 1)
        q = Comprobante.query
        if hasattr(Comprobante, "serie"):
            q = q.filter(func.lower(Comprobante.serie) == pref.lower())
        if hasattr(Comprobante, "correlativo"):
            q = q.filter(func.lower(Comprobante.correlativo) == suf.lower())
        c = q.first()

    if not c:
        return None

    # Items
    items = []
    its = ComprobanteItem.query.filter_by(comprobante_id=c.id).all() if ComprobanteItem else []
    for it in its:
        item_tipo = str(getattr(it, "tipo", "") or "").lower()
        if item_tipo in {"servicio", "service"}:
            # ignorar servicios u otros conceptos en el detalle de inventario
            continue
        pid_it = getattr(it, "ref_id", None) or getattr(it, "producto_id", None)
        cant = float(getattr(it, "cantidad", 0) or 0)
        pvu = getattr(it, "precio_unitario", None)
        if pvu is None:
            pvu = getattr(it, "precio_unit", None)
        if pvu is None:
            pvu = getattr(it, "precio", None)
        pvu = float(pvu or 0)
        sub = getattr(it, "subtotal", None)
        if sub is None:
            sub = cant * pvu
        nombre_linea = getattr(it, "nombre", None)
        items.append({
            "producto": {"id": pid_it} if pid_it else None,
            "cantidad": cant,
            "precio_unitario": pvu,
            "subtotal": float(sub or 0),
            "tipo": item_tipo or None,
            "nombre": nombre_linea,
        })

    # Total
    total = float(getattr(c, "total", 0) or 0)
    if not total:
        total = float(sum(x["subtotal"] for x in items))

    # Paciente / Razón social
    paciente_nombre = ""
    paciente_documento = ""
    paciente_id = getattr(c, "paciente_id", None)
    if paciente_id and 'Paciente' in globals() and Paciente:
        p = Paciente.query.get(paciente_id)
        if p:
            nombres = getattr(p, "nombres", "") or getattr(p, "nombre", "")
            apellidos = getattr(p, "apellidos", "") or ""
            paciente_nombre = (f"{nombres} {apellidos}").strip() or getattr(p, "razon_social", "") or paciente_nombre
            paciente_documento = getattr(p, "documento", "") or getattr(p, "dni", "") or paciente_documento

    for fld in ("paciente_nombre", "cliente_nombre", "razon_social", "cliente_razon_social"):
        if not paciente_nombre:
            val = getattr(c, fld, None)
            if val:
                paciente_nombre = str(val)
    for fld in ("paciente_documento", "cliente_documento", "documento", "cliente_doc", "doc", "dni"):
        if not paciente_documento:
            val = getattr(c, fld, None)
            if val:
                paciente_documento = str(val)

    return {
        "id": c.id,
        "numero": getattr(c, "numero", numero),
        "total": total,
        "paciente_nombre": paciente_nombre,
        "paciente_documento": paciente_documento,
        "paciente_id": paciente_id,
        "items": items,
    }


# Modelos base de inventario
from models.inventario import (
    Producto,
    MovimientoStock,
    TipoMov,
    ProductoPrecioHist,
)
from utils.decorators import role_required

bp = Blueprint("inventario", __name__, url_prefix="/api/inventario")

# ¿Tenés modelos ORM para compras/proveedores?
try:
    from models.inventario import Compra, CompraItem, Proveedor  # opcional en tu proyecto
    HAVE_ORM_COMPRAS = True
except Exception:
    HAVE_ORM_COMPRAS = False

# -----------------------------
# Helpers decimales y utils
# -----------------------------
DEC2 = Decimal("0.01")
DEC3 = Decimal("0.001")
DEC4 = Decimal("0.0001")

def D(x, q=None):
    if isinstance(x, Decimal):
        d = x
    elif x is None:
        d = Decimal("0")
    else:
        d = Decimal(str(x))
    return d.quantize(q, rounding=ROUND_HALF_UP) if q else d

# --- Historial de precios/costos ---
def _log_precio(producto_id, tipo, valor, motivo="", usuario_id=None):
    """Registra historial de precio/costo. No rompe el flujo si falla."""
    try:
        h = ProductoPrecioHist(
            producto_id=producto_id,
            tipo=tipo,  # "costo" | "venta"
            valor=D(valor, DEC2),
            motivo=(motivo or "")[:255],
            usuario_id=usuario_id,
        )
        db.session.add(h)
    except Exception:
        current_app.logger.exception("No se pudo registrar historial de precio")

def _ultimo_costo(pid: int) -> float:
    #Devuelve el último costo registrado (historial tipo='costo');
    #si no hay historial, usa el último costo de compra; si no, el costo promedio actual.
    try:
        row = (ProductoPrecioHist.query
               .filter_by(producto_id=pid, tipo="costo")
               .order_by(ProductoPrecioHist.vigente_desde.desc())
               .first())
        if row and row.valor is not None:
            return float(row.valor or 0)
    except Exception:
        pass
    try:
        r = db.session.execute(text(
            "SELECT i.costo_unitario FROM inv_compra_items i "
            "WHERE i.producto_id=:pid ORDER BY i.id DESC LIMIT 1"
        ), {"pid": pid}).first()
        if r:
            return float(r[0] or 0)
    except Exception:
        pass
    # 3) Promedio actual
    try:
        p = Producto.query.get(pid)
        if p and getattr(p, "precio_costo", None) is not None:
            return float(p.precio_costo or 0)
    except Exception:
        pass
    return 0.0

# ---------- Normalización de proveedor en una compra ----------
def _normalize_compra_proveedor(cdict):
    """
    Asegura que compra['proveedor'] sea {id, nombre}.
    Acepta proveedor como id, string numérica o dict sin nombre.
    """
    if not cdict:
        return None

    prov = cdict.get("proveedor")

    # Si viene como dict (posible {data:{...}} o sin 'nombre')
    if isinstance(prov, dict):
        # aplanar {data:{...}}
        if "data" in prov and isinstance(prov["data"], dict):
            prov = prov["data"]
            cdict["proveedor"] = prov

        nombre = prov.get("nombre") or prov.get("razon_social") or prov.get("nombre_comercial") \
                 or prov.get("display_name") or prov.get("alias") or prov.get("denominacion")
        if nombre:
            cdict["proveedor"] = {**prov, "nombre": str(nombre)}
            return cdict

        pid = prov.get("id") or cdict.get("proveedor_id")
        if pid:
            p = Proveedor.query.get(pid)
            if p:
                cdict["proveedor"] = {"id": p.id, "nombre": p.nombre}
        return cdict

    # Si viene como id (int o string numérica)
    if isinstance(prov, int) or (isinstance(prov, str) and prov.isdigit()):
        p = Proveedor.query.get(int(prov))
        if p:
            cdict["proveedor"] = {"id": p.id, "nombre": p.nombre}
        return cdict

    # Si no vino 'proveedor' pero sí proveedor_id
    pid = cdict.get("proveedor_id")
    if pid:
        p = Proveedor.query.get(pid)
        if p:
            cdict["proveedor"] = {"id": p.id, "nombre": p.nombre}
    return cdict

def _dump_producto(p: Producto):
    return {
        "id": p.id,
        "sku": p.sku,
        "nombre": p.nombre,
        "stock_minimo": float(p.stock_minimo or 0),
        "stock_actual": float(p.stock_actual or 0),
        "precio_costo": float(p.precio_costo or 0),
        "precio_venta": float(getattr(p, "precio_venta", 0) or 0),
        "activo": bool(getattr(p, "activo", True)),
        "ultimo_costo": float(_ultimo_costo(p.id)),   # <-- FIX dict (sin coma suelta)
    }

# ====== Helpers de agrupación/listado de movimientos ======
def _try_fetch_compra_by_ref(ref: str):
    """
    Resuelve una compra a partir de la referencia del movimiento.
    Devuelve dict normalizado con proveedor.nombre siempre que exista.
    """
    ref = (ref or "").strip()
    if not ref:
        return None

    def _digits(s):
        ds = "".join(ch for ch in s if ch.isdigit())
        return int(ds) if ds else None

    if HAVE_ORM_COMPRAS:
        c = Compra.query.filter_by(numero=ref).first()
        if c:
            return _normalize_compra_proveedor(_fetch_compra(c.id))
        cid = _digits(ref)
        if cid:
            c = Compra.query.get(cid)
            if c:
                return _normalize_compra_proveedor(_fetch_compra(c.id))
    else:
        row = db.session.execute(
            text("SELECT id FROM inv_compras WHERE numero=:n LIMIT 1"),
            {"n": ref},
        ).first()
        if row:
            return _normalize_compra_proveedor(_fetch_compra(int(row[0])))
        cid = _digits(ref)
        if cid:
            row = db.session.execute(
                text("SELECT id FROM inv_compras WHERE id=:cid LIMIT 1"),
                {"cid": cid},
            ).first()
            if row:
                return _normalize_compra_proveedor(_fetch_compra(cid))
    return None

def _mov_producto_label(m):
    """
    Para la grilla agrupada:
    - INGRESO: nombre del proveedor si se resuelve la compra; si no, 'INGRESO'
    - EGRESO: 'SALIDA'
    - AJUSTE: 'AJUSTE'
    """
    t = (str(m.tipo) or "").upper()
    if "INGRESO" in t:
        c = _try_fetch_compra_by_ref(getattr(m, "referencia", None))
        if c and c.get("proveedor", {}).get("nombre"):
            return c["proveedor"]["nombre"]
        return "INGRESO"
    if "EGRESO" in t:
        return "SALIDA"
    return "AJUSTE"

def _mov_monto(m):
    """
    Monto (lo que mostramos en 'Cantidad'):
    - INGRESO: total de la compra si existe; fallback a |cantidad| * precio_costo
    - EGRESO/AJUSTE: |cantidad| * precio_costo
    """
    t = (str(m.tipo) or "").upper()
    prod = Producto.query.get(getattr(m, "producto_id", None)) if getattr(m, "producto_id", None) else None
    costo = D(getattr(prod, "precio_costo", 0), DEC2)
    cant = D(abs(m.cantidad or 0), DEC3)

    if "INGRESO" in t:
        c = _try_fetch_compra_by_ref(getattr(m, "referencia", None))
        if c and c.get("total") is not None:
            return float(D(c["total"], DEC2))
        return float((cant * costo).quantize(DEC2, rounding=ROUND_HALF_UP))

    return float((cant * costo).quantize(DEC2, rounding=ROUND_HALF_UP))

def _group_key(m):
    """Clave de agrupación por tipo + referencia base (unifica VENTA/SERVICIO)."""
    t = (str(getattr(m, "tipo", "") or "")).lower()
    ref = _base_ref(getattr(m, "referencia", "") or "") or f"__id_{getattr(m, 'id', '')}"
    return f"{t}::{ref}"


def _parse_bool(s):
    if s is None:
        return None
    s = str(s).strip().lower()
    if s in ("1", "true", "t", "yes", "si", "sí"):
        return True
    if s in ("0", "false", "f", "no"):
        return False
    return None

def aplicar_movimiento(prod: Producto, tipo: str, cantidad: Decimal,
                       motivo: str = "", referencia: str = "", compra_id=None):
    """
    Aplica un movimiento y actualiza el saldo del producto.
    Soporta INGRESO / EGRESO / AJUSTE (en AJUSTE, 'cantidad' es el nuevo saldo).
    """
    tipo = (tipo or "").upper()
    cant = D(cantidad, DEC3)
    if cant <= 0:
        raise ValueError("Cantidad debe ser > 0")

    saldo_anterior = D(prod.stock_actual, DEC3)

    if tipo == "INGRESO":
        nuevo = saldo_anterior + cant
    elif tipo == "EGRESO":
        nuevo = saldo_anterior - cant
    elif tipo == "AJUSTE":
        nuevo = cant
    else:
        raise ValueError("Tipo inválido")

    mov = MovimientoStock(
        fecha=datetime.utcnow(),
        tipo=tipo.lower() if isinstance(getattr(MovimientoStock, "tipo"), str) else tipo,
        producto_id=prod.id,
        cantidad=cant,
        saldo=nuevo,
        motivo=motivo,
        referencia=referencia
    )
    if hasattr(MovimientoStock, "compra_id"):
        setattr(mov, "compra_id", compra_id)

    db.session.add(mov)
    prod.stock_actual = nuevo
    return mov

# -----------------------------
# Productos
# -----------------------------
@bp.get("/productos")
@jwt_required()
def listar_productos():
    """
    - Sin 'page' => autocomplete: devuelve {"data":[...]} (máx 20)
    - Con 'page' y 'per_page' => listado paginado: {"data":[...], "total": N}
      Filtros: q (sku/nombre), activo (true/false)
    """
    qtxt = (request.args.get("q") or "").strip()
    page = int(request.args.get("page") or 0)
    per_page = int(request.args.get("per_page") or 10)
    activo_filter = _parse_bool(request.args.get("activo"))

    q = Producto.query
    if qtxt:
        like = f"%{qtxt}%"
        q = q.filter((Producto.nombre.ilike(like)) | (Producto.sku.ilike(like)))
    if activo_filter is not None and hasattr(Producto, "activo"):
        q = q.filter(Producto.activo == activo_filter)

    q = q.order_by(Producto.nombre.asc())
    if page > 0:
        total = q.count()
        rows = q.offset((page - 1) * per_page).limit(per_page).all()
        return {"data": [_dump_producto(p) for p in rows], "total": total}

    rows = q.limit(20).all()
    return {"data": [_dump_producto(p) for p in rows]}

@bp.get("/productos/<int:pid>")
@jwt_required()
def obtener_producto(pid: int):
    p = Producto.query.get_or_404(pid)
    return _dump_producto(p)

@bp.get("/productos/by-sku")
@jwt_required()
def get_producto_by_sku():
    sku = (request.args.get("sku") or "").strip()
    if not sku:
        return {}
    p = Producto.query.filter(func.upper(Producto.sku) == sku.upper()).first()
    return _dump_producto(p) if p else {}

@bp.post("/productos")
@jwt_required()
@role_required("administracion")
def crear_producto():
    data = request.get_json() or {}
    sku = (data.get("sku") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    stock_minimo = D(data.get("stock_minimo") or 0, DEC3)
    precio_venta = D(data.get("precio_venta") or 0, DEC2)

    if not nombre:
        return {"message": "Nombre requerido"}, 400

    if sku:
        dup = Producto.query.filter(func.upper(Producto.sku) == sku.upper()).first()
        if dup:
            return {"message": "SKU ya existe"}, 400

    p = Producto(
        sku=sku or None,
        nombre=nombre,
        stock_minimo=stock_minimo,
        stock_actual=D(0, DEC3),
        precio_costo=D(0, DEC2),
        precio_venta=precio_venta,
        activo=True,
    )
    db.session.add(p)
    db.session.flush()
    # historial de PV inicial (si corresponde)
    try:
        if precio_venta > 0:
            uid = None
            try:
                j = get_jwt() or {}
                uid = j.get("sub") or j.get("user_id")
            except Exception:
                pass
            _log_precio(p.id, "venta", precio_venta, motivo="precio inicial", usuario_id=uid)
    except Exception:
        current_app.logger.exception("Historial precio_venta (crear_producto)")
    db.session.commit()
    return _dump_producto(p), 201

@bp.put("/productos/<int:pid>")
@jwt_required()
@role_required("administracion")
def actualizar_producto(pid: int):
    """
    Permite actualizar nombre, sku, stock_minimo, precio_venta y activo (opcional).
    """
    p = Producto.query.get_or_404(pid)
    data = request.get_json() or {}

    if "sku" in data:
        sku = (data.get("sku") or "").strip()
        if sku:
            dup = Producto.query.filter(func.upper(Producto.sku) == sku.upper(), Producto.id != p.id).first()
            if dup:
                return {"message": "SKU ya existe"}, 400
            p.sku = sku
        else:
            p.sku = None

    if "nombre" in data:
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return {"message": "Nombre requerido"}, 400
        p.nombre = nombre

    if "stock_minimo" in data:
        p.stock_minimo = D(data.get("stock_minimo") or 0, DEC3)

    if "precio_venta" in data:
        nuevo_pv = D(data.get("precio_venta") or 0, DEC2)
        changed = (D(getattr(p, "precio_venta", 0), DEC2) != nuevo_pv)
        p.precio_venta = nuevo_pv
        if changed:
            motivo = (data.get("motivo") or "actualización manual")[:255]
            uid = None
            try:
                j = get_jwt() or {}
                uid = j.get("sub") or j.get("user_id")
            except Exception:
                pass
            try:
                _log_precio(p.id, "venta", nuevo_pv, motivo=motivo, usuario_id=uid)
            except Exception:
                current_app.logger.exception("Historial precio_venta (actualizar_producto)")

    if "activo" in data and hasattr(p, "activo"):
        p.activo = bool(data.get("activo"))

    db.session.commit()
    return _dump_producto(p)

@bp.patch("/productos/<int:pid>/activo")
@jwt_required()
@role_required("administracion")
def toggle_producto_activo(pid: int):
    """
    Cambia estado activo/inactivo de un producto.
    Body: { "activo": true|false }
    """
    p = Producto.query.get_or_404(pid)
    data = request.get_json() or {}
    val = data.get("activo")
    b = _parse_bool(val)
    if b is None:
        return {"message": "valor 'activo' inválido"}, 400
    p.activo = b
    db.session.commit()
    return {"id": p.id, "activo": bool(p.activo)}

# -----------------------------
# Compras (ORM o SQL directo si no hay modelos)
# -----------------------------
def _ensure_proveedor(nombre: str):
    nombre = (nombre or "").strip()
    if not nombre:
        return None
    if HAVE_ORM_COMPRAS:
        prov = Proveedor.query.filter_by(nombre=nombre).first()
        if not prov:
            prov = Proveedor(nombre=nombre)
            db.session.add(prov)
            db.session.flush()
        return prov.id
    # SQL
    row = db.session.execute(
        text("SELECT id FROM inv_proveedores WHERE nombre=:n LIMIT 1"),
        {"n": nombre},
    ).first()
    if row:
        return int(row[0])
    db.session.execute(
        text("INSERT INTO inv_proveedores(nombre) VALUES (:n)"),
        {"n": nombre},
    )
    db.session.flush()
    return int(db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar())

def _fetch_compra(cid: int):
    if HAVE_ORM_COMPRAS:
        c = Compra.query.get(cid)
        if not c:
            return None

        # nombre del proveedor: relación o lookup por id
        prov_nombre = None
        try:
            prov_nombre = getattr(getattr(c, "proveedor", None), "nombre", None)
        except Exception:
            prov_nombre = None
        if (not prov_nombre) and c.proveedor_id:
            p = Proveedor.query.get(c.proveedor_id)
            if p:
                prov_nombre = p.nombre

        its = CompraItem.query.filter_by(compra_id=cid).all()

        # enriquecer ítems con info de producto (sku/nombre) si es posible
        prod_ids = [it.producto_id for it in its]
        prods = {pp.id: pp for pp in (Producto.query.filter(Producto.id.in_(prod_ids)).all() if prod_ids else [])}

        compra_dict = {
            "id": c.id,
            "fecha": c.fecha.isoformat() if getattr(c, "fecha", None) else None,
            "proveedor_id": c.proveedor_id,
            "proveedor": {"id": c.proveedor_id, "nombre": prov_nombre},
            "tipo_doc": c.tipo_doc,
            "numero": c.numero,
            "nro_registro": getattr(c, "nro_registro", None),
            "total": float(c.total or 0),
            "observacion": getattr(c, "observacion", "") or "",
            "items": [
                {
                    "id": it.id,
                    "producto_id": it.producto_id,
                    "cantidad": float(it.cantidad),
                    "costo_unitario": float(it.costo_unitario),
                    "subtotal": float(it.subtotal),
                    "producto": (
                        {"sku": prods[it.producto_id].sku, "nombre": prods[it.producto_id].nombre}
                        if prods.get(it.producto_id) else None
                    ),
                }
                for it in its
            ],
        }
        return _normalize_compra_proveedor(compra_dict)
    # --- (rama SQL) ---
    row = db.session.execute(
        text(
            """
      SELECT c.id, c.fecha, c.proveedor_id, p.nombre AS proveedor_nombre,
             c.tipo_doc, c.numero, c.nro_registro, c.total, c.observacion
        FROM inv_compras c
   LEFT JOIN inv_proveedores p ON p.id = c.proveedor_id
       WHERE c.id=:cid
    """
        ),
        {"cid": cid},
    ).mappings().first()
    if not row:
        return None
    items = db.session.execute(
        text(
            """
      SELECT i.id, i.producto_id, i.cantidad, i.costo_unitario, i.subtotal,
             pr.sku, pr.nombre
        FROM inv_compra_items i
        JOIN inv_productos pr ON pr.id = i.producto_id
       WHERE i.compra_id=:cid
       ORDER BY i.id
    """
        ),
        {"cid": cid},
    ).mappings().all()
    return {
        "id": row["id"],
        "fecha": row["fecha"].isoformat() if row["fecha"] else None,
        "proveedor_id": row["proveedor_id"],
        "proveedor": {"id": row["proveedor_id"], "nombre": row["proveedor_nombre"]},
        "tipo_doc": row["tipo_doc"],
        "numero": row["numero"],
        "nro_registro": row["nro_registro"],
        "total": float(row["total"] or 0),
        "observacion": row["observacion"] or "",
        "items": [
            {
                "id": it["id"],
                "producto_id": it["producto_id"],
                "cantidad": float(it["cantidad"] or 0),
                "costo_unitario": float(it["costo_unitario"] or 0),
                "subtotal": float(it["subtotal"] or 0),
                "producto": {"sku": it["sku"], "nombre": it["nombre"]},
            }
            for it in items
        ],
    }

@bp.get("/compras/<int:cid>")
@jwt_required()
def get_compra(cid):
    c = _fetch_compra(cid)
    if not c:
        return {"message": "Compra no encontrada"}, 404
    return c

@bp.get("/compras/buscar")
@jwt_required()
def buscar_compra_por_numero():
    numero = (request.args.get("numero") or "").strip()
    if not numero:
        return {"message": "numero requerido"}, 400
    if HAVE_ORM_COMPRAS:
        c = Compra.query.filter_by(numero=numero).first()
        return _fetch_compra(c.id) if c else {}
    row = db.session.execute(
        text("SELECT id FROM inv_compras WHERE numero=:n LIMIT 1"), {"n": numero}
    ).first()
    return _fetch_compra(int(row[0])) if row else {}

@bp.post("/compras")
@jwt_required()
@role_required("administracion")
def crear_compra():
    data = request.get_json() or {}
    proveedor_id = data.get("proveedor_id")
    proveedor_nombre = data.get("proveedor_nombre")
    tipo_doc = (data.get("tipo_doc") or "boleta").lower()
    numero = (data.get("numero") or "").strip()
    nro_registro = (data.get("nro_registro") or "").strip()
    observacion = data.get("observacion") or ""
    items = data.get("items") or []

    if not items:
        return {"message": "Debe enviar items"}, 400

    # --- Regla de unicidad para FACTURA ---
    if tipo_doc == "factura":
        if not numero:
            return {"message": "Para FACTURA el 'numero' es obligatorio"}, 400
        if HAVE_ORM_COMPRAS:
            dup = Compra.query.filter(
                func.lower(Compra.tipo_doc) == "factura",
                func.lower(Compra.numero) == numero.lower(),
            ).first()
            if dup:
                return {"message": f"Ya existe una FACTURA con número '{numero}'"}, 409
        else:
            row = db.session.execute(
                text("SELECT id FROM inv_compras WHERE LOWER(tipo_doc)='factura' AND LOWER(numero)=:n LIMIT 1"),
                {"n": numero.lower()},
            ).first()
            if row:
                return {"message": f"Ya existe una FACTURA con número '{numero}'"}, 409

    if not proveedor_id and proveedor_nombre:
        proveedor_id = _ensure_proveedor(proveedor_nombre)

    # Crear cabecera
    if HAVE_ORM_COMPRAS:
        c = Compra(
            fecha=datetime.utcnow(),
            proveedor_id=proveedor_id,
            tipo_doc=tipo_doc,
            numero=numero,
            nro_registro=nro_registro,
            observacion=observacion,
            total=D(0, DEC2),
        )
        db.session.add(c)
        db.session.flush()
        cid = c.id
    else:
        db.session.execute(
            text("""
              INSERT INTO inv_compras (fecha, proveedor_id, tipo_doc, numero, nro_registro, observacion, total)
              VALUES (NOW(), :pid, :td, :num, :reg, :obs, 0)
            """),
            {"pid": proveedor_id, "td": tipo_doc, "num": numero, "reg": nro_registro, "obs": observacion},
        )
        db.session.flush()
        cid = db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

    total = D(0, DEC2)
    for it in items:
        pid = it.get("producto_id")
        cant = D(it.get("cantidad"), DEC3)
        cu = D(it.get("costo_unitario"), DEC2)
        if not pid or cant <= 0 or cu <= 0:
            db.session.rollback()
            return {"message": "Item inválido"}, 400
        prod = Producto.query.get(pid)
        if not prod:
            db.session.rollback()
            return {"message": f"Producto {pid} no existe"}, 404

        # Promedio ponderado de costo + INGRESO
        old_qty = D(prod.stock_actual, DEC3)
        old_cost = D(prod.precio_costo, DEC2)
        new_qty = old_qty + cant
        new_cost = cu if new_qty <= 0 else ((old_qty * old_cost) + (cant * cu)) / new_qty
        prod.precio_costo = new_cost.quantize(DEC2, rounding=ROUND_HALF_UP)

        aplicar_movimiento(
            prod, "INGRESO", cant,
            motivo="compra",
            referencia=numero or f"COMP-{cid}",
            compra_id=cid,
        )

        # Guardar historial de costo (último costo)
        try:
            _log_precio(prod.id, "costo", cu, motivo=f"compra #{cid}", usuario_id=None)
        except Exception:
            current_app.logger.exception("Historial costo (crear_compra)")

        sub = (cant * cu).quantize(DEC2, rounding=ROUND_HALF_UP)
        total += sub

        if HAVE_ORM_COMPRAS:
            db.session.add(CompraItem(
                compra_id=cid, producto_id=pid, cantidad=cant,
                costo_unitario=cu, subtotal=sub
            ))
        else:
            db.session.execute(
                text("""
                  INSERT INTO inv_compra_items (compra_id, producto_id, cantidad, costo_unitario, subtotal)
                  VALUES (:cid, :pid, :cant, :cu, :sub)
                """),
                {"cid": cid, "pid": pid, "cant": float(cant), "cu": float(cu), "sub": float(sub)}
            )

    if HAVE_ORM_COMPRAS:
        c.total = total
    else:
        db.session.execute(text("UPDATE inv_compras SET total=:t WHERE id=:cid"), {"t": float(total), "cid": cid})

    db.session.commit()
    return {"id": int(cid), "total": float(total)}, 201

@bp.put("/compras/<int:cid>")
@jwt_required()
@role_required("administracion")
def actualizar_compra(cid):
    """
    Edita una compra aplicando SOLO las diferencias por producto:
    - Δ = nueva_cant - cant_anterior
      * Δ > 0: INGRESO por Δ y recalcular costo promedio ponderado con el costo nuevo
      * Δ < 0: EGRESO por |Δ| (no modifica precio_costo)
      * Δ = 0: sin movimiento
    Luego reemplaza los ítems de la compra y actualiza cabecera/total.
    """
    data = request.get_json() or {}
    proveedor_id = data.get("proveedor_id")
    proveedor_nombre = data.get("proveedor_nombre")
    tipo_doc = (data.get("tipo_doc") or "boleta").lower()
    numero = (data.get("numero") or "").strip()
    nro_registro = (data.get("nro_registro") or "").strip()
    observacion = data.get("observacion") or ""
    nuevos = data.get("items") or []

    if not nuevos:
        return {"message": "Debe enviar items"}, 400

    # --- Regla de unicidad para FACTURA (excluyendo esta compra) ---
    if tipo_doc == "factura":
        if not numero:
            return {"message": "Para FACTURA el 'numero' es obligatorio"}, 400
        if HAVE_ORM_COMPRAS:
            dup = Compra.query.filter(
                func.lower(Compra.tipo_doc) == "factura",
                func.lower(Compra.numero) == numero.lower(),
                Compra.id != cid,
            ).first()
            if dup:
                return {"message": f"Ya existe una FACTURA con número '{numero}'"}, 409
        else:
            row = db.session.execute(
                text("""SELECT id FROM inv_compras WHERE id<>:cid AND LOWER(tipo_doc)='factura' AND LOWER(numero)=:n LIMIT 1"""),
                {"cid": cid, "n": numero.lower()},
            ).first()
            if row:
                return {"message": f"Ya existe una FACTURA con número '{numero}'"}, 409

    # Traer compra e ítems actuales
    if HAVE_ORM_COMPRAS:
        c = Compra.query.get_or_404(cid)
        actuales = CompraItem.query.filter_by(compra_id=cid).all()
    else:
        c = db.session.execute(
            text("SELECT id, numero, proveedor_id, tipo_doc, nro_registro, observacion FROM inv_compras WHERE id=:cid"),
            {"cid": cid}
        ).mappings().first()
        if not c:
            return {"message": "Compra no encontrada"}, 404
        actuales = db.session.execute(
            text("SELECT id, producto_id, cantidad, costo_unitario, subtotal FROM inv_compra_items WHERE compra_id=:cid"),
            {"cid": cid},
        ).mappings().all()

    # Resolver proveedor si vino por nombre
    if not proveedor_id and proveedor_nombre:
        proveedor_id = _ensure_proveedor(proveedor_nombre)

    # Mapas auxiliares: cantidades actuales y nuevas por producto
    curr_qty = {}
    if HAVE_ORM_COMPRAS:
        for it in actuales:
            curr_qty[it.producto_id] = curr_qty.get(it.producto_id, D(0, DEC3)) + D(it.cantidad, DEC3)
    else:
        for it in actuales:
            pid = int(it["producto_id"])
            curr_qty[pid] = curr_qty.get(pid, D(0, DEC3)) + D(it["cantidad"], DEC3)

    new_qty = {}
    new_cost = {}  # último costo_unitario declarado por producto (para Δ > 0)
    for it in nuevos:
        pid = it.get("producto_id")
        cant = D(it.get("cantidad"), DEC3)
        cu = D(it.get("costo_unitario"), DEC2)
        if not pid or cant <= 0 or cu <= 0:
            return {"message": "Item inválido"}, 400
        new_qty[pid] = new_qty.get(pid, D(0, DEC3)) + cant
        new_cost[pid] = cu

    # Aplicar SOLO diferencias
    try:
        # (A) actualizar cabecera
        if HAVE_ORM_COMPRAS:
            c.proveedor_id = proveedor_id
            c.tipo_doc = tipo_doc
            c.numero = numero
            c.nro_registro = nro_registro
            c.observacion = observacion
        else:
            db.session.execute(
                text("""
                    UPDATE inv_compras
                       SET proveedor_id=:pid, tipo_doc=:td, numero=:num, nro_registro=:reg, observacion=:obs
                     WHERE id=:cid
                """),
                {"pid": proveedor_id, "td": tipo_doc, "num": numero, "reg": nro_registro, "obs": observacion, "cid": cid},
            )

        # (B) Δ por producto
        todos = set(curr_qty.keys()) | set(new_qty.keys())
        for pid in todos:
            before = curr_qty.get(pid, D(0, DEC3))
            after  = new_qty.get(pid, D(0, DEC3))
            delta  = (after - before)

            if delta == 0:
                continue

            prod = Producto.query.get(pid)
            if not prod:
                db.session.rollback()
                return {"message": f"Producto {pid} no existe"}, 404

            if delta > 0:
                # INGRESO por la diferencia + promedio ponderado
                cu = new_cost.get(pid, D(prod.precio_costo, DEC2))
                old_qty  = D(prod.stock_actual, DEC3)
                old_cost = D(prod.precio_costo, DEC2)
                new_qty_tot = old_qty + delta
                new_cost_avg = cu if new_qty_tot <= 0 else ((old_qty * old_cost) + (delta * cu)) / new_qty_tot
                prod.precio_costo = new_cost_avg.quantize(DEC2, rounding=ROUND_HALF_UP)

                aplicar_movimiento(
                    prod, "INGRESO", D(delta, DEC3),
                    motivo=f"edición compra #{cid}",
                    referencia=(numero or f"ED-{cid}"),
                    compra_id=cid,
                )
                try:
                    _log_precio(prod.id, "costo", cu, motivo=f"edición compra #{cid}")
                except Exception:
                    current_app.logger.exception("Historial costo (actualizar_compra)")
            else:
                # EGRESO por la diferencia (abs). El costo promedio NO se toca
                aplicar_movimiento(
                    prod, "EGRESO", D(abs(delta), DEC3),
                    motivo=f"edición compra #{cid}",
                    referencia=(numero or f"ED-{cid}"),
                    compra_id=cid,
                )

        # (C) reemplazar ítems y totalizar
        if HAVE_ORM_COMPRAS:
            CompraItem.query.filter_by(compra_id=cid).delete()
        else:
            db.session.execute(text("DELETE FROM inv_compra_items WHERE compra_id=:cid"), {"cid": cid})

        total = D(0, DEC2)
        for it in nuevos:
            pid = it["producto_id"]
            cant = D(it["cantidad"], DEC3)
            cu   = D(it["costo_unitario"], DEC2)
            sub  = (cant * cu).quantize(DEC2, rounding=ROUND_HALF_UP)
            total += sub

            if HAVE_ORM_COMPRAS:
                db.session.add(CompraItem(
                    compra_id=cid, producto_id=pid, cantidad=cant,
                    costo_unitario=cu, subtotal=sub
                ))
            else:
                db.session.execute(
                    text("""
                        INSERT INTO inv_compra_items (compra_id, producto_id, cantidad, costo_unitario, subtotal)
                        VALUES (:cid, :pid, :cant, :cu, :sub)
                    """),
                    {"cid": cid, "pid": pid, "cant": float(cant), "cu": float(cu), "sub": float(sub)}
                )

        if HAVE_ORM_COMPRAS:
            c.total = total
        else:
            db.session.execute(text("UPDATE inv_compras SET total=:t WHERE id=:cid"), {"t": float(total), "cid": cid})

        db.session.commit()
        return {"id": int(cid), "total": float(total)}
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error actualizando compra (deltas)")
        return {"message": str(e) or "No se pudo actualizar la compra"}, 500

# -----------------------------
# Movimientos (listado / detalle / lote)
# -----------------------------
@bp.get("/movimientos")
@jwt_required()
def listar_movimientos():
    """
    Devuelve filas agrupadas:
      - INGRESO: 1 fila por compra (referencia/numero)
      - EGRESO/AJUSTE: 1 fila por referencia/batch
    Respuesta: {"data":[...], "total": N}
    """
    page = int(request.args.get("page") or 1)
    per_page = int(request.args.get("per_page") or 10)
    tipo = (request.args.get("tipo") or "").lower()
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")

    q = MovimientoStock.query
    if tipo:
        q = q.filter(func.lower(MovimientoStock.tipo) == tipo)
    else:
        q = q.filter(MovimientoStock.tipo.in_(["ingreso","egreso"]))
    if desde:
        q = q.filter(MovimientoStock.fecha >= desde)
    if hasta:
        q = q.filter(MovimientoStock.fecha <= hasta)

    rows_all = q.order_by(MovimientoStock.fecha.desc()).all()

    groups = {}
    for m in rows_all:
        k = _group_key(m)
        g = groups.get(k)
        if not g:
            g = {
                "tipo": (str(m.tipo) or "").upper(),
                "referencia": _base_ref(m.referencia or ""),
                "ids": [m.id],
                "fecha": m.fecha,
                "motivo": m.motivo,
                "movs": [m],
            }
            groups[k] = g
        else:
            g["ids"].append(m.id)
            g["movs"].append(m)
            if m.fecha and (not g["fecha"] or m.fecha > g["fecha"]):
                g["fecha"] = m.fecha

    rows_out = []
    for g in groups.values():
        first = g["movs"][0]
        if "INGRESO" in g["tipo"]:
            compra = _try_fetch_compra_by_ref(g["referencia"])
            if compra and compra.get("total") is not None:
                monto = float(D(compra["total"], DEC2))
            else:
                comp = _try_fetch_comprobante_by_ref(g.get("referencia"))
                if comp and comp.get("total") is not None:
                    monto = float(D(comp["total"], DEC2))
                else:
                    monto = float(D(sum(_mov_monto(m) for m in g["movs"]), DEC2))

        else:
            comp = _try_fetch_comprobante_by_ref(g.get("referencia"))
            if comp and comp.get("total") is not None:
                monto = float(D(comp["total"], DEC2))
            else:
                monto = float(D(sum(_mov_monto(m) for m in g["movs"]), DEC2))


        rows_out.append({
            "id": g["ids"][0],
            "fecha": g["fecha"].isoformat(timespec="minutes") if g["fecha"] else None,
            "tipo": g["tipo"],
            "motivo": g["motivo"],
            "referencia": g["referencia"],
            "producto_label": _mov_producto_label(first),
            "monto": monto,
            "producto_id": getattr(first, "producto_id", None),
            "cantidad": float(first.cantidad or 0),
            "saldo": float(first.saldo or 0),
        })

    rows_out.sort(key=lambda r: (r["fecha"] or ""), reverse=True)
    total = len(rows_out)
    start = (page - 1) * per_page
    end = start + per_page
    data = rows_out[start:end]

    return {"data": data, "total": total}

@bp.get("/movimientos/<int:mid>")
@jwt_required()
def get_movimiento(mid):
    m = MovimientoStock.query.get_or_404(mid)
    p = Producto.query.get(m.producto_id)

    compra = _normalize_compra_proveedor(_try_fetch_compra_by_ref(m.referencia))

    t = (str(m.tipo) or "").upper()
    items = []
    total_grupo = D(0, DEC2)
    cliente_nombre = ""
    cliente_documento = ""

    if "INGRESO" in t and compra:
        for it in (compra.get("items") or []):
            cant = D(it.get("cantidad", 0), DEC3)
            cu = D(it.get("costo_unitario", 0), DEC2)
            sub = (cant * cu).quantize(DEC2, rounding=ROUND_HALF_UP)
            items.append({
                "producto": it.get("producto") or {"id": it.get("producto_id")},
                "cantidad": float(cant),
                "costo_unitario": float(cu),
                "subtotal": float(sub),
            })
            total_grupo += sub
        if compra.get("total") is not None:
            total_grupo = D(compra["total"], DEC2)

    else:
        # EGRESO/AJUSTE -> intentar cargar desde Comprobante (precios de venta)
        comp = _try_fetch_comprobante_by_ref(_base_ref(m.referencia))
        if comp:
            for it in (comp.get("items") or []):
                cant = D(it.get("cantidad", 0), DEC3)
                pvu = D(it.get("precio_unitario", 0), DEC2)
                sub = (cant * pvu).quantize(DEC2, rounding=ROUND_HALF_UP)
                prod_payload = it.get("producto")
                if not prod_payload and it.get("nombre"):
                    prod_payload = {"nombre": it.get("nombre")}
                items.append({
                    "producto": prod_payload,
                    "cantidad": float(cant),
                    "precio_unitario": float(pvu),
                    "subtotal": float(sub),
                    "nombre": it.get("nombre"),
                    "tipo": it.get("tipo"),
                })
                total_grupo += sub
            cliente_nombre = comp.get("paciente_nombre") or ""
            cliente_documento = comp.get("paciente_documento") or comp.get("cliente_documento") or ""
            total_grupo = D(comp.get("total", float(total_grupo)), DEC2)
        else:
            # Fallback: unificar por referencia base + tipo, ignorando motivo
            movs = (MovimientoStock.query
                    .filter(func.lower(MovimientoStock.tipo) == func.lower(m.tipo))
                    .filter(func.lower(MovimientoStock.referencia) == func.lower(_base_ref(m.referencia)))
                    .order_by(MovimientoStock.id.asc())
                    .all())
            for x in movs:
                prod = Producto.query.get(x.producto_id)
                costo = D(getattr(prod, "precio_costo", 0), DEC2)
                cant = D(abs(x.cantidad or 0), DEC3)
                sub = (cant * costo).quantize(DEC2, rounding=ROUND_HALF_UP)
                items.append({
                    "producto": _dump_producto(prod) if prod else {"id": x.producto_id},
                    "cantidad": float(cant),
                    "costo_unitario": float(costo),
                    "subtotal": float(sub),
                })
                total_grupo += sub


    return {
        "id": m.id,
        "fecha": m.fecha.isoformat(timespec="minutes") if m.fecha else None,
        "tipo": t,
        "producto_id": m.producto_id,
        "cantidad": float(m.cantidad or 0),
        "saldo": float(m.saldo or 0),
        "motivo": m.motivo,
        "referencia": _base_ref(m.referencia or ""),
        "producto": _dump_producto(p) if p else None,
        "producto_label": _mov_producto_label(m),
        "monto": _mov_monto(m),
        "cliente_nombre": cliente_nombre,
        "cliente_documento": cliente_documento,
        "compra": compra,
        "compra_id": compra["id"] if compra else None,
        "compra_numero": compra["numero"] if compra else None,
        "grupo": {
            "items": items,
            "total": float(total_grupo),
        },
    }

@bp.post("/movimientos/lote")
@jwt_required()
@role_required("administracion")
def movimientos_lote():
    payload = (request.get_json() or {})
    items = payload.get("items") or []
    if not items:
        return {"message": "items requeridos"}, 400
    try:
        for it in items:
            pid = it.get("producto_id")
            tipo = (it.get("tipo") or "").upper()
            cant = D(it.get("cantidad"), DEC3)
            mot = it.get("motivo") or ""
            ref = it.get("referencia") or ""
            if not pid or cant <= 0 or tipo not in ("INGRESO", "EGRESO", "AJUSTE"):
                db.session.rollback()
                return {"message": "item inválido"}, 400
            prod = Producto.query.get(pid)
            if not prod:
                db.session.rollback()
                return {"message": f"Producto {pid} no existe"}, 404
            aplicar_movimiento(prod, tipo, cant, motivo=mot, referencia=ref)
        db.session.commit()
        return {"ok": True}
    except Exception as e:
        db.session.rollback()
        return {"message": str(e)}, 500

# -----------------------------
# Kardex
# -----------------------------
@bp.get("/kardex")
@jwt_required()
def kardex():
    pid = int(request.args.get("producto_id") or 0)
    if not pid:
        return {"message": "producto_id requerido"}, 400
    page = int(request.args.get("page") or 1)
    per_page = int(request.args.get("per_page") or 10)
    order = (request.args.get("order") or "desc").lower()

    q = MovimientoStock.query.filter_by(producto_id=pid)
    total = q.count()
    q = q.order_by(MovimientoStock.fecha.asc() if order == "asc" else MovimientoStock.fecha.desc())
    rows = q.offset((page - 1) * per_page).limit(per_page).all()

    data = [
        {
            "id": m.id,
            "fecha": m.fecha.isoformat() if m.fecha else None,
            "tipo": str(m.tipo).upper() if isinstance(m.tipo, str) else m.tipo,
            "cantidad": float(m.cantidad or 0),
            "saldo": float(m.saldo or 0),
            "motivo": m.motivo,
            "referencia": _base_ref(m.referencia or ""),
        }
        for m in rows
    ]
    return {"data": data, "total": total}

# -----------------------------
# Historial de precios/costos
# -----------------------------
@bp.get("/productos/<int:pid>/precios")
@jwt_required()
@role_required("administracion")
def listar_precios_hist(pid: int):
    """Historial de precios/costos del producto."""
    tipo = (request.args.get("tipo") or "").strip().lower()
    limit = int(request.args.get("limit") or 100)
    q = ProductoPrecioHist.query.filter_by(producto_id=pid)
    if tipo in ("costo", "venta"):
        q = q.filter_by(tipo=tipo)
    rows = q.order_by(ProductoPrecioHist.vigente_desde.desc()).limit(max(1, min(1000, limit))).all()
    data = [
        {
            "id": r.id,
            "tipo": r.tipo,
            "valor": float(r.valor or 0),
            "vigente_desde": r.vigente_desde.isoformat() if r.vigente_desde else None,
            "motivo": r.motivo,
            "usuario_id": r.usuario_id,
        } for r in rows
    ]
    return {"data": data, "total": len(data)}

