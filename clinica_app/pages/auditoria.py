from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import empty_state, page_header, table_header
from clinica_app.state.auditoria import AuditoriaState

_ACCIONES = [
    ("", "Todas las acciones"),
    ("crear", "Crear"),
    ("anular", "Anular"),
    ("cerrar_caja", "Cerrar caja"),
    ("eliminar", "Eliminar"),
    ("cambiar_permisos", "Cambiar permisos"),
]

_ENTIDADES = [
    ("", "Todas las entidades"),
    ("comprobante", "Comprobante"),
    ("compra", "Compra"),
    ("cierre_caja", "Cierre de caja"),
    ("caja_movimiento", "Movimiento de caja"),
    ("permiso_rol", "Permiso de rol"),
]


def _accion_badge(accion: rx.Var) -> rx.Component:
    _b = "inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ring-1 ring-inset "
    cls = rx.match(
        accion,
        ("crear", _b + "bg-green-50 text-green-700 ring-green-200"),
        ("anular", _b + "bg-rose-50 text-rose-700 ring-rose-200"),
        ("eliminar", _b + "bg-rose-50 text-rose-700 ring-rose-200"),
        ("cerrar_caja", _b + "bg-sky-50 text-sky-700 ring-sky-200"),
        ("cambiar_permisos", _b + "bg-violet-50 text-violet-700 ring-violet-200"),
        _b + "bg-gray-50 text-gray-600 ring-gray-200",
    )
    return rx.el.span(accion, class_name=cls)


def _row(r: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(r["fecha"], class_name="px-4 py-3 text-sm text-gray-500 whitespace-nowrap font-mono"),
        rx.el.td(r["usuario"], class_name="px-4 py-3 text-sm text-gray-800 whitespace-nowrap"),
        rx.el.td(_accion_badge(r["accion"]), class_name="px-4 py-3"),
        rx.el.td(r["entidad"], class_name="px-4 py-3 text-sm text-gray-600 whitespace-nowrap"),
        rx.el.td(
            rx.cond(r["entidad_id"] != 0, "#" + r["entidad_id"].to(str), "—"),
            class_name="px-4 py-3 text-sm text-gray-500 whitespace-nowrap",
        ),
        rx.el.td(
            rx.el.span(r["detalle"], class_name="text-xs text-gray-500 font-mono break-all"),
            class_name="px-4 py-3 max-w-md",
        ),
        class_name="border-b border-gray-100 hover:bg-gray-50",
    )


def _select(value: rx.Var, on_change, opciones: list) -> rx.Component:
    return rx.el.select(
        *[rx.el.option(label, value=val) for val, label in opciones],
        value=value,
        on_change=on_change,
        class_name=(
            "px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white "
            "focus:outline-none focus:ring-2 focus:ring-sky-500 cursor-pointer"
        ),
    )


def _filtros() -> rx.Component:
    return rx.el.div(
        _select(AuditoriaState.filtro_accion, AuditoriaState.set_filtro_accion, _ACCIONES),
        _select(AuditoriaState.filtro_entidad, AuditoriaState.set_filtro_entidad, _ENTIDADES),
        rx.el.button(
            rx.icon("x", size=15),
            rx.el.span("Limpiar", class_name="ml-1.5"),
            on_click=AuditoriaState.limpiar_filtros,
            class_name=(
                "inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 "
                "border border-gray-300 bg-white hover:bg-gray-50 rounded-lg cursor-pointer transition-colors"
            ),
        ),
        rx.el.span(
            AuditoriaState.total.to(str) + " registro(s)",
            class_name="ml-auto text-sm text-gray-400 self-center",
        ),
        class_name="flex flex-wrap items-center gap-3 mb-4",
    )


def _paginacion() -> rx.Component:
    return rx.el.div(
        rx.el.button(
            rx.icon("chevron-left", size=16),
            on_click=AuditoriaState.prev_page,
            disabled=AuditoriaState.page <= 1,
            class_name="p-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer",
        ),
        rx.el.span(
            "Página " + AuditoriaState.page.to(str) + " de " + AuditoriaState.total_pages.to(str),
            class_name="text-sm text-gray-500",
        ),
        rx.el.button(
            rx.icon("chevron-right", size=16),
            on_click=AuditoriaState.next_page,
            disabled=AuditoriaState.page >= AuditoriaState.total_pages,
            class_name="p-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer",
        ),
        class_name="flex items-center justify-center gap-4 mt-4",
    )


def auditoria_page() -> rx.Component:
    return shell(
        page_header("Auditoría", "Bitácora de acciones sensibles (solo lectura)"),
        _filtros(),
        rx.cond(
            AuditoriaState.registros.length() > 0,
            rx.el.div(
                rx.el.div(
                    rx.el.table(
                        table_header("Fecha", "Usuario", "Acción", "Entidad", "ID", "Detalle"),
                        rx.el.tbody(rx.foreach(AuditoriaState.registros, _row)),
                        class_name="w-full",
                    ),
                    class_name="overflow-x-auto bg-white rounded-xl border border-gray-100 shadow-sm",
                ),
                _paginacion(),
            ),
            empty_state("shield", "Sin registros de auditoría", "Aún no hay acciones registradas para los filtros actuales."),
        ),
        on_mount=AuditoriaState.on_mount,
    )
