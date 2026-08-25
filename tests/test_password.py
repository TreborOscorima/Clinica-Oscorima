"""Política de contraseñas (reglas de complejidad)."""
from __future__ import annotations

import pytest

from clinica_app.services.exceptions import ValidationError
from clinica_app.services.password import validar_password


def test_password_valida_pasa():
    validar_password("Segura123")  # 9 chars, letra + número → no lanza


def test_password_corta_falla():
    with pytest.raises(ValidationError):
        validar_password("Ab12")


def test_password_sin_numero_falla():
    with pytest.raises(ValidationError):
        validar_password("solamenteletras")


def test_password_sin_letra_falla():
    with pytest.raises(ValidationError):
        validar_password("12345678")


def test_password_vacia_falla():
    with pytest.raises(ValidationError):
        validar_password("")
