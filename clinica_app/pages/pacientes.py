from __future__ import annotations

import reflex as rx

from clinica_app.components.badge import estado_badge
from clinica_app.components.layout import shell
from clinica_app.state.pacientes import PacientesState


def _modal_paciente() -> rx.Component:
    titulo = rx.cond(PacientesState.editando_id, "Editar paciente", "Nuevo paciente")
    return rx.cond(
        PacientesState.modal_abierto,
        rx.el.div(
            # Overlay
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=PacientesState.cerrar_modal,
            ),
            # Panel
            rx.el.div(
                rx.el.div(
                    rx.el.h2(titulo, class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=PacientesState.cerrar_modal,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between mb-6",
                ),
                # Campos del formulario
                rx.el.div(
                    _campo("Nombre *",          "text",  PacientesState.form_nombre,    PacientesState.set_form_nombre),
                    _campo("Documento / DNI",   "text",  PacientesState.form_documento, PacientesState.set_form_documento),
                    _campo("Email",             "email", PacientesState.form_email,     PacientesState.set_form_email),
                    _campo("Teléfono",          "text",  PacientesState.form_telefono,  PacientesState.set_form_telefono),
                    _campo("Dirección",         "text",  PacientesState.form_direccion, PacientesState.set_form_direccion),
                    _campo("Fecha nacimiento",  "date",  PacientesState.form_nacimiento, PacientesState.set_form_nacimiento),
                    _campo("Contacto emergencia", "text", PacientesState.form_emergencia, PacientesState.set_form_emergencia),
                    class_name="space-y-4",
                ),
                rx.cond(
                    PacientesState.form_error != "",
                    rx.el.p(
                        PacientesState.form_error,
                        class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded",
                    ),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=PacientesState.cerrar_modal,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            PacientesState.is_saving,
                            rx.el.div(
                                rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                "Guardando...",
                                class_name="flex items-center",
                            ),
                            "Guardar",
                        ),
                        on_click=PacientesState.guardar,
                        disabled=PacientesState.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 transition cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _campo(label: str, tipo: str, value, on_change) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.input(
            type=tipo,
            value=value,
            on_change=on_change,
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
        ),
    )


def _fila_paciente(p: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(p["nombre"], class_name="px-4 py-3 text-sm font-medium text-gray-900"),
        rx.el.td(rx.cond(p["documento"], p["documento"], "—"), class_name="px-4 py-3 text-sm text-gray-600"),
        rx.el.td(rx.cond(p["email"], p["email"], "—"), class_name="px-4 py-3 text-sm text-gray-600"),
        rx.el.td(rx.cond(p["telefono"], p["telefono"], "—"), class_name="px-4 py-3 text-sm text-gray-600"),
        rx.el.td(
            rx.el.span(
                rx.cond(p["edad"], rx.el.span(p["edad"], " años"), "—"),
                class_name="text-sm text-gray-600",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", size=15),
                    on_click=lambda: PacientesState.abrir_editar(p),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded transition cursor-pointer",
                    title="Editar",
                ),
                rx.el.button(
                    rx.icon("trash-2", size=15),
                    on_click=lambda: PacientesState.eliminar(p["id"]),
                    class_name="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition cursor-pointer",
                    title="Eliminar",
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50 transition-colors",
    )


def pacientes_page() -> rx.Component:
    return shell(
        _modal_paciente(),
        # Encabezado
        rx.el.div(
            rx.el.div(
                rx.el.h1("Pacientes", class_name="text-xl font-semibold text-gray-900"),
                rx.el.p(
                    f"{PacientesState.total} registrados",
                    class_name="text-sm text-gray-500",
                ),
            ),
            rx.el.button(
                rx.icon("plus", size=16),
                "Nuevo paciente",
                on_click=PacientesState.abrir_nuevo,
                class_name="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 transition cursor-pointer",
            ),
            class_name="flex items-center justify-between mb-6",
        ),
        # Buscador
        rx.el.div(
            rx.el.div(
                rx.icon("search", size=16, class_name="text-gray-400"),
                rx.el.input(
                    type="text",
                    placeholder="Buscar por nombre o documento...",
                    value=PacientesState.busqueda,
                    on_change=PacientesState.set_busqueda,
                    class_name="w-full outline-none text-sm text-gray-700 placeholder-gray-400 ml-2",
                ),
                class_name="flex items-center px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-sky-500",
            ),
            class_name="mb-5 max-w-md",
        ),
        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Nombre",    class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Documento", class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Email",     class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Teléfono",  class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Edad",      class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Acciones",  class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(
                        rx.foreach(PacientesState.pacientes.to(list[dict]), _fila_paciente),
                    ),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto",
            ),
            # Paginación
            rx.el.div(
                rx.el.button(
                    rx.icon("chevron-left", size=15), "Anterior",
                    on_click=PacientesState.prev_page,
                    disabled=PacientesState.page <= 1,
                    class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition",
                ),
                rx.el.span(
                    rx.el.span("Página "),
                    PacientesState.page,
                    rx.el.span(" de "),
                    PacientesState.total_pages,
                    class_name="text-sm text-gray-500",
                ),
                rx.el.button(
                    "Siguiente", rx.icon("chevron-right", size=15),
                    on_click=PacientesState.next_page,
                    disabled=PacientesState.page >= PacientesState.total_pages,
                    class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition",
                ),
                class_name="flex items-center justify-between px-4 py-3 border-t border-gray-100",
            ),
            class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
        ),
        on_mount=PacientesState.on_mount,
    )
