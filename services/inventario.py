from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select

from extensions import db
from models.inventario import Compra, CompraItem, MovimientoStock, Producto, ProductoPrecioHist, Proveedor
from services.exceptions import ConflictError, NotFoundError, ServiceError


DEC2 = Decimal("0.01")
DEC3 = Decimal("0.001")


def dec(value: Any, quant: Decimal | None = None) -> Decimal:
    if isinstance(value, Decimal):
        number = value
    elif value is None or value == "":
        number = Decimal("0")
    else:
        number = Decimal(str(value))
    return number.quantize(quant, rounding=ROUND_HALF_UP) if quant else number


class InventarioService:
    def __init__(self, clinica_id: int):
        self.clinica_id = clinica_id

    def listar_productos(
        self,
        q: str = "",
        activo: bool | None = None,
        page: int = 0,
        per_page: int = 10,
    ) -> dict[str, Any]:
        query = self._productos_query()
        if q:
            like = f"%{q}%"
            query = query.filter((Producto.nombre.ilike(like)) | (Producto.sku.ilike(like)))
        if activo is not None:
            query = query.filter(Producto.activo == activo)

        query = query.order_by(Producto.nombre.asc())
        if page > 0:
            total = query.count()
            rows = query.offset((page - 1) * per_page).limit(per_page).all()
            return {"data": [self.dump_producto(producto) for producto in rows], "total": total}

        rows = query.limit(20).all()
        return {"data": [self.dump_producto(producto) for producto in rows]}

    def obtener_producto(self, producto_id: int) -> Producto:
        producto = self._productos_query().filter(Producto.id == producto_id).first()
        if producto is None:
            raise NotFoundError("Producto no encontrado")
        return producto

    def obtener_por_sku(self, sku: str) -> Producto | None:
        sku = (sku or "").strip()
        if not sku:
            return None
        return self._productos_query().filter(func.upper(Producto.sku) == sku.upper()).first()

    def crear_producto(self, payload: dict[str, Any], usuario_id: Any = None) -> Producto:
        sku = (payload.get("sku") or "").strip()
        nombre = (payload.get("nombre") or "").strip()
        stock_minimo = dec(payload.get("stock_minimo") or 0, DEC3)
        precio_venta = dec(payload.get("precio_venta") or 0, DEC2)

        if not nombre:
            raise ServiceError("Nombre requerido")
        if sku and self.obtener_por_sku(sku):
            raise ConflictError("SKU ya existe")

        producto = Producto(
            clinica_id=self.clinica_id,
            sku=sku or None,
            nombre=nombre,
            stock_minimo=stock_minimo,
            stock_actual=dec(0, DEC3),
            precio_costo=dec(0, DEC2),
            precio_venta=precio_venta,
            activo=True,
        )
        db.session.add(producto)
        db.session.flush()
        if precio_venta > 0:
            self._log_precio(producto.id, "venta", precio_venta, "precio inicial", usuario_id)
        db.session.commit()
        return producto

    def actualizar_producto(self, producto_id: int, payload: dict[str, Any], usuario_id: Any = None) -> Producto:
        producto = self.obtener_producto(producto_id)

        if "sku" in payload:
            sku = (payload.get("sku") or "").strip()
            if sku:
                dup = self.obtener_por_sku(sku)
                if dup and dup.id != producto.id:
                    raise ConflictError("SKU ya existe")
                producto.sku = sku
            else:
                producto.sku = None

        if "nombre" in payload:
            nombre = (payload.get("nombre") or "").strip()
            if not nombre:
                raise ServiceError("Nombre requerido")
            producto.nombre = nombre

        if "stock_minimo" in payload:
            producto.stock_minimo = dec(payload.get("stock_minimo") or 0, DEC3)

        if "precio_venta" in payload:
            nuevo_pv = dec(payload.get("precio_venta") or 0, DEC2)
            changed = dec(getattr(producto, "precio_venta", 0), DEC2) != nuevo_pv
            producto.precio_venta = nuevo_pv
            if changed:
                motivo = (payload.get("motivo") or "actualizacion manual")[:255]
                self._log_precio(producto.id, "venta", nuevo_pv, motivo, usuario_id)

        if "activo" in payload:
            producto.activo = bool(payload.get("activo"))

        db.session.commit()
        return producto

    def cambiar_producto_activo(self, producto_id: int, activo: bool) -> Producto:
        producto = self.obtener_producto(producto_id)
        producto.activo = activo
        db.session.commit()
        return producto

    def aplicar_movimiento(
        self,
        producto: Producto,
        tipo: str,
        cantidad: Decimal,
        motivo: str = "",
        referencia: str = "",
        compra_id: int | None = None,
    ) -> MovimientoStock:
        tipo = (tipo or "").upper()
        cantidad = dec(cantidad, DEC3)
        if cantidad <= 0:
            raise ServiceError("Cantidad debe ser > 0")

        saldo_anterior = dec(producto.stock_actual, DEC3)
        if tipo == "INGRESO":
            nuevo_saldo = saldo_anterior + cantidad
        elif tipo == "EGRESO":
            nuevo_saldo = saldo_anterior - cantidad
        elif tipo == "AJUSTE":
            nuevo_saldo = cantidad
        else:
            raise ServiceError("Tipo invalido")

        movimiento = MovimientoStock(
            clinica_id=self.clinica_id,
            fecha=datetime.utcnow(),
            tipo=tipo.lower(),
            producto_id=producto.id,
            cantidad=cantidad,
            saldo=nuevo_saldo,
            motivo=motivo,
            referencia=referencia,
        )
        if hasattr(MovimientoStock, "compra_id"):
            setattr(movimiento, "compra_id", compra_id)

        db.session.add(movimiento)
        producto.stock_actual = nuevo_saldo
        return movimiento

    def crear_movimientos_lote(self, items: list[dict[str, Any]]) -> None:
        if not items:
            raise ServiceError("items requeridos")

        for item in items:
            producto_id = item.get("producto_id")
            tipo = (item.get("tipo") or "").upper()
            cantidad = dec(item.get("cantidad"), DEC3)
            if not producto_id or cantidad <= 0 or tipo not in ("INGRESO", "EGRESO", "AJUSTE"):
                raise ServiceError("item invalido")
            producto = self.obtener_producto(int(producto_id))
            self.aplicar_movimiento(
                producto,
                tipo,
                cantidad,
                motivo=item.get("motivo") or "",
                referencia=item.get("referencia") or "",
            )
        db.session.commit()

    def listar_movimientos(
        self,
        tipo: str = "",
        desde: str | None = None,
        hasta: str | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        query = MovimientoStock.query.filter(
            MovimientoStock.clinica_id == self.clinica_id,
            MovimientoStock.is_active.is_(True),
        )
        if tipo:
            query = query.filter(func.lower(MovimientoStock.tipo) == tipo.lower())
        else:
            query = query.filter(MovimientoStock.tipo.in_(["ingreso", "egreso", "ajuste"]))
        if desde:
            query = query.filter(MovimientoStock.fecha >= desde)
        if hasta:
            query = query.filter(MovimientoStock.fecha <= hasta)

        groups: dict[str, dict[str, Any]] = {}
        for movimiento in query.order_by(MovimientoStock.fecha.desc()).all():
            key = self._group_key(movimiento)
            group = groups.get(key)
            if group is None:
                groups[key] = {
                    "tipo": (str(movimiento.tipo) or "").upper(),
                    "referencia": self.base_ref(movimiento.referencia or ""),
                    "ids": [movimiento.id],
                    "fecha": movimiento.fecha,
                    "motivo": movimiento.motivo,
                    "movs": [movimiento],
                }
            else:
                group["ids"].append(movimiento.id)
                group["movs"].append(movimiento)
                if movimiento.fecha and (not group["fecha"] or movimiento.fecha > group["fecha"]):
                    group["fecha"] = movimiento.fecha

        rows = []
        for group in groups.values():
            first = group["movs"][0]
            monto = self._monto_grupo(group)
            rows.append(
                {
                    "id": group["ids"][0],
                    "fecha": group["fecha"].isoformat(timespec="minutes") if group["fecha"] else None,
                    "tipo": group["tipo"],
                    "motivo": group["motivo"],
                    "referencia": group["referencia"],
                    "producto_label": self._mov_producto_label(first),
                    "monto": monto,
                    "producto_id": getattr(first, "producto_id", None),
                    "cantidad": float(first.cantidad or 0),
                    "saldo": float(first.saldo or 0),
                }
            )

        rows.sort(key=lambda row: (row["fecha"] or ""), reverse=True)
        total = len(rows)
        start = (page - 1) * per_page
        return {"data": rows[start:start + per_page], "total": total}

    def detalle_movimiento(self, movimiento_id: int) -> dict[str, Any]:
        movimiento = MovimientoStock.query.filter_by(
            id=movimiento_id,
            clinica_id=self.clinica_id,
            is_active=True,
        ).first()
        if movimiento is None:
            raise NotFoundError("Movimiento no encontrado")

        producto = self._productos_query().filter(Producto.id == movimiento.producto_id).first()
        compra = self._try_fetch_compra_by_ref(movimiento.referencia)
        tipo = (str(movimiento.tipo) or "").upper()
        items: list[dict[str, Any]] = []
        total_grupo = dec(0, DEC2)
        cliente_nombre = ""
        cliente_documento = ""

        if "INGRESO" in tipo and compra:
            for item in compra.get("items") or []:
                cantidad = dec(item.get("cantidad", 0), DEC3)
                costo_unitario = dec(item.get("costo_unitario", 0), DEC2)
                subtotal = (cantidad * costo_unitario).quantize(DEC2, rounding=ROUND_HALF_UP)
                items.append(
                    {
                        "producto": item.get("producto") or {"id": item.get("producto_id")},
                        "cantidad": float(cantidad),
                        "costo_unitario": float(costo_unitario),
                        "subtotal": float(subtotal),
                    }
                )
                total_grupo += subtotal
            if compra.get("total") is not None:
                total_grupo = dec(compra["total"], DEC2)
        else:
            comprobante = self._try_fetch_comprobante_by_ref(self.base_ref(movimiento.referencia))
            if comprobante:
                for item in comprobante.get("items") or []:
                    cantidad = dec(item.get("cantidad", 0), DEC3)
                    precio_unitario = dec(item.get("precio_unitario", 0), DEC2)
                    subtotal = (cantidad * precio_unitario).quantize(DEC2, rounding=ROUND_HALF_UP)
                    producto_payload = item.get("producto")
                    if not producto_payload and item.get("nombre"):
                        producto_payload = {"nombre": item.get("nombre")}
                    items.append(
                        {
                            "producto": producto_payload,
                            "cantidad": float(cantidad),
                            "precio_unitario": float(precio_unitario),
                            "subtotal": float(subtotal),
                            "nombre": item.get("nombre"),
                            "tipo": item.get("tipo"),
                        }
                    )
                    total_grupo += subtotal
                cliente_nombre = comprobante.get("paciente_nombre") or ""
                cliente_documento = comprobante.get("paciente_documento") or comprobante.get("cliente_documento") or ""
                total_grupo = dec(comprobante.get("total", float(total_grupo)), DEC2)
            else:
                movs = (
                    MovimientoStock.query.filter(
                        MovimientoStock.clinica_id == self.clinica_id,
                        MovimientoStock.is_active.is_(True),
                    )
                    .filter(func.lower(MovimientoStock.tipo) == func.lower(movimiento.tipo))
                    .filter(func.lower(MovimientoStock.referencia) == func.lower(self.base_ref(movimiento.referencia)))
                    .order_by(MovimientoStock.id.asc())
                    .all()
                )
                for item_movimiento in movs:
                    item_producto = self._productos_query().filter(Producto.id == item_movimiento.producto_id).first()
                    costo = dec(getattr(item_producto, "precio_costo", 0), DEC2)
                    cantidad = dec(abs(item_movimiento.cantidad or 0), DEC3)
                    subtotal = (cantidad * costo).quantize(DEC2, rounding=ROUND_HALF_UP)
                    items.append(
                        {
                            "producto": self.dump_producto(item_producto) if item_producto else {"id": item_movimiento.producto_id},
                            "cantidad": float(cantidad),
                            "costo_unitario": float(costo),
                            "subtotal": float(subtotal),
                        }
                    )
                    total_grupo += subtotal

        return {
            "id": movimiento.id,
            "fecha": movimiento.fecha.isoformat(timespec="minutes") if movimiento.fecha else None,
            "tipo": tipo,
            "producto_id": movimiento.producto_id,
            "cantidad": float(movimiento.cantidad or 0),
            "saldo": float(movimiento.saldo or 0),
            "motivo": movimiento.motivo,
            "referencia": self.base_ref(movimiento.referencia or ""),
            "producto": self.dump_producto(producto) if producto else None,
            "producto_label": self._mov_producto_label(movimiento),
            "monto": self._mov_monto(movimiento),
            "cliente_nombre": cliente_nombre,
            "cliente_documento": cliente_documento,
            "paciente_nombre": cliente_nombre,
            "paciente_documento": cliente_documento,
            "compra": compra,
            "compra_id": compra["id"] if compra else None,
            "compra_numero": compra["numero"] if compra else None,
            "grupo": {"items": items, "total": float(total_grupo)},
        }

    def ensure_proveedor(self, nombre: str) -> int | None:
        nombre = (nombre or "").strip()
        if not nombre:
            return None

        proveedor = Proveedor.query.filter_by(
            clinica_id=self.clinica_id,
            nombre=nombre,
            is_active=True,
        ).first()
        if proveedor is None:
            proveedor = Proveedor(clinica_id=self.clinica_id, nombre=nombre)
            db.session.add(proveedor)
            db.session.flush()
        return proveedor.id

    def fetch_compra(self, compra_id: int) -> dict[str, Any] | None:
        compra = Compra.query.filter_by(
            id=compra_id,
            clinica_id=self.clinica_id,
            is_active=True,
        ).first()
        if compra is None:
            return None
        return self.dump_compra(compra)

    def buscar_compra_por_numero(self, numero: str) -> dict[str, Any] | None:
        numero = (numero or "").strip()
        if not numero:
            raise ServiceError("numero requerido")

        compra = Compra.query.filter_by(
            clinica_id=self.clinica_id,
            numero=numero,
            is_active=True,
        ).first()
        return self.dump_compra(compra) if compra else None

    def crear_compra(self, payload: dict[str, Any]) -> dict[str, Any]:
        proveedor_id = payload.get("proveedor_id")
        proveedor_nombre = payload.get("proveedor_nombre")
        tipo_doc = (payload.get("tipo_doc") or "boleta").lower()
        numero = (payload.get("numero") or "").strip() or None
        nro_registro = (payload.get("nro_registro") or "").strip()
        observacion = payload.get("observacion") or ""
        items = payload.get("items") or []

        self._validar_items_compra(items)
        self._validar_factura_unica(tipo_doc, numero)

        if not proveedor_id and proveedor_nombre:
            proveedor_id = self.ensure_proveedor(proveedor_nombre)

        try:
            compra = Compra(
                clinica_id=self.clinica_id,
                fecha=datetime.utcnow(),
                proveedor_id=proveedor_id,
                tipo_doc=tipo_doc,
                numero=numero,
                nro_registro=nro_registro,
                observacion=observacion,
                total=dec(0, DEC2),
            )
            db.session.add(compra)
            db.session.flush()

            total = dec(0, DEC2)
            for item in items:
                producto_id = int(item.get("producto_id"))
                cantidad = dec(item.get("cantidad"), DEC3)
                costo_unitario = dec(item.get("costo_unitario"), DEC2)
                producto = self.obtener_producto(producto_id)

                self._aplicar_costo_promedio(producto, cantidad, costo_unitario)
                self.aplicar_movimiento(
                    producto,
                    "INGRESO",
                    cantidad,
                    motivo="compra",
                    referencia=numero or f"COMP-{compra.id}",
                    compra_id=compra.id,
                )
                self._log_precio(producto.id, "costo", costo_unitario, f"compra #{compra.id}")

                subtotal = (cantidad * costo_unitario).quantize(DEC2, rounding=ROUND_HALF_UP)
                total += subtotal
                db.session.add(
                    CompraItem(
                        compra_id=compra.id,
                        producto_id=producto.id,
                        cantidad=cantidad,
                        costo_unitario=costo_unitario,
                        subtotal=subtotal,
                    )
                )

            compra.total = total
            db.session.commit()
            return {"id": int(compra.id), "total": float(total)}
        except ServiceError:
            db.session.rollback()
            raise
        except Exception as exc:
            db.session.rollback()
            raise ServiceError(str(exc) or "No se pudo crear la compra", 500) from exc

    def actualizar_compra(self, compra_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        proveedor_id = payload.get("proveedor_id")
        proveedor_nombre = payload.get("proveedor_nombre")
        tipo_doc = (payload.get("tipo_doc") or "boleta").lower()
        numero = (payload.get("numero") or "").strip() or None
        nro_registro = (payload.get("nro_registro") or "").strip()
        observacion = payload.get("observacion") or ""
        nuevos = payload.get("items") or []

        self._validar_items_compra(nuevos)
        self._validar_factura_unica(tipo_doc, numero, exclude_id=compra_id)

        compra = Compra.query.filter_by(
            id=compra_id,
            clinica_id=self.clinica_id,
            is_active=True,
        ).first()
        if compra is None:
            raise NotFoundError("Compra no encontrada")

        if not proveedor_id and proveedor_nombre:
            proveedor_id = self.ensure_proveedor(proveedor_nombre)

        try:
            actuales = CompraItem.query.filter_by(compra_id=compra_id).all()
            curr_qty: dict[int, Decimal] = {}
            for item in actuales:
                curr_qty[item.producto_id] = curr_qty.get(item.producto_id, dec(0, DEC3)) + dec(item.cantidad, DEC3)

            new_qty: dict[int, Decimal] = {}
            new_cost: dict[int, Decimal] = {}
            for item in nuevos:
                producto_id = int(item.get("producto_id"))
                cantidad = dec(item.get("cantidad"), DEC3)
                costo_unitario = dec(item.get("costo_unitario"), DEC2)
                new_qty[producto_id] = new_qty.get(producto_id, dec(0, DEC3)) + cantidad
                new_cost[producto_id] = costo_unitario

            compra.proveedor_id = proveedor_id
            compra.tipo_doc = tipo_doc
            compra.numero = numero
            compra.nro_registro = nro_registro
            compra.observacion = observacion

            for producto_id in set(curr_qty.keys()) | set(new_qty.keys()):
                before = curr_qty.get(producto_id, dec(0, DEC3))
                after = new_qty.get(producto_id, dec(0, DEC3))
                delta = after - before
                if delta == 0:
                    continue

                producto = self.obtener_producto(producto_id)
                if delta > 0:
                    costo_unitario = new_cost.get(producto_id, dec(producto.precio_costo, DEC2))
                    self._aplicar_costo_promedio(producto, delta, costo_unitario)
                    self.aplicar_movimiento(
                        producto,
                        "INGRESO",
                        dec(delta, DEC3),
                        motivo=f"edicion compra #{compra_id}",
                        referencia=numero or f"ED-{compra_id}",
                        compra_id=compra_id,
                    )
                    self._log_precio(producto.id, "costo", costo_unitario, f"edicion compra #{compra_id}")
                else:
                    self.aplicar_movimiento(
                        producto,
                        "EGRESO",
                        dec(abs(delta), DEC3),
                        motivo=f"edicion compra #{compra_id}",
                        referencia=numero or f"ED-{compra_id}",
                        compra_id=compra_id,
                    )

            CompraItem.query.filter_by(compra_id=compra_id).delete()

            total = dec(0, DEC2)
            for item in nuevos:
                producto_id = int(item["producto_id"])
                producto = self.obtener_producto(producto_id)
                cantidad = dec(item["cantidad"], DEC3)
                costo_unitario = dec(item["costo_unitario"], DEC2)
                subtotal = (cantidad * costo_unitario).quantize(DEC2, rounding=ROUND_HALF_UP)
                total += subtotal
                db.session.add(
                    CompraItem(
                        compra_id=compra_id,
                        producto_id=producto.id,
                        cantidad=cantidad,
                        costo_unitario=costo_unitario,
                        subtotal=subtotal,
                    )
                )

            compra.total = total
            db.session.commit()
            return {"id": int(compra_id), "total": float(total)}
        except ServiceError:
            db.session.rollback()
            raise
        except Exception as exc:
            db.session.rollback()
            raise ServiceError(str(exc) or "No se pudo actualizar la compra", 500) from exc

    def kardex(self, producto_id: int, page: int = 1, per_page: int = 10, order: str = "desc") -> dict[str, Any]:
        self.obtener_producto(producto_id)
        query = MovimientoStock.query.filter_by(
            producto_id=producto_id,
            clinica_id=self.clinica_id,
            is_active=True,
        )
        total = query.count()
        order_column = MovimientoStock.fecha.asc() if order == "asc" else MovimientoStock.fecha.desc()
        rows = query.order_by(order_column).offset((page - 1) * per_page).limit(per_page).all()
        return {
            "data": [
                {
                    "id": movimiento.id,
                    "fecha": movimiento.fecha.isoformat() if movimiento.fecha else None,
                    "tipo": str(movimiento.tipo).upper() if isinstance(movimiento.tipo, str) else movimiento.tipo,
                    "cantidad": float(movimiento.cantidad or 0),
                    "saldo": float(movimiento.saldo or 0),
                    "motivo": movimiento.motivo,
                    "referencia": self.base_ref(movimiento.referencia or ""),
                }
                for movimiento in rows
            ],
            "total": total,
        }

    def listar_precios_hist(self, producto_id: int, tipo: str = "", limit: int = 100) -> dict[str, Any]:
        self.obtener_producto(producto_id)
        query = ProductoPrecioHist.query.filter_by(
            producto_id=producto_id,
            clinica_id=self.clinica_id,
        )
        if tipo in ("costo", "venta"):
            query = query.filter_by(tipo=tipo)

        rows = (
            query.order_by(ProductoPrecioHist.vigente_desde.desc())
            .limit(max(1, min(1000, limit)))
            .all()
        )
        data = [
            {
                "id": row.id,
                "tipo": row.tipo,
                "valor": float(row.valor or 0),
                "vigente_desde": row.vigente_desde.isoformat() if row.vigente_desde else None,
                "motivo": row.motivo,
                "usuario_id": row.usuario_id,
            }
            for row in rows
        ]
        return {"data": data, "total": len(data)}

    def dump_producto(self, producto: Producto) -> dict[str, Any]:
        return {
            "id": producto.id,
            "sku": producto.sku,
            "nombre": producto.nombre,
            "stock_minimo": float(producto.stock_minimo or 0),
            "stock_actual": float(producto.stock_actual or 0),
            "precio_costo": float(producto.precio_costo or 0),
            "precio_venta": float(getattr(producto, "precio_venta", 0) or 0),
            "activo": bool(getattr(producto, "activo", True)),
            "ultimo_costo": self.ultimo_costo(producto.id),
        }

    def dump_compra(self, compra: Compra) -> dict[str, Any]:
        proveedor_nombre = None
        if compra.proveedor_id:
            proveedor = Proveedor.query.filter_by(
                id=compra.proveedor_id,
                clinica_id=self.clinica_id,
                is_active=True,
            ).first()
            proveedor_nombre = proveedor.nombre if proveedor else None

        items = CompraItem.query.filter_by(compra_id=compra.id).all()
        productos = {}
        producto_ids = [item.producto_id for item in items]
        if producto_ids:
            productos = {
                producto.id: producto
                for producto in self._productos_query().filter(Producto.id.in_(producto_ids)).all()
            }

        return {
            "id": compra.id,
            "fecha": compra.fecha.isoformat() if getattr(compra, "fecha", None) else None,
            "proveedor_id": compra.proveedor_id,
            "proveedor": {"id": compra.proveedor_id, "nombre": proveedor_nombre},
            "tipo_doc": compra.tipo_doc,
            "numero": compra.numero,
            "nro_registro": getattr(compra, "nro_registro", None),
            "total": float(compra.total or 0),
            "observacion": getattr(compra, "observacion", "") or "",
            "items": [
                {
                    "id": item.id,
                    "producto_id": item.producto_id,
                    "cantidad": float(item.cantidad or 0),
                    "costo_unitario": float(item.costo_unitario or 0),
                    "subtotal": float(item.subtotal or 0),
                    "producto": (
                        {
                            "sku": productos[item.producto_id].sku,
                            "nombre": productos[item.producto_id].nombre,
                        }
                        if productos.get(item.producto_id)
                        else None
                    ),
                }
                for item in items
            ],
        }

    def ultimo_costo(self, producto_id: int) -> float:
        row = (
            ProductoPrecioHist.query.filter_by(
                producto_id=producto_id,
                clinica_id=self.clinica_id,
                tipo="costo",
            )
            .order_by(ProductoPrecioHist.vigente_desde.desc())
            .first()
        )
        if row and row.valor is not None:
            return float(row.valor or 0)

        producto = self._productos_query().filter(Producto.id == producto_id).first()
        if producto and getattr(producto, "precio_costo", None) is not None:
            return float(producto.precio_costo or 0)
        return 0.0

    @staticmethod
    def base_ref(ref: str) -> str:
        ref = (ref or "").strip()
        return ref[:-4] if ref.endswith("-SRV") else ref

    def _productos_query(self):
        return Producto.query.filter(
            Producto.clinica_id == self.clinica_id,
            Producto.is_active.is_(True),
        )

    def _try_fetch_compra_by_ref(self, ref: str | None) -> dict[str, Any] | None:
        ref = (ref or "").strip()
        if not ref:
            return None

        compra = Compra.query.filter_by(
            clinica_id=self.clinica_id,
            numero=ref,
            is_active=True,
        ).first()
        if compra:
            return self.dump_compra(compra)

        digits = "".join(char for char in ref if char.isdigit())
        if digits:
            compra = Compra.query.filter_by(
                id=int(digits),
                clinica_id=self.clinica_id,
                is_active=True,
            ).first()
            if compra:
                return self.dump_compra(compra)
        return None

    def _try_fetch_comprobante_by_ref(self, ref: str | None) -> dict[str, Any] | None:
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
        numero = self.base_ref(ref)

        comprobante = None
        if hasattr(Comprobante, "numero"):
            comprobante = (
                Comprobante.query.filter(func.lower(Comprobante.numero) == numero.lower())
                .filter(Comprobante.clinica_id == self.clinica_id, Comprobante.is_active.is_(True))
                .first()
            )

        if comprobante is None and "-" in numero:
            prefijo, sufijo = numero.split("-", 1)
            query = Comprobante.query.filter(
                Comprobante.clinica_id == self.clinica_id,
                Comprobante.is_active.is_(True),
            )
            if hasattr(Comprobante, "serie"):
                query = query.filter(func.lower(Comprobante.serie) == prefijo.lower())
            if hasattr(Comprobante, "correlativo"):
                query = query.filter(func.lower(Comprobante.correlativo) == sufijo.lower())
            comprobante = query.first()

        if comprobante is None:
            return None

        items = []
        for item in ComprobanteItem.query.filter_by(comprobante_id=comprobante.id).all():
            item_tipo = str(getattr(item, "tipo", "") or "").lower()
            producto_id = getattr(item, "ref_id", None) or getattr(item, "producto_id", None)
            if item_tipo and item_tipo not in {"producto", "insumo"}:
                producto_id = None
            cantidad = float(getattr(item, "cantidad", 0) or 0)
            precio_unitario = getattr(item, "precio_unitario", None)
            if precio_unitario is None:
                precio_unitario = getattr(item, "precio_unit", None)
            if precio_unitario is None:
                precio_unitario = getattr(item, "precio", None)
            precio_unitario = float(precio_unitario or 0)
            subtotal = getattr(item, "subtotal", None)
            if subtotal is None:
                subtotal = cantidad * precio_unitario
            nombre_linea = getattr(item, "nombre", None)
            items.append(
                {
                    "producto": {"id": producto_id} if producto_id else None,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "subtotal": float(subtotal or 0),
                    "tipo": item_tipo or None,
                    "nombre": nombre_linea,
                }
            )

        total = float(getattr(comprobante, "total", 0) or 0)
        if not total:
            total = float(sum(item["subtotal"] for item in items))

        paciente_nombre = ""
        paciente_documento = ""
        paciente_id = getattr(comprobante, "paciente_id", None)
        if paciente_id and Paciente:
            paciente = db.session.execute(
                select(Paciente).where(
                    Paciente.id == paciente_id,
                    Paciente.clinica_id == self.clinica_id,
                    Paciente.is_active.is_(True),
                )
            ).scalar_one_or_none()
            if paciente:
                nombres = getattr(paciente, "nombres", "") or getattr(paciente, "nombre", "")
                apellidos = getattr(paciente, "apellidos", "") or ""
                paciente_nombre = (f"{nombres} {apellidos}").strip() or getattr(paciente, "razon_social", "") or ""
                paciente_documento = getattr(paciente, "documento", "") or getattr(paciente, "dni", "") or ""

        for field in ("paciente_nombre", "cliente_nombre", "razon_social", "cliente_razon_social"):
            if not paciente_nombre:
                value = getattr(comprobante, field, None)
                if value:
                    paciente_nombre = str(value)
        for field in ("paciente_documento", "cliente_documento", "documento", "cliente_doc", "doc", "dni"):
            if not paciente_documento:
                value = getattr(comprobante, field, None)
                if value:
                    paciente_documento = str(value)

        return {
            "id": comprobante.id,
            "numero": getattr(comprobante, "numero", numero),
            "total": total,
            "paciente_nombre": paciente_nombre,
            "paciente_documento": paciente_documento,
            "paciente_id": paciente_id,
            "items": items,
        }

    def _mov_producto_label(self, movimiento: MovimientoStock) -> str:
        tipo = (str(movimiento.tipo) or "").upper()
        if "INGRESO" in tipo:
            compra = self._try_fetch_compra_by_ref(getattr(movimiento, "referencia", None))
            if compra and compra.get("proveedor", {}).get("nombre"):
                return compra["proveedor"]["nombre"]
            return "INGRESO"
        if "EGRESO" in tipo:
            return "SALIDA"
        return "AJUSTE"

    def _mov_monto(self, movimiento: MovimientoStock) -> float:
        tipo = (str(movimiento.tipo) or "").upper()
        producto = (
            self._productos_query().filter(Producto.id == getattr(movimiento, "producto_id", None)).first()
            if getattr(movimiento, "producto_id", None)
            else None
        )
        costo = dec(getattr(producto, "precio_costo", 0), DEC2)
        cantidad = dec(abs(movimiento.cantidad or 0), DEC3)

        if "INGRESO" in tipo:
            compra = self._try_fetch_compra_by_ref(getattr(movimiento, "referencia", None))
            if compra and compra.get("total") is not None:
                return float(dec(compra["total"], DEC2))
            return float((cantidad * costo).quantize(DEC2, rounding=ROUND_HALF_UP))

        return float((cantidad * costo).quantize(DEC2, rounding=ROUND_HALF_UP))

    def _monto_grupo(self, group: dict[str, Any]) -> float:
        if "INGRESO" in group["tipo"]:
            compra = self._try_fetch_compra_by_ref(group["referencia"])
            if compra and compra.get("total") is not None:
                return float(dec(compra["total"], DEC2))

        comprobante = self._try_fetch_comprobante_by_ref(group.get("referencia"))
        if comprobante and comprobante.get("total") is not None:
            return float(dec(comprobante["total"], DEC2))
        return float(dec(sum(self._mov_monto(movimiento) for movimiento in group["movs"]), DEC2))

    def _group_key(self, movimiento: MovimientoStock) -> str:
        tipo = (str(getattr(movimiento, "tipo", "") or "")).lower()
        ref = self.base_ref(getattr(movimiento, "referencia", "") or "") or f"__id_{getattr(movimiento, 'id', '')}"
        return f"{tipo}::{ref}"

    def _validar_items_compra(self, items: list[dict[str, Any]]) -> None:
        if not items:
            raise ServiceError("Debe enviar items")
        for item in items:
            producto_id = item.get("producto_id")
            cantidad = dec(item.get("cantidad"), DEC3)
            costo_unitario = dec(item.get("costo_unitario"), DEC2)
            if not producto_id or cantidad <= 0 or costo_unitario <= 0:
                raise ServiceError("Item invalido")

    def _validar_factura_unica(
        self,
        tipo_doc: str,
        numero: str | None,
        exclude_id: int | None = None,
    ) -> None:
        if tipo_doc != "factura":
            return
        if not numero:
            raise ServiceError("Para FACTURA el 'numero' es obligatorio")

        query = Compra.query.filter(
            Compra.clinica_id == self.clinica_id,
            Compra.is_active.is_(True),
            func.lower(Compra.tipo_doc) == "factura",
            func.lower(Compra.numero) == numero.lower(),
        )
        if exclude_id is not None:
            query = query.filter(Compra.id != exclude_id)
        if query.first():
            raise ConflictError(f"Ya existe una FACTURA con numero '{numero}'")

    @staticmethod
    def _aplicar_costo_promedio(producto: Producto, cantidad: Decimal, costo_unitario: Decimal) -> None:
        old_qty = dec(producto.stock_actual, DEC3)
        old_cost = dec(producto.precio_costo, DEC2)
        new_qty = old_qty + cantidad
        new_cost = costo_unitario if new_qty <= 0 else ((old_qty * old_cost) + (cantidad * costo_unitario)) / new_qty
        producto.precio_costo = new_cost.quantize(DEC2, rounding=ROUND_HALF_UP)

    def _log_precio(self, producto_id: int, tipo: str, valor: Decimal, motivo: str = "", usuario_id: Any = None) -> None:
        db.session.add(
            ProductoPrecioHist(
                clinica_id=self.clinica_id,
                producto_id=producto_id,
                tipo=tipo,
                valor=dec(valor, DEC2),
                motivo=(motivo or "")[:255],
                usuario_id=usuario_id,
            )
        )
