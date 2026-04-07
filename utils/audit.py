from datetime import datetime
from flask import request
from extensions import db
from models.audit import Auditoria

def log_action(user_id, action, details=""):
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    except RuntimeError:
        ip = None
    entry = Auditoria(user_id=user_id, action=action, details=details, ip=ip, created_at=datetime.utcnow())
    db.session.add(entry)
    db.session.commit()
