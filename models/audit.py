from datetime import datetime
from extensions import db

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
