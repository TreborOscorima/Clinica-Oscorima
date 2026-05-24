from __future__ import annotations

import reflex as rx

from clinica_app.components.sidebar import mobile_drawer, sidebar
from clinica_app.state.base import BaseState


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
            class_name="flex items-center",
        ),
        class_name=(
            "flex items-center gap-3 h-14 px-4 shrink-0 "
            "bg-white border-b border-gray-200 "
            "sticky top-0 z-20 lg:hidden"
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
                # Sidebar fijo de escritorio (sticky, h-screen)
                sidebar(),
                # Drawer overlay para mobile/tablet
                mobile_drawer(),
                # Columna derecha: topbar mobile + área de contenido
                rx.el.div(
                    _mobile_topbar(),
                    # Área de contenido principal — se estira al 100%
                    rx.el.main(
                        rx.cond(
                            title != "",
                            rx.el.div(
                                rx.el.h1(
                                    title,
                                    class_name="text-xl font-semibold text-gray-900",
                                ),
                                class_name="mb-6",
                            ),
                        ),
                        *content,
                        # Padding responsivo: compacto en mobile, generoso en desktop
                        class_name="p-4 sm:p-6 lg:p-8",
                    ),
                    # flex-1 + min-w-0: ocupa TODO el espacio a la derecha del sidebar
                    # overflow-x-hidden: evita scroll horizontal por contenido desbordado
                    class_name=(
                        "flex flex-col flex-1 min-w-0 "
                        "overflow-y-auto overflow-x-hidden "
                        "bg-gray-50"
                    ),
                ),
                # h-screen + overflow-hidden: la app ocupa exactamente el viewport;
                # el scroll ocurre dentro del área de contenido, no en el documento.
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
