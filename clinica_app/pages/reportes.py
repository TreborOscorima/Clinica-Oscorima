from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.reportes import ReportesState

_TIPOS = [
    ("pacientes",  "Pacientes",  "users"),
    ("caja",       "Caja",       "wallet"),
    ("turnos",     "Turnos",     "calendar"),
    ("inventario", "Inventario", "package"),
    ("compras",    "Compras",    "shopping-cart"),
    ("produccion", "Producción", "chart-column"),
]


# ── KPI card ──────────────────────────────────────────────────────────────────

def _kpi(icono: str, label: str, valor: rx.Var | str, color: str) -> rx.Component:
    colores = {
        "sky":    ("bg-sky-50",    "text-sky-600",    "text-sky-900"),
        "green":  ("bg-green-50",  "text-green-600",  "text-green-900"),
        "rose":   ("bg-rose-50",   "text-rose-600",   "text-rose-900"),
        "violet": ("bg-violet-50", "text-violet-600", "text-violet-900"),
    }
    bg, ico_col, val_col = colores.get(color, colores["sky"])
    return rx.el.div(
        rx.el.div(
            rx.icon(icono, size=20, class_name=ico_col),
            class_name=f"p-2 rounded-lg {bg}",
        ),
        rx.el.div(
            rx.el.p(label, class_name="text-xs text-gray-500"),
            rx.el.p(valor, class_name=f"text-xl font-bold {val_col} mt-0.5"),
        ),
        class_name="flex items-center gap-4 bg-white rounded-xl border border-gray-100 shadow-sm p-4",
    )


# ── Analíticas ampliadas ──────────────────────────────────────────────────────

def _ana_stat(label: str, valor: rx.Var | str, sufijo: str, color: str) -> rx.Component:
    return rx.el.div(
        rx.el.p(label, class_name="text-[11px] text-gray-500 uppercase tracking-wide"),
        rx.el.p(
            valor, rx.el.span(sufijo, class_name="text-sm font-normal text-gray-400 ml-1"),
            class_name=f"text-lg font-bold {color} mt-1",
        ),
        class_name="bg-white rounded-lg border border-gray-100 px-4 py-3",
    )


def _prof_row(p: rx.Var) -> rx.Component:
    return rx.el.tr(
        rx.el.td(p["nombre"], class_name="px-4 py-2 text-sm text-gray-800 font-medium"),
        rx.el.td(p["total"], class_name="px-4 py-2 text-sm text-gray-600 text-center"),
        rx.el.td(p["atendidos"], class_name="px-4 py-2 text-sm text-green-700 text-center"),
        rx.el.td(p["cancelados"], class_name="px-4 py-2 text-sm text-rose-600 text-center"),
        rx.el.td(p["tasa_asistencia"].to(str) + "%", class_name="px-4 py-2 text-sm text-gray-600 text-center"),
        rx.el.td(p["horas"].to(str) + " h", class_name="px-4 py-2 text-sm text-gray-600 text-center"),
        rx.el.td("S/ " + p["produccion"].to(str), class_name="px-4 py-2 text-sm text-gray-900 font-semibold text-right"),
        class_name="border-t border-gray-100 hover:bg-gray-50",
    )


def _serv_row(s: rx.Var) -> rx.Component:
    return rx.el.tr(
        rx.el.td(s["nombre"], class_name="px-4 py-2 text-sm text-gray-800 font-medium"),
        rx.el.td(s["veces"], class_name="px-4 py-2 text-sm text-gray-600 text-center"),
        rx.el.td("S/ " + s["produccion"].to(str), class_name="px-4 py-2 text-sm text-gray-900 font-semibold text-right"),
        class_name="border-t border-gray-100 hover:bg-gray-50",
    )


def _tabla(titulo: str, encabezados: list, filas: rx.Component, vacio: str) -> rx.Component:
    return rx.el.div(
        rx.el.p(titulo, class_name="text-sm font-semibold text-gray-700 mb-2"),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(*encabezados, class_name="bg-gray-50 text-[11px] uppercase tracking-wide text-gray-500"),
                ),
                rx.el.tbody(filas),
                class_name="w-full",
            ),
            class_name="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden",
        ),
        class_name="mb-6",
    )


def _th(txt: str, align: str = "left") -> rx.Component:
    return rx.el.th(txt, class_name=f"px-4 py-2 text-{align} font-medium")


