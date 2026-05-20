from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from extensions import db
from models.caja import CajaMovimiento, MetodoPago, TipoMovimiento
from models.paciente import Paciente
from models.profesional import Profesional
from models.servicio import Servicio
from models.turno import EstadoTurno, Turno
from schemas.turno import TurnoSchema
from services.exceptions import ConflictError, NotFoundError, ServiceError
from utils.inventario_ops import consumir_insumos_por_servicio


class TurnoService:
    def __init__(self, clinica_id: int):
        self.clinica_id = clinica_id
        self.schema = TurnoSchema()
        self.schema_many = TurnoSchema(many=True)

    def obtener(self, turno_id: int) -> Turno:
        turno = self._base_query().filter(Turno.id == turno_id).first()
        if turno is None:
            raise NotFoundError("Turno no encontrado")
        return turno

    def listar(self, estado: str = "", page: int = 1, per_page: int = 10) -> dict[str, Any]:
        query = self._base_query()
        if estado:
            try:
                estado_enum = EstadoTurno(estado)
            except Exception as exc:
                raise ServiceError("Estado invalido") from exc
            query = query.filter(Turno.estado == estado_enum)

        query = query.order_by(Turno.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        if pagination.pages and page > pagination.pages:
            pagination = query.paginate(page=pagination.pages, per_page=per_page, error_out=False)

        return {
            "data": self.schema_many.dump(pagination.items),
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages,
            "total": pagination.total,
        }

    def crear(self, payload: dict[str, Any], created_by: Any = None) -> Turno:
        payload = dict(payload)
        payload["clinica_id"] = self.clinica_id
        self._normalizar_profesional(payload)
        self._normalizar_servicio(payload)
        self._validar_paciente(payload.get("paciente_id"))

        turno: Turno = self.schema.load(payload, session=db.session)
        try:
            turno.created_by_id = int(created_by) if created_by is not None else None
        except Exception:
            turno.created_by_id = created_by

        for item in turno.items or []:
            if item.cantidad is None:
                item.cantidad = Decimal("1.00")
            if item.descuento is None:
                item.descuento = Decimal("0.00")

        db.session.add(turno)
        db.session.commit()
        return turno

    def cambiar_estado(self, turno_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        turno = self.obtener(turno_id)
        estado_str = (payload.get("estado") or "").strip().lower()
        motivo = payload.get("motivo_cancelacion")

        try:
            estado_enum = EstadoTurno(estado_str)
        except Exception as exc:
            raise ServiceError("Estado invalido") from exc

        if turno.estado == EstadoTurno.ATENDIDO and estado_enum == EstadoTurno.ATENDIDO:
            raise ConflictError("El turno ya esta atendido")

        turno.estado = estado_enum
        if estado_enum == EstadoTurno.CANCELADO and motivo:
            turno.motivo_cancelacion = motivo

        movimientos_stock: list[dict[str, Any]] = []
        movimiento_caja_id = None

        def _append_consumo(consumo):
            if isinstance(consumo, list):
                movimientos_stock.extend(consumo)
            elif isinstance(consumo, dict):
                movimientos_stock.append(consumo)

        if estado_enum == EstadoTurno.ATENDIDO:
            tiene_items = bool(turno.items)
            referencia = f"TUR-{turno.id:06d}"

            if tiene_items:
                for item in turno.items:
                    try:
                        multiplicador = float(item.cantidad or 1)
                    except Exception:
                        multiplicador = 1.0
                    consumo = consumir_insumos_por_servicio(
                        item.servicio_id,
                        multiplicador=multiplicador,
                        motivo=f"Consumo por turno {turno.id} (item {item.id})",
                        referencia=referencia,
                        clinica_id=self.clinica_id,
                    )
                    _append_consumo(consumo)
            elif turno.servicio_id:
                consumo = consumir_insumos_por_servicio(
                    turno.servicio_id,
                    multiplicador=1.0,
                    motivo=f"Consumo por turno {turno.id}",
                    referencia=referencia,
                    clinica_id=self.clinica_id,
                )
                _append_consumo(consumo)

            if payload.get("cobrar"):
                movimiento_caja_id = self._registrar_cobro(turno, payload, tiene_items)

        db.session.commit()
        response = self.schema.dump(turno)
        response["movimientos_stock"] = movimientos_stock
        response["movimiento_caja_id"] = movimiento_caja_id
        return response

    def reprogramar(self, turno_id: int, payload: dict[str, Any]) -> Turno:
        turno = self.obtener(turno_id)
        nueva_fecha = payload.get("fecha_hora")
        nuevo_estado = (payload.get("estado") or "").strip().lower()

        if not nueva_fecha:
            raise ServiceError("fecha_hora requerida")

        try:
            turno.fecha_hora = datetime.fromisoformat(nueva_fecha)
        except Exception as exc:
            raise ServiceError("fecha_hora invalida") from exc

        if nuevo_estado:
            try:
                turno.estado = EstadoTurno(nuevo_estado)
            except Exception as exc:
                raise ServiceError("estado invalido") from exc

        db.session.commit()
        return turno

    def dump(self, turno: Turno) -> dict[str, Any]:
        return self.schema.dump(turno)

    def _base_query(self):
        return Turno.query.filter(
            Turno.clinica_id == self.clinica_id,
            Turno.is_active.is_(True),
        )

    def _validar_paciente(self, paciente_id: Any) -> None:
        paciente = (
            db.session.execute(
                select(Paciente).where(
                    Paciente.id == paciente_id,
                    Paciente.clinica_id == self.clinica_id,
                    Paciente.is_active.is_(True),
                )
            ).scalar_one_or_none()
            if paciente_id
            else None
        )
        if paciente is None:
            raise NotFoundError("Paciente no encontrado en esta clinica")

    def _normalizar_profesional(self, payload: dict[str, Any]) -> None:
        profesional_id = payload.get("profesional_id")
        profesional_dni = str(payload.get("profesional_dni") or "").strip()
        if not profesional_id and profesional_dni:
            profesional = Profesional.query.filter_by(dni=profesional_dni).first()
            if not profesional:
                raise NotFoundError("Profesional no encontrado por DNI")
            payload["profesional_id"] = profesional.id

    def _normalizar_servicio(self, payload: dict[str, Any]) -> None:
        tiene_items = bool(payload.get("items"))
        servicio_id = payload.get("servicio_id")
        servicio_nombre = (payload.get("servicio_nombre") or "").strip()
        if not tiene_items and not servicio_id and servicio_nombre:
            servicio = Servicio.query.filter(Servicio.nombre.ilike(servicio_nombre)).first()
            if not servicio:
                raise NotFoundError("Servicio no encontrado por nombre")
            payload["servicio_id"] = servicio.id

    def _registrar_cobro(self, turno: Turno, payload: dict[str, Any], tiene_items: bool) -> int:
        monto_req = payload.get("monto")
        if monto_req is None:
            monto = self._calcular_total_turno(turno, tiene_items)
        else:
            try:
                monto = Decimal(str(monto_req))
            except Exception as exc:
                raise ServiceError("Monto invalido") from exc

        if monto <= 0:
            raise ServiceError("Monto invalido")

        metodo = (payload.get("metodo_pago") or MetodoPago.EFECTIVO.value).lower()
        metodos_validos = [metodo_enum.value for metodo_enum in MetodoPago]
        if metodo not in metodos_validos:
            raise ServiceError(f"Metodo de pago invalido. Use: {', '.join(metodos_validos)}")

        observacion_suffix = " (multi-servicio)" if tiene_items else ""
        movimiento = CajaMovimiento(
            clinica_id=self.clinica_id,
            tipo=TipoMovimiento.INGRESO,
            monto=monto,
            metodo_pago=metodo,
            paciente_id=turno.paciente_id,
            profesional_id=turno.profesional_id,
            servicio_id=None if tiene_items else turno.servicio_id,
            turno_id=turno.id,
            observacion=f"Cobro por turno {turno.id}{observacion_suffix}",
        )
        db.session.add(movimiento)
        db.session.flush()
        return int(movimiento.id)

    def _calcular_total_turno(self, turno: Turno, tiene_items: bool) -> Decimal:
        total = Decimal("0.00")
        if tiene_items:
            for item in turno.items:
                precio_item = item.precio if item.precio is not None else item.servicio.precio
                cantidad = Decimal(str(item.cantidad or 1))
                descuento_item = Decimal(str(item.descuento or 0))
                total += (Decimal(str(precio_item or 0)) * cantidad) - descuento_item
        elif turno.servicio_id and turno.servicio:
            total = Decimal(str(getattr(turno.servicio, "precio", 0) or "0"))
        return total
