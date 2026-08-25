from __future__ import annotations

import reflex as rx


def page_header(
    title: str | rx.Var,
    subtitle: str | rx.Var = "",
    action: rx.Component | None = None,
) -> rx.Component:
    """Encabezado estándar de página: título + subtítulo + acción opcional a la derecha."""
    if isinstance(subtitle, rx.Var):
        sub = rx.cond(
            subtitle != "",
            rx.el.p(subtitle, class_name="text-sm text-gray-500 mt-0.5"),
            rx.fragment(),
        )
    elif subtitle:
        sub = rx.el.p(subtitle, class_name="text-sm text-gray-500 mt-0.5")
    else:
        sub = rx.fragment()

    return rx.el.div(
        rx.el.div(
            rx.el.h1(title, class_name="text-xl font-bold text-gray-900 tracking-tight"),
            sub,
        ),
        action if action is not None else rx.fragment(),
        class_name="flex items-center justify-between mb-6",
    )


def empty_state(
    icon: str = "inbox",
    title: str = "Sin resultados",
    subtitle: str = "",
) -> rx.Component:
    """Estado vacío con icono y mensaje centrados."""
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, size=28, class_name="text-gray-300"),
            class_name="w-14 h-14 rounded-full bg-gray-50 flex items-center justify-center mx-auto mb-3",
        ),
        rx.el.p(title, class_name="text-sm font-medium text-gray-500 text-center"),
        rx.el.p(subtitle, class_name="text-xs text-gray-400 text-center mt-0.5") if subtitle else rx.fragment(),
        class_name="py-12 flex flex-col items-center",
    )


def primary_btn(
    label: str,
    icon: str,
    on_click,
    data_attr: str = "",
    title: str = "",
    disabled: rx.Var | bool = False,
) -> rx.Component:
    """Botón primario con icono — sky-600."""
    extra: dict = {}
    if data_attr:
        extra["data_new_action"] = "1"
    if title:
        extra["title"] = title

    return rx.el.button(
        rx.icon(icon, size=16),
        rx.el.span(label, class_name="ml-1.5"),
        on_click=on_click,
        disabled=disabled,
        class_name=(
            "inline-flex items-center px-4 py-2 text-sm font-medium text-white "
            "bg-sky-600 hover:bg-sky-700 disabled:bg-sky-400 "
            "rounded-lg cursor-pointer disabled:cursor-not-allowed transition-colors shadow-sm"
        ),
        **extra,
    )


def secondary_btn(
    label: str,
    icon: str,
    on_click,
    title: str = "",
) -> rx.Component:
    """Botón secundario con icono — borde gris."""
    extra: dict = {}
    if title:
        extra["title"] = title

    return rx.el.button(
        rx.icon(icon, size=15),
        rx.el.span(label, class_name="ml-1.5"),
        on_click=on_click,
        class_name=(
            "inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 "
            "border border-gray-300 bg-white hover:bg-gray-50 "
            "rounded-lg cursor-pointer transition-colors"
        ),
        **extra,
    )


def confirm_dialog(State) -> rx.Component:
    """Modal genérico de confirmación de borrado.

    Lee las vars del mixin de ``BaseState`` (``del_open`` / ``del_titulo`` /
    ``del_mensaje`` / ``del_confirm_label`` / ``del_procesando``) de la subclase
    de estado que se le pase, y dispara ``ejecutar_eliminar`` al confirmar.

    Se monta una sola vez por página:  ``confirm_dialog(PacientesState)``.
    """
    return rx.cond(
        State.del_open,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=State.cancelar_eliminar,
                data_modal_close="1",
            ),
            rx.el.div(
                rx.icon("trash-2", size=36, class_name="text-red-500 mx-auto mb-4"),
                rx.el.h2(
                    State.del_titulo,
                    class_name="text-lg font-semibold text-gray-900 text-center mb-2",
                ),
                rx.el.p(
                    State.del_mensaje,
                    class_name="text-sm text-gray-600 text-center mb-6",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.cancelar_eliminar,
                        class_name=(
                            "px-4 py-2 text-sm font-medium text-gray-700 border "
                            "border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"
                        ),
                    ),
                    rx.el.button(
                        rx.cond(
                            State.del_procesando,
                            rx.el.span(
                                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                                "Eliminando…",
                                class_name="flex items-center",
                            ),
                            rx.el.span(State.del_confirm_label),
                        ),
                        on_click=State.ejecutar_eliminar,
                        disabled=State.del_procesando,
                        data_modal_submit="1",
                        class_name=(
                            "px-5 py-2 text-sm font-medium text-white bg-red-600 "
                            "rounded-lg hover:bg-red-700 disabled:opacity-60 cursor-pointer"
                        ),
                    ),
                    class_name="flex justify-center gap-3",
                ),
                class_name="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm z-50 relative",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
    )


def table_header(*headers: str) -> rx.Component:
    """Fila de encabezado de tabla con fondo gris sutil."""
    return rx.el.thead(
        rx.el.tr(
            *[
                rx.el.th(
                    h,
                    class_name=(
                        "px-4 py-3 text-left text-xs font-semibold "
                        "text-gray-500 uppercase tracking-wide"
                    ),
                )
                for h in headers
            ],
            class_name="bg-gray-50 border-b border-gray-200",
        ),
    )
