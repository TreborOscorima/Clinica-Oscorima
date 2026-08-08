"""Tests de la lógica pura de expiración de sesión (TTL)."""
from __future__ import annotations

from clinica_app.services.sesion import sesion_vencida

TTL = 12 * 3600  # 12 horas
T0 = 1_000_000.0  # instante de login arbitrario (epoch)


def test_sin_login_nunca_vence():
    assert sesion_vencida(0.0, TTL, T0 + 10 * TTL) is False


def test_dentro_del_ttl_no_vence():
    assert sesion_vencida(T0, TTL, T0 + TTL - 1) is False


def test_pasado_el_ttl_vence():
    assert sesion_vencida(T0, TTL, T0 + TTL + 1) is True


def test_borde_exacto_no_vence():
    # A los exactos TTL segundos todavía es válida (estrictamente mayor).
    assert sesion_vencida(T0, TTL, T0 + TTL) is False


def test_recien_logueado_no_vence():
    assert sesion_vencida(T0, TTL, T0) is False
