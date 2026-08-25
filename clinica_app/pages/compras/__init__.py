from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.stat_card import stat_card
from clinica_app.components.ui import confirm_dialog, page_header
from clinica_app.state.compras import ComprasState

from clinica_app.pages.compras._proveedores import _modal_proveedores
from clinica_app.pages.compras._nueva import _modal_nueva, _modal_nuevo_producto
from clinica_app.pages.compras._detalle import _modal_detalle
from clinica_app.pages.compras._anular import _modal_anular


def _fila_compra(c: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(rx.el.p(c["fecha"],     class_name="text-sm text-gray-700"),
                 class_name="px-4 py-3 whitespace-nowrap"),
        rx.el.td(rx.el.p(c["proveedor"], class_name="text-sm font-medium text-gray-900"),
                 class_name="px-4 py-3"),
        rx.el.td(
            rx.el.span(
                c["tipo_doc"], " ", c["numero"],
                class_name="text-xs font-mono text-gray-600 bg-gray-100 px-2 py-0.5 rounded",
            ),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        rx.el.td(
            rx.el.span("$", c["total"], class_name="text-sm font-semibold text-gray-800"),
            class_name="px-4 py-3 whitespace-nowrap text-right",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("eye", size=14, class_name="mr-1"), "Ver",
                    on_click=ComprasState.ver_detalle(c),
                    class_name="flex items-center px-2.5 py-1 text-xs font-medium text-sky-700 border border-sky-300 rounded-lg hover:bg-sky-50 cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("circle-x", size=14, class_name="mr-1"), "Anular",
                    on_click=ComprasState.confirmar_anular(c),
                    class_name="flex items-center px-2.5 py-1 text-xs font-medium text-red-600 border border-red-300 rounded-lg hover:bg-red-50 cursor-pointer",
                ),
                class_name="flex gap-2",
            ),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50 transition-colors",
    )


def compras_page() -> rx.Component:
    return shell(
        _modal_nueva(),
        _modal_detalle(),
        _modal_anular(),
        _modal_proveedores(),
        _modal_nuevo_producto(),
        confirm_dialog(ComprasState),

        page_header(
            "Compras",
            "Registrá órdenes de compra a proveedores",
            action=rx.el.div(
                rx.el.button(
                    rx.icon("users", size=15),
                    rx.el.span("Proveedores", class_name="ml-1.5"),
                    on_click=ComprasState.abrir_proveedores,
                    data_prov_action="1",
                    title="Gestionar proveedores (P)",
                    class_name="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("plus", size=16),
                    rx.el.span("Nueva compra", class_name="ml-1.5"),
                    on_click=ComprasState.abrir_nueva,
                    data_new_action="1",
                    title="Nueva compra (N)",
                    class_name="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 cursor-pointer shadow-sm",
                ),
                class_name="flex gap-2",
            ),
        ),

        # KPIs
        rx.el.div(
            stat_card(
                title="Total compras",
                value=ComprasState.total_compras.to(str),
                icon="shopping-cart",
                color="sky",
                subtitle="Órdenes registradas",
            ),
            stat_card(
                title="Total gastado",
                value=rx.el.span("$", ComprasState.total_gastado),
                icon="wallet",
                color="amber",
                subtitle="Suma de todas las compras",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6",
        ),

        # Búsqueda
        rx.el.div(
            rx.icon("search", size=15,
                    class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"),

            rx.el.input(
                placeholder="Buscar por proveedor o número…",
                on_change=ComprasState.set_busqueda,
                data_search_input="1",
                title="Buscar (/)",
                class_name="pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 w-72",
            ),
            class_name="relative mb-5",
        ),

        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Fecha",       class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Proveedor",   class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Comprobante", class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Total",       class_name="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("",            class_name="px-4 py-3"),
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(
                        rx.cond(
                            ComprasState.compras,
                            rx.foreach(ComprasState.compras, _fila_compra),
                            rx.el.tr(
                                rx.el.td(
                                    rx.el.div(
                                        rx.icon("inbox", size=32, class_name="text-gray-300 mb-2"),
                                        rx.el.p("No hay compras registradas",
                                                class_name="text-sm text-gray-400"),
                                    ),
                                    col_span=5,
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
                ComprasState.total_pages > 1,
                rx.el.div(
                    rx.el.button(
                        rx.icon("chevron-left", size=16), "Anterior",
                        on_click=ComprasState.prev_page,
                        disabled=ComprasState.page <= 1,
                        class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.span(
                        "Página ", ComprasState.page.to(str), " de ", ComprasState.total_pages.to(str),
                        class_name="text-sm text-gray-600",
                    ),
                    rx.el.button(
                        "Siguiente", rx.icon("chevron-right", size=16),
                        on_click=ComprasState.next_page,
                        disabled=ComprasState.page >= ComprasState.total_pages,
                        class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                    ),
                    class_name="flex items-center justify-center gap-4 px-4 py-3 border-t border-gray-200",
                ),
            ),
            class_name="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden",
        ),

        on_mount=ComprasState.on_mount,
    )
