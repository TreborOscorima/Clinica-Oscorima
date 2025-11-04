# models/paciente.py
from extensions import db
from datetime import date, datetime

class Paciente(db.Model):
    __tablename__ = "pacientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(180), nullable=False)
    documento = db.Column(db.String(40), index=True, unique=True)
    direccion = db.Column(db.String(200))
    email = db.Column(db.String(120), unique=True, nullable=True)
    telefono = db.Column(db.String(60))
    fecha_nacimiento = db.Column(db.Date)
    contacto_emergencia = db.Column(db.String(160))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def edad(self):
        if self.fecha_nacimiento:
            hoy = date.today()
            return (
                hoy.year
                - self.fecha_nacimiento.year
                - ((hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
            )
        return None
