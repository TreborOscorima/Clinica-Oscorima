# routes/inventario.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt
from extensions import db
from services.exceptions import ServiceError
from services.inventario import InventarioService
from utils.tenant import get_current_clinica_id


def _clinica_id() -> int:
    return get_current_clinica_id()


def _service() -> InventarioService:
    return InventarioService(_clinica_id())


def _error_response(err: ServiceError):
    return {"message": err.message}, err.status_code


from utils.decorators import role_required

bp = Blueprint("inventario", __name__, url_prefix="/api/inventario")


def _parse_bool(s):
    if s is None:
        return None
    s = str(s).strip().lower()
    if s in ("1", "true", "t", "yes", "si", "sí"):
        return True
    if s in ("0", "false", "f", "no"):
        return False
    return None

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
    return _service().listar_productos(
        q=(request.args.get("q") or "").strip(),
        page=int(request.args.get("page") or 0),
        per_page=int(request.args.get("per_page") or 10),
        activo=_parse_bool(request.args.get("activo")),
    )

@bp.get("/productos/<int:pid>")
@jwt_required()
def obtener_producto(pid: int):
    try:
        producto = _service().obtener_producto(pid)
    except ServiceError as err:
        return _error_response(err)
    return _service().dump_producto(producto)

@bp.get("/productos/by-sku")
@jwt_required()
def get_producto_by_sku():
    sku = (request.args.get("sku") or "").strip()
    if not sku:
        return {}
    producto = _service().obtener_por_sku(sku)
    return _service().dump_producto(producto) if producto else {}

@bp.post("/productos")
@jwt_required()
@role_required("administracion")
def crear_producto():
    data = request.get_json() or {}
    try:
        producto = _service().crear_producto(data, usuario_id=(get_jwt() or {}).get("sub"))
    except ServiceError as err:
        return _error_response(err)
    return _service().dump_producto(producto), 201

@bp.put("/productos/<int:pid>")
@jwt_required()
@role_required("administracion")
def actualizar_producto(pid: int):
    """
    Permite actualizar nombre, sku, stock_minimo, precio_venta y activo (opcional).
    """
    data = request.get_json() or {}
    try:
        producto = _service().actualizar_producto(pid, data, usuario_id=(get_jwt() or {}).get("sub"))
    except ServiceError as err:
        return _error_response(err)
    return _service().dump_producto(producto)

@bp.patch("/productos/<int:pid>/activo")
@jwt_required()
@role_required("administracion")
def toggle_producto_activo(pid: int):
    """
    Cambia estado activo/inactivo de un producto.
    Body: { "activo": true|false }
    """
    data = request.get_json() or {}
    val = data.get("activo")
    b = _parse_bool(val)
    if b is None:
        return {"message": "valor 'activo' inválido"}, 400
    try:
        producto = _service().cambiar_producto_activo(pid, b)
    except ServiceError as err:
        return _error_response(err)
    return {"id": producto.id, "activo": bool(producto.activo)}

# -----------------------------
# Compras
# -----------------------------
def _fetch_compra(cid: int):
    return _service().fetch_compra(cid)


@bp.get("/compras/<int:cid>")
@jwt_required()
def get_compra(cid):
    compra = _fetch_compra(cid)
    if not compra:
        return {"message": "Compra no encontrada"}, 404
    return compra


@bp.get("/compras/buscar")
@jwt_required()
def buscar_compra_por_numero():
    try:
        compra = _service().buscar_compra_por_numero(request.args.get("numero") or "")
    except ServiceError as err:
        return _error_response(err)
    return compra or {}


@bp.post("/compras")
@jwt_required()
@role_required("administracion")
def crear_compra():
    try:
        return _service().crear_compra(request.get_json() or {}), 201
    except ServiceError as err:
        return _error_response(err)


@bp.put("/compras/<int:cid>")
@jwt_required()
@role_required("administracion")
def actualizar_compra(cid):
    try:
        return _service().actualizar_compra(cid, request.get_json() or {})
    except ServiceError as err:
        return _error_response(err)

# -----------------------------
# Movimientos (listado / detalle / lote)
# -----------------------------
@bp.get("/movimientos")
@jwt_required()
def listar_movimientos():
    return _service().listar_movimientos(
        page=int(request.args.get("page") or 1),
        per_page=int(request.args.get("per_page") or 10),
        tipo=(request.args.get("tipo") or "").lower(),
        desde=request.args.get("desde"),
        hasta=request.args.get("hasta"),
    )

@bp.get("/movimientos/<int:mid>")
@jwt_required()
def get_movimiento(mid):
    try:
        return _service().detalle_movimiento(mid)
    except ServiceError as err:
        return _error_response(err)



@bp.post("/movimientos/lote")
@jwt_required()
@role_required("administracion")
def movimientos_lote():
    payload = (request.get_json() or {})
    items = payload.get("items") or []
    try:
        _service().crear_movimientos_lote(items)
        return {"ok": True}
    except ServiceError as err:
        db.session.rollback()
        return _error_response(err)
    except Exception as err:
        db.session.rollback()
        return {"message": str(err)}, 500

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

    try:
        return _service().kardex(pid, page=page, per_page=per_page, order=order)
    except ServiceError as err:
        return _error_response(err)

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
    try:
        return _service().listar_precios_hist(pid, tipo=tipo, limit=limit)
    except ServiceError as err:
        return _error_response(err)



