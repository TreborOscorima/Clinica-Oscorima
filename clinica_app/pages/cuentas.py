from __future__ import annotations

import reflex as rx

from clinica_app.components.badge import estado_badge
from clinica_app.components.layout import shell
from clinica_app.components.stat_card import stat_card
from clinica_app.components.ui import page_header
from clinica_app.state.cuentas import CuentasState


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _filtro_btn(label: str, valor: str) -> rx.Component:
    activo = rx.cond(
        CuentasState.filtro_estado == valor,
        "px-3 py-1.5 text-sm font-medium rounded-lg bg-sky-600 text-white",
        "px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer",
    )
    return rx.el.button(label, on_click=CuentasState.set_filtro_estado(valor), class_name=activo)


def _barra_progreso(d: dict) -> rx.Component:
    """Barra verde proporcional al porcentaje pagado."""
    pct = rx.cond(
        d["total"] == "0.00",
        "0",
        (d["pagado"].to(float) / d["total"].to(float) * 100).to(str),
    )
    return rx.el.div(
        rx.el.div(
            style={"width": pct + "%"},
            class_name="h-1.5 bg-green-500 rounded-full transition-all",
        ),
        class_name="w-full h-1.5 bg-gray-200 rounded-full mt-1",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Fila de tabla
# ─────────────────────────────────────────────────────────────────────────────

def _fila_deuda(d: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.p(d["paciente_nombre"], class_name="text-sm font-medium text-gray-900"),
            rx.el.p(d["creado_en"], class_name="text-xs text-gray-400 mt-0.5"),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        rx.el.td(
            rx.el.span(
                d["comprobante_numero"],
                class_name="text-xs font-mono text-gray-600 bg-gray-100 px-2 py-0.5 rounded",
            ),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        rx.el.td(
            rx.el.span("$", d["total"], class_name="text-sm text-gray-700"),
            class_name="px-4 py-3 whitespace-nowrap text-right",
        ),
        rx.el.td(
            rx.el.span("$", d["pagado"], class_name="text-sm text-green-700 font-medium"),
            class_name="px-4 py-3 whitespace-nowrap text-right",
        ),
        rx.el.td(
            rx.el.span(
                "$", d["saldo"],
                class_name=rx.cond(
                    d["estado"] == "saldado",
                    "text-sm text-gray-400",
                    "text-sm text-red-600 font-semibold",
                ),
            ),
            _barra_progreso(d),
            class_name="px-4 py-3 whitespace-nowrap text-right",
        ),
        rx.el.td(
            estado_badge(d["estado"]),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        rx.el.td(
            rx.cond(
                d["estado"] != "saldado",
                rx.el.button(
                    rx.icon("credit-card", size=14, class_name="mr-1"),
                    "Registrar pago",
                    on_click=CuentasState.abrir_pago(d),
                    class_name="flex items-center px-3 py-1.5 text-xs font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
                rx.el.span("—", class_name="text-xs text-gray-400"),
            ),
            class_name="px-4 py-3 whitespace-nowrap",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50 transition-colors",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Modal de pago
# ─────────────────────────────────────────────────────────────────────────────

def _modal_pago() -> rx.Component:
    return rx.cond(
        CuentasState.modal_pago,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=CuentasState.cerrar_pago),
            rx.el.div(
                # Cabecera
                rx.el.div(
                    rx.el.div(
                        rx.el.h2("Registrar pago", class_name="text-lg font-semibold text-gray-900"),
                        rx.el.p(
                            "Paciente: ", CuentasState.deuda_sel["paciente_nombre"],
                            class_name="text-sm text-gray-500 mt-0.5",
                        ),
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=CuentasState.cerrar_pago,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-start justify-between mb-5",
                ),
                # Resumen deuda
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Total deuda", class_name="text-xs text-gray-500"),
                        rx.el.span("$", CuentasState.deuda_sel["total"], class_name="text-sm font-medium text-gray-800"),
                        class_name="flex justify-between",
                    ),
                    rx.el.div(
                        rx.el.span("Ya pagado", class_name="text-xs text-gray-500"),
                        rx.el.span("$", CuentasState.deuda_sel["pagado"], class_name="text-sm font-medium text-green-700"),
                        class_name="flex justify-between",
                    ),
                    rx.el.div(
                        rx.el.span("Saldo pendiente", class_name="text-xs font-semibold text-gray-700"),
                        rx.el.span("$", CuentasState.deuda_sel["saldo"], class_name="text-sm font-bold text-red-600"),
                        class_name="flex justify-between pt-2 border-t border-gray-200 mt-1",
                    ),
                    class_name="bg-gray-50 rounded-lg p-3 mb-5 space-y-1.5",
                ),
                # Formulario
                rx.el.div(
                    # Monto
                    rx.el.div(
                        rx.el.label("Monto a pagar *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.div(
                            rx.el.span("$", class_name="text-gray-500 text-sm px-3"),
                            
                            rx.el.input(
                                type="text",
                                input_mode="decimal",
                                default_value=CuentasState.form_monto,
                                on_change=CuentasState.set_form_monto,
                                placeholder="0.00",
                                class_name="flex-1 py-2 pr-3 text-sm outline-none",
                            ),
                            class_name="flex items-center border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-sky-500",
                        ),
                    ),
                    # Método de pago
                    rx.el.div(
                        rx.el.label("Método de pago", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.select(
                            rx.el.option("Efectivo",       value="efectivo"),
                            rx.el.option("Tarjeta",        value="tarjeta"),
                            rx.el.option("Transferencia",  value="transferencia"),
                            rx.el.option("Otro",           value="otro"),
                            default_value=CuentasState.form_metodo,
                            on_change=CuentasState.set_form_metodo,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    # Observación
                    rx.el.div(
                        rx.el.label("Observación", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        
                        rx.el.input(
                            type="text",
                            default_value=CuentasState.form_obs,
                            on_change=CuentasState.set_form_obs,
                            placeholder="Opcional…",
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    class_name="space-y-4",
                ),
                # Error
                rx.cond(
                    CuentasState.form_error != "",
                    rx.el.div(
                        rx.icon("circle-alert", size=14, class_name="text-red-500 mr-1.5 flex-shrink-0"),
                        rx.el.span(CuentasState.form_error, class_name="text-sm text-red-700"),
                        class_name="flex items-center mt-4 p-3 bg-red-50 border border-red-200 rounded-lg",
                    ),
                ),
                # Botones
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=CuentasState.cerrar_pago,
                        class_name="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            CuentasState.is_saving,
                            rx.el.span(
                                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                                "Guardando…",
                                class_name="flex items-center",
                            ),
                            rx.el.span("Confirmar pago"),
                        ),
                        on_click=CuentasState.confirmar_pago,
                        disabled=CuentasState.is_saving,
                        data_modal_submit="1",
                        title="Confirmar pago (Ctrl+Enter)",
                        class_name="px-5 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-700 disabled:opacity-60 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3 mt-6",
                ),
                class_name="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md z-50 relative",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Página principal
# ─────────────────────────────────────────────────────────────────────────────

def cuentas_page() -> rx.Component:
    return shell(
        _modal_pago(),
        page_header("Cuentas Corrientes", "Gestioná saldos pendientes y pagos en cuotas"),
        # KPIs
        rx.el.div(
            stat_card(
                title="Deudores activos",
                value=CuentasState.total_deudores.to(str),
                icon="users",
                color="amber",
                subtitle="Con saldo pendiente",
            ),
            stat_card(
                title="Saldo total pendiente",
                value=rx.el.span("$", CuentasState.total_saldo),
                icon="wallet",
                color="red",
                subtitle="Suma de cuotas sin cobrar",
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6",
        ),
        # Filtros
        rx.el.div(
            # Botones de estado
            rx.el.div(
                _filtro_btn("Todos",     ""),
                _filtro_btn("Pendiente", "pendiente"),
                _filtro_btn("Parcial",   "parcial"),
                _filtro_btn("Saldado",   "saldado"),
                class_name="flex gap-2 flex-wrap",
            ),
            # Búsqueda
            rx.el.div(
                rx.icon("search", size=15, class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"),
                
                rx.el.input(
                    placeholder="Buscar paciente…",
                    on_change=CuentasState.set_busqueda,
                    data_search_input="1",
                    title="Buscar (/)",
                    class_name="pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 w-56",
                ),
                class_name="relative",
            ),
            class_name="flex items-center justify-between gap-4 mb-5",
        ),
        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Paciente",      class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Comprobante",   class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Total",         class_name="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Pagado",        class_name="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Saldo",         class_name="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("Estado",        class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.th("",              class_name="px-4 py-3"),
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(
                        rx.cond(
                            CuentasState.deudas,
                            rx.foreach(CuentasState.deudas, _fila_deuda),
                            rx.el.tr(
                                rx.el.td(
                                    rx.el.div(
                                        rx.icon("inbox", size=32, class_name="text-gray-300 mb-2"),
                                        rx.el.p("No hay deudas registradas", class_name="text-sm text-gray-400"),
                                    ),
                                    col_span=7,
                                    class_name="py-16",
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
                CuentasState.total_pages > 1,
                rx.el.div(
                    rx.el.button(
                        rx.icon("chevron-left", size=16), "Anterior",
                        on_click=CuentasState.prev_page,
                        disabled=CuentasState.page <= 1,
                        class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.span(
                        "Página ", CuentasState.page.to(str), " de ", CuentasState.total_pages.to(str),
                        class_name="text-sm text-gray-600",
                    ),
                    rx.el.button(
                        "Siguiente", rx.icon("chevron-right", size=16),
                        on_click=CuentasState.next_page,
                        disabled=CuentasState.page >= CuentasState.total_pages,
                        class_name="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 cursor-pointer",
                    ),
                    class_name="flex items-center justify-center gap-4 px-4 py-3 border-t border-gray-200",
                ),
            ),
            class_name="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden",
        ),
        on_mount=CuentasState.on_mount,
    )
