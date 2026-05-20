from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class EstadoTurno(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    ATENDIDO = "atendido"


class Turno(db.Model):
    __tablename__ = "turnos"
    id = db.Column(db.Integer, primary_key=True)
    clinica_id = db.Column(db.Integer, ForeignKey("clinicas.id"), nullable=False, index=True)
    paciente_id = db.Column(db.Integer, ForeignKey("pacientes.id"), nullable=False)
    profesional_id = db.Column(db.Integer, ForeignKey("profesionales.id"))

    # DEPRECADO: se mantiene para compat, pero la logica nueva usa items (TurnoServicio)
    servicio_id = db.Column(db.Integer, ForeignKey("servicios.id"))

    fecha_hora = db.Column(db.DateTime, nullable=False)
    created_by_id = db.Column(db.Integer, ForeignKey("usuarios.id"))
    estado = db.Column(SAEnum(EstadoTurno), default=EstadoTurno.PENDIENTE)
    motivo_cancelacion = db.Column(db.String(240))
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()

    # Paciente y User son SQLModel (registro distinto al de Flask-SQLAlchemy).
    # Se pasa un callable para evitar la busqueda por string en el registro incorrecto.
    paciente = relationship(lambda: _get_paciente_cls(), lazy="joined")
    profesional = relationship("Profesional", lazy="joined")
    servicio = relationship("Servicio", lazy="joined")
    created_by = relationship(lambda: _get_user_cls(), lazy="joined")

    # NUEVO: items del turno (multiples servicios)
    items = relationship("TurnoServicio", cascade="all, delete-orphan", backref="turno", lazy="joined")


def _get_paciente_cls():
    from models.paciente import Paciente
    return Paciente


def _get_user_cls():
    from models.user import User
    return User
