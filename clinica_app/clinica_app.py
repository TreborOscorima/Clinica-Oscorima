"""
clinica_app/clinica_app.py — Punto de entrada de la aplicación Reflex.

Arrancar en desarrollo:
    reflex run

Arrancar en producción:
    reflex run --env prod
"""
import os

import reflex as rx
from sqlmodel import SQLModel
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse

from clinica_app.config import REPORT_EXPORT_DIR
from clinica_app.database import _engine
import clinica_app.models  # noqa: F401 — registra todos los modelos antes del create_all

# Crea las tablas que no existen (no toca las existentes)
SQLModel.metadata.create_all(_engine)

from clinica_app.pages.login          import login_page
from clinica_app.pages.dashboard      import dashboard_page
from clinica_app.pages.pacientes      import pacientes_page
from clinica_app.pages.profesionales  import profesionales_page
from clinica_app.pages.turnos         import turnos_page
from clinica_app.pages.servicios      import servicios_page
from clinica_app.pages.cobro          import cobro_page
from clinica_app.pages.caja           import caja_page
from clinica_app.pages.inventario     import inventario_page
from clinica_app.pages.reportes       import reportes_page
from clinica_app.pages.configuracion  import configuracion_page
from clinica_app.pages.cuentas        import cuentas_page
from clinica_app.pages.compras        import compras_page
from clinica_app.pages.promociones    import promociones_page


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    style={
        "font_family": "Inter, sans-serif",
        "background_color": "#f9fafb",
    },
)

# ── Rutas públicas ────────────────────────────────────────────────────────────
app.add_page(login_page, route="/login")

# ── Módulo Gestión ────────────────────────────────────────────────────────────
app.add_page(dashboard_page,     route="/")
app.add_page(pacientes_page,     route="/pacientes")
app.add_page(profesionales_page, route="/profesionales")
app.add_page(turnos_page,        route="/turnos")
app.add_page(servicios_page,     route="/servicios")

# ── Módulo Operaciones ────────────────────────────────────────────────────────
app.add_page(cobro_page,         route="/cobro")
app.add_page(caja_page,          route="/caja")
app.add_page(inventario_page,    route="/inventario")
app.add_page(reportes_page,      route="/reportes")

# ── Admin ─────────────────────────────────────────────────────────────────────
app.add_page(configuracion_page, route="/configuracion")

app.add_page(cuentas_page,   route="/cuentas")
app.add_page(compras_page,       route="/compras")
app.add_page(promociones_page,   route="/promociones")
# app.add_page(promociones_page, route="/promociones")


async def _health_check(request: Request) -> JSONResponse:
    """Health check para AWS ALB / ECS."""
    return JSONResponse({"status": "ok"})


async def _descargar_reporte(request: Request) -> FileResponse | JSONResponse:
    filename = os.path.basename(request.path_params.get("filename", ""))
    if not filename:
        return JSONResponse({"error": "not found"}, status_code=404)
    path = os.path.join(REPORT_EXPORT_DIR, filename)
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


app._api.add_route("/health", _health_check)
app._api.add_route("/api/reportes/descargar/{filename}", _descargar_reporte)
