from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.planes_tratamiento import PlanesTratamientoState as S


# ── Piezas de UI ──────────────────────────────────────────────────────────────

def _plan_chip(p: dict) -> rx.Component:
    activo = p["id"] == S.plan_actual_id
    return rx.el.button(
        rx.el.div(
            rx.el.span(p["titulo"], class_name="text-sm font-semibold truncate max-w-[12rem]"),
            rx.el.span(
                p["estado_label"],
                style={"backgroundColor": p["color"], "color": p["text_color"]},
                class_name="text-[10px] font-medium px-1.5 py-0.5 rounded-full ml-2 shrink-0",
            ),
            class_name="flex items-center justify-between w-full",
        ),
        rx.el.div(
            rx.el.span("$" + p["total"].to(str), class_name="text-xs text-gray-500"),
            rx.el.span(p["avance"].to_string() + "% avance", class_name="text-xs text-gray-400"),
            class_name="flex items-center justify-between w-full mt-1",
        ),
        on_click=lambda: S.seleccionar_plan(p["id"]),
        class_name=rx.cond(
            activo,
            "flex flex-col items-start p-3 rounded-xl border-2 border-sky-500 bg-sky-50 text-left w-full cursor-pointer transition",
            "flex flex-col items-start p-3 rounded-xl border border-gray-200 bg-white hover:border-sky-300 text-left w-full cursor-pointer transition",
        ),
    )


def _item_row(it: dict) -> rx.Component:
    return rx.el.div(
        # Pieza (badge FDI) + descripción
        rx.el.div(
            rx.cond(
                it["pieza_numero"] != "",
                rx.el.span(
                    it["pieza_numero"],
                    class_name="text-[11px] font-bold text-sky-700 bg-sky-100 rounded px-1.5 py-0.5 mr-2 shrink-0",
                ),
            ),
            rx.el.span(it["descripcion"], class_name="text-sm text-gray-800"),
            class_name="flex items-center min-w-0 flex-1",
        ),
        # Precio
        rx.el.span("$" + it["precio"].to(str), class_name="text-sm font-medium text-gray-700 w-24 text-right shrink-0"),
        # Estado (select inline)
        rx.el.select(
            rx.foreach(
                S.estados_item_cat.to(list[dict]),
                lambda e: rx.el.option(e["label"], value=e["clave"]),
            ),
            value=it["estado"],
            on_change=lambda v: S.cambiar_estado_item(it["id"], v),
            style={"backgroundColor": it["color"], "color": it["text_color"]},
            class_name="text-xs font-medium rounded-md px-2 py-1 border border-gray-300 cursor-pointer ml-3 shrink-0",
        ),
        # Eliminar
        rx.el.button(
            rx.icon("trash-2", size=15),
            on_click=lambda: S.eliminar_item(it["id"]),
            class_name="text-gray-300 hover:text-red-500 ml-2 cursor-pointer shrink-0",
        ),
        class_name="flex items-center py-2 px-3 border-b border-gray-100 last:border-0 hover:bg-gray-50",
    )


def _fase_block(f: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span("Fase " + f["fase"].to_string(), class_name="text-xs font-bold text-gray-500 uppercase tracking-wide"),
            rx.el.span("Subtotal $" + f["subtotal"].to(str), class_name="text-xs font-semibold text-gray-600"),
            class_name="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-100",
        ),
        rx.foreach(f["items"].to(list[dict]), _item_row),
        class_name="border border-gray-200 rounded-xl overflow-hidden mb-3",
    )


def _kpi(label: str, valor, color: str = "text-gray-900") -> rx.Component:
    return rx.el.div(
        rx.el.span(label, class_name="text-xs text-gray-400 uppercase tracking-wide"),
        rx.el.span(valor, class_name="text-lg font-bold " + color),
        class_name="flex flex-col",
    )


