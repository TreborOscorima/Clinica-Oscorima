from __future__ import annotations

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import historia_clinica as svc
from clinica_app.state.base import BaseState


class TimelineState(BaseState):
    """Línea de tiempo unificada del paciente (auditoría #6).

    Agrega en una sola vista cronológica todo lo que hoy vive repartido en
    varias pantallas. Es de sólo lectura: no crea ni edita datos.
    """

    # Paciente activo
    paciente_id:     int = 0
    paciente_nombre: str = ""

    # Eventos y conteos
    eventos: list[dict] = []
    conteos: dict[str, int] = {}
    total:   int = 0
    is_loading: bool = False

    # Filtro por tipo ("" = todos)
    filtro: str = ""

    # Selector de paciente (búsqueda server-side)
    pac_busqueda:   str = ""
    pac_resultados: list[dict] = []

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("historia"):
            yield rx.redirect("/")
            return
        pid_str = self.router.url.query_parameters.get("paciente_id", "")
        if pid_str:
            try:
                self.paciente_id = int(pid_str)
            except (ValueError, TypeError):
                return
            await self._cargar_nombre_paciente()
            async for s in self.cargar():
                yield s

    # ── Carga ────────────────────────────────────────────────────────────────

    async def _cargar_nombre_paciente(self):
        from sqlmodel import select

        from clinica_app.models.paciente import Paciente
        async with get_async_session() as session:
            p = (await session.execute(
                select(Paciente).where(
                    Paciente.id == self.paciente_id,
                    Paciente.clinica_id == self.clinica_id,
                )
            )).scalars().first()
            self.paciente_nombre = p.nombre if p else ""

    async def cargar(self):
        if not self.paciente_id:
            self.eventos, self.conteos, self.total = [], {}, 0
            return
        self.is_loading = True
        yield
        async with get_async_session() as session:
            data = await svc.timeline(
                session, self.clinica_id, self.paciente_id,
                sede_id=self.sede_actual_id,
            )
        self.eventos = data["eventos"]
        self.conteos = data["conteos"]
        self.total   = data["total"]
        self.is_loading = False

    @rx.var
    def tipos_cat(self) -> list[dict]:
        # El conteo va embebido en cada item para que la UI lo lea como campo
        # directo (indexar un dict Var por otra Var no está soportado en Reflex).
        return [{**t, "conteo": self.conteos.get(t["key"], 0)} for t in svc.TIPOS]

    @rx.var
    def eventos_filtrados(self) -> list[dict]:
        if not self.filtro:
            return self.eventos
        return [e for e in self.eventos if e["tipo"] == self.filtro]

    @rx.var
    def hay_eventos(self) -> bool:
        return len(self.eventos_filtrados) > 0

    def set_filtro(self, tipo: str):
        # Toggle: volver a tocar el filtro activo lo limpia.
        self.filtro = "" if self.filtro == tipo else tipo

    # ── Selector de paciente ─────────────────────────────────────────────────

    async def set_pac_busqueda(self, v: str):
        self.pac_busqueda = v
        if len(v) >= 2:
            from sqlalchemy import String, cast, or_
            from sqlmodel import select

            from clinica_app.models.paciente import Paciente
            like = f"%{v}%"
            async with get_async_session() as session:
                q = select(Paciente).where(
                    Paciente.clinica_id == self.clinica_id,
                    Paciente.is_active.is_(True),
                    or_(
                        Paciente.nombre.ilike(like),
                        cast(Paciente.documento, String).ilike(like),
                    ),
                )
                if self.sede_actual_id:
                    q = q.where(Paciente.sede_id == self.sede_actual_id)
                pacs = (await session.execute(q.limit(8))).scalars().all()
            self.pac_resultados = [
                {"id": str(p.id), "nombre": p.nombre, "documento": p.documento or ""}
                for p in pacs
            ]
        else:
            self.pac_resultados = []

    async def seleccionar_paciente(self, pac_id: str, pac_nombre: str):
        self.paciente_id     = int(pac_id)
        self.paciente_nombre = pac_nombre
        self.pac_busqueda    = ""
        self.pac_resultados  = []
        self.filtro          = ""
        async for s in self.cargar():
            yield s
