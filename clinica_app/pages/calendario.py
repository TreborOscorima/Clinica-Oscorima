from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.calendario import CalendarioState

def _chip_turno(t: dict) -> rx.Component:
    """Tarjeta compacta de turno dentro del calendario."""
    return rx.el.div(
        rx.el.p(t["hora"], class_name="text-xs font-bold text-white opacity-90"),
        rx.el.p(t["paciente_nombre"], class_name="text-xs text-white font-medium truncate"),
        rx.cond(
            t["profesional_nombre"] != "—",
            rx.el.p(t["profesional_nombre"], class_name="text-xs text-white/70 truncate"),
        ),
        rx.el.a(
            "Ver turno →",
            href="/turnos",
            class_name="text-xs text-white/80 hover:text-white underline mt-0.5 block",
        ),
        class_name=rx.match(
            t["estado"],
            ("pendiente",   "bg-amber-500 rounded-lg p-1.5 mb-1 cursor-pointer hover:opacity-90 transition"),
            ("confirmado",  "bg-sky-500 rounded-lg p-1.5 mb-1 cursor-pointer hover:opacity-90 transition"),
            ("atendido",    "bg-green-500 rounded-lg p-1.5 mb-1 cursor-pointer hover:opacity-90 transition"),
            ("cancelado",   "bg-gray-400 rounded-lg p-1.5 mb-1 cursor-pointer hover:opacity-90 transition opacity-60"),
            "bg-sky-500 rounded-lg p-1.5 mb-1 cursor-pointer hover:opacity-90 transition",
        ),
    )


def _celda_hora_dia(celda) -> rx.Component:
    return rx.el.td(
        rx.el.div(
            rx.foreach(celda["turnos"].to(list[dict]), _chip_turno),
            rx.el.button(
                rx.icon("plus", size=12),
                on_click=CalendarioState.abrir_nuevo(celda["fecha_hora_key"].to(str)),
                class_name="opacity-0 group-hover:opacity-100 transition w-full text-gray-300 hover:text-sky-500 hover:bg-sky-50 rounded py-0.5 text-xs flex items-center justify-center cursor-pointer",
                title="Nuevo turno",
            ),
            class_name="p-1",
        ),
        class_name="border border-gray-100 align-top group min-w-24",
    )