def _panel_plan() -> rx.Component:
    return rx.el.div(
        # Cabecera del plan
        rx.el.div(
            rx.el.div(
                rx.el.h2(S.pa_titulo, class_name="text-lg font-semibold text-gray-900"),
                rx.el.p(rx.cond(S.pa_notas != "", S.pa_notas, "Sin notas"), class_name="text-sm text-gray-400 mt-0.5"),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.select(
                    rx.foreach(
                        S.estados_plan_cat.to(list[dict]),
                        lambda e: rx.el.option(e["label"], value=e["clave"]),
                    ),
                    value=S.pa_estado,
                    on_change=S.cambiar_estado_plan,
                    class_name="text-sm rounded-lg px-3 py-2 border border-gray-300 cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("trash-2", size=16),
                    on_click=S.eliminar_plan,
                    title="Eliminar plan",
                    class_name="p-2 text-gray-400 hover:text-red-500 border border-gray-300 rounded-lg cursor-pointer",
                ),
                class_name="flex items-center gap-2 shrink-0",
            ),
            class_name="flex items-start justify-between gap-4 mb-4",
        ),
        # KPIs presupuesto + avance
        rx.el.div(
            _kpi("Presupuesto", "$" + S.pa_total),
            _kpi("Aprobado", "$" + S.pa_total_aprobado, "text-blue-600"),
            _kpi("Terminado", "$" + S.pa_total_terminado, "text-green-600"),
            _kpi("Tratamientos", S.pa_n_items, "text-gray-700"),
            class_name="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-white border border-gray-100 rounded-xl shadow-sm mb-4",
        ),
        # Barra de avance
        rx.el.div(
            rx.el.div(
                rx.el.span("Avance", class_name="text-xs font-medium text-gray-500"),
                rx.el.span(S.pa_avance.to_string() + "%", class_name="text-xs font-bold text-gray-700"),
                class_name="flex items-center justify-between mb-1",
            ),
            rx.el.div(
                rx.el.div(
                    style={"width": S.pa_avance.to_string() + "%"},
                    class_name="h-2 bg-green-500 rounded-full transition-all",
                ),
                class_name="w-full h-2 bg-gray-100 rounded-full overflow-hidden",
            ),
            class_name="mb-5",
        ),
        # Fases + tratamientos
        rx.el.div(
            rx.el.div(
                rx.el.h3("Tratamientos por fase", class_name="text-sm font-semibold text-gray-700"),
                rx.el.button(
                    rx.icon("plus", size=15, class_name="mr-1"),
                    "Agregar tratamiento",
                    on_click=S.abrir_modal_item,
                    class_name="flex items-center px-3 py-1.5 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
                class_name="flex items-center justify-between mb-3",
            ),
            rx.cond(
                S.fases.length() > 0,
                rx.foreach(S.fases.to(list[dict]), _fase_block),
                rx.el.p(
                    "Este plan aún no tiene tratamientos. Agregá el primero con el botón de arriba.",
                    class_name="text-sm text-gray-400 italic py-6 text-center border border-dashed border-gray-200 rounded-xl",
                ),
            ),
        ),
        class_name="flex-1 min-w-0",
    )


# ── Modales ───────────────────────────────────────────────────────────────────

def _modal_plan() -> rx.Component:
    return rx.cond(
        S.modal_plan,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=S.cerrar_modal_plan),
            rx.el.div(
                rx.el.h2("Nuevo plan de tratamiento", class_name="text-lg font-semibold text-gray-900 mb-4"),
                rx.el.label("Título", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.input(
                    placeholder="Ej: Rehabilitación integral superior",
                    default_value=S.np_titulo,
                    on_change=S.set_np_titulo,
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.label("Notas (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.textarea(
                    placeholder="Observaciones generales del plan…",
                    default_value=S.np_notas,
                    on_change=S.set_np_notas,
                    rows="3",
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-5 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=S.cerrar_modal_plan,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        rx.cond(S.is_saving, "Creando…", "Crear plan"),
                        on_click=S.guardar_plan,
                        disabled=S.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_item() -> rx.Component:
    return rx.cond(
        S.modal_item,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=S.cerrar_modal_item),
            rx.el.div(
                rx.el.h2("Agregar tratamiento", class_name="text-lg font-semibold text-gray-900 mb-4"),
                # Servicio del catálogo (opcional, hereda precio)
                rx.el.label("Servicio del catálogo (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.select(
                    rx.el.option("— Manual —", value="0"),
                    rx.foreach(
                        S.servicios.to(list[dict]),
                        lambda s: rx.el.option(s["nombre"].to(str) + "  ($" + s["precio"].to(str) + ")", value=s["id"]),
                    ),
                    value=S.ni_servicio_id,
                    on_change=S.set_ni_servicio,
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.label("Descripción", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.input(
                    placeholder="Ej: Endodoncia unirradicular",
                    value=S.ni_descripcion,
                    on_change=S.set_ni_descripcion,
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Fase", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            type="number", min="1", default_value=S.ni_fase, on_change=S.set_ni_fase,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    rx.el.div(
                        rx.el.label("Pieza FDI (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            placeholder="Ej: 16", default_value=S.ni_pieza, on_change=S.set_ni_pieza,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    rx.el.div(
                        rx.el.label("Precio", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            type="number", min="0", step="0.01",
                            placeholder="0.00", value=S.ni_precio, on_change=S.set_ni_precio,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    class_name="flex gap-3 mb-5",
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=S.cerrar_modal_item,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        rx.cond(S.is_saving, "Agregando…", "Agregar"),
                        on_click=S.guardar_item,
                        disabled=S.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


# ── Página ────────────────────────────────────────────────────────────────────

def planes_tratamiento_page() -> rx.Component:
    return shell(
        _modal_plan(),
        _modal_item(),
        page_header(
            "Plan de tratamiento",
            "Tratamientos propuestos por fases, presupuesto y seguimiento",
            action=rx.cond(
                S.paciente_id != 0,
                rx.el.a(
                    rx.icon("arrow-left", size=15, class_name="mr-1.5"),
                    rx.el.span("Volver a Historia Clínica"),
                    href="/historia-clinica?paciente_id=" + S.paciente_id.to_string(),
                    class_name="inline-flex items-center px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                ),
                rx.fragment(),
            ),
        ),
        rx.cond(
            S.paciente_id == 0,
            rx.el.div(
                rx.icon("clipboard-list", size=48, class_name="text-gray-300 mb-4"),
                rx.el.p("No hay paciente seleccionado", class_name="text-gray-500 font-medium"),
                rx.el.p("Accedé al plan de tratamiento desde la Historia Clínica de un paciente",
                        class_name="text-sm text-gray-400 mt-1"),
                rx.el.a(
                    rx.icon("users", size=14, class_name="mr-2"),
                    "Ir a Pacientes",
                    href="/pacientes",
                    class_name="flex items-center mt-4 px-4 py-2 bg-sky-600 text-white text-sm rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
                class_name="flex flex-col items-center justify-center py-20 text-center",
            ),
            rx.el.div(
                # Paciente
                rx.el.div(
                    rx.icon("user", size=15, class_name="text-gray-400 mr-1.5"),
                    rx.el.span(S.paciente_nombre, class_name="text-sm font-medium text-gray-700"),
                    class_name="flex items-center mb-4 bg-gray-50 px-3 py-2 rounded-lg w-fit",
                ),
                rx.el.div(
                    # Columna izquierda: lista de planes
                    rx.el.div(
                        rx.el.div(
                            rx.el.span("Planes", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.button(
                                rx.icon("plus", size=14, class_name="mr-1"),
                                "Nuevo",
                                on_click=S.abrir_modal_plan,
                                class_name="flex items-center px-2.5 py-1 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer",
                            ),
                            class_name="flex items-center justify-between mb-3",
                        ),
                        rx.cond(
                            S.planes.length() > 0,
                            rx.el.div(
                                rx.foreach(S.planes.to(list[dict]), _plan_chip),
                                class_name="flex flex-col gap-2",
                            ),
                            rx.el.p("Sin planes todavía.", class_name="text-sm text-gray-400 italic"),
                        ),
                        class_name="w-full lg:w-72 shrink-0",
                    ),
                    # Columna derecha: plan seleccionado
                    rx.cond(
                        S.plan_actual_id != 0,
                        _panel_plan(),
                        rx.el.div(
                            rx.icon("clipboard-list", size=40, class_name="text-gray-300 mb-3"),
                            rx.el.p("Seleccioná un plan o creá uno nuevo", class_name="text-sm text-gray-400"),
                            class_name="flex-1 flex flex-col items-center justify-center py-16 border border-dashed border-gray-200 rounded-xl",
                        ),
                    ),
                    class_name="flex flex-col lg:flex-row gap-6 items-start",
                ),
            ),
        ),
        on_mount=S.on_mount,
    )
