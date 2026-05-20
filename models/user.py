from __future__ import annotations

from enum import Enum

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import UniqueConstraint
from sqlmodel import Field
import bcrypt

from extensions import db
from models.base import BaseSQLModel, TenantSQLModel


class RoleEnum(str, Enum):
    ADMIN = "administracion"
    RECEP = "recepcionista"
    PROF = "profesional"
    CONT = "contador"


class User(TenantSQLModel, table=True):
    __tablename__ = "usuarios"
    metadata = db.metadata

    email: str = Field(max_length=120, nullable=False, unique=True)
    password_hash: str = Field(max_length=255, nullable=False)
    nombre: str = Field(max_length=120, nullable=False)
    rol: RoleEnum = Field(
        sa_column=Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.RECEP)
    )
    # is_active + deleted_at vienen de SoftDeleteMixin (reemplazan 'activo')
    # clinica_id viene de TenantMixin
    # id, created_at, updated_at vienen de BaseSQLModel

    def set_password(self, raw: str) -> None:
        pwd_bytes = raw[:72].encode("utf-8")
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        try:
            pwd_bytes = raw[:72].encode("utf-8")
            hash_bytes = self.password_hash.encode("utf-8")
            return bcrypt.checkpw(pwd_bytes, hash_bytes)
        except Exception:
            return False


class PermisoRol(BaseSQLModel, table=True):
    __tablename__ = "permisos_rol"
    metadata = db.metadata

    role: RoleEnum = Field(
        sa_column=Column(SAEnum(RoleEnum), nullable=False)
    )
    module: str = Field(max_length=64, nullable=False)
    can_read: bool = Field(default=True)
    can_write: bool = Field(default=False)

    __table_args__ = (UniqueConstraint("role", "module", name="uq_permisos_rol"),)
