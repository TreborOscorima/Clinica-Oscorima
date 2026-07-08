from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.servicios import ServiciosState

# ── Helpers ───────────────────────────────────────────────────────────────────


def _label(text: str, required: bool = False) -> rx.Component:
    return rx.el.label(
        text,
        rx.cond(required, rx.el.span(" *", class_name="text-red-500"), rx.fragment()),
        class_name="block text-sm font-medium text-gray-700 mb-1",
    )


def _input(placeholder: str, value, on_change, type_: str = "text") -> rx.Component:
    return rx.el.input(
        placeholder=placeholder,
        default_value=value,
        on_change=on_change,
        type=type_,
        class_name=(
            "w-full px-3 py-2 text-sm border border-gray-300 rounded-lg "
            "focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
        ),
    )


def _textarea(placeholder: str, value, on_change, rows: int = 3) -> rx.Component:
    return rx.el.textarea(
        placeholder=placeholder,
        default_value=value,
        on_change=on_change,
        rows=rows,
        class_name=(
            "w-full px-3 py-2 text-sm border border-gray-300 rounded-lg resize-none "
            "focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
        ),
    )


# ── Modal ─────────────────────────────────────────────────────────────────────

def _modal() -> rx.Component:
    titulo = rx.cond(
        ServiciosState.editando_id > 0,
        "Editar servicio",
        "Nuevo servicio",
    )
    return rx.cond(
        ServiciosState.modal_abierto,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=ServiciosState.cerrar_modal,
            ),
            rx.el.div(
                # header
                rx.el.div(
                    rx.el.h2(titulo, class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=ServiciosState.cerrar_modal,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                # form
                rx.el.div(
                    # nombre
                    rx.el.div(
                        _label("Nombre del servicio", required=True),
                        _input("Ej: Limpieza facial profunda", ServiciosState.form_nombre, ServiciosState.set_form_nombre),
                    ),
                    # categoria
                    rx.el.div(
                        _label("Categoría"),
                        rx.el.div(
                            rx.el.select(
                                rx.el.option("— Seleccionar existente —", value=""),
                                rx.foreach(
                                    ServiciosState.categorias_cat,
                                    lambda c: rx.el.option(c, value=c),
                                ),
                                default_value=ServiciosState.form_categoria,
                                on_change=ServiciosState.set_form_categoria,
                                class_name="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                            rx.el.span("o", class_name="text-xs text-gray-400 px-2"),
                            _input("Nueva categoría…", ServiciosState.form_nueva_cat, ServiciosState.set_form_nueva_cat),
                            class_name="flex items-center gap-2",
                        ),
                    ),
                    # precio + duración
                    rx.el.div(
                        rx.el.div(
                            _label("Precio ($)"),
                            _input("0.00", ServiciosState.form_precio, ServiciosState.set_form_precio, type_="number"),
                        ),
                        rx.el.div(
                            _label("Duración (min)"),
                            _input("30", ServiciosState.form_duracion_min, ServiciosState.set_form_duracion_min, type_="number"),
                        ),
                        class_name="grid grid-cols-2 gap-4",
                    ),
                    # descripción
                    rx.el.div(
                        _label("Descripción"),
                        _textarea(
                            "Descripción del servicio para el paciente…",
                            ServiciosState.form_descripcion,
                            ServiciosState.set_form_descripcion,
                            rows=2,
                        ),
                    ),
                    # protocolo
                    rx.el.div(
                        _label("Protocolo / Notas internas"),
                        _textarea(
                            "Pasos del procedimiento, consideraciones, etc.",
                            ServiciosState.form_protocolo,
                            ServiciosState.set_form_protocolo,
                            rows=3,
                        ),
                    ),
                    class_name="space-y-4",
                ),
                # error
                rx.cond(
                    ServiciosState.form_error != "",
                    rx.el.p(
                        ServiciosState.form_error,
                        class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded-lg",
                    ),
                ),
                # footer
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=ServiciosState.cerrar_modal,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            ServiciosState.is_saving,
                            rx.el.div(
                                rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                "Guardando…",
                                class_name="flex items-center",
                            ),
                            "Guardar",
                        ),
                        on_click=ServiciosState.guardar,
                        disabled=ServiciosState.is_saving,
                        data_modal_submit="1",
                        title="Guardar (Ctrl+Enter)",
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50 max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


# ── Card de servicio ──────────────────────────────────────────────────────────

def _card(srv: dict) -> rx.Component:
    return rx.el.div(
        # top: nombre + badge categoría
        rx.el.div(
            rx.el.div(
                rx.el.p(srv["nombre"], class_name="text-sm font-semibold text-gray-900 leading-tight"),
                rx.cond(
                    srv["categoria"] != "",
                    rx.el.span(
                        srv["categoria"],
                        class_name="inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-sky-100 text-sky-700",
                    ),
                ),
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", size=14),
                    on_click=ServiciosState.abrir_editar(srv),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded-lg cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("trash-2", size=14),
                    on_click=ServiciosState.eliminar(srv["id"]),
                    class_name="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg cursor-pointer",
                ),
                class_name="flex items-center gap-0.5 flex-shrink-0",
            ),
            class_name="flex items-start justify-between",
        ),
        # descripción
        rx.cond(
            srv["descripcion"] != "",
            rx.el.p(
                srv["descripcion"],
                class_name="mt-2 text-xs text-gray-500 line-clamp-2",
            ),
        ),
        # footer: precio + duración
        rx.el.div(
            rx.el.div(
                rx.icon("dollar-sign", size=14, class_name="text-emerald-600 mr-0.5"),
                rx.el.span(srv["precio"], class_name="text-sm font-semibold text-emerald-700"),
                class_name="flex items-center",
            ),
            rx.el.div(
                rx.icon("clock", size=13, class_name="text-gray-400 mr-1"),
                rx.el.span(srv["duracion_min"].to(str), " min", class_name="text-xs text-gray-500"),
                class_name="flex items-center",
            ),
            class_name="flex items-center justify-between mt-3 pt-3 border-t border-gray-100",
        ),
        class_name=(
            "bg-white rounded-xl border border-gray-200 shadow-sm p-4 "
            "hover:shadow-md hover:border-sky-200 transition-all"
        ),
    )


# ── Página principal ──────────────────────────────────────────────────────────

def servicios_page() -> rx.Component:
    return shell(
        _modal(),
        page_header(
            "Servicios",
            "Catálogo de servicios médicos y estéticos",
            action=rx.el.button(
                rx.icon("plus", size=16),
                rx.el.span("Nuevo servicio", class_name="ml-1.5"),
                on_click=ServiciosState.abrir_nuevo,
                data_new_action="1",
                title="Nuevo servicio (N)",
                class_name="inline-flex items-center px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 cursor-pointer shadow-sm",
            ),
        ),
        # filtros
        rx.el.div(
            # buscador
            rx.el.div(
                rx.icon("search", size=16, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"),
                
                rx.el.input(
                    placeholder="Buscar servicio…",
                    on_change=ServiciosState.set_busqueda,
                    data_search_input="1",
                    title="Buscar (/)",
                    class_name="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                class_name="relative flex-1",
            ),
            # filtro categoría
            rx.el.select(
                rx.el.option("Todas las categorías", value=""),
                rx.foreach(
                    ServiciosState.categorias_cat,
                    lambda c: rx.el.option(c, value=c),
                ),
                default_value=ServiciosState.filtro_cat,
                on_change=ServiciosState.set_filtro_cat,
                class_name="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white",
            ),
            class_name="flex gap-3 mb-6",
        ),
        # grid de cards
        rx.cond(
            ServiciosState.servicios,
            rx.el.div(
                rx.foreach(ServiciosState.servicios, _card),
                class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4",
            ),
            # vacío
            rx.el.div(
                rx.icon("stethoscope", size=48, class_name="text-gray-300 mb-3"),
                rx.el.p("No hay servicios registrados", class_name="text-gray-500 font-medium"),
                rx.el.p(
                    "Hacé clic en «Nuevo servicio» para agregar el primero",
                    class_name="text-gray-400 text-sm mt-1",
                ),
                rx.el.button(
                    rx.icon("plus", size=16, class_name="mr-2"),
                    "Crear primer servicio",
                    on_click=ServiciosState.abrir_nuevo,
                    class_name="mt-4 flex items-center px-4 py-2 bg-sky-600 text-white text-sm rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
                class_name="flex flex-col items-center py-20 text-center",
            ),
        ),
        # paginación
        rx.cond(
            ServiciosState.total_pages > 1,
            rx.el.div(
                rx.el.button(
                    rx.icon("chevron-left", size=16),
                    "Anterior",
                    on_click=ServiciosState.prev_page,
                    disabled=ServiciosState.page <= 1,
                    class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                ),
                rx.el.span(
                    "Página ", ServiciosState.page.to(str), " de ", ServiciosState.total_pages.to(str),
                    class_name="text-sm text-gray-600",
                ),
                rx.el.button(
                    "Siguiente",
                    rx.icon("chevron-right", size=16),
                    on_click=ServiciosState.next_page,
                    disabled=ServiciosState.page >= ServiciosState.total_pages,
                    class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                ),
                class_name="flex items-center justify-center gap-4 mt-6",
            ),
        ),
        title="Servicios",
        on_mount=ServiciosState.on_mount,
    )
