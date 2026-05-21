from __future__ import annotations

import reflex as rx

from clinica_app.components.sidebar import sidebar
from clinica_app.state.base import BaseState


def shell(*content: rx.Component, title: str = "", on_mount=None) -> rx.Component:
    """
    Layout principal de la app: sidebar fijo + área de contenido scrollable.
    Protegida: redirige al login si el usuario no está autenticado.
    `on_mount` se reenvía al div raíz para que Reflex lo dispare al montar la página.
    """
    outer_kwargs = {}
    if on_mount is not None:
        outer_kwargs["on_mount"] = on_mount

    return rx.el.div(
        rx.cond(
            BaseState.is_authenticated,
            # Layout autenticado
            rx.el.div(
                sidebar(),
                # Contenido principal
                rx.el.main(
                    # Header de página
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
                    class_name="ml-56 p-8 min-h-screen bg-gray-50",
                ),
                class_name="flex",
            ),
            # Redirect — este branch solo se ve un frame antes del redirect
            rx.el.div(
                rx.el.div(
                    rx.icon("loader-circle", size=32, class_name="animate-spin text-sky-600"),
                    class_name="flex items-center justify-center h-screen",
                ),
                on_mount=BaseState.require_auth,
            ),
        ),
        **outer_kwargs,
    )
