from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.state.cobro import CobroState

# ─────────────────────────────────────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────────────────────────────────────

_INPUT_CLS = (
    "w-full px-3 py-2 text-sm border border-gray-300 rounded-lg "
    "focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
)

_METODOS_PAGO = [
    ("efectivo",      "Efectivo"),
    ("tarjeta",       "Tarjeta"),
    ("transferencia", "Transfer."),
    ("otro",          "Otro"),
]


# ─────────────────────────────────────────────────────────────────────────────
#  Panel izquierdo: paciente + catálogo
# ─────────────────────────────────────────────────────────────────────────────

def _pac_resultado(pac: dict) -> rx.Component:
    return rx.el.div(
        rx.el.span(pac["nombre"], class_name="text-sm font-medium text-gray-900 block"),
        rx.el.span(pac["documento"], class_name="text-xs text-gray-500"),
        on_click=CobroState.seleccionar_paciente(pac["id"], pac["nombre"], pac["documento"]),
        class_name="px-3 py-2 hover:bg-sky-50 cursor-pointer border-b border-gray-100 last:border-0",
    )


def _paciente_search() -> rx.Component:
    return rx.el.div(
        rx.el.label("Paciente", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 block"),
        # Campo + dropdown
        rx.el.div(
            rx.el.div(
                rx.icon("search", size=15, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"),
                rx.debounce_input(
                    rx.el.input(
                        placeholder="Buscar por nombre o DNI…",
                        value=CobroState.pac_busqueda,
                        on_change=CobroState.set_pac_busqueda,
                        class_name="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    debounce_timeout=300,
                ),
                class_name="relative",
            ),
            rx.cond(
                CobroState.pac_resultados,
                rx.el.div(
                    rx.foreach(CobroState.pac_resultados, _pac_resultado),
                    class_name=(
                        "absolute z-20 left-0 right-0 bg-white border border-gray-200 "
                        "rounded-lg shadow-lg mt-1 max-h-48 overflow-y-auto"
                    ),
                ),
            ),
            class_name="relative",
        ),
        # Chip del paciente seleccionado
        rx.cond(
            CobroState.pac_id_sel != "",
            rx.el.div(
                rx.icon("user-check", size=14, class_name="text-green-600 flex-shrink-0"),
                rx.el.span(CobroState.pac_nombre_sel, class_name="text-sm font-medium text-gray-800 flex-1 truncate"),
                rx.el.span(CobroState.pac_doc_sel, class_name="text-xs text-gray-500"),
                rx.el.button(
                    rx.icon("x", size=13),
                    on_click=CobroState.limpiar_paciente,
                    class_name="ml-2 text-gray-400 hover:text-red-500 cursor-pointer flex-shrink-0",
                ),
                class_name="flex items-center gap-2 mt-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg",
            ),
        ),
        class_name="mb-5",
    )


def _tab_btn(label: str, tab: str) -> rx.Component:
    return rx.el.button(
        label,
        on_click=CobroState.set_tab_activa(tab),
        class_name=rx.cond(
            CobroState.tab_activa == tab,
            "flex-1 py-2 text-sm font-semibold text-sky-600 border-b-2 border-sky-600",
            "flex-1 py-2 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700 cursor-pointer",
        ),
    )


def _servicio_row(s: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(s["nombre"], class_name="text-sm font-medium text-gray-800 leading-tight"),
            rx.el.p(s["categoria"], class_name="text-xs text-gray-400"),
        ),
        rx.el.div(
            rx.el.span("$", s["precio"], class_name="text-sm font-semibold text-gray-700 mr-2"),
            rx.el.button(
                rx.icon("plus", size=14),
                on_click=CobroState.agregar_servicio(s["id"], s["nombre"], s["precio"]),
                class_name="p-1.5 bg-sky-600 text-white rounded-md hover:bg-sky-700 cursor-pointer",
            ),
        ),
        class_name="flex items-center justify-between px-3 py-2.5 border-b border-gray-100 hover:bg-sky-50 last:border-0 transition-colors",
    )


def _producto_row(p: dict) -> rx.Component:
    return rx.el.div(
        rx.el.p(p["nombre"], class_name="text-sm font-medium text-gray-800"),
        rx.el.div(
            rx.el.span("$", p["precio"], class_name="text-sm font-semibold text-gray-700 mr-2"),
            rx.el.button(
                rx.icon("plus", size=14),
                on_click=CobroState.agregar_producto(p["id"], p["nombre"], p["precio"]),
                class_name="p-1.5 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 cursor-pointer",
            ),
        ),
        class_name="flex items-center justify-between px-3 py-2.5 border-b border-gray-100 hover:bg-emerald-50 last:border-0 transition-colors",
    )


def _catalogo() -> rx.Component:
    return rx.el.div(
        # Pestañas
        rx.el.div(
            _tab_btn("Servicios", "servicios"),
            _tab_btn("Productos", "productos"),
            class_name="flex border-b border-gray-200",
        ),
        # Búsqueda
        rx.el.div(
            rx.icon("search", size=14, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"),
            rx.debounce_input(
                rx.el.input(
                    placeholder="Buscar en catálogo…",
                    value=CobroState.busqueda_item,
                    on_change=CobroState.set_busqueda_item,
                    class_name="w-full pl-8 pr-3 py-2 text-sm border-b border-gray-200 focus:outline-none focus:border-sky-400",
                ),
                debounce_timeout=300,
            ),
            class_name="relative",
        ),
        # Lista
        rx.el.div(
            rx.cond(
                CobroState.tab_activa == "servicios",
                rx.cond(
                    CobroState.servicios_filtrados,
                    rx.foreach(CobroState.servicios_filtrados, _servicio_row),
                    rx.el.div(
                        rx.icon("package-x", size=28, class_name="text-gray-300 mb-2"),
                        rx.el.p("Sin servicios disponibles", class_name="text-sm text-gray-400"),
                        class_name="flex flex-col items-center py-10",
                    ),
                ),
                rx.cond(
                    CobroState.productos_filtrados,
                    rx.foreach(CobroState.productos_filtrados, _producto_row),
                    rx.el.div(
                        rx.icon("package-x", size=28, class_name="text-gray-300 mb-2"),
                        rx.el.p("Sin productos disponibles", class_name="text-sm text-gray-400"),
                        class_name="flex flex-col items-center py-10",
                    ),
                ),
            ),
            class_name="overflow-y-auto",
            style={"max_height": "360px"},
        ),
        class_name="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Panel derecho: carrito + cobro
# ─────────────────────────────────────────────────────────────────────────────

def _carrito_row(item: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(item["nombre"], class_name="text-sm font-medium text-gray-800 leading-tight"),
            rx.el.p(
                "x", item["cantidad"], "  ·  $", item["precio_unit"],
                class_name="text-xs text-gray-500 mt-0.5",
            ),
        ),
        rx.el.div(
            rx.el.span("$", item["subtotal"], class_name="text-sm font-semibold text-gray-800 mr-2"),
            rx.el.button(
                rx.icon("trash-2", size=13),
                on_click=CobroState.quitar_item(item["tipo"], item["ref_id"]),
                class_name="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer",
            ),
        ),
        class_name="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 last:border-0",
    )


def _totales() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span("Subtotal", class_name="text-sm text-gray-600"),
            rx.el.span("$", CobroState.total_bruto_str, class_name="text-sm text-gray-700"),
            class_name="flex justify-between",
        ),
        # Promociones
        rx.cond(
            CobroState.promociones_vigentes.length() > 0,
            rx.el.div(
                rx.el.label("Promoción", class_name="text-sm text-gray-600"),
                rx.el.select(
                    rx.el.option("Sin promoción", value=""),
                    rx.foreach(
                        CobroState.promociones_vigentes,
                        lambda p: rx.el.option(p["nombre"], value=p["id"]),
                    ),
                    value=CobroState.promo_sel_id,
                    on_change=CobroState.set_promo_sel_id,
                    class_name="text-sm border border-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-sky-500 max-w-[180px]",
                ),
                class_name="flex justify-between items-center",
            ),
        ),
        rx.el.div(
            rx.el.label("Descuento ($)", class_name="text-sm text-gray-600"),
            rx.debounce_input(
                rx.el.input(
                    value=CobroState.descuento_global,
                    on_change=CobroState.set_descuento_global,
                    type="number",
                    min="0",
                    step="0.01",
                    class_name="w-24 text-right px-2 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-sky-500",
                ),
                debounce_timeout=300,
            ),
            class_name="flex justify-between items-center",
        ),
        rx.el.hr(class_name="border-gray-200 my-1"),
        rx.el.div(
            rx.el.span("TOTAL", class_name="text-base font-bold text-gray-900"),
            rx.el.span("$", CobroState.total_neto_str, class_name="text-xl font-bold text-sky-700"),
            class_name="flex justify-between items-center",
        ),
        class_name="space-y-2 px-4 py-4 bg-gray-50 border-t border-gray-200",
    )


def _pago_form() -> rx.Component:
    return rx.el.div(
        # Método de pago
        rx.el.div(
            rx.el.label("Método de pago", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 block"),
            rx.el.div(
                *[
                    rx.el.button(
                        label,
                        on_click=CobroState.set_forma_pago(val),
                        class_name=rx.cond(
                            CobroState.forma_pago == val,
                            "flex-1 py-1.5 text-xs font-semibold text-white bg-sky-600 rounded-lg",
                            "flex-1 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                        ),
                    )
                    for val, label in _METODOS_PAGO
                ],
                class_name="flex gap-1.5",
            ),
            class_name="mb-4",
        ),
        # Cuotas
        rx.el.div(
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    checked=CobroState.es_cuotas,
                    on_change=CobroState.set_es_cuotas,
                    class_name="mr-2 accent-sky-600",
                ),
                "Pago en cuotas",
                class_name="flex items-center text-sm font-medium text-gray-700 cursor-pointer select-none",
            ),
            class_name="mb-3",
        ),
        rx.cond(
            CobroState.es_cuotas,
            rx.el.div(
                rx.el.div(
                    rx.el.label("Cuotas", class_name="text-xs text-gray-600 mb-1 block"),
                    rx.el.select(
                        rx.el.option("2 cuotas", value="2"),
                        rx.el.option("3 cuotas", value="3"),
                        rx.el.option("6 cuotas", value="6"),
                        rx.el.option("12 cuotas", value="12"),
                        value=CobroState.num_cuotas,
                        on_change=CobroState.set_num_cuotas,
                        class_name=_INPUT_CLS,
                    ),
                ),
                rx.el.div(
                    rx.el.label("Anticipo ($)", class_name="text-xs text-gray-600 mb-1 block"),
                    rx.debounce_input(
                        rx.el.input(
                            placeholder="0.00",
                            value=CobroState.cuota_inicial,
                            on_change=CobroState.set_cuota_inicial,
                            type="number",
                            min="0",
                            step="0.01",
                            class_name=_INPUT_CLS,
                        ),
                        debounce_timeout=300,
                    ),
                ),
                class_name="grid grid-cols-2 gap-3 mb-4",
            ),
        ),
        # Observación
        rx.el.div(
            rx.el.label("Observación", class_name="text-xs text-gray-500 mb-1 block"),
            rx.debounce_input(
                rx.el.input(
                    placeholder="Opcional…",
                    value=CobroState.observacion,
                    on_change=CobroState.set_observacion,
                    class_name=_INPUT_CLS,
                ),
                debounce_timeout=300,
            ),
            class_name="mb-4",
        ),
        # Error
        rx.cond(
            CobroState.form_error != "",
            rx.el.div(
                rx.icon("circle-alert", size=14, class_name="text-red-500 mr-1.5 flex-shrink-0 mt-0.5"),
                rx.el.span(CobroState.form_error, class_name="text-sm text-red-700"),
                class_name="flex items-start p-3 bg-red-50 border border-red-200 rounded-lg mb-3",
            ),
        ),
        # Confirmar
        rx.el.button(
            rx.cond(
                CobroState.is_saving,
                rx.el.div(
                    rx.icon("loader-circle", size=16, class_name="animate-spin mr-2"),
                    "Procesando…",
                    class_name="flex items-center justify-center",
                ),
                rx.el.div(
                    rx.icon("credit-card", size=16, class_name="mr-2"),
                    "Confirmar cobro",
                    class_name="flex items-center justify-center",
                ),
            ),
            on_click=CobroState.confirmar_cobro,
            disabled=CobroState.is_saving,
            class_name=(
                "w-full py-3 bg-sky-600 text-white font-semibold rounded-xl "
                "hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer text-sm transition-colors"
            ),
        ),
        class_name="px-4 py-4",
    )


def _panel_carrito() -> rx.Component:
    return rx.el.div(
        # Header
        rx.el.div(
            rx.el.div(
                rx.icon("shopping-cart", size=16, class_name="text-gray-600 mr-2"),
                rx.el.span("Carrito", class_name="text-sm font-semibold text-gray-700"),
            ),
            rx.cond(
                CobroState.carrito,
                rx.el.button(
                    "Vaciar",
                    on_click=CobroState.vaciar_carrito,
                    class_name="text-xs text-red-500 hover:text-red-700 cursor-pointer",
                ),
            ),
            class_name="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50",
        ),
        # Ítems
        rx.el.div(
            rx.cond(
                CobroState.carrito,
                rx.foreach(CobroState.carrito, _carrito_row),
                rx.el.div(
                    rx.icon("shopping-cart", size=36, class_name="text-gray-200 mb-3"),
                    rx.el.p("El carrito está vacío", class_name="text-sm text-gray-400"),
                    rx.el.p("Agregá servicios o productos desde el catálogo", class_name="text-xs text-gray-400 mt-1"),
                    class_name="flex flex-col items-center py-8",
                ),
            ),
            class_name="overflow-y-auto",
            style={"max_height": "240px"},
        ),
        # Totales y pago
        _totales(),
        _pago_form(),
        class_name="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Modal: recibo imprimible
# ─────────────────────────────────────────────────────────────────────────────

def _recibo_item_row(item: dict) -> rx.Component:
    return rx.el.div(
        rx.el.span(item["nombre"], class_name="text-xs text-gray-700 flex-1"),
        rx.el.span(
            item["cantidad"], "x $", item["precio_unit"],
            class_name="text-xs text-gray-500 w-28 text-right",
        ),
        rx.el.span(
            "$", item["subtotal"],
            class_name="text-xs font-semibold text-gray-900 w-20 text-right",
        ),
        class_name="flex items-start gap-2 py-1.5 border-b border-dashed border-gray-200 last:border-0",
    )


def _modal_recibo() -> rx.Component:
    return rx.cond(
        CobroState.modal_recibo,
        rx.el.div(
            # Backdrop
            rx.el.div(class_name="fixed inset-0 bg-black/50 z-40"),
            # Panel
            rx.el.div(
                # Botones de acción (se ocultan al imprimir)
                rx.el.div(
                    rx.el.button(
                        rx.icon("printer", size=15, class_name="mr-1.5"),
                        "Imprimir",
                        on_click=CobroState.imprimir_recibo,
                        class_name="flex items-center px-4 py-2 bg-sky-600 text-white text-sm rounded-lg hover:bg-sky-700 cursor-pointer",
                    ),
                    # Descargar PDF
                    rx.el.a(
                        rx.icon("file-down", size=15, class_name="mr-1.5"),
                        "PDF",
                        href=f"/api/recibo/pdf?comp_id={CobroState.ultimo_comp['id']}&clinica_id={CobroState.clinica_id}",
                        target="_blank",
                        class_name="flex items-center px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.icon("x", size=15, class_name="mr-1"),
                        "Cerrar",
                        on_click=CobroState.cerrar_recibo,
                        class_name="flex items-center px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3 mb-4",
                    id="receipt-actions",
                ),
                # Contenido imprimible
                rx.el.div(
                    # Cabecera
                    rx.el.div(
                        rx.el.p("✦ RECIBO DE PAGO ✦", class_name="text-center font-bold text-sm tracking-widest text-gray-900"),
                        rx.el.p(CobroState.ultimo_comp["numero"], class_name="text-center text-xs text-gray-500 font-mono mt-1"),
                        rx.el.p(CobroState.ultimo_comp["fecha"], class_name="text-center text-xs text-gray-400 mt-0.5"),
                        class_name="pb-3 border-b border-dashed border-gray-300 mb-3",
                    ),
                    # Paciente
                    rx.el.div(
                        rx.el.p("Paciente:", class_name="text-xs text-gray-500 mb-0.5"),
                        rx.el.p(CobroState.ultimo_comp["paciente_nombre"], class_name="text-sm font-semibold text-gray-900"),
                        class_name="pb-3 border-b border-dashed border-gray-200 mb-3",
                    ),
                    # Ítems
                    rx.el.div(
                        rx.el.div(
                            rx.el.span("Descripción", class_name="text-xs font-semibold text-gray-500 flex-1"),
                            rx.el.span("Cant.", class_name="text-xs font-semibold text-gray-500 w-28 text-right"),
                            rx.el.span("Total", class_name="text-xs font-semibold text-gray-500 w-20 text-right"),
                            class_name="flex gap-2 pb-1 border-b border-gray-300 mb-1",
                        ),
                        rx.foreach(CobroState.ultimo_items, _recibo_item_row),
                        class_name="mb-3",
                    ),
                    # Totales
                    rx.el.div(
                        rx.el.div(
                            rx.el.span("Descuento:", class_name="text-xs text-gray-500"),
                            rx.el.span("- $", CobroState.ultimo_comp["descuento_global"], class_name="text-xs text-gray-700"),
                            class_name="flex justify-between mb-1",
                        ),
                        rx.el.div(
                            rx.el.span("TOTAL:", class_name="text-sm font-bold text-gray-900"),
                            rx.el.span("$ ", CobroState.ultimo_comp["total"], class_name="text-lg font-bold text-sky-700"),
                            class_name="flex justify-between items-baseline",
                        ),
                        rx.el.div(
                            rx.el.span("Forma de pago:", class_name="text-xs text-gray-500"),
                            rx.el.span(CobroState.ultimo_comp["forma_pago"], class_name="text-xs font-medium text-gray-700 capitalize"),
                            class_name="flex justify-between mt-1",
                        ),
                        class_name="pt-3 border-t border-dashed border-gray-300",
                    ),
                    # Pie
                    rx.el.p(
                        "¡Gracias por su confianza!",
                        class_name="text-center text-xs text-gray-400 italic pt-4",
                    ),
                    class_name="font-mono",
                    id="print-receipt",
                ),
                class_name="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4 z-50 max-h-screen overflow-y-auto",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  CSS para impresión térmica 80mm
# ─────────────────────────────────────────────────────────────────────────────

def _print_styles() -> rx.Component:
    return rx.el.style("""
        @media print {
            body > *:not(.chakra-portal) { visibility: hidden !important; }
            #print-receipt, #print-receipt * { visibility: visible !important; }
            #receipt-actions { display: none !important; }
            #print-receipt {
                position: fixed !important;
                left: 0 !important; top: 0 !important;
                width: 76mm !important;
                padding: 3mm !important;
                font-size: 10px !important;
            }
            @page { size: 80mm auto; margin: 0; }
        }
    """)


# ─────────────────────────────────────────────────────────────────────────────
#  Página principal
# ─────────────────────────────────────────────────────────────────────────────

def cobro_page() -> rx.Component:
    return shell(
        _print_styles(),
        _modal_recibo(),
        # Encabezado
        rx.el.div(
            rx.el.h1("Punto de Cobro", class_name="text-2xl font-bold text-gray-900"),
            rx.el.p(
                "Registrá servicios, productos y medios de pago",
                class_name="text-sm text-gray-500 mt-0.5",
            ),
            class_name="mb-6",
        ),
        # Layout POS: catálogo izquierda, carrito derecha
        rx.el.div(
            # Columna izquierda
            rx.el.div(
                _paciente_search(),
                _catalogo(),
                class_name="space-y-4",
            ),
            # Columna derecha
            _panel_carrito(),
            class_name="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start",
        ),
        title="Punto de Cobro",
        on_mount=CobroState.on_mount,
    )
