from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.state.reportes import ReportesState

_TIPOS = [
    ("pacientes",  "Pacientes",  "users"),
    ("caja",       "Caja",       "wallet"),
    ("turnos",     "Turnos",     "calendar"),
    ("inventario", "Inventario", "package"),
    ("compras",    "Compras",    "shopping-cart"),
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
        # Encabezado
        rx.el.div(
            rx.el.h1("Reportes", class_name="text-xl font-semibold text-gray-900 mb-0.5"),
            rx.el.p("Genera y descarga reportes en Excel", class_name="text-sm text-gray-500"),
            class_name="mb-6",
        ),

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

        # Selector de tipo
        rx.el.div(
            rx.el.p("Tipo de reporte", class_name="text-sm font-medium text-gray-700 mb-3"),
            rx.el.div(
                *[_tipo_card(t, l, i) for t, l, i in _TIPOS],
                class_name="grid grid-cols-3 lg:grid-cols-5 gap-3",
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
                        rx.debounce_input(
                            rx.el.input(
                                type="date", value=ReportesState.fecha_desde,
                                on_change=ReportesState.set_fecha_desde,
                                class_name="px-3 py-2 border border-gray-300 rounded-lg text-sm w-full focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                            debounce_timeout=0,
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Hasta", class_name="block text-xs text-gray-500 mb-1"),
                        rx.debounce_input(
                            rx.el.input(
                                type="date", value=ReportesState.fecha_hasta,
                                on_change=ReportesState.set_fecha_hasta,
                                class_name="px-3 py-2 border border-gray-300 rounded-lg text-sm w-full focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                            debounce_timeout=0,
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
