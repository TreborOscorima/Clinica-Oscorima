from __future__ import annotations

from typing import Any

import reflex as rx


def data_table(
    rows: list[dict] | rx.Var,
    columns: list[dict[str, Any]],
    on_prev: Any = None,
    on_next: Any = None,
    current_page: int | rx.Var = 1,
    total_pages:  int | rx.Var = 1,
    empty_msg: str = "Sin resultados",
) -> rx.Component:
    """
    Tabla genérica con paginación.
    columns: lista de {"label": str, "key": str, "render": Callable | None}
    """
    header_cells = [
        rx.el.th(
            col["label"],
            class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide",
        )
        for col in columns
    ]

    def build_row(row: dict) -> rx.Component:
        cells = []
        for col in columns:
            render_fn = col.get("render")
            if render_fn:
                cell_content = render_fn(row[col["key"]])
            else:
                cell_content = rx.el.span(row[col["key"]], class_name="text-sm text-gray-700")
            cells.append(
                rx.el.td(cell_content, class_name="px-4 py-3 whitespace-nowrap")
            )
        return rx.el.tr(*cells, class_name="border-t border-gray-100 hover:bg-gray-50 transition-colors")

    return rx.el.div(
        # Tabla
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(*header_cells, class_name="bg-gray-50"),
                    class_name="border-b border-gray-200",
                ),
                rx.el.tbody(
                    rx.foreach(rows, build_row),
                ),
                class_name="w-full border-collapse",
            ),
            class_name="overflow-x-auto",
        ),
        # Paginación
        rx.el.div(
            rx.el.button(
                rx.icon("chevron-left", size=16),
                "Anterior",
                on_click=on_prev,
                disabled=current_page <= 1,
                class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer",
            ),
            rx.el.span(
                f"Página {current_page} de {total_pages}",
                class_name="text-sm text-gray-500",
            ),
            rx.el.button(
                "Siguiente",
                rx.icon("chevron-right", size=16),
                on_click=on_next,
                disabled=current_page >= total_pages,
                class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer",
            ),
            class_name="flex items-center justify-between px-4 py-3 border-t border-gray-100",
        ),
        class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
    )