def _modal_nuevo() -> rx.Component:
    return rx.cond(
        CalendarioState.modal_nuevo,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=CalendarioState.cerrar_nuevo),
            rx.el.div(
                rx.el.div(
                    rx.el.h2("Nuevo turno", class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(rx.icon("x", size=18), on_click=CalendarioState.cerrar_nuevo,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                rx.el.div(
                    # Paciente
                    rx.el.div(
                        rx.el.label("Paciente *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.select(
                            rx.el.option("— Seleccioná un paciente —", value=""),
                            rx.foreach(
                                CalendarioState.pacientes_cat,
                                lambda o: rx.el.option(o["nombre"], value=o["id"]),
                            ),
                            default_value=CalendarioState.form_paciente_id,
                            on_change=CalendarioState.set_form_paciente_id,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Profesional
                    rx.el.div(
                        rx.el.label("Profesional", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.select(
                            rx.el.option("— Sin asignar —", value=""),
                            rx.foreach(
                                CalendarioState.profesionales_cat,
                                lambda o: rx.el.option(o["nombre"], value=o["id"]),
                            ),
                            default_value=CalendarioState.form_profesional_id,
                            on_change=CalendarioState.set_form_profesional_id,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Servicio
                    rx.el.div(
                        rx.el.label("Servicio", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.select(
                            rx.el.option("— Sin asignar —", value=""),
                            rx.foreach(
                                CalendarioState.servicios_cat,
                                lambda o: rx.el.option(o["nombre"], value=o["id"]),
                            ),
                            default_value=CalendarioState.form_servicio_id,
                            on_change=CalendarioState.set_form_servicio_id,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Fecha y hora
                    rx.el.div(
                        rx.el.label("Fecha y hora *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        
                        rx.el.input(
                            type="datetime-local",
                            default_value=CalendarioState.form_fecha_hora,
                            on_change=CalendarioState.set_form_fecha_hora,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    class_name="space-y-4",
                ),
                rx.cond(
                    CalendarioState.form_error != "",
                    rx.el.p(CalendarioState.form_error, class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded"),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar", on_click=CalendarioState.cerrar_nuevo,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            CalendarioState.is_saving,
                            rx.el.div(rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"), "Guardando…",
                                      class_name="flex items-center"),
                            "Guardar",
                        ),
                        on_click=CalendarioState.guardar_turno,
                        disabled=CalendarioState.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end mt-5",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _leyenda() -> rx.Component:
    colores = [
        ("bg-amber-500", "Pendiente"),
        ("bg-sky-500",   "Confirmado"),
        ("bg-green-500", "Atendido"),
        ("bg-gray-400",  "Cancelado"),
    ]
    return rx.el.div(
        *[
            rx.el.div(
                rx.el.div(class_name=f"{c} w-3 h-3 rounded-sm mr-1.5 flex-shrink-0"),
                rx.el.span(lbl, class_name="text-xs text-gray-600"),
                class_name="flex items-center",
            )
            for c, lbl in colores
        ],
        class_name="flex items-center gap-4 flex-wrap",
    )


def calendario_page() -> rx.Component:
    return shell(
        _modal_nuevo(),
        page_header(
            "Calendario",
            "Visualizá y agendá turnos por semana",
            action=rx.el.div(
                # Filtro por profesional
                rx.el.select(
                    rx.el.option("Todos los profesionales", value=""),
                    rx.foreach(
                        CalendarioState.profesionales_cat,
                        lambda o: rx.el.option(o["nombre"], value=o["id"]),
                    ),
                    value=CalendarioState.filtro_profesional_id,
                    on_change=CalendarioState.set_filtro_profesional_id,
                    class_name="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                # Navegación semana
                rx.el.div(
                    rx.el.button(
                        rx.icon("chevron-left", size=16),
                        on_click=CalendarioState.semana_anterior,
                        class_name="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                        title="Semana anterior (← flecha izq)",
                    ),
                    rx.el.button(
                        "Hoy",
                        on_click=CalendarioState.ir_a_hoy,
                        class_name="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer text-gray-600",
                    ),
                    rx.el.button(
                        rx.icon("chevron-right", size=16),
                        on_click=CalendarioState.semana_siguiente,
                        class_name="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                        title="Semana siguiente (→ flecha der)",
                    ),
                    class_name="flex gap-1",
                ),
                rx.el.button(
                    rx.icon("plus", size=16),
                    rx.el.span("Nuevo turno", class_name="ml-1.5"),
                    on_click=lambda: CalendarioState.abrir_nuevo(""),
                    class_name="inline-flex items-center px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 cursor-pointer shadow-sm",
                ),
                class_name="flex items-center gap-3 flex-wrap",
            ),
        ),
        # Leyenda
        rx.el.div(_leyenda(), class_name="mb-4"),
        # Grilla semanal
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    # Header: días
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("", class_name="w-14 px-2 py-2 text-xs text-gray-400 font-medium sticky left-0 bg-white z-10"),
                            rx.foreach(
                                CalendarioState.dias_semana,
                                lambda d: rx.el.th(
                                    rx.el.div(
                                        d["label"],
                                        rx.cond(
                                            d["count"],
                                            rx.el.span(
                                                d["count"],
                                                class_name="ml-1.5 inline-flex items-center justify-center w-5 h-5 text-xs bg-sky-600 text-white rounded-full",
                                            ),
                                        ),
                                        class_name="flex items-center justify-center gap-1",
                                    ),
                                    class_name="px-2 py-3 text-xs font-semibold text-gray-700 text-center border-b border-gray-200 min-w-28",
                                ),
                            ),
                        ),
                        class_name="bg-gray-50",
                    ),
                    # Body: horas x días
                    rx.el.tbody(
                        rx.foreach(
                            CalendarioState.grilla_horas,
                            lambda fila: rx.el.tr(
                                rx.el.td(
                                    fila["hora"],
                                    class_name="px-2 py-2 text-xs text-gray-400 font-mono text-right align-top sticky left-0 bg-white border-r border-gray-100 w-14",
                                ),
                                rx.foreach(fila["celdas"].to(list[dict]), _celda_hora_dia),
                                class_name="border-b border-gray-50 hover:bg-gray-50/50 transition",
                            ),
                        ),
                    ),
                    class_name="w-full border-collapse text-sm",
                ),
                class_name="overflow-x-auto",
            ),
            class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
        ),
        on_mount=CalendarioState.on_mount,
    )
