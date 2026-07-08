from __future__ import annotations

import reflex as rx

from clinica_app.components.sidebar import mobile_drawer, sidebar
from clinica_app.state.base import BaseState
from clinica_app.state.auth import AuthState


def _mobile_topbar() -> rx.Component:
    """
    Barra superior visible solo en mobile/tablet (< lg).
    Contiene el botón hamburguesa y el logo de la app.
    """
    return rx.el.header(
        rx.el.button(
            rx.icon("menu", size=22),
            on_click=BaseState.toggle_sidebar,
            class_name=(
                "p-2 rounded-lg text-gray-600 "
                "hover:bg-gray-100 transition-colors cursor-pointer"
            ),
            aria_label="Abrir menú",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("stethoscope", size=16, color="white"),
                class_name="w-6 h-6 bg-sky-600 rounded-md flex items-center justify-center",
            ),
            rx.el.span("WaykiSAC", class_name="ml-2 font-bold text-gray-900"),
            class_name="flex items-center flex-1",
        ),
        class_name=(
            "flex items-center gap-3 h-14 px-4 shrink-0 "
            "bg-white border-b border-gray-200 "
            "sticky top-0 z-20 lg:hidden"
        ),
    )


def _modal_selector_sede() -> rx.Component:
    """Modal de selección de sucursal — aparece post-login cuando hay múltiples sedes."""
    return rx.cond(
        AuthState.mostrar_selector_sede,
        rx.el.div(
            # Backdrop z-40 — debajo del panel
            rx.el.div(class_name="fixed inset-0 bg-black/60 z-40"),
            # Panel centrado z-50 — encima del backdrop
            rx.el.div(
                rx.el.div(
                    # Header
                    rx.el.div(
                        rx.el.div(
                            rx.icon("map-pin", size=22, class_name="text-sky-600"),
                            class_name="w-10 h-10 rounded-full bg-sky-50 flex items-center justify-center mx-auto mb-3",
                        ),
                        rx.el.h2(
                            "¿En qué sucursal trabajás hoy?",
                            class_name="text-lg font-semibold text-gray-900 text-center",
                        ),
                        rx.el.p(
                            "Todos los datos (turnos, caja, cobros) se filtrarán por la sucursal que elijas.",
                            class_name="text-sm text-gray-500 text-center mt-1",
                        ),
                        class_name="mb-5",
                    ),
                    # Lista de sedes — cada botón llama seleccionar_sede con el id
                    rx.el.div(
                        rx.foreach(
                            AuthState.sedes_disponibles,
                            lambda sede: rx.el.button(
                                rx.el.div(
                                    rx.el.div(
                                        rx.icon("building-2", size=18, class_name="text-sky-600"),
                                        class_name="w-9 h-9 rounded-lg bg-sky-50 flex items-center justify-center shrink-0",
                                    ),
                                    rx.el.div(
                                        rx.el.p(sede["nombre"], class_name="text-sm font-medium text-gray-900"),
                                        rx.el.p(sede["direccion"], class_name="text-xs text-gray-500"),
                                        class_name="flex-1 text-left",
                                    ),
                                    rx.icon("chevron-right", size=16, class_name="text-gray-400 shrink-0"),
                                    class_name="flex items-center gap-3",
                                ),
                                on_click=AuthState.seleccionar_sede(sede["id"]),
                                type="button",
                                class_name=(
                                    "w-full px-4 py-3 rounded-xl border border-gray-200 "
                                    "hover:border-sky-400 hover:bg-sky-50 transition-all cursor-pointer "
                                    "text-left"
                                ),
                            ),
                        ),
                        class_name="space-y-2",
                    ),
                    class_name="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 relative z-50 pointer-events-auto",
                ),
                class_name="fixed inset-0 z-50 flex items-center justify-center pointer-events-none",
            ),
        ),
    )


def shell(*content: rx.Component, title: str = "", on_mount=None) -> rx.Component:
    """
    Shell principal del SaaS.

    Estructura de escritorio (lg+):
        [sidebar 256 px] | [contenido flexible — ocupa todo el ancho restante]

    Estructura mobile/tablet (< lg):
        [topbar sticky] / [contenido full-width]
        [drawer slide-in cuando sidebar_open=True]

    El contenido nunca tiene max-width — se estira al 100% del espacio disponible.
    """
    outer_kwargs: dict = {}
    if on_mount is not None:
        outer_kwargs["on_mount"] = on_mount

    return rx.el.div(
        rx.cond(
            BaseState.is_authenticated,

            # ── Shell autenticado ──────────────────────────────────────────────
            rx.el.div(
                # Modal selector de sucursal (aparece si hay múltiples sedes)
                _modal_selector_sede(),
                # Sidebar fijo de escritorio (sticky, h-screen)
                sidebar(),
                # Drawer overlay para mobile/tablet
                mobile_drawer(),
                # Columna derecha: topbar mobile + área de contenido
                rx.el.div(
                    _mobile_topbar(),
                    # Área de contenido principal — se estira al 100%
                    rx.el.main(
                        *content,
                        class_name="p-4 sm:p-6 lg:p-8",
                    ),
                    class_name=(
                        "flex flex-col flex-1 min-w-0 "
                        "overflow-y-auto overflow-x-hidden "
                        "bg-gray-50"
                    ),
                ),
                # Inicializador de atajos de teclado globales (invisible, se monta una sola vez)
                rx.el.div(
                    on_mount=BaseState.setup_keyboard_shortcuts,
                    class_name="hidden",
                    aria_hidden="true",
                ),
                class_name="flex h-screen w-full overflow-hidden",
            ),

            # ── Unauthenticated: spinner + redirect ────────────────────────────
            rx.el.div(
                rx.el.div(
                    rx.icon(
                        "loader-circle",
                        size=32,
                        class_name="animate-spin text-sky-600",
                    ),
                    class_name="flex items-center justify-center h-screen",
                ),
                on_mount=BaseState.require_auth,
            ),
        ),
        **outer_kwargs,
    )
