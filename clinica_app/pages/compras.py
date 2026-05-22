from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.stat_card import stat_card
from clinica_app.state.compras import ComprasState


# ─────────────────────────────────────────────────────────────────────────────
#  Modal: Nueva compra
# ─────────────────────────────────────────────────────────────────────────────

def _fila_carrito(item: dict, idx: int) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            item["producto_nombre"],
            class_name="px-3 py-2 text-sm text-gray-800",
        ),
        rx.el.td(
            item["cantidad"],
            class_name="px-3 py-2 text-sm text-right tabular-nums",
        ),
        rx.el.td(
            "$", item["costo_unitario"],
            class_name="px-3 py-2 text-sm text-right tabular-nums",
        ),
        rx.el.td(
            "$", item["subtotal"],
            class_name="px-3 py-2 text-sm font-medium text-right tabular-nums",
        ),
        rx.el.td(
            rx.el.button(
                rx.icon("trash-2", size=13),
                on_click=ComprasState.quitar_item(idx),
                class_name="text-red-400 hover:text-red-600 cursor-pointer",
            ),
            class_name="px-3 py-2 text-center",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50",
    )


def _modal_nueva() -> rx.Component:
    return rx.cond(
        ComprasState.modal_nueva,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=ComprasState.cerrar_nueva),
            rx.el.div(
                # Cabecera
                rx.el.div(
                    rx.el.h2("Nueva Compra", class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=ComprasState.cerrar_nueva,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between mb-5",
                ),

                # ── Sección: cabecera de compra ────────────────────────────────
                rx.el.p("Datos del comprobante", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3"),
                rx.el.div(
                    # Proveedor
                    rx.el.div(
                        rx.el.label("Proveedor", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.select(
                            rx.el.option("— Sin proveedor —", value=""),
                            rx.foreach(
                                ComprasState.proveedores_cat,
                                lambda p: rx.el.option(p["nombre"], value=p["id"].to(str)),
                            ),
                            value=ComprasState.form_proveedor_id,
                            on_change=ComprasState.set_form_proveedor_id,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Tipo doc + Número
                    rx.el.div(
                        rx.el.div(
                            rx.el.label("Tipo doc.", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.select(
                                rx.el.option("Factura",      value="factura"),
                                rx.el.option("Boleta",       value="boleta"),
                                rx.el.option("Nota entrega", value="nota_entrega"),
                                rx.el.option("Otro",         value="otro"),
                                value=ComprasState.form_tipo_doc,
                                on_change=ComprasState.set_form_tipo_doc,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Número", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.input(
                                type="text",
                                placeholder="Ej: F001-00123",
                                value=ComprasState.form_numero,
                                on_change=ComprasState.set_form_numero,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-3",
                    ),
                    # Nro. registro + Observación
                    rx.el.div(
                        rx.el.div(
                            rx.el.label("Nro. registro", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.input(
                                type="text",
                                placeholder="Opcional",
                                value=ComprasState.form_nro_registro,
                                on_change=ComprasState.set_form_nro_registro,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Observación", class_name="block text-sm font-medium text-gray-700 mb-1"),
                            rx.el.input(
                                type="text",
                                placeholder="Opcional",
                                value=ComprasState.form_observacion,
                                on_change=ComprasState.set_form_observacion,
                                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-3",
                    ),
                    class_name="space-y-3 mb-5",
                ),

                # ── Sección: agregar productos ─────────────────────────────────
                rx.el.p("Productos", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3"),
                rx.el.div(
                    rx.el.select(
                        rx.el.option("— Producto —", value=""),
                        rx.foreach(
                            ComprasState.productos_cat,
                            lambda p: rx.el.option(p["nombre"], value=p["id"]),
                        ),
                        value=ComprasState.cart_producto_id,
                        on_change=ComprasState.set_cart_producto_id,
                        class_name="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    rx.el.input(
                        type="text",
                        placeholder="Cant.",
                        value=ComprasState.cart_cantidad,
                        on_change=ComprasState.set_cart_cantidad,
                        class_name="w-20 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    rx.el.div(
                        rx.el.span("$", class_name="text-gray-500 text-sm px-2"),
                        rx.el.input(
                            type="text",
                            placeholder="Costo",
                            value=ComprasState.cart_costo,
                            on_change=ComprasState.set_cart_costo,
                            class_name="w-24 py-2 pr-2 text-sm outline-none",
                        ),
                        class_name="flex items-center border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-sky-500",
                    ),
                    rx.el.button(
                        rx.icon("plus", size=16),
                        on_click=ComprasState.agregar_item,
                        class_name="px-3 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer",
                    ),
                    class_name="flex gap-2 items-center mb-2",
                ),
                rx.cond(
                    ComprasState.cart_error != "",
                    rx.el.p(ComprasState.cart_error, class_name="text-xs text-red-600 mb-2"),
                ),

                # Tabla carrito
                rx.cond(
                    ComprasState.carrito,
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    rx.el.th("Producto",  class_name="px-3 py-2 text-left text-xs font-semibold text-gray-500"),
                                    rx.el.th("Cant.",     class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                                    rx.el.th("Costo",     class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                                    rx.el.th("Subtotal",  class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                                    rx.el.th("",          class_name="px-3 py-2"),
                                ),
                                class_name="bg-gray-50 border-b border-gray-200",
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    ComprasState.carrito,
                                    lambda item, idx: _fila_carrito(item, idx),
                                ),
                            ),
                            class_name="w-full text-sm",
                        ),
                        rx.el.div(
                            rx.el.span("Total", class_name="text-sm font-semibold text-gray-700"),
                            rx.el.span("$", ComprasState.carrito_total, class_name="text-sm font-bold text-gray-900"),
                            class_name="flex justify-between px-3 py-2 bg-gray-50 border-t border-gray-200",
                        ),
                        class_name="border border-gray-200 rounded-lg overflow-hidden mb-4",
                    ),
                    rx.el.p(
                        "Agrega al menos un producto",
                        class_name="text-xs text-gray-400 text-center py-4 mb-4",
                    ),
                ),

                # Error global
                rx.cond(
                    ComprasState.form_error != "",
                    rx.el.div(
                        rx.icon("circle-alert", size=14, class_name="text-red-500 mr-1.5 flex-shrink-0"),
                        rx.el.span(ComprasState.form_error, class_name="text-sm text-red-700"),
                        class_name="flex items-center p-3 bg-red-50 border border-red-200 rounded-lg mb-4",
                    ),
                ),

                # Botones
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=ComprasState.cerrar_nueva,
                        class_name="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            ComprasState.is_saving,
                            rx.el.span(
                                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                                "Guardando…",
                                class_name="flex items-center",
                            ),
                            rx.el.span("Registrar compra"),
                        ),
                        on_click=ComprasState.guardar_compra,
                        disabled=ComprasState.is_saving,
                        class_name="px-5 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 disabled:opacity-60 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3",
                ),

                class_name="bg-white rounded-2xl shadow-xl p-6 w-full max-w-2xl z-50 relative max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Modal: Detalle de compra
# ─────────────────────────────────────────────────────────────────────────────

def _modal_detalle() -> rx.Component:
    return rx.cond(
        ComprasState.modal_detalle,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=ComprasState.cerrar_detalle),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.h2("Detalle de compra", class_name="text-lg font-semibold text-gray-900"),
                        rx.el.p(
                            ComprasState.compra_sel["tipo_doc"], " ",
                            ComprasState.compra_sel["numero"],
                            class_name="text-sm text-gray-500",
                        ),
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=ComprasState.cerrar_detalle,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-start justify-between mb-4",
                ),
                # Info cabecera
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Proveedor", class_name="text-xs text-gray-500"),
                        rx.el.span(ComprasState.compra_sel["proveedor"], class_name="text-sm text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    rx.el.div(
                        rx.el.span("Fecha", class_name="text-xs text-gray-500"),
                        rx.el.span(ComprasState.compra_sel["fecha"], class_name="text-sm text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    rx.el.div(
                        rx.el.span("Nro. registro", class_name="text-xs text-gray-500"),
                        rx.el.span(ComprasState.compra_sel["nro_registro"], class_name="text-sm text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    rx.el.div(
                        rx.el.span("Observación", class_name="text-xs text-gray-500"),
                        rx.el.span(ComprasState.compra_sel["observacion"], class_name="text-sm text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    class_name="bg-gray-50 rounded-lg p-3 mb-4 space-y-1.5",
                ),
                # Tabla items
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Producto",  class_name="px-3 py-2 text-left text-xs font-semibold text-gray-500"),
                                rx.el.th("Cantidad",  class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                                rx.el.th("Costo u.", class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                                rx.el.th("Subtotal", class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                            ),
                            class_name="bg-gray-50 border-b border-gray-200",
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                ComprasState.detalle_items,
                                lambda i: rx.el.tr(
                                    rx.el.td(i["producto_nombre"], class_name="px-3 py-2 text-sm text-gray-800"),
                                    rx.el.td(i["cantidad"],        class_name="px-3 py-2 text-sm text-right tabular-nums"),
                                    rx.el.td(
                                        "$", i["costo_unitario"],
                                        class_name="px-3 py-2 text-sm text-right tabular-nums",
                                    ),
                                    rx.el.td(
                                        "$", i["subtotal"],
                                        class_name="px-3 py-2 text-sm font-medium text-right tabular-nums",
                                    ),
                                    class_name="border-b border-gray-100",
                                ),
                            ),
                        ),
                        class_name="w-full text-sm",
                    ),
                    rx.el.div(
                        rx.el.span("Total", class_name="text-sm font-semibold text-gray-700"),
                        rx.el.span("$", ComprasState.compra_sel["total"], class_name="text-sm font-bold text-gray-900"),
                        class_name="flex justify-between px-3 py-2 bg-gray-50 border-t border-gray-200",
                    ),
                    class_name="border border-gray-200 rounded-lg overflow-hidden",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cerrar",
                        on_click=ComprasState.cerrar_detalle,
                        class_name="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    class_name="flex justify-end mt-5",
                ),
                class_name="bg-white rounded-2xl shadow-xl p-6 w-full max-w-xl z-50 relative",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Modal: Confirmar anulación
# ─────────────────────────────────────────────────────────────────────────────

def _modal_anular() -> rx.Component:
    return rx.cond(
        ComprasState.modal_anular,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40"),
            rx.el.div(
                rx.icon("triangle-alert", size=36, class_name="text-amber-500 mx-auto mb-4"),
                rx.el.h2("¿Anular esta compra?", class_name="text-lg font-semibold text-gray-900 text-center mb-2"),
                rx.el.p(
                    "Se revertirá el stock de todos los productos de la compra ",
                    rx.el.strong(ComprasState.anular_numero),
                    ". Esta acción no se puede deshacer.",
                    class_name="text-sm text-gray-600 text-center mb-6",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=ComprasState.cerrar_anular,
                        class_name="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            ComprasState.is_saving,
                            rx.el.span(
                                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                                "Anulando…",
                                class_name="flex items-center",
                            ),
                            rx.el.span("Sí, anular"),
                        ),
                        on_click=ComprasState.ejecutar_anular,
                        disabled=ComprasState.is_saving,
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

def _fila_compra(c: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.p(c["fecha"],      class_name="text-sm text-gray-700"),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        rx.el.td(
            rx.el.p(c["proveedor"], class_name="text-sm font-medium text-gray-900"),
            class_name="px-4 py-3",
        ),
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
                    rx.icon("eye", size=14, class_name="mr-1"),
                    "Ver",
                    on_click=ComprasState.ver_detalle(c),
                    class_name="flex items-center px-2.5 py-1 text-xs font-medium text-sky-700 border border-sky-300 rounded-lg hover:bg-sky-50 cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("circle-x", size=14, class_name="mr-1"),
                    "Anular",
                    on_click=ComprasState.confirmar_anular(c),
                    class_name="flex items-center px-2.5 py-1 text-xs font-medium text-red-600 border border-red-300 rounded-lg hover:bg-red-50 cursor-pointer",
                ),
                class_name="flex gap-2",
            ),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50 transition-colors",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Página principal
# ─────────────────────────────────────────────────────────────────────────────

def compras_page() -> rx.Component:
    return shell(
        _modal_nueva(),
        _modal_detalle(),
        _modal_anular(),
        # Header
        rx.el.div(
            rx.el.div(
                rx.el.h1("Compras", class_name="text-2xl font-bold text-gray-900"),
                rx.el.p(
                    ComprasState.total.to(str), " registros",
                    class_name="text-sm text-gray-500 mt-0.5",
                ),
            ),
            rx.el.button(
                rx.icon("plus", size=16, class_name="mr-1.5"),
                "Nueva compra",
                on_click=ComprasState.abrir_nueva,
                class_name="flex items-center px-4 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 cursor-pointer",
            ),
            class_name="flex items-center justify-between mb-6",
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
            rx.icon("search", size=15, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"),
            rx.el.input(
                placeholder="Buscar por proveedor o número…",
                value=ComprasState.busqueda,
                on_change=ComprasState.set_busqueda,
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
                                        rx.el.p("No hay compras registradas", class_name="text-sm text-gray-400"),
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
