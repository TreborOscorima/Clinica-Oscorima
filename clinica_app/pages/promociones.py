from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.stat_card import stat_card
from clinica_app.state.promociones import PromocionesState


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tipo_badge(tipo: str | rx.Var) -> rx.Component:
    return rx.el.span(
        rx.match(
            tipo,
            ("porcentaje", "% Porcentaje"),
            ("monto_fijo", "$ Monto fijo"),
            tipo,
        ),
        class_name=rx.match(
            tipo,
            ("porcentaje", "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-700"),
            ("monto_fijo", "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700"),
            "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600",
        ),
    )


def _vigente_badge(vigente: rx.Var) -> rx.Component:
    return rx.cond(
        vigente,
        rx.el.span("Vigente",   class_name="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700"),
        rx.el.span("Inactiva",  class_name="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-500"),
    )


def _aplica_label(aplica: str | rx.Var) -> rx.Component:
    return rx.match(
        aplica,
        ("todo",      "Todo"),
        ("servicios", "Servicios"),
        ("productos", "Productos"),
        aplica,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Modal formulario
# ─────────────────────────────────────────────────────────────────────────────

def _modal_form() -> rx.Component:
    return rx.cond(
        PromocionesState.modal_form,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=PromocionesState.cerrar_form),
            rx.el.div(
                # Cabecera
                rx.el.div(
                    rx.el.h2(
                        rx.cond(PromocionesState.editando, "Editar promoción", "Nueva promoción"),
                        class_name="text-lg font-semibold text-gray-900",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=PromocionesState.cerrar_form,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between mb-5",
                ),

                # Formulario
                rx.el.div(
                    # Nombre
                    rx.el.div(
                        rx.el.label("Nombre *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            type="text",
                            placeholder="Ej: Descuento nuevos pacientes",
                            value=PromocionesState.form_nombre,
                            on_change=PromocionesState.set_form_nombre,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Descripción
                    rx.el.div(
                        rx.el.label("Descripción", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            type="text",
                            placeholder="Descripción opcional",
                            value=PromocionesState.form_descripcion,
                            on_change=PromocionesState.set_form_descripcion,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Tipo + Valor + Aplica a
                    rx.el.div(
                        rx.el.div(
                            rx.el.label("Tipo", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.select(
                                rx.el.option("% Porcentaje", value="porcentaje"),
                                rx.el.option("$ Monto fijo", value="monto_fijo"),
                                value=PromocionesState.form_tipo,
                                on_change=PromocionesState.set_form_tipo,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Valor *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.input(
                                type="text",
                                input_mode="decimal",
                                placeholder=rx.cond(
                                    PromocionesState.form_tipo == "porcentaje",
                                    "0 – 100",
                                    "0.00",
                                ),
                                value=PromocionesState.form_valor,
                                on_change=PromocionesState.set_form_valor,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Aplica a", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.select(
                                rx.el.option("Todo",      value="todo"),
                                rx.el.option("Servicios", value="servicios"),
                                rx.el.option("Productos", value="productos"),
                                value=PromocionesState.form_aplica_a,
                                on_change=PromocionesState.set_form_aplica_a,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        class_name="grid grid-cols-3 gap-3",
                    ),
                    # Fechas
                    rx.el.div(
                        rx.el.div(
                            rx.el.label("Fecha inicio", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.input(
                                type="date",
                                value=PromocionesState.form_fecha_inicio,
                                on_change=PromocionesState.set_form_fecha_inicio,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Fecha fin", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.input(
                                type="date",
                                value=PromocionesState.form_fecha_fin,
                                on_change=PromocionesState.set_form_fecha_fin,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-3",
                    ),
                    class_name="space-y-4",
                ),

                # Error
                rx.cond(
                    PromocionesState.form_error != "",
                    rx.el.div(
                        rx.icon("circle-alert", size=14, class_name="text-red-500 mr-1.5 flex-shrink-0"),
                        rx.el.span(PromocionesState.form_error, class_name="text-sm text-red-700"),
                        class_name="flex items-center mt-4 p-3 bg-red-50 border border-red-200 rounded-lg",
                    ),
                ),

                # Botones
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=PromocionesState.cerrar_form,
                        class_name="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            PromocionesState.is_saving,
                            rx.el.span(
                                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                                "Guardando…",
                                class_name="flex items-center",
                            ),
                            rx.el.span(
                                rx.cond(PromocionesState.editando, "Guardar cambios", "Crear promoción"),
                            ),
                        ),
                        on_click=PromocionesState.guardar,
                        disabled=PromocionesState.is_saving,
                        class_name="px-5 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 disabled:opacity-60 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3 mt-6",
                ),
                class_name="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg z-50 relative",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Modal eliminar
# ─────────────────────────────────────────────────────────────────────────────

def _modal_eliminar() -> rx.Component:
    return rx.cond(
        PromocionesState.modal_eliminar,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40"),
            rx.el.div(
                rx.icon("trash-2", size=36, class_name="text-red-500 mx-auto mb-4"),
                rx.el.h2("¿Eliminar promoción?", class_name="text-lg font-semibold text-gray-900 text-center mb-2"),
                rx.el.p(
                    rx.el.strong(PromocionesState.eliminar_nombre),
                    " será eliminada permanentemente.",
                    class_name="text-sm text-gray-600 text-center mb-6",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=PromocionesState.cerrar_eliminar,
                        class_name="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            PromocionesState.is_saving,
                            rx.el.span(
                                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                                "Eliminando…",
                                class_name="flex items-center",
                            ),
                            rx.el.span("Eliminar"),
                        ),
                        on_click=PromocionesState.ejecutar_eliminar,
                        disabled=PromocionesState.is_saving,
                        class_name="px-5 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-60 cursor-pointer",
                    ),
                    class_name="flex justify-center gap-3",
                ),
                class_name="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm z-50 relative",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Fila tabla
# ─────────────────────────────────────────────────────────────────────────────

def _fila_promo(p: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.p(p["nombre"], class_name="text-sm font-medium text-gray-900"),
            rx.cond(
                p["descripcion"] != "",
                rx.el.p(p["descripcion"], class_name="text-xs text-gray-400 mt-0.5 max-w-48 truncate"),
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            _tipo_badge(p["tipo"]),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        rx.el.td(
            rx.cond(
                p["tipo"] == "porcentaje",
                rx.el.span(p["valor"], "%", class_name="text-sm font-semibold text-gray-800 tabular-nums"),
                rx.el.span("$ ", p["valor"], class_name="text-sm font-semibold text-gray-800 tabular-nums"),
            ),
            class_name="px-4 py-3 whitespace-nowrap text-right",
        ),
        rx.el.td(
            _aplica_label(p["aplica_a"]),
            class_name="px-4 py-3 whitespace-nowrap text-sm text-gray-600",
        ),
        rx.el.td(
            rx.el.div(
                rx.cond(p["fecha_inicio"] != "", p["fecha_inicio"], "—"),
                " → ",
                rx.cond(p["fecha_fin"] != "", p["fecha_fin"], "sin límite"),
                class_name="text-xs text-gray-500",
            ),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        rx.el.td(
            _vigente_badge(p["vigente"]),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        rx.el.td(
            rx.el.div(
                # Toggle activo
                rx.el.button(
                    rx.cond(
                        p["activo"],
                        rx.icon("toggle-right", size=18, class_name="text-green-600"),
                        rx.icon("toggle-left",  size=18, class_name="text-gray-400"),
                    ),
                    on_click=PromocionesState.toggle_activo(p),
                    class_name="cursor-pointer hover:opacity-70",
                    title=rx.cond(p["activo"], "Desactivar", "Activar"),
                ),
                # Editar
                rx.el.button(
                    rx.icon("pencil", size=14),
                    on_click=PromocionesState.abrir_editar(p),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 cursor-pointer",
                    title="Editar",
                ),
                # Eliminar
                rx.el.button(
                    rx.icon("trash-2", size=14),
                    on_click=PromocionesState.confirmar_eliminar(p),
                    class_name="p-1.5 text-gray-400 hover:text-red-600 cursor-pointer",
                    title="Eliminar",
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50 transition-colors",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Página principal
# ─────────────────────────────────────────────────────────────────────────────

def promociones_page() -> rx.Component:
    return shell(
        _modal_form(),
        _modal_eliminar(),
        # Header
        rx.el.div(
            rx.el.div(
                rx.el.h1("Promociones", class_name="text-2xl font-bold text-gray-900"),
                rx.el.p(
                    PromocionesState.total.to(str), " registros",
                    class_name="text-sm text-gray-500 mt-0.5",
                ),
            ),
            rx.el.button(
                rx.icon("plus", size=16, class_name="mr-1.5"),
                "Nueva promoción",
                on_click=PromocionesState.abrir_nueva,
                class_name="flex items-center px-4 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 cursor-pointer",
            ),
            class_name="flex items-center justify-between mb-6",
        ),
        # KPI
        rx.el.div(
            stat_card(
                title="Promociones activas",
                value=PromocionesState.total_activas.to(str),
                icon="tag",
                color="green",
                subtitle="Con estado activo",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6",
        ),
        # Filtros
        rx.el.div(
            rx.el.div(
                rx.icon("search", size=15, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"),
                rx.el.input(
                    placeholder="Buscar promoción…",
                    value=PromocionesState.busqueda,
                    on_change=PromocionesState.set_busqueda,
                    class_name="pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 w-64",
                ),
                class_name="relative",
            ),
            rx.el.button(
                rx.icon("filter", size=14, class_name="mr-1.5"),
                rx.cond(PromocionesState.solo_activas, "Solo activas ✓", "Todas"),
                on_click=PromocionesState.toggle_solo_activas,
                class_name=rx.cond(
                    PromocionesState.solo_activas,
                    "flex items-center px-3 py-2 text-sm font-medium rounded-lg bg-sky-600 text-white cursor-pointer",
                    "flex items-center px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer",
                ),
            ),
            class_name="flex items-center gap-3 mb-5",
        ),
        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Nombre",    class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Tipo",      class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Valor",     class_name="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Aplica a",  class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Vigencia",  class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Estado",    class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("",          class_name="px-4 py-3"),
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(
                        rx.cond(
                            PromocionesState.promociones,
                            rx.foreach(PromocionesState.promociones, _fila_promo),
                            rx.el.tr(
                                rx.el.td(
                                    rx.el.div(
                                        rx.icon("tag", size=32, class_name="text-gray-300 mb-2"),
                                        rx.el.p("No hay promociones registradas", class_name="text-sm text-gray-400"),
                                    ),
                                    col_span=7,
                                    class_name="py-16 text-center",
                                ),
                            ),
                        ),
                    ),
                    class_name="w-full",
                ),
                class_name="overflow-x-auto",
            ),
            # Paginación
            rx.cond(
                PromocionesState.total_pages > 1,
                rx.el.div(
                    rx.el.button(
                        rx.icon("chevron-left", size=16), "Anterior",
                        on_click=PromocionesState.prev_page,
                        disabled=PromocionesState.page <= 1,
                        class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.span(
                        "Página ", PromocionesState.page.to(str), " de ", PromocionesState.total_pages.to(str),
                        class_name="text-sm text-gray-600",
                    ),
                    rx.el.button(
                        "Siguiente", rx.icon("chevron-right", size=16),
                        on_click=PromocionesState.next_page,
                        disabled=PromocionesState.page >= PromocionesState.total_pages,
                        class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                    ),
                    class_name="flex items-center justify-center gap-4 px-4 py-3 border-t border-gray-200",
                ),
            ),
            class_name="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden",
        ),
        on_mount=PromocionesState.on_mount,
    )
