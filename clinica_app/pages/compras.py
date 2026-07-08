from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.stat_card import stat_card
from clinica_app.components.ui import page_header
from clinica_app.state.compras import ComprasState

_inp = (
    "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm "
    "focus:outline-none focus:ring-2 focus:ring-sky-500"
)


# ─────────────────────────────────────────────────────────────────────────────
#  Modal: Gestionar proveedores
# ─────────────────────────────────────────────────────────────────────────────

def _fila_proveedor(p: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(p["nombre"], class_name="text-sm font-medium text-gray-900"),
            rx.el.div(
                rx.cond(
                    p["telefono"] != "",
                    rx.el.span(
                        rx.icon("phone", size=11, class_name="mr-0.5 inline"),
                        p["telefono"],
                        class_name="text-xs text-gray-400",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    p["email"] != "",
                    rx.el.span(p["email"], class_name="text-xs text-gray-400"),
                    rx.fragment(),
                ),
                rx.cond(
                    p["documento"] != "",
                    rx.el.span(
                        rx.icon("file-text", size=11, class_name="mr-0.5 inline"),
                        p["documento"],
                        class_name="text-xs text-gray-400",
                    ),
                    rx.fragment(),
                ),
                class_name="flex flex-wrap gap-x-3 gap-y-0.5 mt-0.5",
            ),
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("pencil", size=13),
                on_click=ComprasState.prov_iniciar_edicion(p),
                class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded cursor-pointer",
            ),
            rx.el.button(
                rx.icon("trash-2", size=13),
                on_click=ComprasState.prov_eliminar(p["id"]),
                class_name="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded cursor-pointer",
            ),
            class_name="flex gap-0.5 flex-shrink-0",
        ),
        class_name="flex items-start justify-between py-2.5 border-b border-gray-100 last:border-0",
    )