def _panel_analiticas() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p("Analíticas de agenda y producción", class_name="text-sm font-semibold text-gray-800"),
                rx.el.p("Asistencia, cancelaciones y producción por profesional y servicio",
                        class_name="text-xs text-gray-500"),
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.label("Desde", class_name="block text-[11px] text-gray-500 mb-1"),
                    rx.el.input(
                        type="date", default_value=ReportesState.ana_desde,
                        on_change=ReportesState.set_ana_desde,
                        class_name="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                ),
                rx.el.div(
                    rx.el.label("Hasta", class_name="block text-[11px] text-gray-500 mb-1"),
                    rx.el.input(
                        type="date", default_value=ReportesState.ana_hasta,
                        on_change=ReportesState.set_ana_hasta,
                        class_name="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                ),
                rx.el.button(
                    rx.cond(
                        ReportesState.ana_loading,
                        rx.icon("loader-circle", size=16, class_name="animate-spin"),
                        rx.icon("refresh-cw", size=16),
                    ),
                    "Aplicar",
                    on_click=ReportesState.cargar_analiticas,
                    disabled=ReportesState.ana_loading,
                    class_name="inline-flex items-center gap-1.5 self-end px-3 py-1.5 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer transition",
                ),
                class_name="flex items-end gap-3",
            ),
            class_name="flex flex-wrap items-end justify-between gap-4 mb-4",
        ),

        # Resumen
        rx.el.div(
            _ana_stat("Turnos", ReportesState.ana_total, "", "text-gray-900"),
            _ana_stat("Atendidos", ReportesState.ana_atendidos, "", "text-green-700"),
            _ana_stat("Cancelados", ReportesState.ana_cancelados, "", "text-rose-600"),
            _ana_stat("Asistencia", ReportesState.ana_asistencia, "%", "text-sky-700"),
            _ana_stat("Horas agendadas", ReportesState.ana_horas, "h", "text-violet-700"),
            _ana_stat("Producción", "S/ " + ReportesState.ana_produccion, "", "text-emerald-700"),
            class_name="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6",
        ),

        # Tablas
        rx.cond(
            ReportesState.ana_por_profesional.length() > 0,
            _tabla(
                "Producción por profesional",
                [_th("Profesional"), _th("Turnos", "center"), _th("Atend.", "center"),
                 _th("Canc.", "center"), _th("Asist.", "center"), _th("Horas", "center"), _th("Producción", "right")],
                rx.foreach(ReportesState.ana_por_profesional, _prof_row),
                "Sin turnos en el rango",
            ),
            rx.el.p("Sin turnos en el rango seleccionado.", class_name="text-sm text-gray-400 italic mb-6"),
        ),
        rx.cond(
            ReportesState.ana_por_servicio.length() > 0,
            _tabla(
                "Producción por servicio",
                [_th("Servicio"), _th("Veces", "center"), _th("Producción", "right")],
                rx.foreach(ReportesState.ana_por_servicio, _serv_row),
                "Sin servicios realizados",
            ),
        ),

        class_name="mb-8 p-5 bg-gray-50 rounded-2xl border border-gray-100",
    )


# ── Tipo card ─────────────────────────────────────────────────────────────────

def _tipo_card(tipo: str, label: str, icono: str) -> rx.Component:
    return rx.el.button(
        rx.el.div(
            rx.icon(icono, size=22),
            rx.el.span(label, class_name="mt-2 text-sm font-medium"),
            class_name="flex flex-col items-center gap-1",
        ),
        on_click=ReportesState.set_tipo(tipo),
        class_name=rx.cond(
            ReportesState.tipo_reporte == tipo,
            "flex flex-col items-center justify-center p-5 rounded-xl border-2 border-sky-600 bg-sky-50 text-sky-700 cursor-pointer w-full transition",
            "flex flex-col items-center justify-center p-5 rounded-xl border-2 border-gray-200 bg-white text-gray-500 hover:border-sky-300 hover:bg-sky-50 cursor-pointer w-full transition",
        ),
    )


# ── Panel de estado ───────────────────────────────────────────────────────────

