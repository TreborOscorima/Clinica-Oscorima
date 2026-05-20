from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from extensions import db
from models.caja import (
    CajaMovimiento,
    Comprobante,
    ComprobanteItem,
    DeudaPaciente,
    MetodoPago,
    TipoMovimiento,
)
from models.inventario import Producto, TipoMov, aplicar_movimiento
from models.servicio import Servicio
from models.turno import EstadoTurno, Turno
from schemas.caja import CajaMovimientoSchema, DeudaPacienteSchema
from services.exceptions import NotFoundError, ServiceError


mov_schema = CajaMovimientoSchema()
mov_many = CajaMovimientoSchema(many=True)
deuda_many = DeudaPacienteSchema(many=True)

D2 = Decimal("0.01")
ZERO = Decimal("0")


def dec2(value) -> Decimal:
    if value is None:
        value = 0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(D2, rounding=ROUND_HALF_UP)


def parse_datetime(value: str | None, field_name: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ServiceError(f"{field_name} invalido (use ISO 8601)", 400) from exc


def _mp_from_str(value: str) -> MetodoPago:
    normalized = (value or "").strip().lower()
    mapping = {
        "efectivo": MetodoPago.EFECTIVO,
        "tarjeta": MetodoPago.TARJETA,
        "transferencia": MetodoPago.TRANSFERENCIA,
    }
    return mapping.get(normalized, MetodoPago.OTRO)


class CajaService:
    def __init__(self, clinica_id: int):
        self.clinica_id = clinica_id

    # ------------------------------------------------------------------
    # Movimientos manuales
    # ------------------------------------------------------------------

    def listar_movimientos(self, params: dict[str, Any]) -> dict[str, Any]:
        query = CajaMovimiento.query.filter(
            CajaMovimiento.clinica_id == self.clinica_id,
            CajaMovimiento.is_active.is_(True),
        )

        desde = parse_datetime(params.get("desde"), "desde")
        if desde:
            query = query.filter(CajaMovimiento.fecha >= desde)

        hasta = parse_datetime(params.get("hasta"), "hasta")
        if hasta:
            query = query.filter(CajaMovimiento.fecha <= hasta)

        tipo = params.get("tipo")
        if tipo:
            query = query.filter(CajaMovimiento.tipo == tipo)

        metodo = params.get("metodo")
        if metodo:
            query = query.filter(CajaMovimiento.metodo_pago == metodo)

        movimientos = query.order_by(CajaMovimiento.fecha.desc()).limit(500).all()
        return {"data": mov_many.dump(movimientos)}

    def crear_movimiento(self, payload: dict[str, Any]) -> CajaMovimiento:
        data_in = {**payload, "clinica_id": self.clinica_id}
        data_in["tipo"] = self._enum_name(data_in.get("tipo"), TipoMovimiento, "tipo")
        data_in["metodo_pago"] = self._enum_name(data_in.get("metodo_pago"), MetodoPago, "metodo_pago")
        loaded = mov_schema.load(data_in, session=db.session)
        data = {key: value for key, value in vars(loaded).items() if not key.startswith("_")}
        data["clinica_id"] = self.clinica_id
        movimiento = CajaMovimiento(**data)
        db.session.add(movimiento)
        db.session.commit()
        return movimiento

    def eliminar_movimiento(self, movimiento_id: int) -> None:
        movimiento = CajaMovimiento.query.filter(
            CajaMovimiento.id == movimiento_id,
            CajaMovimiento.clinica_id == self.clinica_id,
            CajaMovimiento.is_active.is_(True),
        ).first()
        if not movimiento:
            raise NotFoundError("Movimiento no encontrado")
        movimiento.soft_delete()
        db.session.commit()

    # ------------------------------------------------------------------
    # POS — emisión de comprobantes (Punto de Venta)
    # ------------------------------------------------------------------

    def emitir_pos(
        self,
        payload: dict[str, Any],
        idem_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Emite un comprobante desde el POS de manera atómica (ACID).

        Reglas de negocio críticas:
        - Los items tipo 'producto' descuentan stock de inventario retail.
        - Los items tipo 'servicio' NO descuentan insumos clínicos; ese descuento
          ocurre exclusivamente cuando el Turno cambia a ATENDIDO (TurnoService).
        - Si hay un turno_id asociado, el turno se marca ATENDIDO directamente
          sin relanzar el flujo de inventario (ya fue ejecutado por TurnoService).
        """
        clinica_id = self.clinica_id

        # Idempotencia — devuelve el comprobante previo si la clave ya existe
        if idem_key and hasattr(Comprobante, "idempotency_key"):
            previo = Comprobante.query.filter_by(
                clinica_id=clinica_id, idempotency_key=idem_key
            ).first()
            if previo:
                return self._build_pos_response(previo, ZERO, None, [], idempotent=True)

        tipo = (payload.get("tipo") or "boleta").lower()
        paciente_id = payload.get("paciente_id")
        turno_id = payload.get("turno_id")
        observacion = payload.get("observacion") or ""
        items_raw = payload.get("items") or []
        pagos_raw = payload.get("pagos") or []
        dsc_tipo = payload.get("descuento_tipo")
        dsc_valor = payload.get("descuento_valor")

        if not items_raw:
            raise ServiceError("items requeridos", 400)
        if not pagos_raw:
            raise ServiceError("Debe registrar al menos un pago (puede ser parcial)", 400)

        try:
            # 1) Validar y normalizar items ----------------------------------------
            items_norm = self._validar_items(items_raw, clinica_id)

            # 2) Calcular totales ---------------------------------------------------
            total_bruto = dec2(sum(item["subtotal"] for item in items_norm))
            descuento_global = self._calcular_descuento(total_bruto, dsc_tipo, dsc_valor)
            total_neto = dec2(total_bruto - descuento_global)
            total_pagado = dec2(sum(dec2(p.get("monto") or 0) for p in pagos_raw))

            # 3) Método de pago principal -------------------------------------------
            metodo_principal = (
                pagos_raw[0].get("metodo") if len(pagos_raw) == 1 else "otro"
            ) or "efectivo"
            forma_pago_enum = _mp_from_str(metodo_principal)

            # 4) Cabecera comprobante -----------------------------------------------
            comprobante = Comprobante(
                clinica_id=clinica_id,
                tipo=tipo,
                paciente_id=paciente_id,
                forma_pago=forma_pago_enum,
                observacion=observacion,
                total=total_neto,
                total_bruto=total_bruto,
                descuento_global=descuento_global,
                **({"idempotency_key": idem_key}
                   if (idem_key and hasattr(Comprobante, "idempotency_key"))
                   else {}),
            )
            db.session.add(comprobante)
            db.session.flush()

            prefijo = (
                "B" if tipo.startswith("boleta")
                else "F" if tipo.startswith("factura")
                else "C"
            )
            comprobante.numero = f"{prefijo}-{comprobante.id:06d}"

            # 5) Items del comprobante ---------------------------------------------
            for item in items_norm:
                db.session.add(ComprobanteItem(
                    comprobante_id=comprobante.id,
                    tipo=item["tipo"],
                    ref_id=item["ref_id"],
                    nombre=item["nombre"],
                    cantidad=item["cantidad"],
                    precio_unit=item["precio_unit"],
                    subtotal=item["subtotal"],
                ))

            # 6) Descuento de stock (SOLO productos de venta, nunca insumos clínicos)
            self._descontar_stock_productos(items_norm, clinica_id, comprobante.numero)

            # 7) Movimientos de caja (uno por método de pago) ----------------------
            pagos_creados: list[CajaMovimiento] = []
            for pago in pagos_raw:
                monto_pago = dec2(pago.get("monto") or 0)
                if monto_pago <= 0:
                    continue
                metodo_pago = _mp_from_str(pago.get("metodo"))
                mov = CajaMovimiento(
                    clinica_id=clinica_id,
                    tipo=TipoMovimiento.INGRESO,
                    monto=monto_pago,
                    metodo_pago=metodo_pago,
                    paciente_id=paciente_id,
                    comprobante_id=comprobante.id,
                    turno_id=turno_id if hasattr(CajaMovimiento, "turno_id") else None,
                    observacion=(
                        f"Pago {getattr(metodo_pago, 'value', str(metodo_pago))} "
                        f"{comprobante.numero}"
                    ),
                )
                db.session.add(mov)
                pagos_creados.append(mov)

            # 8) Deuda si el pago fue parcial --------------------------------------
            saldo = dec2(total_neto - total_pagado)
            deuda_obj: DeudaPaciente | None = None
            if saldo > ZERO and paciente_id:
                deuda_obj = DeudaPaciente(
                    clinica_id=clinica_id,
                    paciente_id=paciente_id,
                    comprobante_id=comprobante.id,
                    total=total_neto,
                    pagado=dec2(total_pagado),
                    saldo=saldo,
                    estado="pendiente",
                )
                db.session.add(deuda_obj)

            # 9) Marcar turno como ATENDIDO (sin re-disparar consumo de inventario)
            if turno_id:
                turno = Turno.query.filter(
                    Turno.id == turno_id,
                    Turno.clinica_id == clinica_id,
                    Turno.is_active.is_(True),
                ).first()
                if turno and turno.estado != EstadoTurno.ATENDIDO:
                    turno.estado = EstadoTurno.ATENDIDO

            # 10) Commit atómico ---------------------------------------------------
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            if idem_key and hasattr(Comprobante, "idempotency_key"):
                previo = Comprobante.query.filter_by(
                    clinica_id=clinica_id, idempotency_key=idem_key
                ).first()
                if previo:
                    return self._build_pos_response(previo, ZERO, None, [], idempotent=True)
            raise
        except (ValueError, ServiceError):
            db.session.rollback()
            raise
        except Exception as exc:
            db.session.rollback()
            raise ServiceError(f"Error al emitir comprobante: {exc}", 500) from exc

        return self._build_pos_response(
            comprobante, saldo, deuda_obj, pagos_creados, items_norm=items_norm
        )

    # ------------------------------------------------------------------
    # Deudas / cuentas por cobrar
    # ------------------------------------------------------------------

    def deudas_por_paciente(self, paciente_id: int) -> dict[str, Any]:
        items = (
            DeudaPaciente.query.filter(
                DeudaPaciente.clinica_id == self.clinica_id,
                DeudaPaciente.paciente_id == paciente_id,
                DeudaPaciente.estado == "pendiente",
                DeudaPaciente.is_active.is_(True),
            )
            .order_by(DeudaPaciente.creado_en.desc())
            .all()
        )
        total_saldo = sum((deuda.saldo or 0) for deuda in items)
        return {
            "data": deuda_many.dump(items),
            "saldo_total": float(dec2(total_saldo)),
        }

    def abonar_deudas(self, payload: dict[str, Any]) -> dict[str, Any]:
        paciente_id = payload.get("paciente_id")
        if not paciente_id:
            raise ServiceError("paciente_id requerido", 400)

        try:
            monto = dec2(payload.get("monto"))
        except Exception as exc:
            raise ServiceError("Monto invalido.", 400) from exc
        if monto <= ZERO:
            raise ServiceError("Monto invalido.", 400)

        metodo = self._enum_member(
            payload.get("metodo") or MetodoPago.EFECTIVO.value, MetodoPago, "metodo"
        )
        nota = payload.get("nota") or ""

        # Row-level locking: previene race conditions y saldos negativos
        # cuando múltiples peticiones simultáneas intentan abonar la misma deuda.
        deudas = (
            DeudaPaciente.query.filter(
                DeudaPaciente.clinica_id == self.clinica_id,
                DeudaPaciente.paciente_id == paciente_id,
                DeudaPaciente.estado == "pendiente",
                DeudaPaciente.is_active.is_(True),
                DeudaPaciente.saldo > ZERO,
            )
            .order_by(DeudaPaciente.creado_en.asc())
            .with_for_update()
            .all()
        )
        if not deudas:
            raise NotFoundError("El paciente no tiene deudas pendientes.")

        try:
            restante = monto
            abonado_total = ZERO

            for deuda in deudas:
                if restante <= ZERO:
                    break
                saldo_deuda = dec2(deuda.saldo or 0)
                cubrir = saldo_deuda if saldo_deuda <= restante else restante
                if cubrir <= ZERO:
                    continue

                deuda.pagado = dec2(Decimal(str(deuda.pagado or 0)) + cubrir)
                deuda.saldo = dec2(Decimal(str(deuda.total or 0)) - deuda.pagado)
                if deuda.saldo <= ZERO:
                    deuda.estado = "cancelada"

                abonado_total = dec2(abonado_total + cubrir)
                restante = dec2(restante - cubrir)

                observacion = f"Abono deuda comp {deuda.comprobante_id}"
                if nota:
                    observacion = f"{observacion} - {nota}"

                db.session.add(CajaMovimiento(
                    clinica_id=self.clinica_id,
                    tipo=TipoMovimiento.INGRESO,
                    monto=cubrir,
                    metodo_pago=metodo,
                    paciente_id=paciente_id,
                    comprobante_id=deuda.comprobante_id,
                    observacion=observacion,
                ))

            db.session.commit()

        except Exception as exc:
            db.session.rollback()
            raise ServiceError(f"Error al abonar deuda: {exc}", 500) from exc

        saldo_pendiente = (
            db.session.query(func.coalesce(func.sum(DeudaPaciente.saldo), 0))
            .filter(
                DeudaPaciente.clinica_id == self.clinica_id,
                DeudaPaciente.paciente_id == paciente_id,
                DeudaPaciente.estado == "pendiente",
                DeudaPaciente.is_active.is_(True),
                DeudaPaciente.saldo > ZERO,
            )
            .scalar()
            or ZERO
        )
        return {
            "ok": True,
            "abonado": float(dec2(abonado_total)),
            "saldo": float(dec2(saldo_pendiente)),
        }

    # ------------------------------------------------------------------
    # Resumen de caja
    # ------------------------------------------------------------------

    def resumen(self, params: dict[str, Any]) -> dict[str, Any]:
        start = parse_datetime(params.get("desde"), "desde")
        if not start:
            start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        end = parse_datetime(params.get("hasta"), "hasta")
        if not end:
            end = datetime.utcnow()

        query = (
            db.session.query(CajaMovimiento.tipo, func.coalesce(func.sum(CajaMovimiento.monto), 0))
            .filter(
                CajaMovimiento.clinica_id == self.clinica_id,
                CajaMovimiento.is_active.is_(True),
                CajaMovimiento.fecha >= start,
                CajaMovimiento.fecha <= end,
            )
            .group_by(CajaMovimiento.tipo)
        )
        totales = {}
        for tipo, total in query.all():
            key = tipo.value if hasattr(tipo, "value") else str(tipo)
            totales[key] = float(total)
        return {"desde": start.isoformat(), "hasta": end.isoformat(), "totales": totales}

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _validar_items(self, items_raw: list, clinica_id: int) -> list[dict]:
        """Valida y normaliza cada ítem del carrito POS."""
        items_norm: list[dict] = []
        for item in items_raw:
            item_type = (item.get("tipo") or "").lower()
            if item_type not in ("producto", "servicio"):
                raise ValueError(f"tipo de item invalido: {item_type!r}")

            ref_id = item.get("id")
            if not ref_id:
                raise ValueError("id de item requerido")

            cantidad = dec2(item.get("cantidad") or 0)
            if cantidad <= ZERO:
                raise ValueError("cantidad > 0 requerida")

            precio = item.get("precio")
            nombre = ""

            if item_type == "servicio":
                servicio = Servicio.query.get(ref_id)
                if not servicio:
                    raise ServiceError(f"servicio {ref_id} no existe", 404)
                if precio is None:
                    precio = servicio.precio or 0
                nombre = item.get("nombre") or servicio.nombre or ""
            else:
                producto = Producto.query.filter_by(
                    id=ref_id, clinica_id=clinica_id, is_active=True
                ).first()
                if not producto:
                    raise ServiceError(f"producto {ref_id} no existe", 404)
                if precio is None:
                    if getattr(producto, "precio_venta", None) is not None:
                        precio = producto.precio_venta
                    else:
                        raise ServiceError(
                            f"El producto '{getattr(producto, 'nombre', ref_id)}' "
                            "no tiene precio de venta configurado.",
                            400,
                        )
                nombre = item.get("nombre") or producto.nombre or ""

            precio = dec2(precio)
            items_norm.append({
                "tipo": item_type,
                "ref_id": ref_id,
                "nombre": nombre,
                "cantidad": cantidad,
                "precio_unit": precio,
                "subtotal": dec2(precio * cantidad),
            })
        return items_norm

    def _calcular_descuento(
        self,
        total_bruto: Decimal,
        dsc_tipo: str | None,
        dsc_valor,
    ) -> Decimal:
        """Calcula el descuento global según tipo (porcentaje o monto fijo)."""
        if dsc_tipo not in ("porcentaje", "monto"):
            return ZERO

        try:
            valor = dec2(dsc_valor or 0)
        except Exception:
            return ZERO

        if dsc_tipo == "porcentaje":
            valor = min(max(valor, ZERO), Decimal("100"))
            return dec2(total_bruto * (valor / Decimal("100")))

        return dec2(min(max(valor, ZERO), total_bruto))

    def _descontar_stock_productos(
        self,
        items_norm: list[dict],
        clinica_id: int,
        referencia: str,
    ) -> None:
        """
        Descuenta stock de inventario RETAIL (solo tipo='producto').
        Los ítems de tipo 'servicio' son excluidos deliberadamente:
        sus insumos clínicos se descuentan en TurnoService al marcar ATENDIDO.
        """
        for item in items_norm:
            if item["tipo"] != "producto":
                continue

            producto = Producto.query.filter_by(
                id=item["ref_id"], clinica_id=clinica_id, is_active=True
            ).first()
            if not producto:
                raise ServiceError(f"Producto {item['ref_id']} no encontrado durante el commit", 404)

            try:
                aplicar_movimiento(
                    producto,
                    TipoMov.EGRESO.value if hasattr(TipoMov, "EGRESO") else "egreso",
                    item["cantidad"],
                    motivo="VENTA",
                    ref=referencia,
                )
            except ValueError as exc:
                raise ServiceError(str(exc), 400) from exc

    def _build_pos_response(
        self,
        comprobante: Comprobante,
        saldo: Decimal,
        deuda_obj,
        pagos_creados: list,
        items_norm: list[dict] | None = None,
        idempotent: bool = False,
    ) -> dict[str, Any]:
        fecha = getattr(comprobante, "fecha", datetime.utcnow())
        return {
            "comprobante": {
                "id": comprobante.id,
                "numero": comprobante.numero,
                "tipo": comprobante.tipo,
                "total_bruto": float(dec2(comprobante.total_bruto or 0)),
                "descuento_global": float(dec2(comprobante.descuento_global or 0)),
                "total": float(dec2(comprobante.total or 0)),
                "paciente_id": comprobante.paciente_id,
                "fecha": fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha),
                "forma_pago": getattr(comprobante.forma_pago, "value", str(comprobante.forma_pago)),
                "items": [
                    {
                        "tipo": it["tipo"],
                        "ref_id": it["ref_id"],
                        "nombre": it["nombre"],
                        "cantidad": float(it["cantidad"]),
                        "precio_unit": float(it["precio_unit"]),
                        "subtotal": float(it["subtotal"]),
                    }
                    for it in (items_norm or [])
                ],
            },
            "pagos": [
                {
                    "metodo": getattr(p.metodo_pago, "value", str(p.metodo_pago)),
                    "monto": float(p.monto),
                }
                for p in pagos_creados
            ],
            "saldo_pendiente": float(saldo),
            "deuda": DeudaPacienteSchema().dump(deuda_obj) if deuda_obj else None,
            "pdf_url": f"/api/caja/comprobantes/{comprobante.id}/pdf",
            "idempotent": idempotent,
        }

    @staticmethod
    def _enum_name(value: Any, enum_cls, field_name: str) -> str:
        return CajaService._enum_member(value, enum_cls, field_name).name

    @staticmethod
    def _enum_member(value: Any, enum_cls, field_name: str):
        if hasattr(value, "name"):
            return value
        raw = (value or "").strip()
        if not raw:
            raise ServiceError(f"{field_name} es requerido", 400)
        lowered = raw.lower()
        for item in enum_cls:
            if lowered in {item.name.lower(), item.value.lower()}:
                return item
        valid = ", ".join(item.value for item in enum_cls)
        raise ServiceError(f"{field_name} invalido. Use: {valid}", 400)
