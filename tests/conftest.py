"""Fixtures compartidas para todos los tests."""
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from clinica_app.models import *  # noqa: F401,F403


@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
        s.rollback()


@pytest.fixture
def clinica(session):
    from clinica_app.models.clinica import Clinica
    c = Clinica(nombre="Test Clínica", slug="test-clinica")
    session.add(c)
    session.flush()
    return c


@pytest.fixture
def paciente(session, clinica):
    from clinica_app.models.paciente import Paciente
    p = Paciente(clinica_id=clinica.id, nombre="Ana Test", documento="99000001")
    session.add(p)
    session.flush()
    return p


@pytest.fixture
def admin_user(session, clinica):
    from clinica_app.models.user import RoleEnum, User
    u = User(clinica_id=clinica.id, nombre="Admin", email="admin@test.com", rol=RoleEnum.ADMIN)
    u.set_password("secret123")
    session.add(u)
    session.flush()
    return u
