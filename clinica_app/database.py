from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, create_engine

from clinica_app.config import ASYNC_DATABASE_URL, DATABASE_URL, SQLMODEL_ECHO

# ── Motor síncrono ─────────────────────────────────────────────────────────────
# Usado EXCLUSIVAMENTE por: Alembic, scripts CLI, tareas Celery fuera del loop.
_sync_engine = create_engine(
    DATABASE_URL,
    echo=SQLMODEL_ECHO,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
)

# ── Motor asíncrono ────────────────────────────────────────────────────────────
# Usado por TODOS los event handlers de Reflex (get_async_session).
# Requiere: pip install aiomysql greenlet
_async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=SQLMODEL_ECHO,
    pool_pre_ping=False,   # aiomysql 0.3.x incompatible con ping() de SQLAlchemy
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
)


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Context manager async para event handlers de Reflex.

    expire_on_commit=False es obligatorio: en modo async SQLAlchemy intenta
    re-cargar atributos expirados de forma lazy, lo que bloquea el event loop.
    Con esta flag los objetos se mantienen usables después del commit.
    """
    async with AsyncSession(_async_engine, expire_on_commit=False) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def get_session() -> Iterator[Session]:
    """Context manager síncrono — solo para Alembic y scripts externos."""
    with Session(_sync_engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


