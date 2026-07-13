from __future__ import annotations

from enum import Enum

import bcrypt
from sqlalchemy import Column, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field

from clinica_app.models.base import BaseSQLModel, TenantSQLModel


class RoleEnum(str, Enum):
    ADMIN = "administracion"
    RECEP  = "recepcionista"
    PROF   = "profesional"
    CONT   = "contador"


class User(TenantSQLModel, table=True):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("email", name="uq_usuarios_email"),
    )

    email: str = Field(max_length=120, nullable=False)
    password_hash: str = Field(max_length=255, nullable=False)
    nombre: str = Field(max_length=120, nullable=False)
    rol: RoleEnum = Field(
        sa_column=Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.RECEP)
    )
    # Vínculo opcional con la entidad Profesional (para mostrar agenda propia)
    profesional_id: int | None = Field(default=None, foreign_key="profesionales.id", nullable=True)

    def set_password(self, raw: str) -> None:
        pwd_bytes = raw.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        try:
            return bcrypt.checkpw(raw.encode("utf-8")[:72], self.password_hash.encode("utf-8"))
        except Exception:
            return False


class UsuarioSede(BaseSQLModel, table=True):
    """Sucursales a las que tiene acceso un usuario (no-admin)."""
    __tablename__ = "usuario_sedes"
    __table_args__ = (UniqueConstraint("user_id", "sede_id", name="uq_usuario_sedes"),)

    user_id: int = Field(foreign_key="usuarios.id", nullable=False, index=True)
    sede_id: int = Field(foreign_key="sedes.id",    nullable=False, index=True)


class PermisoRol(BaseSQLModel, table=True):
    __tablename__ = "permisos_rol"

    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    role: RoleEnum = Field(
        sa_column=Column(SAEnum(RoleEnum), nullable=False)
    )
    module: str = Field(max_length=64, nullable=False)
    can_read: bool = Field(default=True)
    can_write: bool = Field(default=False)

    __table_args__ = (
        UniqueConstraint("clinica_id", "role", "module", name="uq_permisos_rol_clinica"),
    )
