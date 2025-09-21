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
