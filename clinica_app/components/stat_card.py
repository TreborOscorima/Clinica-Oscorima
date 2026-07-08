from __future__ import annotations

import reflex as rx


def stat_card(
    title: str | rx.Var,
    value: str | rx.Var,
    icon: str,
    color: str = "sky",
    subtitle: str | rx.Var = "",
) -> rx.Component:
    icon_bg   = f"bg-{color}-50"
    icon_text = f"text-{color}-600"
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(icon, size=22),
                class_name=f"p-3 rounded-xl {icon_bg} {icon_text} shrink-0",
            ),
            rx.el.div(
                rx.el.p(title, class_name="text-xs font-medium text-gray-500 uppercase tracking-wide"),
                rx.el.p(value, class_name="text-2xl font-bold text-gray-900 mt-1 leading-none"),
                rx.cond(
                    subtitle != "",
                    rx.el.p(subtitle, class_name="text-xs text-gray-400 mt-1"),
                ),
            ),
            class_name="flex items-center gap-4",
        ),
        class_name=(
            "bg-white rounded-2xl p-5 shadow-sm border border-gray-100 "
            "hover:shadow-md transition-shadow"
        ),
    )
