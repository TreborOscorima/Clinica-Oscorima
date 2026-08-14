from __future__ import annotations

import asyncio

import reflex as rx

from clinica_app.database import get_async_session
from clinica_app.services import reportes as svc
from clinica_app.state.base import BaseState


class ReportesState(BaseState):

    # ── Selector ───────────────────────────────────────────────────────────────
    tipo_reporte: str = "pacientes"
    fecha_desde:  str = ""
    fecha_hasta:  str = ""

    # ── KPIs del mes ──────────────────────────────────────────────────────────
    kpi_ingresos:         str = "0.00"
    kpi_egresos:          str = "0.00"
    kpi_turnos:           str = "0"
    kpi_pacientes_nuevos: str = "0"

    # ── Analíticas ampliadas ──────────────────────────────────────────────────
    ana_desde:       str = ""
    ana_hasta:       str = ""
    ana_loading:     bool = False
    ana_total:       str = "0"
    ana_atendidos:   str = "0"
    ana_cancelados:  str = "0"
    ana_asistencia:  str = "0.00"
    ana_cancelacion: str = "0.00"
    ana_horas:       str = "0.00"
    ana_produccion:  str = "0.00"
    ana_por_profesional: list[dict] = []
    ana_por_servicio:    list[dict] = []

    # ── Estado de generación ──────────────────────────────────────────────────
    is_generating: bool = False
    is_loading:    bool = False
    archivo:       str  = ""
    gen_error:     str  = ""

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("reportes"):
            yield rx.redirect("/")
            return
        async for s in self._cargar_kpis():
            yield s
        async for s in self.cargar_analiticas():
            yield s

    async def _cargar_kpis(self):
        self.is_loading = True
        yield
        try:
            async with get_async_session() as session:
                kpis = await svc.kpis_mes(session, self.clinica_id, sede_id=self.sede_actual_id)
            self.kpi_ingresos         = kpis["ingresos"]
            self.kpi_egresos          = kpis["egresos"]
            self.kpi_turnos           = str(kpis["turnos"])
            self.kpi_pacientes_nuevos = str(kpis["pacientes_nuevos"])
        except Exception:
            pass
        self.is_loading = False

    # ── Setters ────────────────────────────────────────────────────────────────

    def set_tipo(self, v: str):
        self.tipo_reporte = v
        self.archivo      = ""
        self.gen_error    = ""

    def set_fecha_desde(self, v: str): self.fecha_desde = v
    def set_fecha_hasta(self, v: str): self.fecha_hasta = v

    def set_ana_desde(self, v: str): self.ana_desde = v
    def set_ana_hasta(self, v: str): self.ana_hasta = v

    # ── Analíticas ampliadas ──────────────────────────────────────────────────

    async def cargar_analiticas(self):
        self.ana_loading = True
        yield
        try:
            async with get_async_session() as session:
                data = await svc.analiticas(
                    session, self.clinica_id,
                    desde=self.ana_desde or None, hasta=self.ana_hasta or None,
                    sede_id=self.sede_actual_id,
                )
            r = data["resumen"]
            self.ana_total           = str(r["total"])
            self.ana_atendidos       = str(r["atendidos"])
            self.ana_cancelados      = str(r["cancelados"])
            self.ana_asistencia      = r["tasa_asistencia"]
            self.ana_cancelacion     = r["tasa_cancelacion"]
            self.ana_horas           = r["horas_agendadas"]
            self.ana_produccion      = r["produccion"]
            self.ana_por_profesional = data["por_profesional"]
            self.ana_por_servicio    = data["por_servicio"]
            # Si no había rango, refleja el mes en curso que aplicó el servicio
            if not self.ana_desde:
                self.ana_desde = data.get("desde", "")
        except Exception:
            pass
        self.ana_loading = False

    # ── Generar ────────────────────────────────────────────────────────────────

    async def generar_reporte(self):
        self.is_generating = True
        self.archivo       = ""
        self.gen_error     = ""
        yield

        params: dict = {}
        if self.fecha_desde:
            params["desde"] = self.fecha_desde
        if self.fecha_hasta:
            params["hasta"] = self.fecha_hasta

        try:
            filename = await asyncio.to_thread(svc.generar_reporte, self.clinica_id, self.tipo_reporte, params, sede_id=self.sede_actual_id)
            self.archivo = filename
        except Exception as exc:
            self.gen_error = str(exc)
        finally:
            self.is_generating = False

    # ── Computed vars ──────────────────────────────────────────────────────────

    @rx.var(cache=False)
    def archivo_url(self) -> str:
        from clinica_app.services.download_token import crear_token
        token = crear_token(self.user_id, self.clinica_id)
        return f"/api/reportes/descargar/{self.archivo}?token={token}"

    @rx.var
    def reporte_listo(self) -> bool:
        return self.archivo != ""

    @rx.var
    def reporte_fallido(self) -> bool:
        return self.gen_error != ""

    @rx.var
    def mostrar_fechas(self) -> bool:
        return (
            (self.tipo_reporte == "caja")
            | (self.tipo_reporte == "turnos")
            | (self.tipo_reporte == "compras")
            | (self.tipo_reporte == "produccion")
        )
