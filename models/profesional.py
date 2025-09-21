from datetime import datetime
from extensions import db

class Profesional(db.Model):
    __tablename__ = "profesionales"
    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(40), unique=True, index=True)
    matricula = db.Column(db.String(60), unique=True, nullable=True, index=True)
    nombres = db.Column(db.String(120), nullable=False)
    apellidos = db.Column(db.String(120), nullable=False)
    especialidad = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