def _modal_proveedores() -> rx.Component:
    return rx.cond(
        ComprasState.modal_proveedores,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-[55]",
                on_click=ComprasState.cerrar_proveedores,
                data_modal_close="1",
            ),
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.icon("users", size=18, class_name="text-sky-600 mr-2"),
                        rx.el.h2("Proveedores", class_name="text-lg font-semibold text-gray-900"),
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=ComprasState.cerrar_proveedores,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),

                # Form add/edit
                rx.el.div(
                    rx.el.p(
                        rx.cond(ComprasState.prov_editando, "Editar proveedor", "Nuevo proveedor"),
                        class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3",
                    ),
                    rx.el.div(
                        # Nombre
                        rx.el.div(
                            rx.el.label("Nombre *", class_name="block text-xs font-medium text-gray-600 mb-1"),
                            
                            rx.el.input(
                                type="text", placeholder="Ej: Distribuidora Norte",
                                default_value=ComprasState.prov_form_nombre,
                                on_change=ComprasState.set_prov_form_nombre,
                                class_name=_inp,
                            ),
                        ),
                        # Documento + Teléfono
                        rx.el.div(
                            rx.el.div(
                                rx.el.label("RUC / DNI", class_name="block text-xs font-medium text-gray-600 mb-1"),
                                
                                rx.el.input(
                                    type="text", placeholder="Opcional",
                                    default_value=ComprasState.prov_form_documento,
                                    on_change=ComprasState.set_prov_form_documento,
                                    class_name=_inp,
                                ),
                            ),
                            rx.el.div(
                                rx.el.label("Teléfono", class_name="block text-xs font-medium text-gray-600 mb-1"),
                                
                                rx.el.input(
                                    type="text", placeholder="Opcional",
                                    default_value=ComprasState.prov_form_telefono,
                                    on_change=ComprasState.set_prov_form_telefono,
                                    class_name=_inp,
                                ),
                            ),
                            class_name="grid grid-cols-2 gap-3",
                        ),
                        # Email + Dirección
                        rx.el.div(
                            rx.el.div(
                                rx.el.label("Email", class_name="block text-xs font-medium text-gray-600 mb-1"),
                                
                                rx.el.input(
                                    type="email", placeholder="Opcional",
                                    default_value=ComprasState.prov_form_email,
                                    on_change=ComprasState.set_prov_form_email,
                                    class_name=_inp,
                                ),
                            ),
                            rx.el.div(
                                rx.el.label("Dirección", class_name="block text-xs font-medium text-gray-600 mb-1"),
                                
                                rx.el.input(
                                    type="text", placeholder="Opcional",
                                    default_value=ComprasState.prov_form_direccion,
                                    on_change=ComprasState.set_prov_form_direccion,
                                    class_name=_inp,
                                ),
                            ),
                            class_name="grid grid-cols-2 gap-3",
                        ),
                        class_name="space-y-3",
                    ),
                    rx.cond(
                        ComprasState.prov_form_error != "",
                        rx.el.p(ComprasState.prov_form_error,
                                class_name="mt-2 text-xs text-red-600 bg-red-50 rounded p-2"),
                    ),
                    rx.el.div(
                        rx.cond(
                            ComprasState.prov_editando,
                            rx.el.button(
                                "Cancelar",
                                on_click=ComprasState.prov_cancelar_edicion,
                                class_name="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                            ),
                            rx.fragment(),
                        ),
                        rx.el.button(
                            rx.cond(
                                ComprasState.prov_is_saving,
                                rx.el.span(
                                    rx.icon("loader-circle", size=13, class_name="animate-spin mr-1"),
                                    "Guardando…",
                                    class_name="flex items-center",
                                ),
                                rx.cond(
                                    ComprasState.prov_editando,
                                    rx.el.span("Guardar cambios"),
                                    rx.el.span("Agregar proveedor"),
                                ),
                            ),
                            on_click=ComprasState.guardar_proveedor,
                            disabled=ComprasState.prov_is_saving,
                            data_modal_submit="1",
                            title="Guardar proveedor (Ctrl+Enter)",
                            class_name="px-3 py-1.5 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-60 cursor-pointer",
                        ),
                        class_name="flex justify-end gap-2 mt-3",
                    ),
                    class_name="bg-gray-50 rounded-xl p-4 mb-5",
                ),

                # List
                rx.cond(
                    ComprasState.proveedores_cat,
                    rx.el.div(
                        rx.el.p(
                            "Proveedores registrados",
                            class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2",
                        ),
                        rx.el.div(
                            rx.foreach(ComprasState.proveedores_cat, _fila_proveedor),
                            class_name="max-h-56 overflow-y-auto",
                        ),
                    ),
                    rx.el.p(
                        "Aún no hay proveedores registrados",
                        class_name="text-sm text-gray-400 text-center py-4",
                    ),
                ),

                class_name="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg z-[60] relative max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-[55] p-4",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Modal: Nuevo producto rápido
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
#  Modal: Nueva compra
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
#  Modal: Detalle de compra
# ─────────────────────────────────────────────────────────────────────────────

def _modal_detalle() -> rx.Component:
    return rx.cond(
        ComprasState.modal_detalle,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=ComprasState.cerrar_detalle, data_modal_close="1"),
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
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Proveedor",    class_name="text-xs text-gray-500"),
                        rx.el.span(ComprasState.compra_sel["proveedor"], class_name="text-sm text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    rx.el.div(
                        rx.el.span("Fecha",        class_name="text-xs text-gray-500"),
                        rx.el.span(ComprasState.compra_sel["fecha"],    class_name="text-sm text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    rx.el.div(
                        rx.el.span("Nro. orden / ref.", class_name="text-xs text-gray-500"),
                        rx.el.span(ComprasState.compra_sel["nro_registro"], class_name="text-sm text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    rx.el.div(
                        rx.el.span("Observación",  class_name="text-xs text-gray-500"),
                        rx.el.span(ComprasState.compra_sel["observacion"], class_name="text-sm text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    class_name="bg-gray-50 rounded-lg p-3 mb-4 space-y-1.5",
                ),
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th("Producto",  class_name="px-3 py-2 text-left text-xs font-semibold text-gray-500"),
                                rx.el.th("Cantidad",  class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                                rx.el.th("Costo u.",  class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                                rx.el.th("Subtotal",  class_name="px-3 py-2 text-right text-xs font-semibold text-gray-500"),
                            ),
                            class_name="bg-gray-50 border-b border-gray-200",
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                ComprasState.detalle_items,
                                lambda i: rx.el.tr(
                                    rx.el.td(i["producto_nombre"], class_name="px-3 py-2 text-sm text-gray-800"),
                                    rx.el.td(i["cantidad"],        class_name="px-3 py-2 text-sm text-right tabular-nums"),
                                    rx.el.td("$", i["costo_unitario"], class_name="px-3 py-2 text-sm text-right tabular-nums"),
                                    rx.el.td("$", i["subtotal"],   class_name="px-3 py-2 text-sm font-medium text-right tabular-nums"),
                                    class_name="border-b border-gray-100",
                                ),
                            ),
                        ),
                        class_name="w-full text-sm",
                    ),
                    rx.el.div(
                        rx.el.span("Total", class_name="text-sm font-semibold text-gray-700"),
                        rx.el.span("$", ComprasState.compra_sel["total"],
                                   class_name="text-sm font-bold text-gray-900"),
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
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=ComprasState.cerrar_anular, data_modal_close="1"),
            rx.el.div(
                rx.icon("triangle-alert", size=36, class_name="text-amber-500 mx-auto mb-4"),
                rx.el.h2("¿Anular esta compra?",
                         class_name="text-lg font-semibold text-gray-900 text-center mb-2"),
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
                        data_modal_submit="1",
                        title="Confirmar anulación (Ctrl+Enter)",
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


# ─────────────────────────────────────────────────────────────────────────────
#  Página principal
# ─────────────────────────────────────────────────────────────────────────────

def compras_page() -> rx.Component:
    return shell(
        _modal_nueva(),
        _modal_detalle(),
        _modal_anular(),
        _modal_proveedores(),
        _modal_nuevo_producto(),

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
