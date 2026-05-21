from __future__ import annotations

import asyncio

import reflex as rx

from clinica_app.services.reportes import encolar_reporte, estado_job
from clinica_app.state.base import BaseState


class ReportesState(BaseState):

    tipo_reporte: str  = "pacientes"
    fecha_desde:  str  = ""
    fecha_hasta:  str  = ""

    job_id:       str  = ""
    job_status:   str  = ""     # "queued" | "started" | "finished" | "failed"
    job_result:   str  = ""
    job_error:    str  = ""
    is_enqueuing: bool = False

    def on_mount(self):
        return self.require_auth()

    def set_tipo(self, v: str):
        self.tipo_reporte = v
        self.job_id       = ""
        self.job_status   = ""
        self.job_result   = ""
        self.job_error    = ""

    # ── Setters de formulario (Reflex 0.9.x no auto-genera setters en sub-states)
    def set_fecha_desde(self, v: str): self.fecha_desde = v
    def set_fecha_hasta(self, v: str): self.fecha_hasta = v

    async def generar_reporte(self):
        self.is_enqueuing = True
        self.job_id       = ""
        self.job_status   = "queued"
        self.job_error    = ""
        yield

        params: dict = {}
        if self.fecha_desde:
            params["desde"] = self.fecha_desde
        if self.fecha_hasta:
            params["hasta"] = self.fecha_hasta

        try:
            job_id = encolar_reporte(self.clinica_id, self.tipo_reporte, params)
        except Exception as exc:
            self.job_error    = f"Error al encolar: {exc}"
            self.job_status   = "failed"
            self.is_enqueuing = False
            return

        self.job_id       = job_id
        self.is_enqueuing = False

        # Polling hasta que el job termine (máx. 2 min, tick 3 seg)
        for _ in range(40):
            await asyncio.sleep(3)
            info = estado_job(self.job_id)
            self.job_status = info["status"]
            if info["status"] == "finished":
                self.job_result = info["result"] or ""
                break
            if info["status"] in ("failed", "not_found"):
                self.job_error = info["error"] or "Error desconocido"
                break
            yield

    @rx.var
    def reporte_listo(self) -> bool:
        return self.job_status == "finished"

    @rx.var
    def reporte_fallido(self) -> bool:
        return self.job_status == "failed"

    @rx.var
    def procesando(self) -> bool:
        return self.job_status in ("queued", "started")
