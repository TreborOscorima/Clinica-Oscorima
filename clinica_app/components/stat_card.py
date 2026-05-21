from __future__ import annotations

import reflex as rx


def stat_card(
    title: str | rx.Var,
    value: str | rx.Var,
    icon: str,
    color: str = "sky",
    subtitle: str | rx.Var = "",
) -> rx.Component:
    icon_bg   = f"bg-{color}-100"
    icon_text = f"text-{color}-600"
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(icon, size=20),
                class_name=f"p-2.5 rounded-lg {icon_bg} {icon_text}",
            ),
            rx.el.div(
                rx.el.p(title, class_name="text-xs font-medium text-gray-500 uppercase tracking-wide"),
                rx.el.p(value, class_name="text-2xl font-bold text-gray-900 mt-1"),
                rx.cond(
                    subtitle != "",
                    rx.el.p(subtitle, class_name="text-xs text-gray-400 mt-0.5"),
                ),
            ),
            class_name="flex items-start gap-4",
        ),
        class_name="bg-white rounded-xl p-5 shadow-sm border border-gray-100",
    )
