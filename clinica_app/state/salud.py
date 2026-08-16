from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import salud as svc
from clinica_app.state.base import BaseState


class SaludState(BaseState):
    """Dashboard de salud del sistema (solo lectura, admin)."""

    estado:     dict = {}
    is_loading: bool = False

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("auditoria"):
            yield rx.redirect("/")
            return
        async for s in self.cargar():
            yield s

    async def cargar(self):
        self.is_loading = True
        yield
        try:
            async with get_async_session() as session:
                self.estado = await svc.estado_sistema(session)
        except Exception:
            self.estado = {"status": "degraded", "db": {"ok": False}}
        self.is_loading = False

    @rx.var
    def status(self) -> str:
        return self.estado.get("status", "")

    @rx.var
    def db_ok(self) -> bool:
        return bool(self.estado.get("db", {}).get("ok", False))

    @rx.var
    def db_latencia(self) -> str:
        ms = self.estado.get("db", {}).get("latencia_ms")
        return f"{ms} ms" if ms is not None else "—"

    @rx.var
    def disco_pct(self) -> float:
        return float(self.estado.get("disco", {}).get("pct_usado", 0) or 0)

    @rx.var
    def disco_texto(self) -> str:
        d = self.estado.get("disco", {})
        if "libre_gb" not in d:
            return "—"
        return f"{d.get('libre_gb', 0)} GB libres de {d.get('total_gb', 0)} GB"

    @rx.var
    def disco_ok(self) -> bool:
        return bool(self.estado.get("disco", {}).get("ok", True))

    @rx.var
    def uptime_texto(self) -> str:
        return self.estado.get("uptime", {}).get("texto", "—")

    @rx.var
    def backups_configurado(self) -> bool:
        return bool(self.estado.get("backups", {}).get("configurado", False))

    @rx.var
    def backups_ok(self) -> bool:
        return bool(self.estado.get("backups", {}).get("ok", True))

    @rx.var
    def backups_texto(self) -> str:
        b = self.estado.get("backups", {})
        if not b.get("configurado", False):
            return "Sin configurar"
        if b.get("error"):
            return str(b["error"])
        edad = b.get("edad_horas")
        ultimo = b.get("ultimo", "")
        return f"Último: {ultimo} (hace {edad} h)" if edad is not None else "—"
