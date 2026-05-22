"""Tests del servicio de cuentas / deudas."""
from __future__ import annotations

from decimal import Decimal

import pytest

from clinica_app.services import cuentas as svc
from clinica_app.services.exceptions import NotFoundError, ServiceError


# ── Fixtures adicionales ──────────────────────────────────────────────────────

@pytest.fixture
def comprobante_con_deuda(session, clinica, paciente):
    """Crea un comprobante + DeudaPaciente de $200 con $50 anticipo → saldo $150."""
    from clinica_app.models.caja import (
        Comprobante, ComprobanteItem, DeudaPaciente, MetodoPago,
    )

    comp = Comprobante(
        clinica_id=clinica.id,
        paciente_id=paciente.id,
        numero="REC-TEST-001",
        total=Decimal("200.00"),
        total_bruto=Decimal("200.00"),
        descuento_global=Decimal("0"),
        forma_pago=MetodoPago.EFECTIVO,
    )
    session.add(comp)
    session.flush()

    item = ComprobanteItem(
        comprobante_id=comp.id,
        tipo="servicio",
        ref_id=1,
        nombre="Consulta",
        cantidad=Decimal("1"),
        precio_unit=Decimal("200.00"),
        subtotal=Decimal("200.00"),
    )
    session.add(item)

    deuda = DeudaPaciente(
        clinica_id=clinica.id,
        paciente_id=paciente.id,
        comprobante_id=comp.id,
        total=Decimal("200.00"),
        pagado=Decimal("50.00"),
        saldo=Decimal("150.00"),
        estado="parcial",
    )
    session.add(deuda)
    session.flush()
    return {"comp": comp, "deuda": deuda}


# ── Tests de listar ───────────────────────────────────────────────────────────

def test_listar_vacio(session, clinica):
    res = svc.listar(session, clinica.id)
    assert res["total"] == 0
    assert res["data"] == []


def test_listar_con_deuda(session, clinica, comprobante_con_deuda):
    res = svc.listar(session, clinica.id)
    assert res["total"] == 1
    assert res["data"][0]["saldo"] == "150.00"
    assert res["data"][0]["estado"] == "parcial"


def test_listar_filtro_estado(session, clinica, comprobante_con_deuda):
    res_parcial  = svc.listar(session, clinica.id, estado="parcial")
    res_saldado  = svc.listar(session, clinica.id, estado="saldado")
    assert res_parcial["total"] == 1
    assert res_saldado["total"] == 0


def test_listar_filtro_paciente(session, clinica, paciente, comprobante_con_deuda):
    res = svc.listar(session, clinica.id, paciente_q=paciente.nombre[:4])
    assert res["total"] == 1

    res_nada = svc.listar(session, clinica.id, paciente_q="ZZZXXX")
    assert res_nada["total"] == 0


def test_listar_kpis(session, clinica, comprobante_con_deuda):
    res = svc.listar(session, clinica.id)
    assert res["total_deudores"] >= 1
    assert Decimal(res["total_saldo"]) >= Decimal("150.00")


# ── Tests de registrar_pago ───────────────────────────────────────────────────

def test_registrar_pago_parcial(session, clinica, comprobante_con_deuda):
    deuda_id = comprobante_con_deuda["deuda"].id
    resultado = svc.registrar_pago(session, clinica.id, deuda_id, "50.00", "efectivo")
    assert resultado["estado"] == "parcial"
    assert Decimal(resultado["saldo"]) == Decimal("100.00")
    assert Decimal(resultado["pagado"]) == Decimal("100.00")


def test_registrar_pago_total(session, clinica, comprobante_con_deuda):
    deuda_id = comprobante_con_deuda["deuda"].id
    resultado = svc.registrar_pago(session, clinica.id, deuda_id, "150.00", "tarjeta")
    assert resultado["estado"] == "saldado"
    assert Decimal(resultado["saldo"]) == Decimal("0.00")


def test_registrar_pago_monto_cero(session, clinica, comprobante_con_deuda):
    deuda_id = comprobante_con_deuda["deuda"].id
    with pytest.raises(ServiceError):
        svc.registrar_pago(session, clinica.id, deuda_id, "0", "efectivo")


def test_registrar_pago_supera_saldo(session, clinica, comprobante_con_deuda):
    deuda_id = comprobante_con_deuda["deuda"].id
    with pytest.raises(ServiceError):
        svc.registrar_pago(session, clinica.id, deuda_id, "9999.00", "efectivo")


def test_registrar_pago_ya_saldado(session, clinica, comprobante_con_deuda):
    deuda_id = comprobante_con_deuda["deuda"].id
    svc.registrar_pago(session, clinica.id, deuda_id, "150.00", "efectivo")
    with pytest.raises(ServiceError):
        svc.registrar_pago(session, clinica.id, deuda_id, "1.00", "efectivo")


def test_registrar_pago_deuda_inexistente(session, clinica):
    with pytest.raises(NotFoundError):
        svc.registrar_pago(session, clinica.id, 99999, "10.00", "efectivo")
