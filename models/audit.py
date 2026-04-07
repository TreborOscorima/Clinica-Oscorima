from datetime import datetime
from extensions import db


class Auditoria(db.Model):
    """Registro de auditoría de acciones del sistema."""
    __tablename__ = "auditoria"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
