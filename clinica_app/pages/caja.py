from __future__ import annotations

import reflex as rx

from clinica_app.components.badge import estado_badge
from clinica_app.components.layout import shell
from clinica_app.components.stat_card import stat_card
from clinica_app.components.ui import page_header
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
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
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
                                default_value=CajaState.form_monto,
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
                            default_value=CajaState.form_metodo,
                            on_change=CajaState.set_form_metodo,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Observación
                    rx.el.div(
                        rx.el.label("Observación", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        
                        rx.el.textarea(
                            default_value=CajaState.form_observacion,
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
                        data_modal_submit="1",
                        title="Guardar (Ctrl+Enter)",
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


def _modal_cierre() -> rx.Component:
    return rx.cond(
        CajaState.modal_cierre,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=CajaState.cerrar_modal_cierre),
            rx.el.div(
                rx.el.div(
                    rx.el.h2("Cierre de caja", class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(rx.icon("x", size=18), on_click=CajaState.cerrar_modal_cierre,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between mb-5",
                ),
                # Resumen del día
                rx.el.div(
                    rx.el.p("Resumen del día de hoy", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3"),
                    rx.el.div(
                        rx.el.div(
                            rx.el.span("Ingresos", class_name="text-sm text-gray-600"),
                            rx.el.span(f"$ {CajaState.ingresos_dia}", class_name="text-sm font-semibold text-green-700"),
                            class_name="flex justify-between py-2 border-b border-gray-100",
                        ),
                        rx.el.div(
                            rx.el.span("Egresos", class_name="text-sm text-gray-600"),
                            rx.el.span(f"$ {CajaState.egresos_dia}", class_name="text-sm font-semibold text-red-600"),
                            class_name="flex justify-between py-2 border-b border-gray-100",
                        ),
                        rx.el.div(
                            rx.el.span("Saldo neto", class_name="text-sm font-semibold text-gray-800"),
                            rx.el.span(f"$ {CajaState.saldo_dia}", class_name="text-base font-bold text-sky-700"),
                            class_name="flex justify-between py-2",
                        ),
                    ),
                    class_name="bg-gray-50 rounded-xl p-4 mb-5",
                ),
                rx.el.p(
                    rx.icon("triangle-alert", size=14, class_name="inline mr-1 text-amber-500"),
                    "El cierre es definitivo para el día de hoy. No se puede revertir.",
                    class_name="text-xs text-amber-700 bg-amber-50 p-3 rounded-lg mb-4",
                ),
                # Mensajes
                rx.cond(
                    CajaState.cierre_msg != "",
                    rx.el.p(CajaState.cierre_msg, class_name="text-sm text-green-700 bg-green-50 p-3 rounded-lg mb-3"),
                ),
                rx.cond(
                    CajaState.cierre_error != "",
                    rx.el.p(CajaState.cierre_error, class_name="text-sm text-red-600 bg-red-50 p-3 rounded-lg mb-3"),
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=CajaState.cerrar_modal_cierre,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.cond(
                        CajaState.cierre_msg == "",
                        rx.el.button(
                            rx.cond(
                                CajaState.is_cerrando,
                                rx.el.div(rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                          "Cerrando...", class_name="flex items-center"),
                                rx.el.div(rx.icon("lock", size=16, class_name="mr-1"), "Confirmar cierre",
                                          class_name="flex items-center"),
                            ),
                            on_click=CajaState.confirmar_cierre,
                            disabled=CajaState.is_cerrando,
                            data_modal_submit="1",
                            title="Confirmar cierre (Ctrl+Enter)",
                            class_name="flex items-center px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-red-400 cursor-pointer",
                        ),
                    ),
                    class_name="flex gap-3 justify-end",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _tab_btn(label: str, tab_value: str, icon_name: str) -> rx.Component:
    return rx.el.button(
        rx.icon(icon_name, size=16),
        rx.el.span(label, class_name="ml-1.5"),
        on_click=lambda: CajaState.set_tab_caja(tab_value),
        class_name=rx.cond(
            CajaState.tab_caja == tab_value,
            "flex items-center px-4 py-2.5 text-sm font-semibold text-sky-700 border-b-2 border-sky-600 bg-white cursor-pointer",
            "flex items-center px-4 py-2.5 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-700 hover:border-gray-300 cursor-pointer",
        ),
    )


def _fila_comp(c: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.span(c["numero"], class_name="text-sm font-mono text-gray-700"),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span(c["fecha"], class_name="text-sm text-gray-600"),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span(c["paciente_nombre"], class_name="text-sm text-gray-700"),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span("$ ", c["total"], class_name="text-sm font-semibold text-green-700"),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.span(c["forma_pago"], class_name="text-sm text-gray-600 capitalize"),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.a(
                rx.icon("file-down", size=15),
                href=f"/api/recibo/pdf?comp_id={c['id']}&clinica_id={CajaState.clinica_id}&token={CajaState.download_token}",
                target="_blank",
                title="Descargar PDF",
                class_name="inline-flex items-center p-1.5 text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 rounded cursor-pointer",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50",
    )


def _seccion_comprobantes() -> rx.Component:
    return rx.el.div(
        # Filtros
        rx.el.div(
            rx.el.div(
                rx.icon("search", size=16, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"),
                rx.el.input(
                    type="text",
                    placeholder="Buscar por paciente o N. comprobante...",
                    default_value=CajaState.comp_busqueda,
                    on_change=CajaState.set_comp_busqueda,
                    class_name="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                class_name="relative flex-1",
            ),
            rx.el.select(
                rx.el.option("Todos los pagos", value=""),
                rx.el.option("Efectivo", value="efectivo"),
                rx.el.option("Tarjeta", value="tarjeta"),
                rx.el.option("Transferencia", value="transferencia"),
                rx.el.option("Otro", value="otro"),
                default_value=CajaState.comp_filtro_pago,
                on_change=CajaState.set_comp_filtro_pago,
                class_name="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
            ),
            class_name="flex gap-3 mb-5",
        ),
        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            *[rx.el.th(h, class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase")
                              for h in ["N. Comprobante", "Fecha", "Paciente", "Total", "Pago", "PDF"]],
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(rx.foreach(CajaState.comprobantes.to(list[dict]), _fila_comp)),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto",
            ),
            rx.cond(
                CajaState.comp_total == 0,
                rx.el.p("Sin comprobantes", class_name="text-sm text-gray-400 italic text-center py-8"),
            ),
            rx.el.div(
                rx.el.button(rx.icon("chevron-left", size=15), "Anterior",
                             on_click=CajaState.comp_prev_page, disabled=CajaState.comp_page <= 1,
                             class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-40 cursor-pointer"),
                rx.el.span(CajaState.comp_page, " / ", CajaState.comp_total_pages, class_name="text-sm text-gray-500"),
                rx.el.button("Siguiente", rx.icon("chevron-right", size=15),
                             on_click=CajaState.comp_next_page, disabled=CajaState.comp_page >= CajaState.comp_total_pages,
                             class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-40 cursor-pointer"),
                class_name="flex items-center justify-between px-4 py-3 border-t border-gray-100",
            ),
            class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
        ),
    )


def _seccion_movimientos() -> rx.Component:
    return rx.el.div(
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
        # Historial de cierres
        rx.el.div(
            rx.el.button(
                rx.icon("chevron-down", size=16, class_name=rx.cond(CajaState.ver_historial, "rotate-180 transition", "transition")),
                "Historial de cierres de caja",
                on_click=CajaState.toggle_historial,
                class_name="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 cursor-pointer mt-6",
            ),
            rx.cond(
                CajaState.ver_historial,
                rx.el.div(
                    rx.cond(
                        CajaState.cierres.length() == 0,
                        rx.el.p("Sin cierres registrados", class_name="text-sm text-gray-400 italic text-center py-4"),
                        rx.el.div(
                            rx.el.table(
                                rx.el.thead(
                                    rx.el.tr(
                                        *[rx.el.th(h, class_name="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase")
                                          for h in ["Fecha", "Ingresos", "Egresos", "Saldo neto", "Registrado"]],
                                    ),
                                    class_name="bg-gray-50 border-b border-gray-200",
                                ),
                                rx.el.tbody(
                                    rx.foreach(
                                        CajaState.cierres.to(list[dict]),
                                        lambda c: rx.el.tr(
                                            rx.el.td(c["fecha"], class_name="px-4 py-2 text-sm font-mono text-gray-600"),
                                            rx.el.td(rx.el.span(f"$ {c['total_ingresos']}", class_name="text-sm font-semibold text-green-700"), class_name="px-4 py-2"),
                                            rx.el.td(rx.el.span(f"$ {c['total_egresos']}", class_name="text-sm font-semibold text-red-600"), class_name="px-4 py-2"),
                                            rx.el.td(rx.el.span(f"$ {c['saldo']}", class_name="text-sm font-bold text-sky-700"), class_name="px-4 py-2"),
                                            rx.el.td(c["creado_en"], class_name="px-4 py-2 text-xs text-gray-400 font-mono"),
                                            class_name="border-t border-gray-100 hover:bg-gray-50",
                                        ),
                                    ),
                                ),
                                class_name="w-full border-collapse",
                            ),
                            class_name="mt-3 bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden",
                        ),
                    ),
                ),
            ),
        ),
    )


def caja_page() -> rx.Component:
    return shell(
        _modal_movimiento(),
        _modal_cierre(),
        page_header(
            "Caja",
            "Registra ingresos, egresos y cierres del día",
            action=rx.el.div(
                rx.el.button(
                    rx.icon("lock", size=15),
                    rx.el.span("Cierre del día", class_name="ml-1.5"),
                    on_click=CajaState.abrir_cierre,
                    class_name="inline-flex items-center px-4 py-2 text-sm font-medium border border-red-200 text-red-600 bg-red-50 rounded-lg hover:bg-red-100 cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("plus", size=16),
                    rx.el.span("Nuevo movimiento", class_name="ml-1.5"),
                    on_click=CajaState.abrir_modal,
                    data_new_action="1",
                    title="Nuevo movimiento (N)",
                    class_name="inline-flex items-center px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 cursor-pointer shadow-sm",
                ),
                class_name="flex items-center gap-3",
            ),
        ),
        # KPIs del día
        rx.el.div(
            stat_card("Ingresos hoy",  f"$ {CajaState.ingresos_dia}", "trending-up",   "green"),
            stat_card("Egresos hoy",   f"$ {CajaState.egresos_dia}",  "trending-down",  "red"),
            stat_card("Saldo del día", f"$ {CajaState.saldo_dia}",    "wallet",         "sky"),
            stat_card("Movimientos",   CajaState.total_movs_dia,       "receipt",        "purple"),
            class_name="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6",
        ),
        # Pestañas
        rx.el.div(
            _tab_btn("Movimientos", "movimientos", "arrow-left-right"),
            _tab_btn("Comprobantes", "comprobantes", "file-text"),
            class_name="flex border-b border-gray-200 mb-5",
        ),
        # Contenido según pestaña
        rx.cond(
            CajaState.tab_caja == "comprobantes",
            _seccion_comprobantes(),
            _seccion_movimientos(),
        ),
        on_mount=CajaState.on_mount,
    )
