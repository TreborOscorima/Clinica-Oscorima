from datetime import datetime
from extensions import db

class Servicio(db.Model):
    __tablename__ = "servicios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Numeric(10,2), default=0)
    duracion_min = db.Column(db.Integer, default=30)
    insumos = db.Column(db.Text)  # lista simple (CSV/JSON) para starter
    protocolo = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
