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


async def test_crear_con_ficha_medica(session, clinica):
    # A1: la ficha médica (alergias/antecedentes/medicación/hábitos/grupo) viaja
    # de vuelta en el dump para que la UI la muestre.
    p = await svc.crear(session, clinica.id, payload={
        "nombre": "Ficha Completa",
        "documento": "77000001",
        "grupo_sanguineo": "O+",
        "alergias": "Penicilina, látex",
        "antecedentes": "Hipertensión",
        "medicacion": "Enalapril 10mg",
        "habitos": "No fuma",
    })
    assert p["grupo_sanguineo"] == "O+"
    assert p["alergias"] == "Penicilina, látex"
    assert p["antecedentes"] == "Hipertensión"
    assert p["medicacion"] == "Enalapril 10mg"
    assert p["habitos"] == "No fuma"


async def test_crear_sin_ficha_medica_ok(session, clinica):
    # Los campos de ficha médica son opcionales: sin ellos el dump devuelve None.
    p = await svc.crear(session, clinica.id, payload={"nombre": "Sin Ficha"})
    assert p["alergias"] is None
    assert p["grupo_sanguineo"] is None


async def test_actualizar_ficha_medica(session, clinica):
    p = await svc.crear(session, clinica.id, payload={"nombre": "Base Ficha", "documento": "77000002"})
    assert p["alergias"] is None
    actualizado = await svc.actualizar(
        session, clinica.id, p["id"],
        {"alergias": "Ibuprofeno", "grupo_sanguineo": "A-"},
    )
    assert actualizado["alergias"] == "Ibuprofeno"
    assert actualizado["grupo_sanguineo"] == "A-"


async def test_crear_con_sexo_y_tipo_documento(session, clinica):
    # Los nuevos campos demográficos viajan de vuelta en el dump.
    p = await svc.crear(session, clinica.id, payload={
        "nombre": "Demo Sexo", "documento": "88000001",
        "tipo_documento": "dni", "sexo": "femenino",
    })
    assert p["tipo_documento"] == "dni"
    assert p["sexo"] == "femenino"


async def test_dump_campos_demograficos_por_defecto_vacios(session, clinica):
    p = await svc.crear(session, clinica.id, payload={"nombre": "Sin Demo"})
    assert p["tipo_documento"] == ""
    assert p["sexo"] == ""


async def test_pasaporte_admite_letras(session, clinica):
    # Pasaporte es alfanumérico: se acepta un documento con letras.
    p = await svc.crear(session, clinica.id, payload={
        "nombre": "Extranjero", "documento": "AB1234567", "tipo_documento": "pasaporte",
    })
    assert p["documento"] == "AB1234567"


async def test_dni_rechaza_letras(session, clinica):
    # DNI es numérico: un documento con letras debe fallar la validación.
    with pytest.raises(ValidationError):
        await svc.crear(session, clinica.id, payload={
            "nombre": "DNI Malo", "documento": "AB12", "tipo_documento": "dni",
        })


async def test_pasaporte_rechaza_simbolos(session, clinica):
    # Aun alfanumérico, no se admiten espacios ni símbolos.
    with pytest.raises(ValidationError):
        await svc.crear(session, clinica.id, payload={
            "nombre": "Pasaporte Malo", "documento": "AB-12/34", "tipo_documento": "pasaporte",
        })


async def test_cambiar_a_pasaporte_permite_documento_alfanumerico(session, clinica):
    # Un paciente con DNI numérico puede pasar a pasaporte alfanumérico en la edición.
    p = await svc.crear(session, clinica.id, payload={
        "nombre": "Muta Doc", "documento": "88000002", "tipo_documento": "dni",
    })
    upd = await svc.actualizar(session, clinica.id, p["id"], {
        "documento": "XY9988", "tipo_documento": "pasaporte",
    })
    assert upd["documento"] == "XY9988"
    assert upd["tipo_documento"] == "pasaporte"


async def test_eliminar_paciente(session, clinica):
    p = await svc.crear(session, clinica.id, payload={"nombre": "A borrar", "documento": "44000001"})
    await svc.eliminar(session, clinica.id, p["id"])

    with pytest.raises(NotFoundError):
        await svc.obtener(session, clinica.id, p["id"])
