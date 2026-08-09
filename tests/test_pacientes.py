"""Tests del servicio de pacientes."""
from __future__ import annotations

import pytest

from clinica_app.services import pacientes as svc
from clinica_app.services.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


async def test_listar_vacio(session, clinica):
    res = await svc.listar(session, clinica.id)
    assert res["total"] == 0
    assert res["data"] == []


async def test_crear_paciente(session, clinica):
    p = await svc.crear(session, clinica.id, payload={"nombre": "Juan Pérez", "documento": "12000001"})
    assert p["nombre"] == "Juan Pérez"
    assert p["id"] is not None


async def test_crear_documento_duplicado(session, clinica):
    await svc.crear(session, clinica.id, payload={"nombre": "P1", "documento": "55000001"})
    with pytest.raises(ConflictError):
        await svc.crear(session, clinica.id, payload={"nombre": "P2", "documento": "55000001"})


async def test_crear_documento_no_numerico_falla(session, clinica):
    # Paridad con el CHECK constraint `chk_documento_digits` (^[0-9]+$):
    # el servicio valida ANTES de tocar la BD y lanza un error claro.
    with pytest.raises(ValidationError):
        await svc.crear(session, clinica.id, payload={"nombre": "Malo", "documento": "ABC-123"})


async def test_crear_documento_vacio_ok(session, clinica):
    # El documento es opcional: sin documento no debe fallar la validación.
    p = await svc.crear(session, clinica.id, payload={"nombre": "Sin Doc"})
    assert p["documento"] is None


async def test_actualizar_documento_no_numerico_falla(session, clinica):
    p = await svc.crear(session, clinica.id, payload={"nombre": "Base", "documento": "66000001"})
    with pytest.raises(ValidationError):
        await svc.actualizar(session, clinica.id, p["id"], {"documento": "12x45"})


async def test_listar_con_busqueda(session, clinica):
    await svc.crear(session, clinica.id, payload={"nombre": "María López", "documento": "22000001"})
    await svc.crear(session, clinica.id, payload={"nombre": "Pedro Ruiz",  "documento": "22000002"})

    res = await svc.listar(session, clinica.id, q="maría")
    assert res["total"] == 1
    assert res["data"][0]["nombre"] == "María López"


async def test_actualizar_paciente(session, clinica):
    p = await svc.crear(session, clinica.id, payload={"nombre": "Original", "documento": "33000001"})
    actualizado = await svc.actualizar(session, clinica.id, p["id"], {"nombre": "Modificado"})
    assert actualizado["nombre"] == "Modificado"


async def test_eliminar_paciente(session, clinica):
    p = await svc.crear(session, clinica.id, payload={"nombre": "A borrar", "documento": "44000001"})
    await svc.eliminar(session, clinica.id, p["id"])

    with pytest.raises(NotFoundError):
        await svc.obtener(session, clinica.id, p["id"])
