from __future__ import annotations

import reflex as rx

from clinica_app.state.compras import ComprasState

_inp = (
    "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm "
    "focus:outline-none focus:ring-2 focus:ring-sky-500"
)


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
                on_click=ComprasState.confirmar_eliminar(p),
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
