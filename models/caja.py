from datetime import datetime, date
from enum import Enum

from sqlalchemy import Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from extensions import db


class TipoMovimiento(str, Enum):
    INGRESO = "ingreso"
    EGRESO = "egreso"


class MetodoPago(str, Enum):
    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"
    OTRO = "otro"


class Comprobante(db.Model):
    __tablename__ = "comprobantes"
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), default="recibo")
    numero = db.Column(db.String(40), unique=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    paciente_id = db.Column(db.Integer, ForeignKey("pacientes.id"))
    # Totales
    total = db.Column(db.Numeric(10, 2), default=0)              # total neto (después de descuento)
    total_bruto = db.Column(db.Numeric(10, 2), default=0)         # suma de subtotales de items
    descuento_global = db.Column(db.Numeric(10, 2), default=0)    # monto descontado globalmente
    # Otros
    forma_pago = db.Column(SAEnum(MetodoPago), default=MetodoPago.EFECTIVO)
    observacion = db.Column(db.String(240))

    # Idempotencia (nuevo)
    idempotency_key = db.Column(db.String(64), unique=True, index=True, nullable=True)


class CajaMovimiento(db.Model):
    __tablename__ = "caja_movimientos"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    tipo = db.Column(SAEnum(TipoMovimiento), nullable=False, default=TipoMovimiento.INGRESO)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo_pago = db.Column(SAEnum(MetodoPago), default=MetodoPago.EFECTIVO)
    paciente_id = db.Column(db.Integer, ForeignKey("pacientes.id"), nullable=True)
    profesional_id = db.Column(db.Integer, ForeignKey("profesionales.id"), nullable=True)
    servicio_id = db.Column(db.Integer, ForeignKey("servicios.id"), nullable=True)
    comprobante_id = db.Column(db.Integer, ForeignKey("comprobantes.id"), nullable=True)
    turno_id = db.Column(db.Integer, db.ForeignKey("turnos.id"), nullable=True)
    observacion = db.Column(db.String(240))


class CierreCaja(db.Model):
    __tablename__ = "cierres_caja"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today, unique=True)
    total_ingresos = db.Column(db.Numeric(10, 2), default=0)
    total_egresos = db.Column(db.Numeric(10, 2), default=0)
    saldo = db.Column(db.Numeric(10, 2), default=0)
    usuario_id = db.Column(db.Integer, ForeignKey("usuarios.id"), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class ComprobanteItem(db.Model):
    __tablename__ = "comprobante_items"
    id = db.Column(db.Integer, primary_key=True)
    comprobante_id = db.Column(db.Integer, ForeignKey("comprobantes.id"), nullable=False, index=True)
    # tipo del ítem: 'producto' o 'servicio'
    tipo = db.Column(db.String(20), nullable=False)
    ref_id = db.Column(db.Integer, nullable=False)  # producto_id o servicio_id
    nombre = db.Column(db.String(200), nullable=False)
    cantidad = db.Column(db.Numeric(10, 3), default=0)
    precio_unit = db.Column(db.Numeric(10, 2), default=0)
    subtotal = db.Column(db.Numeric(10, 2), default=0)

    comprobante = relationship("Comprobante", backref="items")


class DeudaPaciente(db.Model):
    __tablename__ = "deudas_paciente"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, ForeignKey("pacientes.id"), nullable=False, index=True)
    comprobante_id = db.Column(db.Integer, ForeignKey("comprobantes.id"), nullable=False, index=True)
    total = db.Column(db.Numeric(10, 2), nullable=False)  # total del comprobante (neto)
    pagado = db.Column(db.Numeric(10, 2), default=0)      # suma de pagos registrados
    saldo = db.Column(db.Numeric(10, 2), nullable=False)  # total - pagado
    estado = db.Column(db.String(20), default="pendiente")  # pendiente / cancelada
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
