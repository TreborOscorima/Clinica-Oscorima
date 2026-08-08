from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import auditoria as svc
from clinica_app.state.base import BaseState


class AuditoriaState(BaseState):
    """Visor de la bitácora de auditoría (solo lectura, admin)."""

    registros:   list[dict] = []
    total:       int        = 0
    total_pages: int        = 1
    page:        int        = 1
    per_page:    int        = 30
    is_loading:  bool       = False

    # Filtros
    filtro_accion:  str = ""
    filtro_entidad: str = ""

    # ── Ciclo de vida ──────────────────────────────────────────────────────────
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
        async with get_async_session() as session:
            result = await svc.listar(
                session,
                self.clinica_id,
                accion=self.filtro_accion,
                entidad=self.filtro_entidad,
                page=self.page,
                per_page=self.per_page,
            )
        self.registros   = result["data"]
        self.total       = result["total"]
        self.total_pages = result["pages"]
        self.is_loading  = False

    # ── Filtros ────────────────────────────────────────────────────────────────
    async def set_filtro_accion(self, v: str):
        self.filtro_accion = v
        self.page = 1
        async for s in self.cargar():
            yield s

    async def set_filtro_entidad(self, v: str):
        self.filtro_entidad = v
        self.page = 1
        async for s in self.cargar():
            yield s

    async def limpiar_filtros(self):
        self.filtro_accion = ""
        self.filtro_entidad = ""
        self.page = 1
        async for s in self.cargar():
            yield s

    # ── Paginación ─────────────────────────────────────────────────────────────
    async def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            async for s in self.cargar():
                yield s

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            async for s in self.cargar():
                yield s
