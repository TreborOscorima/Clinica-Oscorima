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


from clinica_app.models.turno import EstadoTurno, Turno


async def _servicio(session, clinica, nombre="Limpieza", precio="80", duracion=30):
    from clinica_app.models.servicio import Servicio
    s = Servicio(clinica_id=clinica.id, nombre=nombre, precio=Decimal(precio), duracion_min=duracion)
    session.add(s)
    await session.flush()
    return s


async def _profesional(session, clinica, nombres="Ana", apellidos="García"):
    from clinica_app.models.profesional import Profesional
    p = Profesional(clinica_id=clinica.id, nombres=nombres, apellidos=apellidos)
    session.add(p)
    await session.flush()
    return p


async def _turno(session, clinica, paciente, *, estado, servicio_id=None, profesional_id=None, dia=15):
    t = Turno(
        clinica_id=clinica.id, paciente_id=paciente.id,
        servicio_id=servicio_id, profesional_id=profesional_id,
        fecha_hora=datetime(2026, 3, dia, 10, 0), estado=estado, is_active=True,
    )
    session.add(t)
    await session.flush()
    return t


_RANGO = {"desde": "2026-03-01", "hasta": "2026-03-31"}


async def test_analiticas_sin_datos(session, clinica):
    data = await svc.analiticas(session, clinica.id, **_RANGO)
    assert data["resumen"]["total"] == 0
    assert data["resumen"]["produccion"] == "0.00"
    assert data["resumen"]["tasa_asistencia"] == "0.00"
    assert data["por_profesional"] == []
    assert data["por_servicio"] == []


async def test_analiticas_produccion_por_servicio(session, clinica, paciente):
    serv = await _servicio(session, clinica, nombre="Corona", precio="200")
    await _turno(session, clinica, paciente, estado=EstadoTurno.ATENDIDO, servicio_id=serv.id)
    await _turno(session, clinica, paciente, estado=EstadoTurno.ATENDIDO, servicio_id=serv.id)

    data = await svc.analiticas(session, clinica.id, **_RANGO)
    assert data["resumen"]["produccion"] == "400.00"
    assert data["por_servicio"][0]["nombre"] == "Corona"
    assert data["por_servicio"][0]["veces"] == 2
    assert data["por_servicio"][0]["produccion"] == "400.00"


async def test_analiticas_por_profesional_y_asistencia(session, clinica, paciente):
    serv = await _servicio(session, clinica, precio="100")
    prof = await _profesional(session, clinica)
    await _turno(session, clinica, paciente, estado=EstadoTurno.ATENDIDO, servicio_id=serv.id, profesional_id=prof.id)
    await _turno(session, clinica, paciente, estado=EstadoTurno.CANCELADO, servicio_id=serv.id, profesional_id=prof.id)

    data = await svc.analiticas(session, clinica.id, **_RANGO)
    fila = data["por_profesional"][0]
    assert fila["nombre"] == "Ana García"
    assert fila["total"] == 2
    assert fila["atendidos"] == 1
    assert fila["cancelados"] == 1
    assert fila["produccion"] == "100.00"
    assert fila["tasa_asistencia"] == "50.00"


async def test_analiticas_no_shows_y_tasas(session, clinica, paciente):
    serv = await _servicio(session, clinica, precio="50")
    await _turno(session, clinica, paciente, estado=EstadoTurno.ATENDIDO, servicio_id=serv.id)
    await _turno(session, clinica, paciente, estado=EstadoTurno.ATENDIDO, servicio_id=serv.id)
    await _turno(session, clinica, paciente, estado=EstadoTurno.CANCELADO, servicio_id=serv.id)
    await _turno(session, clinica, paciente, estado=EstadoTurno.PENDIENTE, servicio_id=serv.id)

    r = (await svc.analiticas(session, clinica.id, **_RANGO))["resumen"]
    assert r["total"] == 4
    assert r["atendidos"] == 2
    assert r["cancelados"] == 1
    assert r["pendientes"] == 1
    assert r["tasa_asistencia"] == "50.00"
    assert r["tasa_cancelacion"] == "25.00"


async def test_analiticas_horas_excluye_cancelados(session, clinica, paciente):
    serv = await _servicio(session, clinica, precio="50", duracion=60)
    await _turno(session, clinica, paciente, estado=EstadoTurno.ATENDIDO, servicio_id=serv.id)
    await _turno(session, clinica, paciente, estado=EstadoTurno.CANCELADO, servicio_id=serv.id)

    r = (await svc.analiticas(session, clinica.id, **_RANGO))["resumen"]
    # Solo el turno no cancelado (60 min = 1.00 h) cuenta para horas agendadas
    assert r["horas_agendadas"] == "1.00"


async def test_analiticas_usa_items_del_turno(session, clinica, paciente):
    from clinica_app.models.turno_servicio import TurnoServicio
    serv = await _servicio(session, clinica, precio="80")
    t = await _turno(session, clinica, paciente, estado=EstadoTurno.ATENDIDO, servicio_id=serv.id)
    # Ítem con precio propio (120) y cantidad 2, descuento 40 -> 200; ignora precio del servicio (80)
    session.add(TurnoServicio(turno_id=t.id, servicio_id=serv.id,
                              precio=Decimal("120"), cantidad=Decimal("2"), descuento=Decimal("40")))
    await session.flush()

    r = (await svc.analiticas(session, clinica.id, **_RANGO))["resumen"]
    assert r["produccion"] == "200.00"


async def test_analiticas_respeta_rango_de_fechas(session, clinica, paciente):
    serv = await _servicio(session, clinica, precio="90")
    await _turno(session, clinica, paciente, estado=EstadoTurno.ATENDIDO, servicio_id=serv.id, dia=15)

    # Rango que NO incluye marzo
    data = await svc.analiticas(session, clinica.id, desde="2026-04-01", hasta="2026-04-30")
    assert data["resumen"]["total"] == 0


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


def test_export_excel_produccion(tmp_path, monkeypatch):
    """El Excel de producción genera las 3 hojas usando la sesión sync."""
    import openpyxl

    import clinica_app.database as db
    import clinica_app.tasks.reportes as rep
    from clinica_app.models.profesional import Profesional
    from clinica_app.models.servicio import Servicio
    from clinica_app.models.turno import EstadoTurno, Turno

    eng = create_engine(f"sqlite:///{tmp_path / 'rep.db'}")
    SQLModel.metadata.create_all(eng)
    monkeypatch.setattr(db, "_sync_engine", eng)
    monkeypatch.setattr(rep, "REPORT_EXPORT_DIR", str(tmp_path))

    with db.get_session() as s:
        s.add(Servicio(id=1, clinica_id=1, nombre="Corona", precio=Decimal("200"), duracion_min=30))
        s.add(Profesional(id=1, clinica_id=1, nombres="Ana", apellidos="García"))
        s.flush()
        s.add(Turno(clinica_id=1, paciente_id=1, servicio_id=1, profesional_id=1,
                    fecha_hora=datetime(2026, 3, 15, 10, 0), estado=EstadoTurno.ATENDIDO, is_active=True))

    path = rep._reporte_produccion(1, {"desde": "2026-03-01", "hasta": "2026-03-31"})

    assert os.path.exists(path)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["Resumen", "Por Profesional", "Por Servicio"]
