from __future__ import annotations

import reflex as rx

from clinica_app.state.compras import ComprasState


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
