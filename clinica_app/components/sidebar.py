from __future__ import annotations

import reflex as rx

from clinica_app.state.base import BaseState


def _nav_item(label: str, icon: str, href: str) -> rx.Component:
    active = rx.State.router.page.path == href
    return rx.el.a(
        rx.el.div(
            rx.icon(icon, size=18),
            rx.el.span(label, class_name="ml-3 text-sm font-medium"),
            class_name=rx.cond(
                rx.State.router.page.path == href,
                "flex items-center px-3 py-2.5 rounded-lg bg-sky-100 text-sky-700",
                "flex items-center px-3 py-2.5 rounded-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors",
            ),
        ),
        href=href,
        class_name="block",
    )


def sidebar() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            # Logo
            rx.el.div(
                rx.el.div(
                    rx.icon("stethoscope", size=20, color="white"),
                    class_name="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center",
                ),
                rx.el.span(
                    "WaykiSAC",
                    class_name="ml-2 font-bold text-gray-900 text-lg",
                ),
                class_name="flex items-center px-3 mb-8",
            ),
            # Navegación principal
            rx.el.nav(
                rx.el.p("MENÚ", class_name="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-2"),
                _nav_item("Dashboard",   "layout-dashboard", "/"),
                _nav_item("Pacientes",   "users",            "/pacientes"),
                _nav_item("Turnos",      "calendar",         "/turnos"),
                _nav_item("Caja",        "wallet",           "/caja"),
                _nav_item("Inventario",  "package",          "/inventario"),
                _nav_item("Reportes",    "bar-chart-2",      "/reportes"),
                rx.cond(
                    BaseState.is_admin,
                    rx.el.div(
                        rx.el.p("ADMIN", class_name="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-2 mt-6"),
                        _nav_item("Configuración", "settings", "/configuracion"),
                    ),
                ),
                class_name="space-y-1",
            ),
            # Footer — usuario
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            BaseState.user_nombre[:1].upper(),
                            class_name="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center text-sm font-bold",
                        ),
                        rx.el.div(
                            rx.el.p(BaseState.user_nombre, class_name="text-sm font-medium text-gray-900 truncate max-w-28"),
                            rx.el.p(BaseState.rol_display, class_name="text-xs text-gray-500"),
                        ),
                        class_name="flex items-center gap-2 flex-1 min-w-0",
                    ),
                    rx.el.button(
                        rx.icon("log-out", size=16),
                        on_click=BaseState.logout,
                        class_name="text-gray-400 hover:text-red-500 transition-colors cursor-pointer",
                        title="Cerrar sesión",
                    ),
                    class_name="flex items-center justify-between",
                ),
                class_name="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-white",
            ),
            class_name="flex flex-col h-full p-4 relative",
        ),
        class_name="fixed left-0 top-0 bottom-0 w-56 bg-white border-r border-gray-200 shadow-sm z-10",
    )
