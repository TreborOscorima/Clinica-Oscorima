from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LoginIntento(SQLModel, table=True):
    """Registra intentos de login fallidos para rate limiting persistente."""

    __tablename__ = "login_intentos"
    __table_args__ = (
        Index("ix_login_intentos_email_created", "email", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=120, nullable=False, index=True)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime, default=_utcnow, nullable=False),
    )
