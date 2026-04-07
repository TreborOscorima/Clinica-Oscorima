from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SAEnum
import bcrypt
from extensions import db

class RoleEnum(str, Enum):
    ADMIN = "administracion"
    RECEP = "recepcionista"
    PROF = "profesional"
    CONT = "contador"

class User(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    rol = db.Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.RECEP)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, raw):
        # bcrypt requiere bytes y max 72 chars
        pwd_bytes = raw[:72].encode('utf-8')
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    def check_password(self, raw):
        try:
            pwd_bytes = raw[:72].encode('utf-8')
            hash_bytes = self.password_hash.encode('utf-8')
            return bcrypt.checkpw(pwd_bytes, hash_bytes)
        except Exception:
            return False

class PermisoRol(db.Model):
    __tablename__ = "permisos_rol"
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(SAEnum(RoleEnum), nullable=False)
    module = db.Column(db.String(64), nullable=False)
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("role", "module", name="uq_permisos_rol"),)
