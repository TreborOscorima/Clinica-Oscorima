from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.state.notas_clinicas import NotasClinicasState

_TIPOS = ["evolucion", "anamnesis", "diagnostico", "indicacion", "otro"]
_TIPOS_LABELS = {
    "evolucion":   "Evolución",
    "anamnesis":   "Anamnesis",
    "diagnostico": "Diagnóstico",
    "indicacion":  "Indicación",
    "otro":        "Otro",
}

_TIPO_COLORS = {
    "evolucion":   "bg-sky-100 text-sky-700",
    "anamnesis":   "bg-purple-100 text-purple-700",
    "diagnostico": "bg-amber-100 text-amber-700",
    "indicacion":  "bg-green-100 text-green-700",
    "otro":        "bg-gray-100 text-gray-600",
}


def _tipo_badge(tipo: str) -> rx.Component:
    return rx.el.span(
        rx.match(
            tipo,
            ("evolucion",   "Evolución"),
            ("anamnesis",   "Anamnesis"),
            ("diagnostico", "Diagnóstico"),
            ("indicacion",  "Indicación"),
            "Otro",
        ),
        class_name=rx.match(
            tipo,
            ("evolucion",   "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-sky-100 text-sky-700"),
            ("anamnesis",   "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700"),
            ("diagnostico", "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700"),
            ("indicacion",  "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700"),
            "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600",
        ),
    )


