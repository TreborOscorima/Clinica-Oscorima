from __future__ import annotations

import reflex as rx


_BADGE_STYLES: dict[str, str] = {
    # Turnos
    "pendiente":  "bg-yellow-100 text-yellow-800",
    "confirmado": "bg-blue-100 text-blue-800",
    "atendido":   "bg-green-100 text-green-800",
    "cancelado":  "bg-red-100 text-red-800",
    # Caja
    "ingreso": "bg-green-100 text-green-800",
    "egreso":  "bg-red-100 text-red-800",
    # Stock
    "ok":      "bg-green-100 text-green-800",
    "minimo":  "bg-red-100 text-red-800",
    # Genérico
    "activo":   "bg-green-100 text-green-800",
    "inactivo": "bg-gray-100 text-gray-600",
}


def estado_badge(estado: str | rx.Var, label: str | rx.Var | None = None) -> rx.Component:
    """Badge de estado coloreado según el valor."""
    display = label if label is not None else estado
    return rx.el.span(
        display,
        class_name=rx.match(
            estado,
            ("pendiente",  "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800"),
            ("confirmado", "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800"),
            ("atendido",   "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800"),
            ("cancelado",  "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-800"),
            ("ingreso",    "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800"),
            ("egreso",     "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-800"),
            ("activo",     "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800"),
            ("parcial",    "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800"),
            ("saldado",    "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800"),
            "inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600",
        ),
    )
