"""Tests del servicio de pacientes."""
from __future__ import annotations

import pytest

from clinica_app.services import pacientes as svc
from clinica_app.services.exceptions import ConflictError, NotFoundError


def test_listar_vacio(session, clinica):
    res = svc.listar(session, clinica.id)
    assert res["total"] == 0
    assert res["data"] == []


def test_crear_paciente(session, clinica):
    p = svc.crear(session, clinica.id, {"nombre": "Juan Pérez", "documento": "12000001"})
    assert p["nombre"] == "Juan Pérez"
    assert p["id"] is not None


def test_crear_documento_duplicado(session, clinica):
    svc.crear(session, clinica.id, {"nombre": "P1", "documento": "DUP001"})
    with pytest.raises(ConflictError):
        svc.crear(session, clinica.id, {"nombre": "P2", "documento": "DUP001"})


def test_listar_con_busqueda(session, clinica):
    svc.crear(session, clinica.id, {"nombre": "María López", "documento": "22000001"})
    svc.crear(session, clinica.id, {"nombre": "Pedro Ruiz",  "documento": "22000002"})

    res = svc.listar(session, clinica.id, q="maría")
    assert res["total"] == 1
    assert res["data"][0]["nombre"] == "María López"


def test_actualizar_paciente(session, clinica):
    p = svc.crear(session, clinica.id, {"nombre": "Original", "documento": "33000001"})
    actualizado = svc.actualizar(session, clinica.id, p["id"], {"nombre": "Modificado"})
    assert actualizado["nombre"] == "Modificado"


def test_eliminar_paciente(session, clinica):
    p = svc.crear(session, clinica.id, {"nombre": "A borrar", "documento": "44000001"})
    svc.eliminar(session, clinica.id, p["id"])

    with pytest.raises(NotFoundError):
        svc.obtener(session, clinica.id, p["id"])
