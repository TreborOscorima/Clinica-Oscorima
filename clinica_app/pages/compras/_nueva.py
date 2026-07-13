from __future__ import annotations

import reflex as rx

from clinica_app.state.compras import ComprasState
from clinica_app.pages.compras._proveedores import _inp


def _modal_nuevo_producto() -> rx.Component:
    return rx.cond(
        ComprasState.modal_nuevo_prod,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/50 z-[65]",
                on_click=ComprasState.cerrar_nuevo_prod,
                data_modal_close="1",
            ),
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.icon("package-plus", size=18, class_name="text-sky-600 mr-2"),
                        rx.el.h2("Nuevo producto", class_name="text-base font-semibold text-gray-900"),
                    ),
                    rx.el.button(
                        rx.icon("x", size=16),
                        on_click=ComprasState.cerrar_nuevo_prod,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between mb-4",
                ),
                rx.el.p(
                    "El producto no existe en el inventario. Completá los datos para registrarlo.",
                    class_name="text-xs text-gray-500 mb-4",
                ),

                rx.el.div(
                    # Nombre
                    rx.el.div(
                        rx.el.label("Nombre *", class_name="block text-xs font-medium text-gray-600 mb-1"),

                        rx.el.input(
                            type="text", placeholder="Nombre del producto",
                            default_value=ComprasState.np_nombre,
                            on_change=ComprasState.set_np_nombre,
                            class_name=_inp,
                        ),
                    ),
                    # SKU + Stock inicial
                    rx.el.div(
                        rx.el.div(
                            rx.el.label("SKU / Código de barras", class_name="block text-xs font-medium text-gray-600 mb-1"),

                            rx.el.input(
                                type="text", placeholder="Ej: 7790001234567",
                                default_value=ComprasState.np_sku,
                                on_change=ComprasState.set_np_sku,
                                class_name=_inp,
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Stock inicial", class_name="block text-xs font-medium text-gray-600 mb-1"),

                            rx.el.input(
                                type="number", placeholder="0",
                                default_value=ComprasState.np_stock_inicial,
                                on_change=ComprasState.set_np_stock_inicial,
                                class_name=_inp,
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-3",
                    ),
                    # Precio costo + Precio venta
                    rx.el.div(
                        rx.el.div(
                            rx.el.label("Precio costo ($)", class_name="block text-xs font-medium text-gray-600 mb-1"),

                            rx.el.input(
                                type="number", placeholder="0.00",
                                default_value=ComprasState.np_precio_costo,
                                on_change=ComprasState.set_np_precio_costo,
                                class_name=_inp,
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Precio venta ($)", class_name="block text-xs font-medium text-gray-600 mb-1"),

                            rx.el.input(
                                type="number", placeholder="0.00",
                                default_value=ComprasState.np_precio_venta,
                                on_change=ComprasState.set_np_precio_venta,
                                class_name=_inp,
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-3",
                    ),
                    class_name="space-y-3",
                ),

                rx.cond(
                    ComprasState.np_error != "",
                    rx.el.p(ComprasState.np_error,
                            class_name="mt-3 text-xs text-red-600 bg-red-50 rounded p-2"),
                ),

                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=ComprasState.cerrar_nuevo_prod,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            ComprasState.np_is_saving,
                            rx.el.span(
                                rx.icon("loader-circle", size=13, class_name="animate-spin mr-1"),
                                "Guardando…",
                                class_name="flex items-center",
                            ),
                            rx.el.span("Guardar y agregar"),
                        ),
                        on_click=ComprasState.guardar_nuevo_prod,
                        disabled=ComprasState.np_is_saving,
                        data_modal_submit="1",
                        title="Guardar y agregar al carrito (Ctrl+Enter)",
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-60 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3 mt-5",
                ),

                class_name="bg-white rounded-2xl shadow-2xl p-5 w-full max-w-sm z-[70] relative",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-[65] p-4",
        ),
    )


def _fila_carrito(item: dict, idx: int) -> rx.Component:
    return rx.el.tr(
        rx.el.td(item["producto_nombre"],  class_name="px-3 py-2 text-sm text-gray-800"),
        rx.el.td(item["cantidad"],         class_name="px-3 py-2 text-sm text-right tabular-nums"),
        rx.el.td("$", item["costo_unitario"], class_name="px-3 py-2 text-sm text-right tabular-nums"),
        rx.el.td("$", item["subtotal"],    class_name="px-3 py-2 text-sm font-medium text-right tabular-nums"),
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


def _match_item(p: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(p["nombre"], class_name="text-sm font-medium text-gray-800"),
            rx.cond(
                p["sku"] != "",
                rx.el.span(p["sku"], class_name="text-xs text-gray-400 font-mono ml-1.5"),
                rx.fragment(),
            ),
        ),
        rx.el.span("$", p["costo"], class_name="text-xs text-emerald-600 flex-shrink-0"),
        on_click=ComprasState.seleccionar_producto(p["id"]),
        class_name=(
            "flex items-center justify-between px-3 py-2 cursor-pointer "
            "hover:bg-sky-50 border-b border-gray-100 last:border-0"
        ),
    )


def _modal_nueva() -> rx.Component:
    return rx.cond(
        ComprasState.modal_nueva,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=ComprasState.cerrar_nueva, data_modal_close="1"),
            rx.el.div(
                # Cabecera
                rx.el.div(
                    rx.el.h2("Nueva Compra", class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=ComprasState.cerrar_nueva,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),

                # ── Sección: datos del comprobante ─────────────────────────────
                rx.el.p("Datos del comprobante",
                        class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3"),
                rx.el.div(
                    # Proveedor
                    rx.el.div(
                        rx.el.div(
                            rx.el.label("Proveedor", class_name="text-sm font-medium text-gray-700"),
                            rx.el.button(
                                rx.icon("settings-2", size=12, class_name="mr-1"),
                                "Gestionar",
                                on_click=ComprasState.abrir_proveedores,
                                class_name="flex items-center text-xs text-sky-600 hover:text-sky-800 cursor-pointer",
                            ),
                            class_name="flex items-center justify-between mb-1",
                        ),
                        rx.el.select(
                            rx.el.option("— Sin proveedor —", value=""),
                            rx.foreach(
                                ComprasState.proveedores_cat,
                                lambda p: rx.el.option(p["nombre"], value=p["id"].to(str)),
                            ),
                            default_value=ComprasState.form_proveedor_id,
                            on_change=ComprasState.set_form_proveedor_id,
                            class_name=(
                                "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm "
                                "focus:outline-none focus:ring-2 focus:ring-sky-500"
                            ),
                        ),
                        # Detalle del proveedor seleccionado
                        rx.cond(
                            ComprasState.prov_tiene_sel,
                            rx.el.div(
                                rx.cond(
                                    ComprasState.prov_sel_detalle["telefono"] != "",
                                    rx.el.span(
                                        rx.icon("phone", size=11, class_name="mr-1"),
                                        ComprasState.prov_sel_detalle["telefono"],
                                        class_name="flex items-center text-xs text-gray-500",
                                    ),
                                    rx.fragment(),
                                ),
                                rx.cond(
                                    ComprasState.prov_sel_detalle["email"] != "",
                                    rx.el.span(
                                        rx.icon("mail", size=11, class_name="mr-1"),
                                        ComprasState.prov_sel_detalle["email"],
                                        class_name="flex items-center text-xs text-gray-500",
                                    ),
                                    rx.fragment(),
                                ),
                                rx.cond(
                                    ComprasState.prov_sel_detalle["documento"] != "",
                                    rx.el.span(
                                        rx.icon("file-text", size=11, class_name="mr-1"),
                                        ComprasState.prov_sel_detalle["documento"],
                                        class_name="flex items-center text-xs text-gray-500",
                                    ),
                                    rx.fragment(),
                                ),
                                class_name="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 bg-sky-50 rounded-lg px-3 py-1.5",
                            ),
                            rx.fragment(),
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
                                default_value=ComprasState.form_tipo_doc,
                                on_change=ComprasState.set_form_tipo_doc,
                                class_name=(
                                    "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm "
                                    "focus:outline-none focus:ring-2 focus:ring-sky-500"
                                ),
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Número", class_name="block text-sm font-medium text-gray-700 mb-1"),

                            rx.el.input(
                                type="text", placeholder="Ej: F001-00123",
                                default_value=ComprasState.form_numero,
                                on_change=ComprasState.set_form_numero,
                                class_name=_inp,
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-3",
                    ),

                    # RUC/Documento (autocomplete) + Nro. orden
                    rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                rx.el.label("RUC / Documento", class_name="text-sm font-medium text-gray-700"),
                                rx.el.span(
                                    rx.icon("lock", size=10, class_name="mr-0.5"),
                                    "Desde proveedor",
                                    class_name="flex items-center text-xs text-gray-400",
                                ),
                                class_name="flex items-center justify-between mb-1",
                            ),
                            rx.el.input(
                                type="text",
                                read_only=True,
                                value=ComprasState.prov_sel_detalle["documento"],
                                placeholder="— Selecciona un proveedor —",
                                class_name=(
                                    "w-full px-3 py-2 border border-gray-200 rounded-lg text-sm "
                                    "bg-gray-50 text-gray-600 cursor-default select-all "
                                    "focus:outline-none"
                                ),
                            ),
                        ),
                        rx.el.div(
                            rx.el.label("Nro. orden / referencia", class_name="block text-sm font-medium text-gray-700 mb-1"),

                            rx.el.input(
                                type="text", placeholder="Opcional",
                                default_value=ComprasState.form_nro_registro,
                                on_change=ComprasState.set_form_nro_registro,
                                class_name=_inp,
                            ),
                        ),
                        class_name="grid grid-cols-2 gap-3",
                    ),

                    # Observación
                    rx.el.div(
                        rx.el.label("Observación", class_name="block text-sm font-medium text-gray-700 mb-1"),

                        rx.el.input(
                            type="text", placeholder="Opcional",
                            default_value=ComprasState.form_observacion,
                            on_change=ComprasState.set_form_observacion,
                            class_name=_inp,
                        ),
                    ),

                    class_name="space-y-3 mb-5",
                ),

                # ── Sección: productos ─────────────────────────────────────────
                rx.el.p("Productos",
                        class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3"),

                # Fila de búsqueda + campos
                rx.el.div(
                    # Search con autocomplete
                    rx.el.div(
                        rx.icon("search", size=14,
                                class_name="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"),
                        rx.el.input(
                            type="text",
                            placeholder="Nombre o código de barras…",
                            on_change=ComprasState.set_cart_busqueda,
                            on_key_down=ComprasState.handle_cart_busqueda_key,
                            class_name=(
                                "w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg text-sm "
                                "focus:outline-none focus:ring-2 focus:ring-sky-500"
                            ),
                        ),
                        # Dropdown de resultados
                        rx.cond(
                            ComprasState.cart_prod_matches,
                            rx.el.div(
                                rx.foreach(ComprasState.cart_prod_matches, _match_item),
                                class_name=(
                                    "absolute top-full left-0 right-0 mt-0.5 bg-white "
                                    "border border-gray-200 rounded-lg shadow-xl z-10 "
                                    "max-h-48 overflow-y-auto"
                                ),
                            ),
                            rx.fragment(),
                        ),
                        class_name="relative flex-1 min-w-0",
                    ),

                    # Botón "Nuevo" cuando no hay coincidencias
                    rx.cond(
                        ComprasState.cart_sin_coincidencias,
                        rx.el.button(
                            rx.icon("plus", size=13, class_name="mr-1"),
                            "Nuevo",
                            on_click=ComprasState.abrir_nuevo_prod,
                            class_name=(
                                "flex items-center px-2.5 py-2 text-xs font-medium "
                                "text-sky-700 border border-sky-300 rounded-lg "
                                "hover:bg-sky-50 cursor-pointer whitespace-nowrap"
                            ),
                        ),
                        rx.fragment(),
                    ),

                    # Cantidad

                    rx.el.input(
                        type="text", placeholder="Cant.",
                        default_value=ComprasState.cart_cantidad,
                        on_change=ComprasState.set_cart_cantidad,
                        class_name="w-20 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),

                    # Costo
                    rx.el.div(
                        rx.el.span("$", class_name="text-gray-500 text-sm px-2"),

                        rx.el.input(
                            type="text", placeholder="Costo",
                            default_value=ComprasState.cart_costo,
                            on_change=ComprasState.set_cart_costo,
                            class_name="w-20 py-2 pr-2 text-sm outline-none",
                        ),
                        class_name="flex items-center border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-sky-500",
                    ),

                    # Botón agregar
                    rx.el.button(
                        rx.icon("plus", size=16),
                        on_click=ComprasState.agregar_item,
                        class_name="px-3 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer",
                    ),
                    class_name="flex gap-2 items-center mb-2",
                ),

                # Chip producto seleccionado
                rx.cond(
                    ComprasState.cart_tiene_producto,
                    rx.el.div(
                        rx.icon("package", size=13, class_name="text-sky-600 flex-shrink-0"),
                        rx.el.span(ComprasState.cart_producto_nombre,
                                   class_name="text-sm font-medium text-gray-800 flex-1 truncate"),
                        rx.el.button(
                            rx.icon("x", size=13),
                            on_click=ComprasState.limpiar_producto_sel,
                            class_name="text-gray-400 hover:text-red-500 cursor-pointer flex-shrink-0",
                        ),
                        class_name="flex items-center gap-2 px-3 py-1.5 bg-sky-50 border border-sky-200 rounded-lg mb-2",
                    ),
                    rx.fragment(),
                ),

                # Error de carrito
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
                            rx.el.span("$", ComprasState.carrito_total,
                                       class_name="text-sm font-bold text-gray-900"),
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
                        data_modal_submit="1",
                        title="Registrar compra (Ctrl+Enter)",
                        class_name="px-5 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 disabled:opacity-60 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3",
                ),

                class_name="bg-white rounded-2xl shadow-xl p-6 w-full max-w-2xl z-50 relative max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
    )
