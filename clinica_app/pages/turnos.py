from __future__ import annotations

import reflex as rx

from clinica_app.components.badge import estado_badge
from clinica_app.components.layout import shell
from clinica_app.state.turnos import TurnosState

_ESTADOS = ["", "pendiente", "confirmado", "atendido", "cancelado"]
_ESTADOS_LABELS = ["Todos", "Pendiente", "Confirmado", "Atendido", "Cancelado"]


def _modal_nuevo() -> rx.Component:
    return rx.cond(
        TurnosState.modal_nuevo,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=TurnosState.cerrar_nuevo),
            rx.el.div(
                rx.el.div(
                    rx.el.h2("Nuevo turno", class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(rx.icon("x", size=18), on_click=TurnosState.cerrar_nuevo,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between mb-6",
                ),
                rx.el.div(
                    _select_field("Paciente *", TurnosState.pacientes_cat,
                                  TurnosState.form_paciente_id,
                                  TurnosState.set_form_paciente_id),
                    _select_field("Profesional", TurnosState.profesionales_cat,
                                  TurnosState.form_profesional_id,
                                  TurnosState.set_form_profesional_id, required=False),
                    _input_field("Fecha y hora *", "datetime-local",
                                 TurnosState.form_fecha_hora, TurnosState.set_form_fecha_hora),
                    class_name="space-y-4",
                ),
                rx.cond(
                    TurnosState.form_error != "",
                    rx.el.p(TurnosState.form_error, class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded"),
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=TurnosState.cerrar_nuevo,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        rx.cond(TurnosState.is_saving,
                                rx.el.div(rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"), "Guardando...",
                                          class_name="flex items-center"),
                                "Guardar"),
                        on_click=TurnosState.guardar_turno, disabled=TurnosState.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer disabled:bg-sky-400",
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_estado() -> rx.Component:
    return rx.cond(
        TurnosState.modal_estado,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=TurnosState.cerrar_estado),
            rx.el.div(
                rx.el.h2("Cambiar estado", class_name="text-lg font-semibold text-gray-900 mb-4"),
                rx.el.div(
                    rx.el.label("Estado", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.select(
                        rx.el.option("Pendiente", value="pendiente"),
                        rx.el.option("Confirmado", value="confirmado"),
                        rx.el.option("Atendido", value="atendido"),
                        rx.el.option("Cancelado", value="cancelado"),
                        value=TurnosState.form_nuevo_estado,
                        on_change=TurnosState.set_form_nuevo_estado,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    class_name="mb-4",
                ),
                rx.cond(
                    TurnosState.form_nuevo_estado == "cancelado",
                    rx.el.div(
                        rx.el.label("Motivo (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.textarea(
                            value=TurnosState.form_motivo,
                            on_change=TurnosState.set_form_motivo,
                            rows=3,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="mb-4",
                    ),
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=TurnosState.cerrar_estado,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button("Guardar", on_click=TurnosState.guardar_estado,
                                 class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer"),
                    class_name="flex gap-3 justify-end",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _input_field(label, tipo, value, on_change) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.input(type=tipo, value=value, on_change=on_change,
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"),
    )


def _select_field(label, options, value, on_change, required=True) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.select(
            rx.cond(not required, rx.el.option("— Sin asignar —", value="")),
            rx.foreach(options, lambda o: rx.el.option(o["nombre"], value=o["id"])),
            value=value,
            on_change=on_change,
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
        ),
    )


def _fila_turno(t: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(rx.cond(t["paciente_nombre"], t["paciente_nombre"], "—"), class_name="px-4 py-3 text-sm font-medium text-gray-900"),
        rx.el.td(rx.cond(t["profesional_nombre"], t["profesional_nombre"], "—"), class_name="px-4 py-3 text-sm text-gray-600"),
        rx.el.td(rx.cond(t["servicio_nombre"], t["servicio_nombre"], "—"), class_name="px-4 py-3 text-sm text-gray-600"),
        rx.el.td(
            rx.el.span(
                t["fecha_hora"],  # servicio ya devuelve "YYYY-MM-DD HH:MM"
                class_name="text-sm text-gray-600 font-mono",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(estado_badge(t["estado"]), class_name="px-4 py-3"),
        rx.el.td(
            rx.el.button(
                rx.icon("pencil", size=15),
                on_click=lambda: TurnosState.abrir_estado(t),
                class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded cursor-pointer transition",
                title="Cambiar estado",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50 transition-colors",
    )


def turnos_page() -> rx.Component:
    return shell(
        _modal_nuevo(),
        _modal_estado(),
        # Encabezado
        rx.el.div(
            rx.el.div(
                rx.el.h1("Turnos", class_name="text-xl font-semibold text-gray-900"),
                rx.el.p(f"{TurnosState.total} registrados", class_name="text-sm text-gray-500"),
            ),
            rx.el.button(
                rx.icon("plus", size=16), "Nuevo turno",
                on_click=TurnosState.abrir_nuevo,
                class_name="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 cursor-pointer",
            ),
            class_name="flex items-center justify-between mb-6",
        ),
        # Filtros de estado
        rx.el.div(
            rx.foreach(
                list(zip(_ESTADOS, _ESTADOS_LABELS)),
                lambda pair: rx.el.button(
                    pair[1],
                    on_click=lambda: TurnosState.set_filtro_estado(pair[0]),
                    class_name=rx.cond(
                        TurnosState.filtro_estado == pair[0],
                        "px-4 py-1.5 text-sm font-medium rounded-full bg-sky-600 text-white",
                        "px-4 py-1.5 text-sm font-medium rounded-full bg-white border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer",
                    ),
                ),
            ),
            class_name="flex gap-2 mb-5 flex-wrap",
        ),
        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            *[rx.el.th(h, class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase")
                              for h in ["Paciente", "Profesional", "Servicio", "Fecha/hora", "Estado", ""]],
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(rx.foreach(TurnosState.turnos.to(list[dict]), _fila_turno)),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto",
            ),
            rx.el.div(
                rx.el.button(rx.icon("chevron-left", size=15), "Anterior",
                             on_click=TurnosState.prev_page, disabled=TurnosState.page <= 1,
                             class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 cursor-pointer"),
                rx.el.span(TurnosState.page, " / ", TurnosState.total_pages, class_name="text-sm text-gray-500"),
                rx.el.button("Siguiente", rx.icon("chevron-right", size=15),
                             on_click=TurnosState.next_page, disabled=TurnosState.page >= TurnosState.total_pages,
                             class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 cursor-pointer"),
                class_name="flex items-center justify-between px-4 py-3 border-t border-gray-100",
            ),
            class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
        ),
        on_mount=TurnosState.on_mount,
    )
