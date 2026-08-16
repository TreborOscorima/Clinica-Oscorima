from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.salud import SaludState


def _refresh_btn() -> rx.Component:
    return rx.el.button(
        rx.icon("refresh-cw", size=15),
        rx.el.span("Actualizar", class_name="ml-1.5"),
        on_click=SaludState.cargar,
        disabled=SaludState.is_loading,
        class_name=(
            "inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 "
            "border border-gray-300 bg-white hover:bg-gray-50 rounded-lg cursor-pointer "
            "transition-colors disabled:opacity-50"
        ),
    )


def _status_banner() -> rx.Component:
    ok = SaludState.status == "ok"
    return rx.el.div(
        rx.icon(
            rx.cond(ok, "circle-check", "triangle-alert"),
            size=20,
            class_name=rx.cond(ok, "text-green-600", "text-amber-600"),
        ),
        rx.el.span(
            rx.cond(ok, "Sistema operativo", "Sistema degradado"),
            class_name=rx.cond(
                ok, "text-green-800 font-semibold", "text-amber-800 font-semibold"
            ),
        ),
        class_name=rx.cond(
            ok,
            "flex items-center gap-2 p-4 rounded-xl border border-green-200 bg-green-50 mb-5",
            "flex items-center gap-2 p-4 rounded-xl border border-amber-200 bg-amber-50 mb-5",
        ),
    )


def _card(icono: str, titulo: str, valor: rx.Var, detalle: rx.Var, ok: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(icono, size=18, class_name="text-gray-400"),
                rx.el.span(titulo, class_name="text-sm font-medium text-gray-500"),
                class_name="flex items-center gap-2",
            ),
            rx.el.span(
                class_name=rx.cond(
                    ok,
                    "w-2.5 h-2.5 rounded-full bg-green-500",
                    "w-2.5 h-2.5 rounded-full bg-amber-500",
                ),
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.p(valor, class_name="text-2xl font-bold text-gray-900 mt-3"),
        rx.el.p(detalle, class_name="text-xs text-gray-500 mt-1"),
        class_name="bg-white rounded-xl border border-gray-100 shadow-sm p-5",
    )


def _disco_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("hard-drive", size=18, class_name="text-gray-400"),
                rx.el.span("Disco", class_name="text-sm font-medium text-gray-500"),
                class_name="flex items-center gap-2",
            ),
            rx.el.span(
                class_name=rx.cond(
                    SaludState.disco_ok,
                    "w-2.5 h-2.5 rounded-full bg-green-500",
                    "w-2.5 h-2.5 rounded-full bg-amber-500",
                ),
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.p(
            SaludState.disco_pct.to(str) + "%",
            class_name="text-2xl font-bold text-gray-900 mt-3",
        ),
        rx.el.div(
            rx.el.div(
                class_name=rx.cond(
                    SaludState.disco_ok,
                    "h-2 rounded-full bg-green-500",
                    "h-2 rounded-full bg-amber-500",
                ),
                style={"width": SaludState.disco_pct.to(str) + "%"},
            ),
            class_name="w-full h-2 bg-gray-100 rounded-full mt-2 overflow-hidden",
        ),
        rx.el.p(SaludState.disco_texto, class_name="text-xs text-gray-500 mt-1"),
        class_name="bg-white rounded-xl border border-gray-100 shadow-sm p-5",
    )


def salud_page() -> rx.Component:
    return shell(
        page_header(
            "Salud del sistema",
            "Estado en vivo: base de datos, disco, uptime y backups",
            action=_refresh_btn(),
        ),
        _status_banner(),
        rx.el.div(
            _card(
                "database", "Base de datos",
                rx.cond(SaludState.db_ok, "Conectada", "Sin conexión"),
                SaludState.db_latencia,
                SaludState.db_ok,
            ),
            _disco_card(),
            _card(
                "clock", "Uptime",
                SaludState.uptime_texto,
                "Tiempo desde el último arranque",
                True,
            ),
            _card(
                "shield-check", "Backups",
                rx.cond(
                    SaludState.backups_configurado,
                    rx.cond(SaludState.backups_ok, "Al día", "Atrasado"),
                    "Sin configurar",
                ),
                SaludState.backups_texto,
                SaludState.backups_ok,
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
        ),
        on_mount=SaludState.on_mount,
    )
