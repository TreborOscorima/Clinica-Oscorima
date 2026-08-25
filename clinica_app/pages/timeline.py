from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import empty_state, page_header
from clinica_app.state.timeline import TimelineState

# color base por tipo, para el punto del riel y el ícono
_CIRCLE = "w-9 h-9 rounded-full flex items-center justify-center shrink-0 ring-4 ring-white "


def _dot(tipo: rx.Var) -> rx.Component:
    """Punto del riel: círculo de color + ícono, según el tipo del evento."""
    return rx.el.div(
        rx.match(
            tipo,
            ("turno",          rx.icon("calendar-clock", size=17, class_name="text-sky-600")),
            ("nota",           rx.icon("clipboard-list",  size=17, class_name="text-indigo-600")),
            ("receta",         rx.icon("pill",            size=17, class_name="text-violet-600")),
            ("consentimiento", rx.icon("signature",       size=17, class_name="text-teal-600")),
            ("adjunto",        rx.icon("paperclip",       size=17, class_name="text-slate-600")),
            ("odontograma",    rx.icon("smile",           size=17, class_name="text-cyan-600")),
            ("plan",           rx.icon("clipboard-check", size=17, class_name="text-amber-600")),
            ("sesion",         rx.icon("brush",           size=17, class_name="text-pink-600")),
            ("evaluacion",     rx.icon("scan-face",       size=17, class_name="text-fuchsia-600")),
            ("cobro",          rx.icon("credit-card",     size=17, class_name="text-emerald-600")),
            rx.icon("dot", size=17, class_name="text-gray-500"),
        ),
        class_name=rx.match(
            tipo,
            ("turno",          _CIRCLE + "bg-sky-100"),
            ("nota",           _CIRCLE + "bg-indigo-100"),
            ("receta",         _CIRCLE + "bg-violet-100"),
            ("consentimiento", _CIRCLE + "bg-teal-100"),
            ("adjunto",        _CIRCLE + "bg-slate-100"),
            ("odontograma",    _CIRCLE + "bg-cyan-100"),
            ("plan",           _CIRCLE + "bg-amber-100"),
            ("sesion",         _CIRCLE + "bg-pink-100"),
            ("evaluacion",     _CIRCLE + "bg-fuchsia-100"),
            ("cobro",          _CIRCLE + "bg-emerald-100"),
            _CIRCLE + "bg-gray-100",
        ),
    )


_BADGE_BASE = "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize "


def _estado_badge(estado: rx.Var) -> rx.Component:
    """Chip de estado del evento: verde/rojo/ámbar en los casos con semántica,
    neutro para el resto. Se oculta si el estado viene vacío."""
    return rx.cond(
        estado != "",
        rx.el.span(
            estado,
            class_name=rx.match(
                estado,
                ("atendido",   _BADGE_BASE + "bg-green-100 text-green-700"),
                ("confirmado", _BADGE_BASE + "bg-sky-100 text-sky-700"),
                ("firmada",    _BADGE_BASE + "bg-green-100 text-green-700"),
                ("cancelado",  _BADGE_BASE + "bg-red-100 text-red-600"),
                ("anulado",    _BADGE_BASE + "bg-red-100 text-red-600"),
                ("pendiente",  _BADGE_BASE + "bg-amber-100 text-amber-700"),
                _BADGE_BASE + "bg-gray-100 text-gray-500",
            ),
        ),
        rx.fragment(),
    )


def _evento(e: rx.Var) -> rx.Component:
    return rx.el.div(
        # Riel: punto + línea vertical
        rx.el.div(
            _dot(e["tipo"]),
            class_name="relative flex flex-col items-center",
        ),
        # Tarjeta del evento
        rx.el.a(
            rx.el.div(
                rx.el.div(
                    rx.el.span(e["titulo"], class_name="text-sm font-semibold text-gray-900"),
                    _estado_badge(e["estado"]),
                    class_name="flex items-center gap-2 flex-wrap",
                ),
                rx.el.span(e["fecha"], class_name="text-xs text-gray-400 shrink-0 whitespace-nowrap"),
                class_name="flex items-start justify-between gap-3",
            ),
            rx.cond(
                e["detalle"] != "",
                rx.el.p(e["detalle"], class_name="text-sm text-gray-600 mt-1 leading-snug"),
                rx.fragment(),
            ),
            href=e["href"],
            class_name=(
                "block flex-1 bg-white border border-gray-200 rounded-xl px-4 py-3 "
                "hover:border-sky-300 hover:shadow-sm transition cursor-pointer"
            ),
        ),
        class_name="flex gap-4 relative pb-5 timeline-row",
    )


