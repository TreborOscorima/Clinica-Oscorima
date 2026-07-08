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
from clinica_app.database import get_async_session as _get_async_session
from clinica_app.database import _sync_engine as _engine
import clinica_app.models  # noqa: F401 — registra todos los modelos antes del create_all

# Crea las tablas que no existen (no toca las existentes)
SQLModel.metadata.create_all(_engine)


def _migrate_columns() -> None:
    """Agrega columnas nuevas a tablas existentes sin romper datos. Seguro de re-ejecutar."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    def _add(conn, table: str, col: str, definition: str) -> None:
        try:
            conn.execute(text(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {definition}"))
        except OperationalError as exc:
            if "Duplicate column name" in str(exc) or "1060" in str(exc):
                pass
            else:
                raise

    with _engine.connect() as conn:
        # Nuevas columnas en `clinicas`
        _add(conn, "clinicas", "direccion_fiscal",        "VARCHAR(240) NULL")
        _add(conn, "clinicas", "zona_horaria",            "VARCHAR(80) NULL")
        _add(conn, "clinicas", "rubro",                   "VARCHAR(80) NULL")
        _add(conn, "clinicas", "mensaje_recibo",          "VARCHAR(240) NULL")
        _add(conn, "clinicas", "papel_impresion",         "VARCHAR(20) NULL DEFAULT '80mm'")
        _add(conn, "clinicas", "ancho_recibo",            "INT NULL")
        _add(conn, "clinicas", "margen_global",           "DOUBLE NOT NULL DEFAULT 50.0")
        _add(conn, "clinicas", "mostrar_impuesto_recibo", "TINYINT(1) NOT NULL DEFAULT 0")
        # Nuevas columnas en `sedes`
        _add(conn, "sedes", "margen_local", "DOUBLE NULL")
        conn.commit()


_migrate_columns()

from clinica_app.pages.login             import login_page
from clinica_app.pages.dashboard         import dashboard_page
from clinica_app.pages.pacientes         import pacientes_page
from clinica_app.pages.profesionales     import profesionales_page
from clinica_app.pages.turnos            import turnos_page
from clinica_app.pages.servicios         import servicios_page
from clinica_app.pages.cobro             import cobro_page
from clinica_app.pages.caja              import caja_page
from clinica_app.pages.inventario        import inventario_page
from clinica_app.pages.reportes          import reportes_page
from clinica_app.pages.configuracion     import configuracion_page
from clinica_app.pages.cuentas           import cuentas_page
from clinica_app.pages.compras           import compras_page
from clinica_app.pages.promociones       import promociones_page
from clinica_app.pages.notas_clinicas    import notas_clinicas_page
from clinica_app.pages.calendario        import calendario_page


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

app.add_page(cuentas_page,        route="/cuentas")
app.add_page(compras_page,        route="/compras")
app.add_page(promociones_page,    route="/promociones")
app.add_page(notas_clinicas_page, route="/historia-clinica")
app.add_page(calendario_page,     route="/calendario")


async def _health_check(request: Request) -> JSONResponse:
    """Health check para AWS ALB / ECS."""
    return JSONResponse({"status": "ok"})


async def _api_ping(request: Request) -> JSONResponse:
    """Ping liviano — usado por el HEALTHCHECK del contenedor Docker."""
    return JSONResponse({"status": "ok"})


async def _api_health(request: Request) -> JSONResponse:
    """Health con identidad de app — usado por deploy-prod.sh vía NPM."""
    return JSONResponse({"status": "ok", "app": "waykisac-clinica"})


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


async def _generar_pdf_recibo(request: Request) -> FileResponse | JSONResponse:
    """Genera y descarga el PDF de un comprobante. ?comp_id=X&clinica_id=Y"""
    try:
        comp_id   = int(request.query_params.get("comp_id", 0))
        clinica_id = int(request.query_params.get("clinica_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Parámetros inválidos"}, status_code=400)

    if not comp_id or not clinica_id:
        return JSONResponse({"error": "comp_id y clinica_id requeridos"}, status_code=400)

    try:
        from clinica_app.services.pdf_recibo import generar_recibo_pdf, obtener_datos_comprobante
        from clinica_app.config import CLINICA_NOMBRE
        async with _get_async_session() as session:
            comp_dict, pac_nombre = await obtener_datos_comprobante(session, clinica_id, comp_id)
        filename = generar_recibo_pdf(comp_dict, pac_nombre, CLINICA_NOMBRE)
        path = os.path.join(REPORT_EXPORT_DIR, filename)
        if not os.path.isfile(path):
            return JSONResponse({"error": "PDF no generado"}, status_code=500)
        return FileResponse(path, filename=filename, media_type="application/pdf")
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except Exception as exc:
        return JSONResponse({"error": "Error interno"}, status_code=500)


app._api.add_route("/health", _health_check)
app._api.add_route("/api/ping", _api_ping)
app._api.add_route("/api/health", _api_health)
app._api.add_route("/api/reportes/descargar/{filename}", _descargar_reporte)
app._api.add_route("/api/recibo/pdf", _generar_pdf_recibo)
