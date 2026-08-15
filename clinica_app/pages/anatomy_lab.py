"""Laboratorio del Motor Anatómico — Etapa E1 (validación del puente JS↔Reflex).

Página interna (permiso `historia`) que prueba el mecanismo completo en aislamiento:
render 3D (Three.js vendorizado) → click con raycast → puente → handler de Python →
repintado desde el estado. Sin datos clínicos ni BD. En E3 este mismo patrón se
aplica sobre el odontograma real.
"""
from __future__ import annotations

import reflex as rx

from clinica_app.components.anatomy_viewer import anatomy_viewer
from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.anatomy_lab import AnatomyLabState

_LEYENDA = [
    ("#dc2626", "Caries"),
    ("#f59e0b", "Observación"),
    ("#16a34a", "Sano"),
    ("#e5e7eb", "Sin estado"),
]


def _chip_leyenda(par) -> rx.Component:
    return rx.el.div(
        rx.el.span(style={"background_color": par[0]},
                   class_name="inline-block w-3 h-3 rounded-full border border-gray-300"),
        rx.el.span(par[1], class_name="text-xs text-gray-600"),
        class_name="flex items-center gap-1.5",
    )


def anatomy_lab_page() -> rx.Component:
    return shell(
        page_header(
            "Motor Anatómico · Lab E1",
            "Prototipo del puente 3D↔Reflex — arrastrá para rotar, rueda para zoom, click en una pieza.",
        ),
        rx.el.div(
            # Columna del visor
            rx.el.div(
                anatomy_viewer(AnatomyLabState.on_pick, height="460px"),
                rx.el.div(
                    rx.foreach(_LEYENDA, _chip_leyenda),
                    class_name="flex items-center gap-4 mt-3 flex-wrap",
                ),
                class_name="flex-1 min-w-0",
            ),
            # Panel lateral: selección + bitácora de eventos (prueba el ida y vuelta)
            rx.el.div(
                rx.el.div(
                    rx.el.p("Última selección", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wider"),
                    rx.el.p(
                        rx.cond(AnatomyLabState.picked_id != "", AnatomyLabState.picked_id, "—"),
                        class_name="text-2xl font-bold text-sky-600 mt-1",
                    ),
                    class_name="pb-4 mb-4 border-b border-gray-100",
                ),
                rx.el.p("Eventos (JS→Python→JS)", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2"),
                rx.cond(
                    AnatomyLabState.eventos,
                    rx.el.ul(
                        rx.foreach(
                            AnatomyLabState.eventos,
                            lambda e: rx.el.li(e, class_name="text-sm text-gray-700 py-1 border-b border-gray-50 last:border-0"),
                        ),
                    ),
                    rx.el.p("Hacé click en una pieza para registrar el primer evento.",
                            class_name="text-sm text-gray-400 italic"),
                ),
                class_name="w-72 bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex-shrink-0",
            ),
            class_name="flex gap-6 items-start flex-wrap",
        ),
        on_mount=AnatomyLabState.on_mount,
    )
