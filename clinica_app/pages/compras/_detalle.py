from __future__ import annotations

import reflex as rx

from clinica_app.state.compras import ComprasState


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
