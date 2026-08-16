"""Tests del worker de recordatorios de turnos y del scheduler.

`enviar_recordatorios` usa el engine SÍNCRONO (`_sync_engine`), igual que las
tareas de reportes → se testea apuntando `recordatorios._engine` a un SQLite
temporal y monkeypatcheando el envío real de notificaciones.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select


def _setup(tmp_path, monkeypatch, fake_resultado):
    """Prepara un engine SQLite temporal + fake de notificaciones. Devuelve el
    módulo recordatorios ya monkeypatcheado y el engine."""
    import clinica_app.tasks.recordatorios as rec

    eng = create_engine(f"sqlite:///{tmp_path / 'rec.db'}")
    SQLModel.metadata.create_all(eng)
    monkeypatch.setattr(rec, "_engine", eng)

    llamadas: list[dict] = []

    def fake_notificar(turno, paciente_email="", paciente_tel=""):
        llamadas.append({"email": paciente_email, "tel": paciente_tel})
        return dict(fake_resultado)

    monkeypatch.setattr(rec.notif, "notificar_recordatorio", fake_notificar)
    return rec, eng, llamadas


def _seed_turno(eng, *, horas_adelante=24, email="ana@mail.com", tel="+51999",
                estado=None):
    from clinica_app.models.paciente import Paciente
    from clinica_app.models.turno import EstadoTurno, Turno

    fecha = datetime.now(timezone.utc) + timedelta(hours=horas_adelante)
    with Session(eng) as s:
        p = Paciente(clinica_id=1, nombre="Ana", documento="1",
                     email=email, telefono=tel, is_active=True)
        s.add(p)
        s.flush()
        t = Turno(clinica_id=1, paciente_id=p.id, fecha_hora=fecha,
                  estado=estado or EstadoTurno.CONFIRMADO, is_active=True)
        s.add(t)
        s.commit()
        return t.id


def _recordatorios(eng, turno_id):
    from clinica_app.models.recordatorio_turno import RecordatorioTurno
    with Session(eng) as s:
        return s.exec(
            select(RecordatorioTurno).where(RecordatorioTurno.turno_id == turno_id)
        ).all()


def test_envia_y_registra_ambos_canales(tmp_path, monkeypatch):
    rec, eng, llamadas = _setup(tmp_path, monkeypatch, {"email": True, "whatsapp": True})
    turno_id = _seed_turno(eng)

    resumen = rec.enviar_recordatorios()

    assert resumen["turnos"] == 1
    assert resumen["recordados"] == 1
    assert resumen["omitidos"] == 0
    assert resumen["canales_ok"] == 2
    assert resumen["canales_fallidos"] == 0
    assert len(llamadas) == 1 and llamadas[0]["email"] == "ana@mail.com"

    filas = _recordatorios(eng, turno_id)
    assert {f.canal for f in filas} == {"email", "whatsapp"}
    assert all(f.estado == "enviado" for f in filas)
    destinos = {f.canal: f.destino for f in filas}
    assert destinos["email"] == "ana@mail.com" and destinos["whatsapp"] == "+51999"


def test_idempotente_no_reenvia(tmp_path, monkeypatch):
    """Correr dos veces no vuelve a notificar un turno ya recordado."""
    rec, eng, llamadas = _setup(tmp_path, monkeypatch, {"email": True})
    _seed_turno(eng)

    r1 = rec.enviar_recordatorios()
    r2 = rec.enviar_recordatorios()

    assert r1["recordados"] == 1
    assert r2["recordados"] == 0
    assert r2["omitidos"] == 1
    # El proveedor se llamó una sola vez en total (la 2ª corrida saltea).
    assert len(llamadas) == 1


def test_fallo_se_registra_y_se_reintenta(tmp_path, monkeypatch):
    """Un envío fallido queda como FALLIDO y NO bloquea el reintento siguiente."""
    rec, eng, _ = _setup(tmp_path, monkeypatch, {"email": False})
    turno_id = _seed_turno(eng, tel="")

    r1 = rec.enviar_recordatorios()
    assert r1["recordados"] == 0
    assert r1["canales_fallidos"] == 1
    filas = _recordatorios(eng, turno_id)
    assert len(filas) == 1 and filas[0].estado == "fallido"

    # Segunda corrida: ahora el proveedor acepta → se reintenta y queda enviado.
    monkeypatch.setattr(rec.notif, "notificar_recordatorio",
                        lambda *a, **k: {"email": True})
    r2 = rec.enviar_recordatorios()
    assert r2["recordados"] == 1
    assert r2["omitidos"] == 0
    estados = {f.estado for f in _recordatorios(eng, turno_id)}
    assert "enviado" in estados


def test_turno_fuera_de_ventana_se_ignora(tmp_path, monkeypatch):
    rec, eng, llamadas = _setup(tmp_path, monkeypatch, {"email": True})
    _seed_turno(eng, horas_adelante=50)   # fuera de [20, 28] h

    resumen = rec.enviar_recordatorios()
    assert resumen["turnos"] == 0
    assert resumen["recordados"] == 0
    assert llamadas == []


def test_turno_cancelado_no_se_recuerda(tmp_path, monkeypatch):
    from clinica_app.models.turno import EstadoTurno
    rec, eng, _ = _setup(tmp_path, monkeypatch, {"email": True})
    _seed_turno(eng, estado=EstadoTurno.CANCELADO)

    resumen = rec.enviar_recordatorios()
    assert resumen["turnos"] == 0


# ── notificar_recordatorio: gating por canal ────────────────────────────────────

def test_notificar_recordatorio_sin_canales_habilitados_devuelve_vacio():
    """Con NOTIF_* deshabilitado (default de test) no hay intento de envío."""
    from clinica_app.services import notificaciones as notif
    res = notif.notificar_recordatorio({"fecha_hora": "x"},
                                       paciente_email="a@b.com", paciente_tel="+51")
    assert res == {}


def test_notificar_recordatorio_email_habilitado(monkeypatch):
    from clinica_app.services import notificaciones as notif
    monkeypatch.setattr(notif, "NOTIF_EMAIL_ENABLED", True)
    monkeypatch.setattr(notif, "send_email", lambda *a, **k: True)
    res = notif.notificar_recordatorio({"fecha_hora": "x"}, paciente_email="a@b.com")
    assert res == {"email": True}


# ── scheduler: helpers puros ────────────────────────────────────────────────────

def test_scheduler_hora_minuto_valida_y_fallback():
    from clinica_app.tasks import scheduler as sch
    assert sch._hora_minuto("08:30") == (8, 30)
    assert sch._hora_minuto("25:00") == (18, 0)   # inválida → fallback
    assert sch._hora_minuto("basura") == (18, 0)


def test_scheduler_proximo_disparo_hoy_y_manana():
    # Aritmética pura sobre un datetime aware; usa UTC para no depender de la
    # base de zonas horarias (tzdata) en el entorno de test.
    from clinica_app.tasks import scheduler as sch

    tz = timezone.utc
    ahora = datetime(2026, 8, 16, 10, 0, tzinfo=tz)
    # 18:00 de hoy aún no pasó → mismo día
    assert sch._proximo_disparo(ahora, 18, 0) == datetime(2026, 8, 16, 18, 0, tzinfo=tz)
    # 09:00 ya pasó → mañana
    assert sch._proximo_disparo(ahora, 9, 0) == datetime(2026, 8, 17, 9, 0, tzinfo=tz)
