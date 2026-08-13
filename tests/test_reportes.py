"""Tests del servicio de reportes (KPIs del mes en curso)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlmodel import SQLModel

from clinica_app.services import caja as caja_svc
from clinica_app.services import reportes as svc
from clinica_app.services import turnos as turnos_svc


async def test_kpis_mes_sin_datos(session, clinica):
    kpis = await svc.kpis_mes(session, clinica.id)
    assert Decimal(kpis["ingresos"]) == Decimal("0.00")
    assert Decimal(kpis["egresos"]) == Decimal("0.00")
    assert kpis["turnos"] == 0
    assert kpis["pacientes_nuevos"] == 0


async def test_kpis_mes_agrega_ingresos_y_egresos(session, clinica):
    await caja_svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "100"})
    await caja_svc.registrar_movimiento(session, clinica.id, {"tipo": "ingreso", "monto": "50"})
    await caja_svc.registrar_movimiento(session, clinica.id, {"tipo": "egreso", "monto": "40"})

    kpis = await svc.kpis_mes(session, clinica.id)
    assert Decimal(kpis["ingresos"]) == Decimal("150.00")
    assert Decimal(kpis["egresos"]) == Decimal("40.00")


async def test_kpis_mes_cuenta_pacientes_nuevos(session, clinica, paciente):
    kpis = await svc.kpis_mes(session, clinica.id)
    assert kpis["pacientes_nuevos"] == 1


async def test_kpis_mes_cuenta_turnos_del_mes(session, clinica, paciente):
    ahora = datetime.now(timezone.utc).replace(tzinfo=None, second=0, microsecond=0).isoformat()
    await turnos_svc.crear(session, clinica.id, {"paciente_id": paciente.id, "fecha_hora": ahora})

    kpis = await svc.kpis_mes(session, clinica.id)
    assert kpis["turnos"] == 1


def test_export_excel_no_detached_instance(tmp_path, monkeypatch):
    """Regresión: la exportación a Excel usa la sesión sync `get_session()`.

    Sin `expire_on_commit=False`, al salir del `with get_session()` el commit
    expira los objetos y el `for p in rows` posterior en tasks/reportes.py
    disparaba `DetachedInstanceError`. Este test ejecuta el generador real
    apuntando el engine sync a un SQLite temporal.
    """
    import clinica_app.database as db
    import clinica_app.tasks.reportes as rep
    from clinica_app.models.paciente import Paciente

    eng = create_engine(f"sqlite:///{tmp_path / 'rep.db'}")
    SQLModel.metadata.create_all(eng)
    monkeypatch.setattr(db, "_sync_engine", eng)
    monkeypatch.setattr(rep, "REPORT_EXPORT_DIR", str(tmp_path))

    with db.get_session() as s:
        s.add(Paciente(clinica_id=1, nombre="Ana", documento="1", is_active=True))

    path = rep._reporte_pacientes(1, {})  # sin el fix -> DetachedInstanceError

    assert path.endswith(".xlsx")
    assert os.path.exists(path)
