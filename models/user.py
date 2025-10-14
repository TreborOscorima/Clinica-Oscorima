from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SAEnum
from passlib.hash import bcrypt
from extensions import db

class RoleEnum(str, Enum):
    ADMIN = "administracion"
    RECEP = "recepcionista"
    PROF = "profesional"
    CONT = "contador"

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    rol = db.Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.RECEP)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, raw):
        self.password_hash = bcrypt.hash(raw)

    def check_password(self, raw):
        return bcrypt.verify(raw, self.password_hash)


class RolePermission(db.Model):
    __tablename__ = "role_permissions"
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(SAEnum(RoleEnum), nullable=False)
    module = db.Column(db.String(64), nullable=False)
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("role", "module", name="uq_role_permissions"),)
