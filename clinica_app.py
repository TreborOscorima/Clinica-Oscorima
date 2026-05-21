"""
clinica_app.py — Punto de entrada de la aplicación Reflex.

Arrancar en desarrollo:
    reflex run

Arrancar en producción:
    reflex run --env prod
"""
import reflex as rx
from fastapi.responses import JSONResponse

from clinica_app.pages.login      import login_page
from clinica_app.pages.dashboard  import dashboard_page
from clinica_app.pages.pacientes  import pacientes_page
from clinica_app.pages.turnos     import turnos_page
from clinica_app.pages.caja       import caja_page
from clinica_app.pages.inventario import inventario_page
from clinica_app.pages.reportes       import reportes_page
from clinica_app.pages.configuracion  import configuracion_page


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    style={
        "font_family": "Inter, sans-serif",
        "background_color": "#f9fafb",
    },
)

app.add_page(login_page,     route="/login")
app.add_page(dashboard_page, route="/")
app.add_page(pacientes_page, route="/pacientes")
app.add_page(turnos_page,    route="/turnos")
app.add_page(caja_page,      route="/caja")
app.add_page(inventario_page, route="/inventario")
app.add_page(reportes_page,      route="/reportes")
app.add_page(configuracion_page, route="/configuracion")


@app.api.get("/health")
async def health_check():
    """Health check para AWS ALB / ECS. Retorna 200 si el backend está vivo."""
    return JSONResponse({"status": "ok"})
