"""Fixtures compartidas para todos los tests (async con aiosqlite)."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from clinica_app.models import *  # noqa: F401,F403


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine) as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def clinica(session):
    from clinica_app.models.clinica import Clinica
    c = Clinica(nombre="Test Clínica", slug="test-clinica")
    session.add(c)
    await session.flush()
    return c


@pytest_asyncio.fixture
async def paciente(session, clinica):
    from clinica_app.models.paciente import Paciente
    p = Paciente(clinica_id=clinica.id, nombre="Ana Test", documento="99000001")
    session.add(p)
    await session.flush()
    return p


@pytest_asyncio.fixture
async def admin_user(session, clinica):
    from clinica_app.models.user import RoleEnum, User
    u = User(clinica_id=clinica.id, nombre="Admin", email="admin@test.com", rol=RoleEnum.ADMIN)
    u.set_password("secret123")
    session.add(u)
    await session.flush()
    return u
