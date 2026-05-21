from __future__ import annotations

import reflex as rx

from clinica_app.components.badge import estado_badge
from clinica_app.components.layout import shell
from clinica_app.components.stat_card import stat_card
from clinica_app.state.caja import CajaState


def _modal_movimiento() -> rx.Component:
    return rx.cond(
        CajaState.modal_abierto,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=CajaState.cerrar_modal),
            rx.el.div(
                rx.el.div(
                    rx.el.h2("Nuevo movimiento", class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(rx.icon("x", size=18), on_click=CajaState.cerrar_modal,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between mb-6",
                ),
                rx.el.div(
                    # Tipo
                    rx.el.div(
                        rx.el.label("Tipo *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.div(
                            rx.el.button(
                                rx.icon("trending-up", size=16), "Ingreso",
                                on_click=CajaState.set_form_tipo("ingreso"),
                                class_name=rx.cond(
                                    CajaState.form_tipo == "ingreso",
                                    "flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-green-600 text-white",
                                    "flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer",
                                ),
                            ),
                            rx.el.button(
                                rx.icon("trending-down", size=16), "Egreso",
                                on_click=CajaState.set_form_tipo("egreso"),
                                class_name=rx.cond(
                                    CajaState.form_tipo == "egreso",
                                    "flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-red-600 text-white",
                                    "flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer",
                                ),
                            ),
                            class_name="flex gap-2",
                        ),
                    ),
                    # Monto
                    rx.el.div(
                        rx.el.label("Monto *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.div(
                            rx.el.span("$", class_name="text-gray-500 text-sm px-3"),
                            rx.el.input(
                                type="text", input_mode="decimal",
                                value=CajaState.form_monto,
                                on_change=CajaState.set_form_monto,
                                placeholder="0.00",
                                class_name="flex-1 py-2 pr-3 outline-none text-sm",
                            ),
                            class_name="flex items-center border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-sky-500",
                        ),
                    ),
                    # Método de pago
                    rx.el.div(
                        rx.el.label("Método de pago", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.select(
                            rx.el.option("Efectivo", value="efectivo"),
                            rx.el.option("Tarjeta", value="tarjeta"),
                            rx.el.option("Transferencia", value="transferencia"),
                            rx.el.option("Otro", value="otro"),
                            value=CajaState.form_metodo,
                            on_change=CajaState.set_form_metodo,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Observación
                    rx.el.div(
                        rx.el.label("Observación", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.textarea(
                            value=CajaState.form_observacion,
                            on_change=CajaState.set_form_observacion,
                            rows=2, placeholder="Opcional...",
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none",
                        ),
                    ),
                    class_name="space-y-4",
                ),
                rx.cond(
                    CajaState.form_error != "",
                    rx.el.p(CajaState.form_error, class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded"),
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=CajaState.cerrar_modal,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        rx.cond(CajaState.is_saving,
                                rx.el.div(rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                          "Guardando...", class_name="flex items-center"),
                                "Guardar"),
                        on_click=CajaState.guardar_movimiento, disabled=CajaState.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _fila_mov(m: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.span(m["fecha"],  # servicio ya devuelve "YYYY-MM-DD HH:MM"
                       class_name="text-sm text-gray-600 font-mono"),
            class_name="px-4 py-3",
        ),
        rx.el.td(estado_badge(m["tipo"]), class_name="px-4 py-3"),
        rx.el.td(
            rx.el.span(
                "$ ", m["monto"],
                class_name=rx.cond(
                    m["tipo"] == "ingreso",
                    "text-sm font-semibold text-green-700",
                    "text-sm font-semibold text-red-700",
                ),
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(rx.cond(m["metodo_pago"], m["metodo_pago"], "—"), class_name="px-4 py-3 text-sm text-gray-600 capitalize"),
        rx.el.td(rx.cond(m["observacion"], m["observacion"], "—"), class_name="px-4 py-3 text-sm text-gray-500 max-w-xs truncate"),
        rx.el.td(
            rx.el.button(
                rx.icon("trash-2", size=15),
                on_click=lambda: CajaState.eliminar_movimiento(m["id"]),
                class_name="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50",
    )


def caja_page() -> rx.Component:
    return shell(
        _modal_movimiento(),
        # Encabezado
        rx.el.div(
            rx.el.h1("Caja", class_name="text-xl font-semibold text-gray-900"),
            rx.el.button(
                rx.icon("plus", size=16), "Nuevo movimiento",
                on_click=CajaState.abrir_modal,
                class_name="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 cursor-pointer",
            ),
            class_name="flex items-center justify-between mb-6",
        ),
        # KPIs del día
        rx.el.div(
            stat_card("Ingresos hoy",  f"$ {CajaState.ingresos_dia}", "trending-up",   "green"),
            stat_card("Egresos hoy",   f"$ {CajaState.egresos_dia}",  "trending-down",  "red"),
            stat_card("Saldo del día", f"$ {CajaState.saldo_dia}",    "wallet",         "sky"),
            stat_card("Movimientos",   CajaState.total_movs_dia,       "receipt",        "purple"),
            class_name="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6",
        ),
        # Filtros
        rx.el.div(
            rx.el.button("Todos", on_click=lambda: CajaState.set_filtro_tipo(""),
                         class_name=rx.cond(CajaState.filtro_tipo == "",
                                            "px-4 py-1.5 text-sm font-medium rounded-full bg-sky-600 text-white",
                                            "px-4 py-1.5 text-sm font-medium rounded-full bg-white border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer")),
            rx.el.button("Ingresos", on_click=lambda: CajaState.set_filtro_tipo("ingreso"),
                         class_name=rx.cond(CajaState.filtro_tipo == "ingreso",
                                            "px-4 py-1.5 text-sm font-medium rounded-full bg-sky-600 text-white",
                                            "px-4 py-1.5 text-sm font-medium rounded-full bg-white border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer")),
            rx.el.button("Egresos", on_click=lambda: CajaState.set_filtro_tipo("egreso"),
                         class_name=rx.cond(CajaState.filtro_tipo == "egreso",
                                            "px-4 py-1.5 text-sm font-medium rounded-full bg-sky-600 text-white",
                                            "px-4 py-1.5 text-sm font-medium rounded-full bg-white border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer")),
            class_name="flex gap-2 mb-5",
        ),
        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            *[rx.el.th(h, class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase")
                              for h in ["Fecha", "Tipo", "Monto", "Método", "Observación", ""]],
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(rx.foreach(CajaState.movimientos.to(list[dict]), _fila_mov)),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto",
            ),
            rx.el.div(
                rx.el.button(rx.icon("chevron-left", size=15), "Anterior",
                             on_click=CajaState.prev_page, disabled=CajaState.page <= 1,
                             class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-40 cursor-pointer"),
                rx.el.span(CajaState.page, " / ", CajaState.total_pages, class_name="text-sm text-gray-500"),
                rx.el.button("Siguiente", rx.icon("chevron-right", size=15),
                             on_click=CajaState.next_page, disabled=CajaState.page >= CajaState.total_pages,
                             class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-40 cursor-pointer"),
                class_name="flex items-center justify-between px-4 py-3 border-t border-gray-100",
            ),
            class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
        ),
        on_mount=CajaState.on_mount,
    )
