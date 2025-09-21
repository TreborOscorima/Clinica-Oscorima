# models/turno_servicio.py
from extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class TurnoServicio(db.Model):
    __tablename__ = "turno_servicios"
    id = db.Column(db.Integer, primary_key=True)
    turno_id = db.Column(db.Integer, ForeignKey("turnos.id", ondelete="CASCADE"), nullable=False)
    servicio_id = db.Column(db.Integer, ForeignKey("servicios.id"), nullable=False)

    precio = db.Column(db.Numeric(10,2), nullable=True)     # si es None, usar precio de Servicio al atender
    cantidad = db.Column(db.Numeric(10,2), default=1)
    descuento = db.Column(db.Numeric(10,2), default=0)
    nota = db.Column(db.String(240))

    servicio = relationship("Servicio", lazy="joined")
