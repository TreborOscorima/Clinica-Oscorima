"""Tests del servicio de salud del sistema y de la integración Sentry (no-op)."""
from __future__ import annotations

from clinica_app.services import salud
from clinica_app import sentry_config


# ── salud: chequeos individuales ────────────────────────────────────────────────

def test_estado_disco_estructura():
    d = salud.estado_disco(".")
    assert d["ok"] is True or d["ok"] is False
    for k in ("total_gb", "usado_gb", "libre_gb", "pct_usado"):
        assert k in d
    assert 0 <= d["pct_usado"] <= 100


def test_uptime_positivo():
    up = salud.uptime()
    assert up["segundos"] >= 0
    assert isinstance(up["texto"], str) and up["texto"]


def test_backups_sin_configurar(monkeypatch):
    monkeypatch.setattr(salud, "BACKUP_DIR", "")
    b = salud.estado_backups()
    assert b["configurado"] is False
    assert b["ok"] is True   # no configurado != fallo


def test_backups_dir_inexistente(monkeypatch):
    monkeypatch.setattr(salud, "BACKUP_DIR", "/no/existe/backups/xyz")
    b = salud.estado_backups()
    assert b["configurado"] is True
    assert b["ok"] is False


def test_backups_al_dia(tmp_path, monkeypatch):
    dump = tmp_path / "life_db_2026-08-16.sql"
    dump.write_text("-- dump")
    monkeypatch.setattr(salud, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(salud, "BACKUP_MAX_AGE_HOURS", 26)
    b = salud.estado_backups()
    assert b["configurado"] is True
    assert b["ok"] is True
    assert b["ultimo"] == "life_db_2026-08-16.sql"
    assert b["edad_horas"] < 1


async def test_estado_db_ok(session):
    d = await salud.estado_db(session)
    assert d["ok"] is True
    assert "latencia_ms" in d


async def test_estado_sistema_agrega(session, monkeypatch):
    monkeypatch.setattr(salud, "BACKUP_DIR", "")   # sin backups -> no degrada
    est = await salud.estado_sistema(session)
    assert est["status"] == "ok"
    assert est["db"]["ok"] is True
    for k in ("db", "disco", "uptime", "backups", "ts"):
        assert k in est


async def test_estado_sistema_degrada_si_db_falla(session, monkeypatch):
    async def _falla(_s):
        return {"ok": False, "error": "boom"}
    monkeypatch.setattr(salud, "estado_db", _falla)
    monkeypatch.setattr(salud, "BACKUP_DIR", "")
    est = await salud.estado_sistema(session)
    assert est["status"] == "degraded"


# ── Sentry: no-op sin DSN ───────────────────────────────────────────────────────

def test_init_sentry_sin_dsn(monkeypatch):
    monkeypatch.setattr(sentry_config, "SENTRY_DSN", "")
    monkeypatch.setattr(sentry_config, "_inicializado", False)
    assert sentry_config.init_sentry() is False
