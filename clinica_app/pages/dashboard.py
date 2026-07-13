from __future__ import annotations

import reflex as rx

from clinica_app.components.badge import estado_badge
from clinica_app.components.layout import shell
from clinica_app.components.stat_card import stat_card
from clinica_app.state.dashboard import DashboardState


def _fila_turno_reciente(t: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(rx.el.span("#", t["id"]), class_name="px-4 py-3 text-xs font-mono text-gray-400"),
        rx.el.td(t["paciente_nombre"], class_name="px-4 py-3 text-sm text-gray-700"),
        rx.el.td(t["fecha_hora"], class_name="px-4 py-3 text-sm text-gray-600 font-mono"),
        rx.el.td(estado_badge(t["estado"]), class_name="px-4 py-3"),
        class_name="border-t border-gray-100 hover:bg-gray-50",
    )


def dashboard_page() -> rx.Component:
    return shell(
        # Saludo
        rx.el.div(
            rx.el.h1(
                rx.el.span("Hola, ", class_name="font-normal text-gray-500"),
                DashboardState.user_nombre,
                class_name="text-2xl font-bold text-gray-900 tracking-tight mb-1",
            ),
            rx.el.p("Resumen de actividad de hoy", class_name="text-sm text-gray-500"),
            class_name="mb-8",
        ),
        # KPIs
        rx.el.div(
            stat_card("Pacientes activos",   DashboardState.total_pacientes,  "users",    "sky"),
            stat_card("Turnos hoy",          DashboardState.turnos_hoy,        "calendar", "indigo"),
            stat_card("Turnos pendientes",   DashboardState.turnos_pendientes, "clock",    "yellow"),
            stat_card("Ingresos hoy",        f"$ {DashboardState.ingresos_hoy}", "wallet", "green"),
            class_name="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8",
        ),
        # Accesos rápidos
        rx.el.div(
            rx.el.p("Acceso rápido", class_name="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4"),
            rx.el.div(
                _quick_link("/pacientes", "users",          "Pacientes"),
                _quick_link("/turnos",    "calendar",       "Turnos"),
                _quick_link("/cobro",     "shopping-cart",  "Cobro"),
                _quick_link("/caja",      "wallet",         "Caja"),
                _quick_link("/compras",   "truck",          "Compras"),
                _quick_link("/inventario","package",        "Inventario"),
                class_name="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3",
            ),
            class_name="mb-8",
        ),
        # Resumen financiero del mes
        rx.el.div(
            rx.el.div(
                rx.icon("trending-up", size=16, class_name="text-sky-600 mr-2"),
                rx.el.p("Resumen financiero del mes", class_name="text-sm font-semibold text-gray-700"),
                class_name="flex items-center mb-4",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.p("Ingresos del mes", class_name="text-xs text-gray-500 uppercase tracking-wide"),
                    rx.el.p(f"$ {DashboardState.ingresos_mes}", class_name="text-xl font-bold text-green-700 mt-1"),
                    rx.el.div(
                        rx.el.span(DashboardState.variacion_pct, "%", class_name=rx.cond(
                            DashboardState.variacion_pct.startswith("+"),
                            "text-xs font-medium text-green-600",
                            "text-xs font-medium text-red-600",
                        )),
                        rx.el.span(" vs mes anterior", class_name="text-xs text-gray-400 ml-1"),
                        class_name="flex items-center mt-1",
                    ),
                    class_name="bg-white rounded-xl border border-gray-100 shadow-sm p-4",
                ),
                rx.el.div(
                    rx.el.p("Egresos del mes", class_name="text-xs text-gray-500 uppercase tracking-wide"),
                    rx.el.p(f"$ {DashboardState.egresos_mes}", class_name="text-xl font-bold text-red-600 mt-1"),
                    rx.el.p(f"Mes anterior: $ {DashboardState.egresos_mes_ant}", class_name="text-xs text-gray-400 mt-1"),
                    class_name="bg-white rounded-xl border border-gray-100 shadow-sm p-4",
                ),
                rx.el.div(
                    rx.el.p("Saldo neto del mes", class_name="text-xs text-gray-500 uppercase tracking-wide"),
                    rx.el.p(f"$ {DashboardState.saldo_mes}", class_name="text-xl font-bold text-sky-700 mt-1"),
                    rx.el.p("Ingresos − Egresos", class_name="text-xs text-gray-400 mt-1"),
                    class_name="bg-white rounded-xl border border-gray-100 shadow-sm p-4",
                ),
                class_name="grid grid-cols-1 sm:grid-cols-3 gap-4",
            ),
            class_name="mb-8",
        ),
        # Gráfico ingresos últimos 7 días
        rx.el.div(
            rx.el.p("Ingresos últimos 7 días", class_name="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4"),
            rx.el.div(
                rx.foreach(
                    DashboardState.ingresos_7dias,
                    lambda d: rx.el.div(
                        rx.el.div(
                            rx.el.div(
                                class_name="w-full bg-sky-500 rounded-t-sm",
                                style={"height": d["pct"]},
                            ),
                            class_name="w-full flex flex-col justify-end",
                            style={"height": "80px"},
                        ),
                        rx.el.p(d["fecha"], class_name="text-xs text-gray-400 mt-1 text-center"),
                        rx.el.p(d["monto"], class_name="text-xs text-gray-500 text-center font-mono"),
                        class_name="flex flex-col items-center flex-1",
                    ),
                ),
                class_name="flex gap-2 items-end p-4 bg-white rounded-xl shadow-sm border border-gray-100",
            ),
            class_name="mb-8",
        ),
        # Top 5 servicios del mes
        rx.el.div(
            rx.el.p("Top servicios del mes", class_name="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4"),
            rx.cond(
                DashboardState.top_servicios,
                rx.el.div(
                    rx.foreach(
                        DashboardState.top_servicios.to(list[dict]),
                        lambda s: rx.el.div(
                            rx.el.div(
                                rx.el.span(s["nombre"], class_name="text-sm font-medium text-gray-800 truncate flex-1"),
                                rx.el.span(
                                    s["count"], " sesiones",
                                    class_name="text-xs text-gray-400 ml-2 shrink-0",
                                ),
                                class_name="flex items-center justify-between mb-1",
                            ),
                            rx.el.div(
                                rx.el.span("$", s["total"], class_name="text-xs font-semibold text-sky-600"),
                                class_name="text-right",
                            ),
                            class_name="px-4 py-3 border-b border-gray-100 last:border-0",
                        ),
                    ),
                    class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
                ),
                rx.el.div(
                    rx.icon("bar-chart-2", size=28, class_name="text-gray-200 mb-2"),
                    rx.el.p("Sin cobros este mes", class_name="text-sm text-gray-400"),
                    class_name="flex flex-col items-center py-8 bg-white rounded-xl shadow-sm border border-gray-100",
                ),
            ),
            class_name="mb-8",
        ),
        # Agenda del profesional (solo si rol = profesional)
        rx.cond(
            DashboardState.is_profesional,
            rx.el.div(
                rx.el.div(
                    rx.icon("calendar-check", size=16, class_name="text-sky-600 mr-2"),
                    rx.el.p("Mis turnos de hoy", class_name="text-sm font-semibold text-gray-700"),
                    class_name="flex items-center mb-4",
                ),
                rx.cond(
                    DashboardState.mis_turnos_hoy.length() == 0,
                    rx.el.div(
                        rx.icon("coffee", size=28, class_name="text-gray-200 mb-2"),
                        rx.el.p("Sin turnos asignados hoy", class_name="text-sm text-gray-400"),
                        class_name="flex flex-col items-center py-8 bg-white rounded-xl shadow-sm border border-gray-100",
                    ),
                    rx.el.div(
                        rx.foreach(
                            DashboardState.mis_turnos_hoy.to(list[dict]),
                            lambda t: rx.el.div(
                                rx.el.div(
                                    rx.el.span(t["hora"], class_name="text-sm font-bold text-sky-700 w-12"),
                                    rx.el.div(
                                        rx.el.p(t["paciente_nombre"], class_name="text-sm font-medium text-gray-800"),
                                        rx.el.p(t["servicio"], class_name="text-xs text-gray-500"),
                                        class_name="flex-1",
                                    ),
                                    estado_badge(t["estado"]),
                                    class_name="flex items-center gap-3",
                                ),
                                class_name="px-4 py-3 border-b border-gray-100 last:border-0",
                            ),
                        ),
                        class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
                    ),
                ),
                class_name="mb-8",
            ),
        ),
        # Turnos recientes
        rx.el.div(
            rx.el.p("Últimos turnos", class_name="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4"),
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            *[rx.el.th(h, class_name="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase")
                              for h in ["#", "Paciente", "Fecha/hora", "Estado"]],
                        ),
                        class_name="bg-gray-50 border-b border-gray-100",
                    ),
                    rx.el.tbody(rx.foreach(DashboardState.turnos_recientes.to(list[dict]), _fila_turno_reciente)),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto bg-white rounded-xl shadow-sm border border-gray-100",
            ),
        ),
        on_mount=DashboardState.on_mount,
    )


def _quick_link(href: str, icon: str, label: str) -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.el.div(
                rx.icon(icon, size=20, class_name="text-sky-600"),
                class_name="w-10 h-10 rounded-xl bg-sky-50 flex items-center justify-center mb-2",
            ),
            rx.el.span(label, class_name="text-sm font-medium text-gray-700"),
            class_name="flex flex-col items-center py-5",
        ),
        href=href,
        class_name=(
            "flex justify-center bg-white rounded-2xl border border-gray-100 shadow-sm "
            "hover:border-sky-300 hover:shadow-md hover:-translate-y-0.5 transition-all duration-150"
        ),
    )
