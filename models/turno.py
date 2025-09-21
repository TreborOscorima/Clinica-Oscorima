from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from extensions import db

class EstadoTurno(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    ATENDIDO = "atendido"

class Turno(db.Model):
    __tablename__ = "turnos"
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, ForeignKey("pacientes.id"), nullable=False)
    profesional_id = db.Column(db.Integer, ForeignKey("profesionales.id"))

    # DEPRECADO: se mantiene para compat, pero la lógica nueva usa items (TurnoServicio)
    servicio_id = db.Column(db.Integer, ForeignKey("servicios.id"))

    fecha_hora = db.Column(db.DateTime, nullable=False)
    estado = db.Column(SAEnum(EstadoTurno), default=EstadoTurno.PENDIENTE)
    motivo_cancelacion = db.Column(db.String(240))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones “amigables”
    paciente = relationship("Paciente", lazy="joined")
    profesional = relationship("Profesional", lazy="joined")
    servicio = relationship("Servicio", lazy="joined")  # ← por compat con listados existentes

    # NUEVO: items del turno (múltiples servicios)
    items = relationship("TurnoServicio", cascade="all, delete-orphan", backref="turno", lazy="joined")
