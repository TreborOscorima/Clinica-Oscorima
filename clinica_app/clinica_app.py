"""
clinica_app/clinica_app.py — Punto de entrada de la aplicación Reflex.

Arrancar en desarrollo:
    reflex run

Arrancar en producción:
    reflex run --env prod
"""
import asyncio
import os

import reflex as rx
from sqlmodel import SQLModel
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route, Router

from clinica_app.config import REPORT_EXPORT_DIR
from clinica_app.database import get_async_session as _get_async_session
from clinica_app.database import _sync_engine as _engine
from clinica_app.logging_config import setup_logging
from clinica_app.sentry_config import init_sentry
from clinica_app.services.download_token import validar_token
import clinica_app.models  # noqa: F401 — registra todos los modelos antes del create_all

# Observabilidad: configura el logging (JSON en prod) y Sentry (no-op sin DSN).
setup_logging()
init_sentry()

# Crea las tablas que no existen (no toca las existentes)
SQLModel.metadata.create_all(_engine)

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
from clinica_app.pages.auditoria         import auditoria_page
from clinica_app.pages.salud             import salud_page
from clinica_app.pages.cuentas           import cuentas_page
from clinica_app.pages.compras           import compras_page
from clinica_app.pages.promociones       import promociones_page
from clinica_app.pages.notas_clinicas    import notas_clinicas_page
from clinica_app.pages.odontograma        import odontograma_page
from clinica_app.pages.planes_tratamiento import planes_tratamiento_page
from clinica_app.pages.sesiones_esteticas import sesiones_esteticas_page
from clinica_app.pages.calendario        import calendario_page
from clinica_app.pages.mapa_estetico     import mapa_estetico_page
from clinica_app.pages.timeline          import timeline_page


# ── API handlers ─────────────────────────────────────────────────────────────

