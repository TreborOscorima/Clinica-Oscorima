from __future__ import annotations

import reflex as rx


def _campo(label: str, tipo: str, value, on_change, placeholder: str = "") -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-xs font-medium text-gray-600 mb-1"),

        rx.el.input(
            type=tipo, default_value=value, on_change=on_change, placeholder=placeholder,
            class_name="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm "
                       "focus:outline-none focus:ring-2 focus:ring-sky-500 transition bg-white",
        ),
    )


def _select(label: str, value, on_change, options: list[tuple[str, str]]) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-xs font-medium text-gray-600 mb-1"),
        rx.el.select(
            *[rx.el.option(lbl, value=val) for val, lbl in options],
            default_value=value, on_change=on_change,
            class_name="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm "
                       "focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white",
        ),
    )


def _campo_pw(label: str, value, on_change) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-xs font-medium text-gray-600 mb-1"),

        rx.el.input(
            type="password", default_value=value, on_change=on_change, placeholder="••••••••",
            class_name="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm "
                       "focus:outline-none focus:ring-2 focus:ring-sky-500 transition",
        ),
    )


def _btn(label: str, on_click, color: str = "sky", size: str = "md") -> rx.Component:
    px = "px-4 py-2" if size == "md" else "px-3 py-1.5"
    return rx.el.button(
        label, on_click=on_click,
        class_name=f"{px} text-sm font-medium bg-{color}-600 text-white rounded-lg "
                   f"hover:bg-{color}-700 transition cursor-pointer",
    )


def _btn_spinner(label: str, loading_label: str, is_loading, on_click, **kwargs) -> rx.Component:
    return rx.el.button(
        rx.cond(
            is_loading,
            rx.el.div(
                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                loading_label, class_name="flex items-center",
            ),
            label,
        ),
        on_click=on_click, disabled=is_loading,
        class_name="px-4 py-2 text-sm bg-sky-600 text-white font-medium rounded-lg "
                   "hover:bg-sky-700 disabled:bg-sky-400 disabled:cursor-not-allowed transition cursor-pointer",
        **kwargs,
    )


def _alert(msg, color: str = "green") -> rx.Component:
    icon = "circle-check" if color == "green" else "circle-alert"
    return rx.el.div(
        rx.icon(icon, size=14, class_name=f"shrink-0 text-{color}-600"),
        rx.el.span(msg, class_name=f"text-sm text-{color}-700 ml-2"),
        class_name=f"flex items-center mt-3 px-3 py-2 rounded-lg bg-{color}-50 border border-{color}-200",
    )


def _toggle_switch(value: bool, on_click) -> rx.Component:
    return rx.el.button(
        rx.el.div(
            rx.el.div(
                class_name=rx.cond(
                    value,
                    "absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all",
                    "absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all",
                ),
            ),
            class_name=rx.cond(
                value,
                "relative w-9 h-5 bg-sky-600 rounded-full transition-colors",
                "relative w-9 h-5 bg-gray-300 rounded-full transition-colors",
            ),
        ),
        on_click=on_click,
        class_name="cursor-pointer focus:outline-none",
    )


def _section_title(title: str, subtitle: str) -> rx.Component:
    return rx.el.div(
        rx.el.h2(title, class_name="text-sm font-bold text-gray-700 uppercase tracking-wider"),
        rx.el.p(subtitle, class_name="text-xs text-gray-500 mt-0.5"),
        class_name="mb-5",
    )
