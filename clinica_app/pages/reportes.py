from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.state.reportes import ReportesState

_TIPOS = [
    ("pacientes", "Pacientes", "users"),
    ("caja",      "Caja",     "wallet"),
    ("turnos",    "Turnos",   "calendar"),
]


def _tipo_card(tipo: str, label: str, icon: str) -> rx.Component:
    return rx.el.button(
        rx.el.div(
            rx.icon(icon, size=22),
            rx.el.span(label, class_name="mt-2 text-sm font-medium"),
            class_name="flex flex-col items-center gap-1",
        ),
        on_click=lambda: ReportesState.set_tipo(tipo),
        class_name=rx.cond(
            ReportesState.tipo_reporte == tipo,
            "flex flex-col items-center justify-center p-6 rounded-xl border-2 border-sky-600 bg-sky-50 text-sky-700 cursor-pointer w-full",
            "flex flex-col items-center justify-center p-6 rounded-xl border-2 border-gray-200 bg-white text-gray-600 hover:border-sky-300 hover:bg-sky-50 cursor-pointer w-full transition",
        ),
    )


def _status_panel() -> rx.Component:
    return rx.cond(
        ReportesState.job_id != "",
        rx.el.div(
            # Procesando
            rx.cond(
                ReportesState.procesando,
                rx.el.div(
                    rx.el.div(
                        rx.icon("loader-circle", size=24, class_name="animate-spin text-sky-600"),
                        rx.el.div(
                            rx.el.p("Generando reporte...", class_name="font-medium text-gray-900"),
                            rx.el.p(f"Job ID: {ReportesState.job_id}", class_name="text-xs text-gray-400 font-mono mt-0.5"),
                        ),
                        class_name="flex items-center gap-4",
                    ),
                    class_name="p-5 bg-blue-50 border border-blue-200 rounded-xl",
                ),
            ),
            # Listo
            rx.cond(
                ReportesState.reporte_listo,
                rx.el.div(
                    rx.el.div(
                        rx.icon("check-circle", size=24, class_name="text-green-600"),
                        rx.el.div(
                            rx.el.p("¡Reporte generado!", class_name="font-medium text-gray-900"),
                            rx.el.p(ReportesState.job_result, class_name="text-xs text-gray-500 font-mono mt-0.5 break-all"),
                        ),
                        class_name="flex items-start gap-4",
                    ),
                    class_name="p-5 bg-green-50 border border-green-200 rounded-xl",
                ),
            ),
            # Error
            rx.cond(
                ReportesState.reporte_fallido,
                rx.el.div(
                    rx.el.div(
                        rx.icon("x-circle", size=24, class_name="text-red-600"),
                        rx.el.div(
                            rx.el.p("Error al generar el reporte", class_name="font-medium text-gray-900"),
                            rx.el.p(ReportesState.job_error, class_name="text-xs text-red-600 mt-0.5"),
                        ),
                        class_name="flex items-start gap-4",
                    ),
                    class_name="p-5 bg-red-50 border border-red-200 rounded-xl",
                ),
            ),
            class_name="mt-6",
        ),
    )


def reportes_page() -> rx.Component:
    return shell(
        rx.el.div(
            rx.el.h1("Reportes", class_name="text-xl font-semibold text-gray-900 mb-1"),
            rx.el.p("Genera y descarga reportes en Excel", class_name="text-sm text-gray-500 mb-8"),
        ),
        # Selector de tipo
        rx.el.div(
            rx.el.p("Tipo de reporte", class_name="text-sm font-medium text-gray-700 mb-3"),
            rx.el.div(
                *[_tipo_card(t, l, i) for t, l, i in _TIPOS],
                class_name="grid grid-cols-3 gap-4",
            ),
            class_name="mb-6",
        ),
        # Parámetros de fecha (solo para caja)
        rx.cond(
            ReportesState.tipo_reporte == "caja",
            rx.el.div(
                rx.el.p("Rango de fechas (opcional)", class_name="text-sm font-medium text-gray-700 mb-3"),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Desde", class_name="block text-xs text-gray-500 mb-1"),
                        rx.el.input(
                            type="date", value=ReportesState.fecha_desde,
                            on_change=ReportesState.set_var("fecha_desde"),
                            class_name="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    rx.el.div(
                        rx.el.label("Hasta", class_name="block text-xs text-gray-500 mb-1"),
                        rx.el.input(
                            type="date", value=ReportesState.fecha_hasta,
                            on_change=ReportesState.set_var("fecha_hasta"),
                            class_name="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
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
                ReportesState.is_enqueuing | ReportesState.procesando,
                rx.el.div(
                    rx.icon("loader-circle", size=18, class_name="animate-spin mr-2"),
                    "Procesando...",
                    class_name="flex items-center",
                ),
                rx.el.div(
                    rx.icon("download", size=18, class_name="mr-2"),
                    "Generar reporte",
                    class_name="flex items-center",
                ),
            ),
            on_click=ReportesState.generar_reporte,
            disabled=ReportesState.is_enqueuing | ReportesState.procesando,
            class_name="px-6 py-2.5 bg-sky-600 text-white font-medium rounded-lg hover:bg-sky-700 disabled:bg-sky-400 disabled:cursor-not-allowed cursor-pointer transition",
        ),
        # Panel de estado
        _status_panel(),
        on_mount=ReportesState.on_mount,
    )
