"""Cruce receta ↔ alergias: detección de alérgenos declarados en la prescripción.

Función pura (sin BD): normaliza sin acentos e insensible a mayúsculas, separa
los términos de la alergia y matchea por substring contra el cuerpo de la receta.
"""
from __future__ import annotations

from clinica_app.services.recetas import detectar_conflictos_alergia as detectar


def test_match_basico():
    assert detectar("Amoxicilina 500mg c/8h", "Penicilina, Amoxicilina") == ["Amoxicilina"]


def test_insensible_mayusculas():
    assert detectar("AMOXICILINA 500", "amoxicilina") == ["amoxicilina"]


def test_ignora_acentos():
    # La alergia trae acento, la receta no (y viceversa).
    assert detectar("aspirina", "Aspirína") == ["Aspirína"]
    assert detectar("Dipiróna 1g", "dipirona") == ["dipirona"]


def test_substring_droga_con_dosis():
    assert detectar("Penicilina G sódica 1.000.000 UI", "penicilina") == ["penicilina"]


def test_varios_separadores():
    alergias = "Penicilina; Látex / Ibuprofeno\nSulfas"
    cuerpo = "Ibuprofeno 400mg y aplicar guantes sin látex"
    res = detectar(cuerpo, alergias)
    assert "Ibuprofeno" in res
    assert "Látex" in res
    assert "Penicilina" not in res
    assert "Sulfas" not in res


def test_separador_y():
    assert detectar("Naproxeno", "Aspirina y Naproxeno") == ["Naproxeno"]


def test_ignora_terminos_cortos():
    # Términos < 3 chars no cuentan (evita ruido tipo "AB").
    assert detectar("Comprimido AB por la mañana", "AB") == []


def test_sin_conflicto():
    assert detectar("Paracetamol 500mg", "Penicilina, Sulfas") == []


def test_alergias_vacias():
    assert detectar("Amoxicilina", "") == []
    assert detectar("Amoxicilina", "   ") == []


def test_cuerpo_vacio():
    assert detectar("", "Penicilina") == []


def test_dedup_preserva_orden():
    # Mismo alérgeno repetido en la lista → una sola vez.
    assert detectar("Ibuprofeno c/8h, ibuprofeno gel", "Ibuprofeno, ibuprofeno") == ["Ibuprofeno"]
