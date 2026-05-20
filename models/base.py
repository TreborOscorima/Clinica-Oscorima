from __future__ import annotations

from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy import and_
from sqlmodel import Field, SQLModel, select


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IdMixin(SQLModel):
    id: int | None = Field(default=None, primary_key=True)


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": utcnow},
    )


class SoftDeleteMixin(SQLModel):
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, nullable=True, index=True)

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = utcnow()


class TenantMixin(SQLModel):
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)


class BaseSQLModel(IdMixin, TimestampMixin, SQLModel):
    pass


class TenantSQLModel(BaseSQLModel, TenantMixin, SoftDeleteMixin):
    """Base obligatoria para datos operativos de una clinica."""


TenantModelT = TypeVar("TenantModelT", bound=TenantSQLModel)


def tenant_select(model: type[TenantModelT], clinica_id: int, include_deleted: bool = False):
    conditions = [model.clinica_id == clinica_id]
    if not include_deleted:
        conditions.append(model.is_active.is_(True))
    return select(model).where(and_(*conditions))
