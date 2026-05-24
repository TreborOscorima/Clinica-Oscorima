from __future__ import annotations

import reflex as rx

from clinica_app.state.base import BaseState


# ── Primitivos de navegación ──────────────────────────────────────────────────

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
        on_click=BaseState.close_sidebar,
        class_name="block",
    )


def _section(label: str) -> rx.Component:
    return rx.el.p(
        label,
        class_name="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 mb-1 mt-5",
    )


# ── Bloques reutilizables ─────────────────────────────────────────────────────

def _logo() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("stethoscope", size=20, color="white"),
            class_name="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center shrink-0",
        ),
        rx.el.span("WaykiSAC", class_name="ml-2 font-bold text-gray-900 text-lg"),
        class_name="flex items-center px-3 py-4 shrink-0",
    )


def _nav_links() -> rx.Component:
    return rx.el.nav(
        _section("Gestión"),
        _nav_item("Dashboard",        "layout-dashboard",  "/"),
        _nav_item("Pacientes",         "users",             "/pacientes"),
        _nav_item("Historia Clínica",  "clipboard-list",    "/historia-clinica"),
        _nav_item("Profesionales",     "user-check",        "/profesionales"),
        _nav_item("Calendario",        "calendar-days",     "/calendario"),
        _nav_item("Turnos",            "calendar-clock",    "/turnos"),
        _nav_item("Servicios",         "stethoscope",       "/servicios"),
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
        class_name="flex-1 space-y-0.5 overflow-y-auto px-2 pb-2",
    )


def _user_footer() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                BaseState.user_nombre[:1].upper(),
                class_name="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center text-sm font-bold shrink-0",
            ),
            rx.el.div(
                rx.el.p(BaseState.user_nombre, class_name="text-sm font-medium text-gray-900 truncate max-w-[7rem]"),
                rx.el.p(BaseState.rol_display, class_name="text-xs text-gray-500"),
                class_name="flex-1 min-w-0",
            ),
            rx.el.button(
                rx.icon("log-out", size=16),
                on_click=BaseState.logout,
                class_name="ml-auto text-gray-400 hover:text-red-500 transition-colors cursor-pointer shrink-0",
                title="Cerrar sesión",
            ),
            class_name="flex items-center gap-2",
        ),
        class_name="shrink-0 px-3 py-3 border-t border-gray-200",
    )


# ── Componentes públicos ──────────────────────────────────────────────────────

def sidebar() -> rx.Component:
    """
    Sidebar de escritorio — sticky, ocupa todo el alto del viewport.
    Oculto en mobile/tablet (< lg), visible en lg+.
    """
    return rx.el.aside(
        _logo(),
        _nav_links(),
        _user_footer(),
        class_name=(
            "hidden lg:flex flex-col w-64 shrink-0 "
            "bg-white border-r border-gray-200 "
            "h-screen sticky top-0 overflow-y-auto"
        ),
    )


def mobile_drawer() -> rx.Component:
    """
    Drawer móvil — slide-in overlay activado por el botón hamburguesa.
    Solo renderiza contenido cuando sidebar_open=True.
    Invisible en lg+ vía CSS.
    """
    return rx.cond(
        BaseState.sidebar_open,
        rx.el.div(
            # Backdrop
            rx.el.div(
                on_click=BaseState.close_sidebar,
                class_name="fixed inset-0 bg-black/50 z-40 lg:hidden",
            ),
            # Panel
            rx.el.aside(
                # Logo + botón cerrar
                rx.el.div(
                    rx.el.div(
                        rx.icon("stethoscope", size=20, color="white"),
                        class_name="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center shrink-0",
                    ),
                    rx.el.span("WaykiSAC", class_name="ml-2 font-bold text-gray-900 text-lg flex-1"),
                    rx.el.button(
                        rx.icon("x", size=20),
                        on_click=BaseState.close_sidebar,
                        class_name="p-1 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer shrink-0",
                    ),
                    class_name="flex items-center px-3 py-4 shrink-0",
                ),
                _nav_links(),
                _user_footer(),
                class_name=(
                    "fixed left-0 top-0 h-full w-64 "
                    "bg-white shadow-2xl z-50 "
                    "flex flex-col overflow-y-auto lg:hidden"
                ),
            ),
            class_name="lg:hidden",
        ),
    )
