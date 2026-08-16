"""Tests de observabilidad: formateo JSON, setup idempotente y la línea
estructurada que emite la auditoría por cada acción de negocio."""
from __future__ import annotations

import json
import logging

from clinica_app import logging_config as lc


def _record(**extra) -> logging.LogRecord:
    rec = logging.LogRecord(
        name="clinica.test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hola %s", args=("mundo",), exc_info=None,
    )
    for k, v in extra.items():
        setattr(rec, k, v)
    return rec


def test_json_formatter_campos_base_y_extra():
    fmt = lc.JsonFormatter()
    out = fmt.format(_record(clinica_id=7, entidad="compra", entidad_id=42))
    data = json.loads(out)   # debe ser JSON válido
    assert data["level"] == "INFO"
    assert data["logger"] == "clinica.test"
    assert data["msg"] == "hola mundo"          # el %-format se resuelve
    assert "ts" in data
    # Los campos `extra` salen como claves de primer nivel.
    assert data["clinica_id"] == 7
    assert data["entidad"] == "compra"
    assert data["entidad_id"] == 42


def test_json_formatter_incluye_excepcion():
    fmt = lc.JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        rec = _record()
        rec.exc_info = sys.exc_info()
    data = json.loads(fmt.format(rec))
    assert "boom" in data["exc"]


def test_setup_logging_idempotente(monkeypatch):
    root = logging.getLogger()
    handlers_previos = list(root.handlers)
    flag_previo = getattr(root, "_clinica_configurado", False)
    try:
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.delenv("LOG_JSON", raising=False)
        lc.setup_logging(force=True)
        n1 = len(root.handlers)
        assert root.level == logging.WARNING
        lc.setup_logging()          # 2ª vez sin force → no agrega handlers
        assert len(root.handlers) == n1
    finally:
        root.handlers = handlers_previos
        root._clinica_configurado = flag_previo  # type: ignore[attr-defined]
        root.setLevel(logging.WARNING)


def test_quiere_json_por_env(monkeypatch):
    monkeypatch.setenv("LOG_JSON", "true")
    assert lc._quiere_json() is True
    monkeypatch.setenv("LOG_JSON", "false")
    assert lc._quiere_json() is False
    monkeypatch.delenv("LOG_JSON", raising=False)
    monkeypatch.setenv("ENV", "prod")           # sin override → prod = JSON
    assert lc._quiere_json() is True


async def test_auditoria_emite_linea_estructurada(session, clinica, caplog):
    """`auditoria.registrar` loguea una línea con el contexto de la acción."""
    from clinica_app.services import auditoria

    with caplog.at_level(logging.INFO, logger="clinica.audit"):
        await auditoria.registrar(
            session, clinica.id,
            usuario_id=3, accion="anular", entidad="compra", entidad_id=99,
        )

    audit = [r for r in caplog.records if r.name == "clinica.audit"]
    assert len(audit) == 1
    rec = audit[0]
    assert rec.accion == "anular"
    assert rec.entidad == "compra"
    assert rec.entidad_id == 99
    assert rec.clinica_id == clinica.id
    assert rec.usuario_id == 3
