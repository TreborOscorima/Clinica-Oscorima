from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, create_engine

from clinica_app.config import DATABASE_URL, SQLMODEL_ECHO

_engine = create_engine(
    DATABASE_URL,
    echo=SQLMODEL_ECHO,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """Context manager: abre sesión, hace commit en éxito, rollback en excepción."""
    with Session(_engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_raw_session() -> Session:
    """Sesión sin context manager — útil en event handlers que gestionan su propio ciclo."""
    return Session(_engine)
