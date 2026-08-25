"""Cronograma de cuotas de una deuda financiada."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from clinica_app.models.caja import DeudaPaciente
from clinica_app.services import cuotas as svc


async def _deuda(session, clinica, *, total="1000.00", pagado="0.00", comp_id=1):
    total_d, pagado_d = Decimal(total), Decimal(pagado)
    d = DeudaPaciente(
        clinica_id=clinica.id, paciente_id=1, comprobante_id=comp_id,
        total=total_d, pagado=pagado_d, saldo=total_d - pagado_d, estado="pendiente",
    )
    session.add(d)
    await session.flush()
    return d


# ── helpers puros ────────────────────────────────────────────────────────────

def test_add_meses_conserva_dia():
    assert svc._add_meses(date(2026, 1, 15), 1) == date(2026, 2, 15)
    assert svc._add_meses(date(2026, 1, 15), 12) == date(2027, 1, 15)


def test_add_meses_clamp_fin_de_mes():
    # 31 de enero + 1 mes → 28 de febrero (2026 no bisiesto)
    assert svc._add_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_montos_suman_el_total_con_resto_en_la_ultima():
    montos = svc._montos(Decimal("100.00"), 3)
    assert len(montos) == 3
    assert sum(montos) == Decimal("100.00")
    assert montos[-1] != montos[0]  # la última absorbe el resto de redondeo


# ── generar ──────────────────────────────────────────────────────────────────

async def test_generar_crea_n_cuotas_mensuales(session, clinica):
    d = await _deuda(session, clinica, total="900.00")
    cuotas = await svc.generar(
        session, clinica_id=clinica.id, deuda_id=d.id, total="900.00", num_cuotas=3,
        desde=date(2026, 1, 10),
    )
    assert [c["numero"] for c in cuotas] == [1, 2, 3]
    assert sum(Decimal(c["monto"]) for c in cuotas) == Decimal("900.00")
    # vencimientos mensuales desde el mes siguiente
    assert cuotas[0]["vencimiento"] == "10/02/2026"
    assert cuotas[2]["vencimiento"] == "10/04/2026"


async def test_generar_noop_si_total_cero(session, clinica):
    d = await _deuda(session, clinica, total="0.00")
    assert await svc.generar(session, clinica_id=clinica.id, deuda_id=d.id, total="0", num_cuotas=3) == []


async def test_generar_noop_si_num_cuotas_invalido(session, clinica):
    d = await _deuda(session, clinica)
    assert await svc.generar(session, clinica_id=clinica.id, deuda_id=d.id, total="100", num_cuotas=0) == []


# ── estado derivado (waterfall) ──────────────────────────────────────────────

async def test_listar_sin_pago_todas_pendientes_o_vencidas(session, clinica):
    d = await _deuda(session, clinica, total="300.00", pagado="0.00")
    await svc.generar(session, clinica_id=clinica.id, deuda_id=d.id, total="300.00", num_cuotas=3,
                      desde=date(2100, 1, 1))  # futuro lejano → todas pendientes
    cuotas = await svc.listar_por_deuda(session, clinica.id, d.id)
    assert all(c["estado"] == "pendiente" for c in cuotas)


async def test_listar_pago_parcial_cubre_en_cascada(session, clinica):
    # 3 cuotas de 100; pagado 150 → cuota1 pagada, cuota2 parcial, cuota3 pendiente
    d = await _deuda(session, clinica, total="300.00", pagado="150.00")
    await svc.generar(session, clinica_id=clinica.id, deuda_id=d.id, total="300.00", num_cuotas=3,
                      desde=date(2100, 1, 1))
    cuotas = await svc.listar_por_deuda(session, clinica.id, d.id)
    assert [c["estado"] for c in cuotas] == ["pagada", "parcial", "pendiente"]


async def test_listar_pago_total_todas_pagadas(session, clinica):
    d = await _deuda(session, clinica, total="300.00", pagado="300.00")
    await svc.generar(session, clinica_id=clinica.id, deuda_id=d.id, total="300.00", num_cuotas=3,
                      desde=date(2100, 1, 1))
    cuotas = await svc.listar_por_deuda(session, clinica.id, d.id)
    assert all(c["estado"] == "pagada" for c in cuotas)


async def test_listar_marca_vencida_si_venc_pasado_y_no_pagada(session, clinica):
    d = await _deuda(session, clinica, total="100.00", pagado="0.00")
    await svc.generar(session, clinica_id=clinica.id, deuda_id=d.id, total="100.00", num_cuotas=1,
                      desde=date(2020, 1, 1))  # venc en 2020 → vencida
    cuotas = await svc.listar_por_deuda(session, clinica.id, d.id)
    assert cuotas[0]["estado"] == "vencida"


# ── proximos_vencimientos ────────────────────────────────────────────────────

async def test_proximos_vencimientos_devuelve_primera_no_saldada(session, clinica):
    d = await _deuda(session, clinica, total="300.00", pagado="100.00")
    await svc.generar(session, clinica_id=clinica.id, deuda_id=d.id, total="300.00", num_cuotas=3,
                      desde=date(2100, 1, 1))
    prox = await svc.proximos_vencimientos(session, clinica.id, [d.id])
    # cuota1 pagada (100), la próxima es la 2
    assert prox[d.id]["vencimiento"] == "01/03/2100"
    assert prox[d.id]["estado"] == "pendiente"


async def test_proximos_vencimientos_vacio_sin_ids(session, clinica):
    assert await svc.proximos_vencimientos(session, clinica.id, []) == {}


# ── integración: la venta en cuotas genera el cronograma ─────────────────────

async def test_venta_en_cuotas_genera_cronograma(session, clinica, paciente):
    from sqlmodel import select
    from clinica_app.models.caja import CuotaDeuda, DeudaPaciente
    from clinica_app.services import cobro as cobro_svc

    await cobro_svc.crear(session, clinica.id, {
        "paciente_id": paciente.id,
        "items": [{"tipo": "servicio", "ref_id": 1, "nombre": "Tratamiento",
                   "cantidad": "1", "precio_unit": "600.00"}],
        "forma_pago": "efectivo",
        "descuento_global": "0",
        "es_cuotas": True, "num_cuotas": 3, "cuota_inicial": "0",
    })
    deuda = (await session.execute(
        select(DeudaPaciente).where(DeudaPaciente.paciente_id == paciente.id)
    )).scalars().first()
    assert deuda is not None
    cuotas = (await session.execute(
        select(CuotaDeuda).where(CuotaDeuda.deuda_id == deuda.id).order_by(CuotaDeuda.numero)
    )).scalars().all()
    assert len(cuotas) == 3
    assert sum(Decimal(str(c.monto)) for c in cuotas) == Decimal("600.00")


async def test_venta_con_anticipo_financia_solo_el_saldo(session, clinica, paciente):
    from sqlmodel import select
    from clinica_app.models.caja import CuotaDeuda, DeudaPaciente
    from clinica_app.services import cobro as cobro_svc

    await cobro_svc.crear(session, clinica.id, {
        "paciente_id": paciente.id,
        "items": [{"tipo": "servicio", "ref_id": 1, "nombre": "Tratamiento",
                   "cantidad": "1", "precio_unit": "600.00"}],
        "forma_pago": "efectivo",
        "descuento_global": "0",
        "es_cuotas": True, "num_cuotas": 3, "cuota_inicial": "150.00",
    })
    deuda = (await session.execute(
        select(DeudaPaciente).where(DeudaPaciente.paciente_id == paciente.id)
    )).scalars().first()
    cuotas = (await session.execute(
        select(CuotaDeuda).where(CuotaDeuda.deuda_id == deuda.id)
    )).scalars().all()
    # financia 600 - 150 = 450
    assert sum(Decimal(str(c.monto)) for c in cuotas) == Decimal("450.00")