def _filtro_chip(t: rx.Var) -> rx.Component:
    """Chip de filtro por tipo, con su conteo. Se atenúa si no hay eventos."""
    n = t["conteo"].to(int)
    activo = TimelineState.filtro == t["key"]
    return rx.cond(
        n > 0,
        rx.el.button(
            rx.el.span(t["label"]),
            rx.el.span(
                n,
                class_name=rx.cond(
                    activo,
                    "ml-1.5 px-1.5 rounded-full bg-white/25 text-xs",
                    "ml-1.5 px-1.5 rounded-full bg-gray-100 text-gray-500 text-xs",
                ),
            ),
            on_click=TimelineState.set_filtro(t["key"]),
            class_name=rx.cond(
                activo,
                "inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-sky-600 text-white cursor-pointer",
                "inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-white border border-gray-200 text-gray-600 hover:border-gray-300 cursor-pointer",
            ),
        ),
        rx.fragment(),
    )


def _selector_paciente() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("search", size=16, class_name="text-gray-400"),
            rx.el.input(
                placeholder="Buscar paciente por nombre o documento…",
                value=TimelineState.pac_busqueda,
                on_change=TimelineState.set_pac_busqueda,
                class_name="flex-1 bg-transparent text-sm focus:outline-none",
            ),
            class_name="flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-lg",
        ),
        rx.cond(
            TimelineState.pac_resultados.length() > 0,
            rx.el.div(
                rx.foreach(
                    TimelineState.pac_resultados,
                    lambda p: rx.el.button(
                        rx.el.span(p["nombre"], class_name="text-sm text-gray-800"),
                        rx.el.span(p["documento"], class_name="text-xs text-gray-400"),
                        on_click=TimelineState.seleccionar_paciente(p["id"], p["nombre"]),
                        class_name="flex items-center justify-between w-full px-3 py-2 hover:bg-sky-50 text-left cursor-pointer border-b border-gray-50 last:border-0",
                    ),
                ),
                class_name="mt-1 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden max-w-xl",
            ),
            rx.fragment(),
        ),
        class_name="mb-6 max-w-xl",
    )


def _cuerpo() -> rx.Component:
    return rx.cond(
        TimelineState.paciente_id != 0,
        rx.el.div(
            # Filtros por tipo
            rx.el.div(
                rx.foreach(TimelineState.tipos_cat, _filtro_chip),
                class_name="flex items-center gap-2 flex-wrap mb-6",
            ),
            # Línea de tiempo
            rx.cond(
                TimelineState.hay_eventos,
                rx.el.div(
                    rx.foreach(TimelineState.eventos_filtrados, _evento),
                    class_name="relative",
                ),
                empty_state(
                    "history",
                    "Sin eventos",
                    "Este paciente todavía no tiene registros en la historia clínica",
                ),
            ),
        ),
        empty_state(
            "users",
            "Elegí un paciente",
            "Buscá arriba para ver toda su historia clínica en una sola línea de tiempo",
        ),
    )


def timeline_page() -> rx.Component:
    return shell(
        # La línea vertical del riel se dibuja con un pseudo-borde por fila.
        rx.el.style(
            ".timeline-row::before{content:'';position:absolute;left:1.125rem;top:2.25rem;"
            "bottom:0;width:2px;background:#e5e7eb;}"
            ".timeline-row:last-child::before{display:none;}"
        ),
        page_header(
            "Línea de tiempo",
            rx.cond(
                TimelineState.paciente_nombre != "",
                TimelineState.paciente_nombre,
                "Historia clínica unificada del paciente",
            ),
        ),
        _selector_paciente(),
        _cuerpo(),
        title="Línea de tiempo",
        on_mount=TimelineState.on_mount,
    )
