from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.state.inventario import InventarioState


def _campo(label, tipo, value, on_change, placeholder="") -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.debounce_input(
            rx.el.input(type=tipo, value=value, on_change=on_change, placeholder=placeholder,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"),
            debounce_timeout=300,
        ),
    )


def _modal_producto() -> rx.Component:
    titulo = rx.cond(InventarioState.editando_id, "Editar producto", "Nuevo producto")
    return rx.cond(
        InventarioState.modal_producto,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=InventarioState.cerrar_producto),
            rx.el.div(
                rx.el.div(
                    rx.el.h2(titulo, class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(rx.icon("x", size=18), on_click=InventarioState.cerrar_producto,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between mb-6",
                ),
                rx.el.div(
                    _campo("Nombre *", "text", InventarioState.form_nombre, InventarioState.set_form_nombre),
                    _campo("SKU", "text", InventarioState.form_sku, InventarioState.set_form_sku),
                    rx.el.div(
                        _campo("Precio costo", "text", InventarioState.form_precio_costo,
                               InventarioState.set_form_precio_costo, "0.00"),
                        _campo("Precio venta", "text", InventarioState.form_precio_venta,
                               InventarioState.set_form_precio_venta, "0.00"),
                        class_name="grid grid-cols-2 gap-3",
                    ),
                    rx.el.div(
                        _campo("Stock actual", "text", InventarioState.form_stock_actual,
                               InventarioState.set_form_stock_actual, "0"),
                        _campo("Stock mínimo", "text", InventarioState.form_stock_minimo,
                               InventarioState.set_form_stock_minimo, "0"),
                        class_name="grid grid-cols-2 gap-3",
                    ),
                    class_name="space-y-4",
                ),
                rx.cond(InventarioState.form_error != "",
                        rx.el.p(InventarioState.form_error,
                                class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded")),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=InventarioState.cerrar_producto,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        rx.cond(InventarioState.is_saving,
                                rx.el.div(rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                          "Guardando...", class_name="flex items-center"),
                                "Guardar"),
                        on_click=InventarioState.guardar_producto, disabled=InventarioState.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer disabled:bg-sky-400",
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_movimiento() -> rx.Component:
    return rx.cond(
        InventarioState.modal_mov,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=InventarioState.cerrar_mov),
            rx.el.div(
                rx.el.h2("Movimiento de stock", class_name="text-lg font-semibold text-gray-900 mb-1"),
                rx.el.p(InventarioState.mov_prod_nombre, class_name="text-sm text-gray-500 mb-4"),
                rx.el.div(
                    rx.el.label("Tipo", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.select(
                        rx.el.option("Ingreso", value="ingreso"),
                        rx.el.option("Egreso", value="egreso"),
                        rx.el.option("Ajuste", value="ajuste"),
                        value=InventarioState.form_mov_tipo,
                        on_change=InventarioState.set_form_mov_tipo,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    class_name="mb-4",
                ),
                _campo("Cantidad *", "text", InventarioState.form_mov_cantidad,
                       InventarioState.set_form_mov_cantidad, "0"),
                rx.el.div(class_name="mb-4"),
                _campo("Motivo", "text", InventarioState.form_mov_motivo,
                       InventarioState.set_form_mov_motivo, "Opcional..."),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=InventarioState.cerrar_mov,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button("Registrar", on_click=InventarioState.guardar_movimiento,
                                 class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer"),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _fila_producto(p: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(rx.cond(p["sku"], p["sku"], "—"), class_name="px-4 py-3 text-xs text-gray-500 font-mono"),
        rx.el.td(p["nombre"], class_name="px-4 py-3 text-sm font-medium text-gray-900"),
        rx.el.td(
            rx.el.span(
                rx.cond(p["precio_venta"], rx.el.span("$ ", p["precio_venta"]), "—"),
                class_name="text-sm text-gray-600",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.span(
                    p["stock_actual"],
                    class_name=rx.cond(
                        p["bajo_minimo"],
                        "text-sm font-semibold text-red-700",
                        "text-sm font-semibold text-gray-800",
                    ),
                ),
                rx.cond(
                    p["bajo_minimo"],
                    rx.el.span(
                        rx.icon("triangle-alert", size=14),
                        " Stock bajo",
                        class_name="ml-2 text-xs text-red-600 flex items-center gap-0.5",
                    ),
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("arrow-up-down", size=15),
                    on_click=lambda: InventarioState.abrir_mov(p),
                    class_name="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded cursor-pointer",
                    title="Movimiento de stock",
                ),
                rx.el.button(
                    rx.icon("pencil", size=15),
                    on_click=lambda: InventarioState.abrir_editar(p),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("trash-2", size=15),
                    on_click=lambda: InventarioState.eliminar_producto(p["id"]),
                    class_name="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer",
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50",
    )


def inventario_page() -> rx.Component:
    return shell(
        _modal_producto(),
        _modal_movimiento(),
        # Encabezado
        rx.el.div(
            rx.el.div(
                rx.el.h1("Inventario", class_name="text-xl font-semibold text-gray-900"),
                rx.el.p(f"{InventarioState.total} productos", class_name="text-sm text-gray-500"),
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("triangle-alert", size=16),
                    rx.cond(InventarioState.solo_minimo, "Ver todos", "Stock bajo"),
                    on_click=InventarioState.toggle_minimo,
                    class_name=rx.cond(
                        InventarioState.solo_minimo,
                        "flex items-center gap-1.5 px-3 py-2 text-sm text-orange-700 border border-orange-300 bg-orange-50 rounded-lg cursor-pointer",
                        "flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                ),
                rx.el.button(
                    rx.icon("plus", size=16), "Nuevo producto",
                    on_click=InventarioState.abrir_nuevo,
                    class_name="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
                class_name="flex items-center gap-3",
            ),
            class_name="flex items-center justify-between mb-6",
        ),
        # Buscador
        rx.el.div(
            rx.el.div(
                rx.icon("search", size=16, class_name="text-gray-400"),
                rx.debounce_input(
                    rx.el.input(
                        type="text", placeholder="Buscar por nombre o SKU...",
                        value=InventarioState.busqueda, on_change=InventarioState.set_busqueda,
                        class_name="w-full outline-none text-sm text-gray-700 placeholder-gray-400 ml-2",
                    ),
                    debounce_timeout=300,
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
                            *[rx.el.th(h, class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase")
                              for h in ["SKU", "Nombre", "Precio venta", "Stock", "Acciones"]],
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(rx.foreach(InventarioState.productos.to(list[dict]), _fila_producto)),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto",
            ),
            rx.el.div(
                rx.el.button(rx.icon("chevron-left", size=15), "Anterior",
                             on_click=InventarioState.prev_page, disabled=InventarioState.page <= 1,
                             class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-40 cursor-pointer"),
                rx.el.span(InventarioState.page, " / ", InventarioState.total_pages, class_name="text-sm text-gray-500"),
                rx.el.button("Siguiente", rx.icon("chevron-right", size=15),
                             on_click=InventarioState.next_page, disabled=InventarioState.page >= InventarioState.total_pages,
                             class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-40 cursor-pointer"),
                class_name="flex items-center justify-between px-4 py-3 border-t border-gray-100",
            ),
            class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
        ),
        on_mount=InventarioState.on_mount,
    )