def _status_panel() -> rx.Component:
    return rx.cond(
        ReportesState.is_generating | ReportesState.reporte_listo | ReportesState.reporte_fallido,
        rx.el.div(
            # Generando
            rx.cond(
                ReportesState.is_generating,
                rx.el.div(
                    rx.icon("loader-circle", size=22, class_name="animate-spin text-sky-600"),
                    rx.el.p("Generando reporte…", class_name="font-medium text-gray-800"),
                    class_name="flex items-center gap-3 p-5 bg-blue-50 border border-blue-200 rounded-xl",
                ),
            ),
            # Listo
            rx.cond(
                ReportesState.reporte_listo,
                rx.el.div(
                    rx.el.div(
                        rx.icon("circle-check", size=22, class_name="text-green-600"),
                        rx.el.div(
                            rx.el.p("¡Reporte generado!", class_name="font-medium text-gray-900"),
                            rx.el.p(ReportesState.archivo, class_name="text-xs text-gray-500 font-mono mt-0.5 break-all"),
                        ),
                        class_name="flex items-start gap-3",
                    ),
                    rx.el.a(
                        rx.icon("download", size=16, class_name="mr-1.5"),
                        "Descargar Excel",
                        href=ReportesState.archivo_url,
                        download=ReportesState.archivo,
                        class_name="inline-flex items-center mt-3 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition cursor-pointer",
                    ),
                    class_name="p-5 bg-green-50 border border-green-200 rounded-xl",
                ),
            ),
            # Error
            rx.cond(
                ReportesState.reporte_fallido,
                rx.el.div(
                    rx.icon("circle-x", size=22, class_name="text-red-600"),
                    rx.el.div(
                        rx.el.p("Error al generar el reporte", class_name="font-medium text-gray-900"),
                        rx.el.p(ReportesState.gen_error, class_name="text-xs text-red-600 mt-0.5"),
                    ),
                    class_name="flex items-start gap-3 p-5 bg-red-50 border border-red-200 rounded-xl",
                ),
            ),
            class_name="mt-6",
        ),
    )


# ── Página principal ──────────────────────────────────────────────────────────

def reportes_page() -> rx.Component:
    return shell(
        page_header("Reportes", "Genera y descarga reportes en Excel"),

        # KPIs del mes
        rx.el.div(
            rx.el.p("Resumen del mes", class_name="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3"),
            rx.el.div(
                _kpi("trending-up",  "Ingresos del mes",   "S/ " + ReportesState.kpi_ingresos,         "green"),
                _kpi("trending-down","Egresos del mes",    "S/ " + ReportesState.kpi_egresos,           "rose"),
                _kpi("calendar",     "Turnos del mes",     ReportesState.kpi_turnos,         "sky"),
                _kpi("user-plus",    "Pacientes nuevos",   ReportesState.kpi_pacientes_nuevos, "violet"),
                class_name="grid grid-cols-2 lg:grid-cols-4 gap-4",
            ),
            class_name="mb-8",
        ),

        # Panel de analíticas ampliadas
        _panel_analiticas(),

        # Selector de tipo
        rx.el.div(
            rx.el.p("Descargar reporte Excel", class_name="text-sm font-medium text-gray-700 mb-3"),
            rx.el.div(
                *[_tipo_card(t, l, i) for t, l, i in _TIPOS],
                class_name="grid grid-cols-3 lg:grid-cols-6 gap-3",
            ),
            class_name="mb-6",
        ),

        # Filtro de fechas (caja, turnos, compras)
        rx.cond(
            ReportesState.mostrar_fechas,
            rx.el.div(
                rx.el.p("Rango de fechas (opcional)", class_name="text-sm font-medium text-gray-700 mb-3"),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Desde", class_name="block text-xs text-gray-500 mb-1"),
                        
                        rx.el.input(
                            type="date", default_value=ReportesState.fecha_desde,
                            on_change=ReportesState.set_fecha_desde,
                            class_name="px-3 py-2 border border-gray-300 rounded-lg text-sm w-full focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Hasta", class_name="block text-xs text-gray-500 mb-1"),
                        
                        rx.el.input(
                            type="date", default_value=ReportesState.fecha_hasta,
                            on_change=ReportesState.set_fecha_hasta,
                            class_name="px-3 py-2 border border-gray-300 rounded-lg text-sm w-full focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    class_name="flex gap-4",
                ),
                class_name="mb-6",
            ),
        ),

        # Botón generar
        rx.el.button(
            rx.cond(
                ReportesState.is_generating,
                rx.el.div(
                    rx.icon("loader-circle", size=18, class_name="animate-spin mr-2"),
                    "Generando…",
                    class_name="flex items-center",
                ),
                rx.el.div(
                    rx.icon("file-spreadsheet", size=18, class_name="mr-2"),
                    "Generar reporte Excel",
                    class_name="flex items-center",
                ),
            ),
            on_click=ReportesState.generar_reporte,
            disabled=ReportesState.is_generating,
            class_name="px-6 py-2.5 bg-sky-600 text-white font-medium rounded-lg hover:bg-sky-700 disabled:bg-sky-400 disabled:cursor-not-allowed cursor-pointer transition",
        ),

        # Panel de estado / descarga
        _status_panel(),

        on_mount=ReportesState.on_mount,
    )
