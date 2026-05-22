from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.state.profesionales import ProfesionalesState

# ── Helpers de campo ──────────────────────────────────────────────────────────

def _label(text: str, required: bool = False) -> rx.Component:
    return rx.el.label(
        text,
        rx.cond(required, rx.el.span(" *", class_name="text-red-500"), rx.fragment()),
        class_name="block text-sm font-medium text-gray-700 mb-1",
    )


def _input(placeholder: str, value, on_change, type_: str = "text") -> rx.Component:
    return rx.el.input(
        placeholder=placeholder,
        value=value,
        on_change=on_change,
        type=type_,
        class_name=(
            "w-full px-3 py-2 text-sm border border-gray-300 rounded-lg "
            "focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
        ),
    )


# ── Modal crear / editar ──────────────────────────────────────────────────────

def _modal() -> rx.Component:
    titulo = rx.cond(
        ProfesionalesState.editando_id > 0,
        "Editar profesional",
        "Nuevo profesional",
    )
    return rx.cond(
        ProfesionalesState.modal_abierto,
        rx.el.div(
            # backdrop
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=ProfesionalesState.cerrar_modal,
            ),
            # panel
            rx.el.div(
                # header
                rx.el.div(
                    rx.el.h2(titulo, class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=ProfesionalesState.cerrar_modal,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between mb-6",
                ),
                # body — 2 columnas
                rx.el.div(
                    # fila 1
                    rx.el.div(
                        rx.el.div(
                            _label("Nombres", required=True),
                            _input("Ej: Juan Carlos", ProfesionalesState.form_nombres, ProfesionalesState.set_form_nombres),
                        ),
                        rx.el.div(
                            _label("Apellidos", required=True),
                            _input("Ej: Gómez", ProfesionalesState.form_apellidos, ProfesionalesState.set_form_apellidos),
                        ),
                        class_name="grid grid-cols-2 gap-4",
                    ),
                    # fila 2
                    rx.el.div(
                        rx.el.div(
                            _label("DNI / Documento"),
                            _input("Ej: 12345678", ProfesionalesState.form_dni, ProfesionalesState.set_form_dni),
                        ),
                        rx.el.div(
                            _label("Matrícula"),
                            _input("Ej: MP-12345", ProfesionalesState.form_matricula, ProfesionalesState.set_form_matricula),
                        ),
                        class_name="grid grid-cols-2 gap-4",
                    ),
                    # fila 3
                    rx.el.div(
                        _label("Especialidad"),
                        _input("Ej: Dermatología estética", ProfesionalesState.form_especialidad, ProfesionalesState.set_form_especialidad),
                    ),
                    # fila 4
                    rx.el.div(
                        rx.el.div(
                            _label("Teléfono"),
                            _input("Ej: +54 9 11 1234-5678", ProfesionalesState.form_telefono, ProfesionalesState.set_form_telefono, type_="tel"),
                        ),
                        rx.el.div(
                            _label("Email"),
                            _input("profesional@clinica.com", ProfesionalesState.form_email, ProfesionalesState.set_form_email, type_="email"),
                        ),
                        class_name="grid grid-cols-2 gap-4",
                    ),
                    class_name="space-y-4",
                ),
                # error
                rx.cond(
                    ProfesionalesState.form_error != "",
                    rx.el.p(
                        ProfesionalesState.form_error,
                        class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded-lg",
                    ),
                ),
                # footer
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=ProfesionalesState.cerrar_modal,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            ProfesionalesState.is_saving,
                            rx.el.div(
                                rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                "Guardando...",
                                class_name="flex items-center",
                            ),
                            "Guardar",
                        ),
                        on_click=ProfesionalesState.guardar,
                        disabled=ProfesionalesState.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


# ── Fila de tabla ─────────────────────────────────────────────────────────────

def _fila(prof: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        prof["nombres"].to(str)[0],
                        class_name="text-white text-sm font-semibold",
                    ),
                    class_name="w-9 h-9 rounded-full bg-sky-500 flex items-center justify-center flex-shrink-0",
                ),
                rx.el.div(
                    rx.el.p(prof["nombre_completo"], class_name="text-sm font-medium text-gray-900"),
                    rx.el.p(prof["especialidad"], class_name="text-xs text-gray-500"),
                ),
                class_name="flex items-center gap-3",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span(
                prof["dni"],
                class_name="text-sm text-gray-700",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span(prof["matricula"], class_name="text-sm text-gray-700"),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span(prof["telefono"], class_name="text-sm text-gray-700"),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span(prof["email"], class_name="text-sm text-gray-500"),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", size=15),
                    on_click=ProfesionalesState.abrir_editar(prof),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded-lg cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("trash-2", size=15),
                    on_click=ProfesionalesState.eliminar(prof["id"]),
                    class_name="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg cursor-pointer",
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50 transition-colors",
    )


# ── Página principal ──────────────────────────────────────────────────────────

def profesionales_page() -> rx.Component:
    return shell(
        _modal(),
        # header
        rx.el.div(
            rx.el.div(
                rx.el.h1("Profesionales", class_name="text-2xl font-bold text-gray-900"),
                rx.el.p(
                    ProfesionalesState.total.to(str) + " registrados",
                    class_name="text-sm text-gray-500 mt-0.5",
                ),
            ),
            rx.el.button(
                rx.icon("user-plus", size=16, class_name="mr-2"),
                "Nuevo profesional",
                on_click=ProfesionalesState.abrir_nuevo,
                class_name=(
                    "flex items-center px-4 py-2 bg-sky-600 text-white text-sm "
                    "font-medium rounded-lg hover:bg-sky-700 cursor-pointer"
                ),
            ),
            class_name="flex items-start justify-between mb-6",
        ),
        # buscador
        rx.el.div(
            rx.el.div(
                rx.icon("search", size=16, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"),
                rx.el.input(
                    placeholder="Buscar por nombre, DNI, matrícula o especialidad…",
                    value=ProfesionalesState.busqueda,
                    on_change=ProfesionalesState.set_busqueda,
                    class_name="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                class_name="relative",
            ),
            class_name="mb-5",
        ),
        # tabla
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        *[
                            rx.el.th(h, class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider")
                            for h in ["Profesional", "DNI", "Matrícula", "Teléfono", "Email", ""]
                        ]
                    ),
                    class_name="bg-gray-50 border-b border-gray-200",
                ),
                rx.el.tbody(
                    rx.cond(
                        ProfesionalesState.profesionales,
                        rx.foreach(ProfesionalesState.profesionales, _fila),
                        rx.el.tr(
                            rx.el.td(
                                rx.el.div(
                                    rx.icon("users", size=40, class_name="text-gray-300 mb-3"),
                                    rx.el.p("No hay profesionales registrados", class_name="text-gray-500 text-sm"),
                                    rx.el.p("Hacé clic en «Nuevo profesional» para comenzar", class_name="text-gray-400 text-xs mt-1"),
                                    class_name="flex flex-col items-center py-16",
                                ),
                                col_span=6,
                                class_name="text-center",
                            )
                        ),
                    )
                ),
                class_name="w-full",
            ),
            class_name="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden",
        ),
        # paginación
        rx.cond(
            ProfesionalesState.total_pages > 1,
            rx.el.div(
                rx.el.button(
                    rx.icon("chevron-left", size=16),
                    "Anterior",
                    on_click=ProfesionalesState.prev_page,
                    disabled=ProfesionalesState.page <= 1,
                    class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                ),
                rx.el.span(
                    "Página ", ProfesionalesState.page.to(str), " de ", ProfesionalesState.total_pages.to(str),
                    class_name="text-sm text-gray-600",
                ),
                rx.el.button(
                    "Siguiente",
                    rx.icon("chevron-right", size=16),
                    on_click=ProfesionalesState.next_page,
                    disabled=ProfesionalesState.page >= ProfesionalesState.total_pages,
                    class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                ),
                class_name="flex items-center justify-center gap-4 mt-5",
            ),
        ),
        title="Profesionales",
        on_mount=ProfesionalesState.on_mount,
    )
