from __future__ import annotations

import reflex as rx

from clinica_app.state.base import BaseState


def _nav_item(label: str, icon: str, href: str) -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.icon(icon, size=17),
            rx.el.span(label, class_name="ml-3 text-sm font-medium"),
            class_name=rx.cond(
                rx.State.router.page.path == href,
                "flex items-center px-3 py-2 rounded-lg bg-sky-100 text-sky-700",
                "flex items-center px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors",
            ),
        ),
        href=href,
        class_name="block",
    )


def _section(label: str) -> rx.Component:
    return rx.el.p(
        label,
        class_name="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-1 mt-5",
    )


def sidebar() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            # ── Logo ──────────────────────────────────────────────────────────
            rx.el.div(
                rx.el.div(
                    rx.icon("stethoscope", size=20, color="white"),
                    class_name="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center",
                ),
                rx.el.span("WaykiSAC", class_name="ml-2 font-bold text-gray-900 text-lg"),
                class_name="flex items-center px-3 mb-6",
            ),

            # ── Navegación ────────────────────────────────────────────────────
            rx.el.nav(
                _section("Gestión"),
                _nav_item("Dashboard",       "layout-dashboard", "/"),
                _nav_item("Pacientes",        "users",            "/pacientes"),
                _nav_item("Profesionales",    "user-check",       "/profesionales"),
                _nav_item("Turnos",           "calendar-clock",   "/turnos"),
                _nav_item("Servicios",        "stethoscope",      "/servicios"),

                _section("Operaciones"),
                _nav_item("Punto de Cobro",   "credit-card",      "/cobro"),
                _nav_item("Caja",             "wallet",           "/caja"),
                _nav_item("Cuentas Ctes.",    "file-text",        "/cuentas"),
                _nav_item("Compras",          "shopping-cart",    "/compras"),
                _nav_item("Inventario",       "package",          "/inventario"),
                _nav_item("Promociones",      "tag",              "/promociones"),
                _nav_item("Reportes",         "bar-chart-2",      "/reportes"),

                rx.cond(
                    BaseState.is_admin,
                    rx.el.div(
                        _section("Admin"),
                        _nav_item("Configuración", "settings", "/configuracion"),
                    ),
                ),
                class_name="space-y-0.5 overflow-y-auto",
            ),

            # ── Footer ────────────────────────────────────────────────────────
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            BaseState.user_nombre[:1].upper(),
                            class_name="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0",
                        ),
                        rx.el.div(
                            rx.el.p(BaseState.user_nombre, class_name="text-sm font-medium text-gray-900 truncate max-w-24"),
                            rx.el.p(BaseState.rol_display, class_name="text-xs text-gray-500"),
                        ),
                        class_name="flex items-center gap-2 flex-1 min-w-0",
                    ),
                    rx.el.button(
                        rx.icon("log-out", size=16),
                        on_click=BaseState.logout,
                        class_name="text-gray-400 hover:text-red-500 transition-colors cursor-pointer flex-shrink-0",
                        title="Cerrar sesión",
                    ),
                    class_name="flex items-center justify-between",
                ),
                class_name="absolute bottom-0 left-0 right-0 p-3 border-t border-gray-200 bg-white",
            ),

            class_name="flex flex-col h-full pt-4 px-2 pb-16 relative overflow-hidden",
        ),
        class_name="fixed left-0 top-0 bottom-0 w-56 bg-white border-r border-gray-200 shadow-sm z-10 overflow-y-auto",
    )
