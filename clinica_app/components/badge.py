from __future__ import annotations

import reflex as rx


def estado_badge(estado: str | rx.Var, label: str | rx.Var | None = None) -> rx.Component:
    """Badge de estado con estilo pill refinado."""
    display = label if label is not None else estado
    return rx.el.span(
        display,
        class_name=rx.match(
            estado,
            ("pendiente",  "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-amber-50 text-amber-800 border border-amber-200"),
            ("confirmado", "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-200"),
            ("atendido",   "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200"),
            ("cancelado",  "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-red-50 text-red-700 border border-red-200"),
            ("ingreso",    "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200"),
            ("egreso",     "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-red-50 text-red-700 border border-red-200"),
            ("activo",     "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200"),
            ("vigente",    "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200"),
            ("inactivo",   "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-gray-100 text-gray-500 border border-gray-200"),
            ("parcial",    "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-200"),
            ("saldado",    "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200"),
            "inline-flex items-center px-2.5 py-0.5 text-xs font-semibold rounded-full bg-gray-100 text-gray-600 border border-gray-200",
        ),
    )
