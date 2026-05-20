from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from flask import Flask, current_app, g
from sqlmodel import SQLModel, Session, create_engine


def init_sqlmodel(app: Flask) -> None:
    """Inicializa el engine SQLModel para los modelos nuevos."""
    engine_options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}))
    engine = create_engine(
        app.config["DATABASE_URL"],
        echo=app.config.get("SQLMODEL_ECHO", False),
        **engine_options,
    )
    app.extensions["sqlmodel_engine"] = engine


def get_engine():
    return current_app.extensions["sqlmodel_engine"]


def get_session() -> Session:
    """Sesion SQLModel por request, separada de Flask-SQLAlchemy legacy."""
    if "sqlmodel_session" not in g:
        g.sqlmodel_session = Session(get_engine())
    return g.sqlmodel_session


def close_sqlmodel_session(_: BaseException | None = None) -> None:
    session = g.pop("sqlmodel_session", None)
    if session is not None:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_sqlmodel_tables() -> None:
    SQLModel.metadata.create_all(get_engine())