def _modal_nota() -> rx.Component:
    return rx.cond(
        NotasClinicasState.modal_abierto,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=NotasClinicasState.cerrar_modal,
            ),
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.h2(
                        rx.cond(NotasClinicasState.editar_id != 0, "Editar nota", "Nueva nota clínica"),
                        class_name="text-lg font-semibold text-gray-900",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=NotasClinicasState.cerrar_modal,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between mb-5",
                ),
                # Paciente info
                rx.el.div(
                    rx.icon("user", size=14, class_name="text-gray-400 mr-1"),
                    rx.el.span(NotasClinicasState.paciente_nombre, class_name="text-sm text-gray-600"),
                    class_name="flex items-center mb-4 bg-gray-50 px-3 py-2 rounded-lg",
                ),
                # Tipo
                rx.el.div(
                    rx.el.label("Tipo de nota", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.select(
                        rx.el.option("Evolución",   value="evolucion"),
                        rx.el.option("Anamnesis",   value="anamnesis"),
                        rx.el.option("Diagnóstico", value="diagnostico"),
                        rx.el.option("Indicación",  value="indicacion"),
                        rx.el.option("Otro",        value="otro"),
                        value=NotasClinicasState.form_tipo,
                        on_change=NotasClinicasState.set_form_tipo,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    class_name="mb-4",
                ),
                # Turno ID (opcional)
                rx.el.div(
                    rx.el.label("ID de turno (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.debounce_input(
                        rx.el.input(
                            type="text",
                            placeholder="Ej: 42",
                            value=NotasClinicasState.form_turno_id,
                            on_change=NotasClinicasState.set_form_turno_id,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        debounce_timeout=300,
                    ),
                    class_name="mb-4",
                ),
                # Contenido
                rx.el.div(
                    rx.el.label("Contenido *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.debounce_input(
                        rx.el.textarea(
                            placeholder="Escribí la nota clínica aquí…",
                            value=NotasClinicasState.form_contenido,
                            on_change=NotasClinicasState.set_form_contenido,
                            rows=6,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none",
                        ),
                        debounce_timeout=300,
                    ),
                    class_name="mb-4",
                ),
                # Error
                rx.cond(
                    NotasClinicasState.form_error != "",
                    rx.el.p(
                        NotasClinicasState.form_error,
                        class_name="mb-3 text-sm text-red-600 bg-red-50 p-2 rounded",
                    ),
                ),
                # Botones
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=NotasClinicasState.cerrar_modal,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            NotasClinicasState.is_saving,
                            rx.el.div(
                                rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                "Guardando…",
                                class_name="flex items-center",
                            ),
                            "Guardar nota",
                        ),
                        on_click=NotasClinicasState.guardar,
                        disabled=NotasClinicasState.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _fila_nota(n: dict) -> rx.Component:
    return rx.el.div(
        # Header de la nota
        rx.el.div(
            rx.el.div(
                _tipo_badge(n["tipo"]),
                rx.cond(
                    n["turno_id"],
                    rx.el.span(
                        rx.icon("calendar-clock", size=12, class_name="mr-1"),
                        "Turno #", n["turno_id"],
                        class_name="flex items-center text-xs text-gray-400 ml-2",
                    ),
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.el.span(n["created_at"], class_name="text-xs text-gray-400 mr-3"),
                rx.cond(
                    n["profesional_nombre"],
                    rx.el.span(n["profesional_nombre"], class_name="text-xs text-gray-500 mr-3"),
                ),
                rx.el.button(
                    rx.icon("pencil", size=14),
                    on_click=lambda: NotasClinicasState.abrir_editar(n),
                    class_name="p-1 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded cursor-pointer transition",
                    title="Editar",
                ),
                rx.el.button(
                    rx.icon("trash-2", size=14),
                    on_click=lambda: NotasClinicasState.eliminar(n["id"]),
                    class_name="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer transition",
                    title="Eliminar",
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="flex items-center justify-between",
        ),
        # Contenido
        rx.el.p(
            n["contenido"],
            class_name="mt-2 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed",
        ),
        class_name="bg-white rounded-xl border border-gray-100 shadow-sm p-4 hover:shadow-md transition",
    )


def notas_clinicas_page() -> rx.Component:
    return shell(
        _modal_nota(),
        # Header
        rx.el.div(
            rx.el.div(
                rx.el.h1("Historia Clínica", class_name="text-xl font-semibold text-gray-900"),
                rx.el.p(
                    rx.cond(
                        NotasClinicasState.paciente_nombre != "",
                        NotasClinicasState.paciente_nombre,
                        "Seleccioná un paciente desde la ficha",
                    ),
                    class_name="text-sm text-gray-500",
                ),
            ),
            rx.cond(
                NotasClinicasState.paciente_id != 0,
                rx.el.button(
                    rx.icon("plus", size=16),
                    "Nueva nota",
                    on_click=NotasClinicasState.abrir_nueva,
                    class_name="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
            ),
            class_name="flex items-center justify-between mb-6",
        ),
        # Sin paciente seleccionado
        rx.cond(
            NotasClinicasState.paciente_id == 0,
            rx.el.div(
                rx.icon("file-text", size=48, class_name="text-gray-300 mb-4"),
                rx.el.p("No hay paciente seleccionado", class_name="text-gray-500 font-medium"),
                rx.el.p(
                    "Accedé a esta sección desde la ficha de un paciente",
                    class_name="text-sm text-gray-400 mt-1",
                ),
                rx.el.a(
                    rx.icon("users", size=14, class_name="mr-2"),
                    "Ir a Pacientes",
                    href="/pacientes",
                    class_name="flex items-center mt-4 px-4 py-2 bg-sky-600 text-white text-sm rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
                class_name="flex flex-col items-center justify-center py-20 text-center",
            ),
            # Lista de notas
            rx.el.div(
                rx.cond(
                    NotasClinicasState.total == 0,
                    rx.el.div(
                        rx.icon("clipboard", size=40, class_name="text-gray-300 mb-3"),
                        rx.el.p("Sin notas clínicas", class_name="text-gray-500"),
                        rx.el.p("Creá la primera nota para este paciente", class_name="text-sm text-gray-400"),
                        class_name="flex flex-col items-center py-16 text-center",
                    ),
                    rx.el.div(
                        rx.foreach(NotasClinicasState.notas.to(list[dict]), _fila_nota),
                        class_name="space-y-3",
                    ),
                ),
                # Paginación
                rx.cond(
                    NotasClinicasState.total_pages > 1,
                    rx.el.div(
                        rx.el.button(
                            rx.icon("chevron-left", size=15), "Anterior",
                            on_click=NotasClinicasState.prev_page,
                            disabled=NotasClinicasState.page <= 1,
                            class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 cursor-pointer",
                        ),
                        rx.el.span(
                            NotasClinicasState.page, " / ", NotasClinicasState.total_pages,
                            class_name="text-sm text-gray-500",
                        ),
                        rx.el.button(
                            "Siguiente", rx.icon("chevron-right", size=15),
                            on_click=NotasClinicasState.next_page,
                            disabled=NotasClinicasState.page >= NotasClinicasState.total_pages,
                            class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 cursor-pointer",
                        ),
                        class_name="flex items-center justify-between mt-4",
                    ),
                ),
            ),
        ),
        on_mount=NotasClinicasState.on_mount,
    )