async def _health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def _api_ping(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def _api_health(request: Request) -> JSONResponse:
    """Salud del sistema para monitores externos: 200 si ok, 503 si degradado.

    NO es el endpoint del healthcheck de Docker (ese es /api/ping, trivial): un
    blip de BD acá no debe reiniciar el contenedor.
    """
    from clinica_app.services import salud
    try:
        async with _get_async_session() as session:
            datos = await salud.estado_sistema(session)
    except Exception:
        datos = {"status": "degraded", "db": {"ok": False, "error": "sin sesión"}}
    datos["app"] = "tuwaykilife-clinica"
    code = 200 if datos.get("status") == "ok" else 503
    return JSONResponse(datos, status_code=code)


async def _descargar_reporte(request: Request) -> FileResponse | JSONResponse:
    auth = validar_token(request.query_params.get("token", ""))
    if auth is None:
        return JSONResponse({"error": "No autorizado"}, status_code=401)

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
    auth = validar_token(request.query_params.get("token", ""))
    if auth is None:
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    token_user_id, token_clinica_id = auth

    try:
        comp_id   = int(request.query_params.get("comp_id", 0))
        clinica_id = int(request.query_params.get("clinica_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Parámetros inválidos"}, status_code=400)

    if not comp_id or not clinica_id:
        return JSONResponse({"error": "comp_id y clinica_id requeridos"}, status_code=400)

    if clinica_id != token_clinica_id:
        return JSONResponse({"error": "No autorizado para esta clínica"}, status_code=403)

    try:
        from clinica_app.services.pdf_recibo import generar_recibo_pdf, obtener_datos_comprobante
        from clinica_app.config import CLINICA_NOMBRE
        async with _get_async_session() as session:
            comp_dict, pac_nombre = await obtener_datos_comprobante(session, clinica_id, comp_id)
        filename = await asyncio.to_thread(generar_recibo_pdf, comp_dict, pac_nombre, CLINICA_NOMBRE)
        path = os.path.join(REPORT_EXPORT_DIR, filename)
        if not os.path.isfile(path):
            return JSONResponse({"error": "PDF no generado"}, status_code=500)
        return FileResponse(path, filename=filename, media_type="application/pdf")
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except Exception:
        return JSONResponse({"error": "Error interno"}, status_code=500)


async def _generar_pdf_odontograma(request: Request) -> Response | JSONResponse:
    """Exporta el odontograma (vivo o una versión histórica) a PDF.

    Protegido por token efímero + chequeo de clínica, igual que el recibo. Con
    `version_id` > 0 exporta esa versión; si no, el estado actual.
    """
    auth = validar_token(request.query_params.get("token", ""))
    if auth is None:
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    _token_user_id, token_clinica_id = auth

    try:
        paciente_id = int(request.query_params.get("paciente_id", 0))
        clinica_id  = int(request.query_params.get("clinica_id", 0))
        version_id  = int(request.query_params.get("version_id", 0))
        sede_id     = int(request.query_params.get("sede_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Parámetros inválidos"}, status_code=400)

    if not paciente_id or not clinica_id:
        return JSONResponse({"error": "paciente_id y clinica_id requeridos"}, status_code=400)
    if clinica_id != token_clinica_id:
        return JSONResponse({"error": "No autorizado para esta clínica"}, status_code=403)

    try:
        from clinica_app.services import odontograma as _odo
        from clinica_app.services.pdf_odontograma import generar_odontograma_pdf
        from clinica_app.services.exceptions import NotFoundError
        from clinica_app.config import CLINICA_NOMBRE
        async with _get_async_session() as session:
            datos = await _odo.datos_export(
                session, clinica_id, paciente_id,
                version_id=version_id, sede_id=sede_id,
            )
        pdf_bytes = await asyncio.to_thread(
            generar_odontograma_pdf,
            clinica_nombre=CLINICA_NOMBRE,
            **datos,
        )
        etiqueta = f"-v{version_id}" if version_id else ""
        filename = f"odontograma-paciente{paciente_id}{etiqueta}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    except NotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except Exception:
        return JSONResponse({"error": "Error interno"}, status_code=500)


async def _generar_pdf_estetica(request: Request) -> Response | JSONResponse:
    """Exporta el mapa estético del paciente (evaluaciones + procedimientos +
    puntos + fotos) a PDF. Protegido por token efímero + chequeo de clínica,
    igual que el odontograma."""
    auth = validar_token(request.query_params.get("token", ""))
    if auth is None:
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    _token_user_id, token_clinica_id = auth

    try:
        paciente_id = int(request.query_params.get("paciente_id", 0))
        clinica_id  = int(request.query_params.get("clinica_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Parámetros inválidos"}, status_code=400)

    if not paciente_id or not clinica_id:
        return JSONResponse({"error": "paciente_id y clinica_id requeridos"}, status_code=400)
    if clinica_id != token_clinica_id:
        return JSONResponse({"error": "No autorizado para esta clínica"}, status_code=403)

    try:
        from clinica_app.services import estetica_mapa as _mapa
        from clinica_app.services.pdf_estetica import generar_estetica_pdf
        from clinica_app.services.exceptions import NotFoundError
        from clinica_app.config import CLINICA_NOMBRE
        async with _get_async_session() as session:
            datos = await _mapa.datos_export(session, clinica_id, paciente_id)
        pdf_bytes = await asyncio.to_thread(
            generar_estetica_pdf,
            clinica_nombre=CLINICA_NOMBRE,
            **datos,
        )
        filename = f"mapa-estetico-paciente{paciente_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    except NotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except Exception:
        return JSONResponse({"error": "Error interno"}, status_code=500)


async def _descargar_adjunto(request: Request) -> FileResponse | JSONResponse:
    """Sirve un adjunto clínico. Protegido por token efímero + chequeo de clínica."""
    auth = validar_token(request.query_params.get("token", ""))
    if auth is None:
        return JSONResponse({"error": "No autorizado"}, status_code=401)
    _token_user_id, token_clinica_id = auth

    try:
        adj_id     = int(request.query_params.get("id", 0))
        clinica_id = int(request.query_params.get("clinica_id", 0))
    except (ValueError, TypeError):
        return JSONResponse({"error": "Parámetros inválidos"}, status_code=400)

    if not adj_id or not clinica_id:
        return JSONResponse({"error": "id y clinica_id requeridos"}, status_code=400)
    if clinica_id != token_clinica_id:
        return JSONResponse({"error": "No autorizado para esta clínica"}, status_code=403)

    try:
        from clinica_app.services import adjuntos as _adj_svc
        from clinica_app.services import storage as _storage
        from clinica_app.services.exceptions import NotFoundError
        async with _get_async_session() as session:
            adj = await _adj_svc.obtener(session, clinica_id, adj_id)
            nombre, stored_name, mime = adj.nombre, adj.stored_name, adj.mime
        path = _storage.ruta_absoluta(clinica_id, stored_name)
        if not os.path.isfile(path):
            return JSONResponse({"error": "Archivo no encontrado"}, status_code=404)
        return FileResponse(
            path,
            filename=nombre,
            media_type=mime or "application/octet-stream",
        )
    except NotFoundError:
        return JSONResponse({"error": "not found"}, status_code=404)
    except Exception:
        return JSONResponse({"error": "Error interno"}, status_code=500)


# ── ASGI middleware: intercepta /api/* antes del SPA fallback ────────────────

from clinica_app.api_admin import admin_routes      # /api/admin/* — panel Owner TUWAYKI
from clinica_app.api_registro import registro_routes  # /api/registro — alta multi-empresa

_custom_api = Router(routes=[
    Route("/api/ping", _api_ping),
    Route("/api/health", _api_health),
    Route("/api/reportes/descargar/{filename}", _descargar_reporte),
    Route("/api/recibo/pdf", _generar_pdf_recibo),
    Route("/api/odontograma/pdf", _generar_pdf_odontograma),
    Route("/api/estetica/pdf", _generar_pdf_estetica),
    Route("/api/adjunto", _descargar_adjunto),
    Route("/health", _health_check),
    *admin_routes,
    *registro_routes,
])


def _api_transformer(asgi_app):
    async def middleware(scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path.startswith("/api/") or path == "/health":
                await _custom_api(scope, receive, send)
                return
        await asgi_app(scope, receive, send)
    return middleware


app = rx.App(
    stylesheets=[
        "/fonts/inter.css",
    ],
    style={
        "font_family": "Inter, sans-serif",
        "background_color": "#f9fafb",
    },
    # Branding + PWA/mobile: se inyecta en el <head> de todas las páginas.
    head_components=[
        rx.el.meta(name="theme-color", content="#0284c7"),
        rx.el.meta(name="mobile-web-app-capable", content="yes"),
        rx.el.meta(name="apple-mobile-web-app-capable", content="yes"),
        rx.el.meta(name="apple-mobile-web-app-status-bar-style", content="default"),
        rx.el.meta(name="apple-mobile-web-app-title", content="TUWAYKILIFE"),
        rx.el.link(rel="icon", type="image/png", href="/tuwaykilife-icon.png"),
        rx.el.link(rel="shortcut icon", href="/favicon.ico"),
        rx.el.link(rel="apple-touch-icon", href="/tuwaykilife-icon.png"),
        rx.el.link(rel="manifest", href="/manifest.json"),
        # PWA: registra el Service Worker (habilita "Instalar app") y muestra el
        # banner de instalación propio al dispararse `beforeinstallprompt`
        # (Chrome ya casi no muestra el mini-infobar nativo). Ver
        # assets/js/twk-pwa.js. Se usa rx.el.script (elemento <script> crudo):
        # rx.script(src=...) en head_components descarta el src en Reflex 0.9.8.
        rx.el.script(src="/js/twk-pwa.js", defer=True),
    ],
    api_transformer=_api_transformer,
)

# ── Rutas públicas ────────────────────────────────────────────────────────────
app.add_page(login_page, route="/login", title="TUWAYKILIFE | Iniciar sesión")

# ── Módulo Gestión ────────────────────────────────────────────────────────────
app.add_page(dashboard_page,     route="/",              title="TUWAYKILIFE | Panel")
app.add_page(pacientes_page,     route="/pacientes",     title="TUWAYKILIFE | Pacientes")
app.add_page(profesionales_page, route="/profesionales", title="TUWAYKILIFE | Profesionales")
app.add_page(turnos_page,        route="/turnos",        title="TUWAYKILIFE | Turnos")
app.add_page(servicios_page,     route="/servicios",     title="TUWAYKILIFE | Servicios")

# ── Módulo Operaciones ────────────────────────────────────────────────────────
app.add_page(cobro_page,         route="/cobro",         title="TUWAYKILIFE | Punto de cobro")
app.add_page(caja_page,          route="/caja",          title="TUWAYKILIFE | Caja")
app.add_page(inventario_page,    route="/inventario",    title="TUWAYKILIFE | Inventario")
app.add_page(reportes_page,      route="/reportes",      title="TUWAYKILIFE | Reportes")

# ── Admin ─────────────────────────────────────────────────────────────────────
app.add_page(configuracion_page, route="/configuracion", title="TUWAYKILIFE | Configuración")
app.add_page(auditoria_page,     route="/auditoria",     title="TUWAYKILIFE | Auditoría")
app.add_page(salud_page,         route="/salud",         title="TUWAYKILIFE | Salud del sistema")

app.add_page(cuentas_page,        route="/cuentas",         title="TUWAYKILIFE | Cuentas corrientes")
app.add_page(compras_page,        route="/compras",         title="TUWAYKILIFE | Compras")
app.add_page(promociones_page,    route="/promociones",     title="TUWAYKILIFE | Promociones")
app.add_page(notas_clinicas_page, route="/historia-clinica", title="TUWAYKILIFE | Historia clínica")
app.add_page(timeline_page,       route="/linea-tiempo",     title="TUWAYKILIFE | Línea de tiempo")
app.add_page(odontograma_page,    route="/odontograma",     title="TUWAYKILIFE | Odontograma")
app.add_page(planes_tratamiento_page, route="/plan-tratamiento", title="TUWAYKILIFE | Plan de tratamiento")
app.add_page(sesiones_esteticas_page, route="/galeria-estetica", title="TUWAYKILIFE | Galería estética")
app.add_page(mapa_estetico_page,  route="/mapa-estetico",   title="TUWAYKILIFE | Mapa estético")
app.add_page(calendario_page,     route="/calendario",      title="TUWAYKILIFE | Calendario")
