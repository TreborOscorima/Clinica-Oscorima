from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.odontograma import OdontogramaState


def _diente(p: dict) -> rx.Component:
    return rx.el.button(
        rx.el.span(p["numero"], class_name="text-xs font-bold leading-none"),
        rx.cond(
            p["nota"] != "",
            rx.el.span(class_name="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-white/80 ring-1 ring-gray-500"),
        ),
        on_click=lambda: OdontogramaState.abrir_pieza(p),
        style={"backgroundColor": p["color"], "color": p["text_color"]},
        title=p["estado_label"],
        class_name="relative w-9 h-11 rounded-md border border-gray-300 flex items-center justify-center hover:ring-2 hover:ring-sky-400 cursor-pointer transition shrink-0",
    )


def _arcada(piezas, etiqueta: str) -> rx.Component:
    return rx.el.div(
        rx.el.span(etiqueta, class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1"),
        rx.el.div(
            rx.foreach(piezas.to(list[dict]), _diente),
            class_name="flex gap-1 justify-center min-w-max",
        ),
        class_name="flex flex-col items-center",
    )


def _leyenda_item(e: dict) -> rx.Component:
    return rx.el.div(
        rx.el.span(style={"backgroundColor": e["color"]}, class_name="w-3 h-3 rounded-sm border border-gray-300 shrink-0"),
        rx.el.span(e["label"], class_name="text-xs text-gray-600"),
        class_name="flex items-center gap-1.5",
    )


def _resumen_chip(r: dict) -> rx.Component:
    return rx.el.div(
        rx.el.span(style={"backgroundColor": r["color"]}, class_name="w-2.5 h-2.5 rounded-full shrink-0"),
        rx.el.span(r["label"], class_name="text-xs font-medium text-gray-700"),
        rx.el.span(r["count"], class_name="text-xs font-bold text-gray-900 ml-0.5"),
        class_name="flex items-center gap-1.5 px-2.5 py-1 bg-white border border-gray-200 rounded-full",
    )


def _modal_pieza() -> rx.Component:
    return rx.cond(
        OdontogramaState.modal_abierto,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=OdontogramaState.cerrar_modal,
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("smile", size=18, class_name="text-sky-600 mr-2"),
                        rx.el.h2("Pieza ", OdontogramaState.sel_numero, class_name="text-lg font-semibold text-gray-900"),
                        class_name="flex items-center",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=OdontogramaState.cerrar_modal,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                # Estado
                rx.el.div(
                    rx.el.label("Estado", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.select(
                        rx.foreach(
                            OdontogramaState.estados_cat.to(list[dict]),
                            lambda e: rx.el.option(e["label"], value=e["clave"]),
                        ),
                        default_value=OdontogramaState.sel_estado,
                        on_change=OdontogramaState.set_sel_estado,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    class_name="mb-4",
                ),
                # Nota
                rx.el.div(
                    rx.el.label("Nota (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.input(
                        type="text",
                        placeholder="Ej: cara oclusal, control en 30 días…",
                        default_value=OdontogramaState.sel_nota,
                        on_change=OdontogramaState.set_sel_nota,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    class_name="mb-5",
                ),
                # Botones
                rx.el.div(
                    rx.el.button(
                        rx.icon("eraser", size=15, class_name="mr-1"),
                        "Volver a sano",
                        on_click=OdontogramaState.resetear_pieza,
                        class_name="flex items-center px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer mr-auto",
                    ),
                    rx.el.button(
                        "Cancelar",
                        on_click=OdontogramaState.cerrar_modal,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            OdontogramaState.is_saving,
                            rx.el.div(rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"), "Guardando…", class_name="flex items-center"),
                            "Guardar",
                        ),
                        on_click=OdontogramaState.guardar_pieza,
                        disabled=OdontogramaState.is_saving,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex items-center gap-3",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def odontograma_page() -> rx.Component:
    return shell(
        _modal_pieza(),
        page_header(
            "Odontograma",
            "Estado dental por pieza (numeración FDI)",
            action=rx.cond(
                OdontogramaState.paciente_id != 0,
                rx.el.a(
                    rx.icon("arrow-left", size=15, class_name="mr-1.5"),
                    rx.el.span("Volver a Historia Clínica"),
                    href=rx.cond(
                        OdontogramaState.paciente_id != 0,
                        "/historia-clinica?paciente_id=" + OdontogramaState.paciente_id.to_string(),
                        "/historia-clinica",
                    ),
                    class_name="inline-flex items-center px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                ),
                rx.fragment(),
            ),
        ),
        rx.cond(
            OdontogramaState.paciente_id == 0,
            rx.el.div(
                rx.icon("smile", size=48, class_name="text-gray-300 mb-4"),
                rx.el.p("No hay paciente seleccionado", class_name="text-gray-500 font-medium"),
                rx.el.p("Accedé al odontograma desde la Historia Clínica de un paciente", class_name="text-sm text-gray-400 mt-1"),
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
                    rx.el.span(OdontogramaState.paciente_nombre, class_name="text-sm font-medium text-gray-700"),
                    class_name="flex items-center mb-4 bg-gray-50 px-3 py-2 rounded-lg w-fit",
                ),
                # Resumen
                rx.cond(
                    OdontogramaState.resumen.length() > 0,
                    rx.el.div(
                        rx.foreach(OdontogramaState.resumen.to(list[dict]), _resumen_chip),
                        class_name="flex flex-wrap gap-2 mb-5",
                    ),
                    rx.el.p("Sin hallazgos cargados — todas las piezas figuran como sanas.", class_name="text-sm text-gray-400 italic mb-5"),
                ),
                # Arcadas
                rx.el.div(
                    rx.el.div(
                        _arcada(OdontogramaState.superior, "Superior"),
                        rx.el.div(class_name="h-px bg-gray-200 my-4 w-full"),
                        _arcada(OdontogramaState.inferior, "Inferior"),
                        class_name="inline-flex flex-col gap-1 min-w-max",
                    ),
                    class_name="overflow-x-auto p-4 bg-white border border-gray-100 rounded-xl shadow-sm",
                ),
                rx.el.p(
                    "Tocá una pieza para registrar su estado. El punto blanco indica que la pieza tiene una nota.",
                    class_name="text-xs text-gray-400 mt-3",
                ),
                # Leyenda
                rx.el.div(
                    rx.el.span("Referencias", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide w-full mb-1"),
                    rx.el.div(
                        rx.foreach(OdontogramaState.estados_cat.to(list[dict]), _leyenda_item),
                        class_name="flex flex-wrap gap-x-4 gap-y-2",
                    ),
                    class_name="mt-5 p-4 bg-gray-50 border border-gray-100 rounded-xl",
                ),
            ),
        ),
        on_mount=OdontogramaState.on_mount,
    )
