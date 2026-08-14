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


def _diente_ro(p: dict) -> rx.Component:
    """Diente en modo solo lectura (visor de versión histórica)."""
    return rx.el.div(
        rx.el.span(p["numero"], class_name="text-xs font-bold leading-none"),
        rx.cond(
            p["nota"] != "",
            rx.el.span(class_name="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-white/80 ring-1 ring-gray-500"),
        ),
        style={"backgroundColor": p["color"], "color": p["text_color"]},
        title=p["estado_label"],
        class_name="relative w-9 h-11 rounded-md border border-gray-300 flex items-center justify-center shrink-0",
    )


def _arcada_ro(piezas, etiqueta: str) -> rx.Component:
    return rx.el.div(
        rx.el.span(etiqueta, class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1"),
        rx.el.div(
            rx.foreach(piezas.to(list[dict]), _diente_ro),
            class_name="flex gap-1 justify-center min-w-max",
        ),
        class_name="flex flex-col items-center",
    )


def _diente_cmp(p: dict) -> rx.Component:
    """Diente de comparación (solo lectura); anilla ámbar si la pieza cambió."""
    return rx.el.div(
        rx.el.span(p["numero"], class_name="text-xs font-bold leading-none"),
        rx.cond(
            p["cambio"],
            rx.el.span(class_name="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-amber-400 ring-2 ring-white"),
        ),
        style={"backgroundColor": p["color"], "color": p["text_color"]},
        title=p["estado_label"],
        class_name=rx.cond(
            p["cambio"],
            "relative w-9 h-11 rounded-md border-2 border-amber-400 flex items-center justify-center shrink-0",
            "relative w-9 h-11 rounded-md border border-gray-300 flex items-center justify-center shrink-0",
        ),
    )


def _arcada_cmp(piezas, etiqueta: str) -> rx.Component:
    return rx.el.div(
        rx.el.span(etiqueta, class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1"),
        rx.el.div(
            rx.foreach(piezas.to(list[dict]), _diente_cmp),
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


def _version_row(v: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("clock", size=13, class_name="text-gray-400 mr-1.5 shrink-0"),
            rx.el.span(v["fecha"], class_name="text-xs text-gray-500 shrink-0"),
            rx.el.span(v["titulo"], class_name="text-sm font-medium text-gray-800 ml-3 truncate"),
            rx.el.span(
                v["con_datos"], " ",
                rx.cond(v["con_datos"] == 1, "hallazgo", "hallazgos"),
                class_name="text-xs text-gray-400 ml-auto shrink-0",
            ),
            class_name="flex items-center min-w-0",
        ),
        rx.cond(
            v["nota"] != "",
            rx.el.p(v["nota"], class_name="text-xs text-gray-500 mt-1 italic truncate"),
        ),
        rx.el.div(
            rx.foreach(v["resumen"].to(list[dict]), _resumen_chip),
            class_name="flex flex-wrap gap-1.5 mt-2",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("eye", size=14, class_name="mr-1"),
                "Ver",
                on_click=lambda: OdontogramaState.ver_version(v["id"]),
                class_name="inline-flex items-center px-2.5 py-1 text-xs text-sky-700 border border-sky-200 rounded-lg hover:bg-sky-50 cursor-pointer",
            ),
            rx.el.a(
                rx.icon("file-down", size=14, class_name="mr-1"),
                "PDF",
                href=f"/api/odontograma/pdf?paciente_id={OdontogramaState.paciente_id}&clinica_id={OdontogramaState.clinica_id}&sede_id={OdontogramaState.sede_actual_id}&version_id={v['id']}&token={OdontogramaState.download_token}",
                target="_blank",
                class_name="inline-flex items-center px-2.5 py-1 text-xs text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
            ),
            rx.cond(
                OdontogramaState.puede_versionar,
                rx.el.button(
                    rx.icon("trash-2", size=14),
                    on_click=lambda: OdontogramaState.eliminar_version(v["id"]),
                    title="Eliminar versión",
                    class_name="inline-flex items-center px-2 py-1 text-xs text-gray-400 border border-gray-200 rounded-lg hover:bg-red-50 hover:text-red-600 cursor-pointer",
                ),
                rx.fragment(),
            ),
            class_name="flex items-center gap-2 mt-3",
        ),
        class_name="p-3 bg-white border border-gray-200 rounded-xl",
    )


def _panel_historial() -> rx.Component:
    return rx.cond(
        OdontogramaState.mostrar_historial,
        rx.el.div(
            rx.el.div(
                rx.icon("history", size=15, class_name="text-gray-500 mr-2"),
                rx.el.span("Historial de versiones", class_name="text-sm font-semibold text-gray-700"),
                class_name="flex items-center mb-3",
            ),
            rx.cond(
                OdontogramaState.versiones.length() > 0,
                rx.el.div(
                    rx.foreach(OdontogramaState.versiones.to(list[dict]), _version_row),
                    class_name="flex flex-col gap-2",
                ),
                rx.el.p(
                    "Todavía no guardaste versiones. Guardá una para registrar la evolución dental en el tiempo.",
                    class_name="text-sm text-gray-400 italic",
                ),
            ),
            class_name="mt-5 p-4 bg-gray-50 border border-gray-100 rounded-xl",
        ),
    )


def _modal_crear_version() -> rx.Component:
    return rx.cond(
        OdontogramaState.modal_version,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=OdontogramaState.cerrar_modal_version,
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("camera", size=18, class_name="text-sky-600 mr-2"),
                        rx.el.h2("Guardar versión del odontograma", class_name="text-lg font-semibold text-gray-900"),
                        class_name="flex items-center",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=OdontogramaState.cerrar_modal_version,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                rx.el.p(
                    "Se congelará el estado actual de todas las piezas como una versión histórica. El odontograma vivo se sigue editando normalmente.",
                    class_name="text-sm text-gray-500 mb-4",
                ),
                rx.el.div(
                    rx.el.label("Título", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.input(
                        type="text",
                        placeholder="Ej: Estado inicial, Post-tratamiento…",
                        value=OdontogramaState.ver_titulo,
                        on_change=OdontogramaState.set_ver_titulo,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    rx.el.p("Si lo dejás vacío, se usa la fecha y hora.", class_name="text-xs text-gray-400 mt-1"),
                    class_name="mb-4",
                ),
                rx.el.div(
                    rx.el.label("Nota (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.input(
                        type="text",
                        placeholder="Contexto de la versión…",
                        value=OdontogramaState.ver_nota,
                        on_change=OdontogramaState.set_ver_nota,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    class_name="mb-5",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=OdontogramaState.cerrar_modal_version,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            OdontogramaState.is_versionando,
                            rx.el.div(rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"), "Guardando…", class_name="flex items-center"),
                            rx.el.div(rx.icon("camera", size=16, class_name="mr-1.5"), "Guardar versión", class_name="flex items-center"),
                        ),
                        on_click=OdontogramaState.crear_version,
                        disabled=OdontogramaState.is_versionando,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex items-center justify-end gap-3",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_ver_version() -> rx.Component:
    return rx.cond(
        OdontogramaState.viendo_version,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=OdontogramaState.cerrar_version,
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("history", size=18, class_name="text-sky-600 mr-2"),
                        rx.el.div(
                            rx.el.h2(OdontogramaState.v_titulo, class_name="text-lg font-semibold text-gray-900 leading-tight"),
                            rx.el.span(OdontogramaState.v_fecha, class_name="text-xs text-gray-400"),
                            class_name="flex flex-col",
                        ),
                        class_name="flex items-center",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=OdontogramaState.cerrar_version,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-4 border-b border-gray-100",
                ),
                rx.el.div(
                    rx.icon("eye", size=13, class_name="text-amber-500 mr-1.5"),
                    rx.el.span("Solo lectura — es una versión histórica.", class_name="text-xs text-amber-700"),
                    class_name="flex items-center px-3 py-1.5 bg-amber-50 border border-amber-100 rounded-lg mb-4 w-fit",
                ),
                rx.cond(
                    OdontogramaState.v_nota != "",
                    rx.el.p(OdontogramaState.v_nota, class_name="text-sm text-gray-500 italic mb-3"),
                ),
                rx.cond(
                    OdontogramaState.v_resumen.length() > 0,
                    rx.el.div(
                        rx.foreach(OdontogramaState.v_resumen.to(list[dict]), _resumen_chip),
                        class_name="flex flex-wrap gap-2 mb-4",
                    ),
                    rx.el.p("Sin hallazgos — todas las piezas figuraban como sanas.", class_name="text-sm text-gray-400 italic mb-4"),
                ),
                rx.el.div(
                    rx.el.div(
                        _arcada_ro(OdontogramaState.v_superior, "Superior"),
                        rx.el.div(class_name="h-px bg-gray-200 my-4 w-full"),
                        _arcada_ro(OdontogramaState.v_inferior, "Inferior"),
                        class_name="inline-flex flex-col gap-1 min-w-max",
                    ),
                    class_name="overflow-x-auto p-4 bg-white border border-gray-100 rounded-xl",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cerrar",
                        on_click=OdontogramaState.cerrar_version,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    class_name="flex justify-end mt-5",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-3xl mx-4 z-50 max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _bloque_arcada_cmp(titulo, fecha, sup, inf) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(titulo, class_name="text-sm font-semibold text-gray-800"),
            rx.cond(
                fecha != "",
                rx.el.span(fecha, class_name="text-xs text-gray-400 ml-2"),
            ),
            class_name="flex items-baseline mb-2",
        ),
        rx.el.div(
            rx.el.div(
                _arcada_cmp(sup, "Superior"),
                rx.el.div(class_name="h-px bg-gray-200 my-3 w-full"),
                _arcada_cmp(inf, "Inferior"),
                class_name="inline-flex flex-col gap-1 min-w-max",
            ),
            class_name="overflow-x-auto p-3 bg-white border border-gray-100 rounded-xl",
        ),
        class_name="mb-4",
    )


def _cambio_row(c: dict) -> rx.Component:
    return rx.el.div(
        rx.el.span("Pieza ", c["numero"], class_name="text-sm font-semibold text-gray-800 w-20 shrink-0"),
        rx.el.span(
            rx.el.span(style={"backgroundColor": c["a_color"]}, class_name="inline-block w-2.5 h-2.5 rounded-full mr-1.5 align-middle"),
            c["a_label"],
            class_name="text-xs text-gray-600",
        ),
        rx.icon("arrow-right", size=14, class_name="text-gray-400 mx-2 shrink-0"),
        rx.el.span(
            rx.el.span(style={"backgroundColor": c["b_color"]}, class_name="inline-block w-2.5 h-2.5 rounded-full mr-1.5 align-middle"),
            c["b_label"],
            class_name="text-xs font-medium text-gray-800",
        ),
        class_name="flex items-center py-1.5 border-b border-gray-100 last:border-0",
    )


def _select_cmp(valor, on_change) -> rx.Component:
    return rx.el.select(
        rx.foreach(
            OdontogramaState.cmp_opciones.to(list[dict]),
            lambda o: rx.el.option(o["label"], value=o["value"]),
        ),
        value=valor.to_string(),
        on_change=on_change,
        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white",
    )


def _modal_comparar() -> rx.Component:
    return rx.cond(
        OdontogramaState.cmp_abierto,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=OdontogramaState.cerrar_comparar,
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("git-compare-arrows", size=18, class_name="text-sky-600 mr-2"),
                        rx.el.h2("Comparar versiones", class_name="text-lg font-semibold text-gray-900"),
                        class_name="flex items-center",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=OdontogramaState.cerrar_comparar,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-4 border-b border-gray-100",
                ),
                # Selectores A / B
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Versión A", class_name="block text-xs font-medium text-gray-500 mb-1"),
                        _select_cmp(OdontogramaState.cmp_a_id, OdontogramaState.set_cmp_a),
                        class_name="flex-1",
                    ),
                    rx.icon("arrow-right", size=18, class_name="text-gray-300 mt-5 shrink-0"),
                    rx.el.div(
                        rx.el.label("Versión B", class_name="block text-xs font-medium text-gray-500 mb-1"),
                        _select_cmp(OdontogramaState.cmp_b_id, OdontogramaState.set_cmp_b),
                        class_name="flex-1",
                    ),
                    class_name="flex items-start gap-3 mb-4",
                ),
                # Resumen de cambios
                rx.cond(
                    OdontogramaState.cmp_n > 0,
                    rx.el.div(
                        rx.icon("triangle-alert", size=14, class_name="text-amber-500 mr-1.5"),
                        rx.el.span(OdontogramaState.cmp_n, class_name="text-sm font-bold text-gray-900 mr-1"),
                        rx.el.span(
                            rx.cond(OdontogramaState.cmp_n == 1, "pieza con cambios", "piezas con cambios"),
                            class_name="text-sm text-gray-600",
                        ),
                        class_name="flex items-center px-3 py-1.5 bg-amber-50 border border-amber-100 rounded-lg mb-4 w-fit",
                    ),
                    rx.el.div(
                        rx.icon("check", size=14, class_name="text-green-500 mr-1.5"),
                        rx.el.span("Sin diferencias entre A y B.", class_name="text-sm text-gray-600"),
                        class_name="flex items-center px-3 py-1.5 bg-green-50 border border-green-100 rounded-lg mb-4 w-fit",
                    ),
                ),
                # Arcadas A y B
                _bloque_arcada_cmp(
                    OdontogramaState.cmp_titulo_a, OdontogramaState.cmp_fecha_a,
                    OdontogramaState.cmp_sup_a, OdontogramaState.cmp_inf_a,
                ),
                _bloque_arcada_cmp(
                    OdontogramaState.cmp_titulo_b, OdontogramaState.cmp_fecha_b,
                    OdontogramaState.cmp_sup_b, OdontogramaState.cmp_inf_b,
                ),
                # Detalle de cambios
                rx.cond(
                    OdontogramaState.cmp_cambios.length() > 0,
                    rx.el.div(
                        rx.el.span("Detalle de cambios (A → B)", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                        rx.el.div(
                            rx.foreach(OdontogramaState.cmp_cambios.to(list[dict]), _cambio_row),
                            class_name="mt-2",
                        ),
                        class_name="mt-2 p-3 bg-gray-50 border border-gray-100 rounded-xl",
                    ),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cerrar",
                        on_click=OdontogramaState.cerrar_comparar,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    class_name="flex justify-end mt-5",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-4xl mx-4 z-50 max-h-[90vh] overflow-y-auto",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def odontograma_page() -> rx.Component:
    return shell(
        _modal_pieza(),
        _modal_crear_version(),
        _modal_ver_version(),
        _modal_comparar(),
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
                # Paciente + acciones
                rx.el.div(
                    rx.el.div(
                        rx.icon("user", size=15, class_name="text-gray-400 mr-1.5"),
                        rx.el.span(OdontogramaState.paciente_nombre, class_name="text-sm font-medium text-gray-700"),
                        class_name="flex items-center bg-gray-50 px-3 py-2 rounded-lg w-fit",
                    ),
                    rx.el.div(
                        rx.el.a(
                            rx.icon("file-down", size=15, class_name="mr-1.5"),
                            "Exportar PDF",
                            href=f"/api/odontograma/pdf?paciente_id={OdontogramaState.paciente_id}&clinica_id={OdontogramaState.clinica_id}&sede_id={OdontogramaState.sede_actual_id}&token={OdontogramaState.download_token}",
                            target="_blank",
                            class_name="inline-flex items-center px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                        ),
                        rx.cond(
                            OdontogramaState.puede_versionar,
                            rx.el.button(
                                rx.icon("camera", size=15, class_name="mr-1.5"),
                                "Guardar versión",
                                on_click=OdontogramaState.abrir_modal_version,
                                class_name="inline-flex items-center px-3 py-2 text-sm text-sky-700 border border-sky-200 rounded-lg hover:bg-sky-50 cursor-pointer",
                            ),
                            rx.fragment(),
                        ),
                        rx.el.button(
                            rx.icon("history", size=15, class_name="mr-1.5"),
                            "Historial",
                            rx.cond(
                                OdontogramaState.versiones.length() > 0,
                                rx.el.span(
                                    OdontogramaState.versiones.length(),
                                    class_name="ml-1.5 px-1.5 py-0.5 text-xs font-bold bg-gray-100 text-gray-600 rounded-full",
                                ),
                                rx.fragment(),
                            ),
                            on_click=OdontogramaState.toggle_historial,
                            class_name="inline-flex items-center px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                        ),
                        rx.cond(
                            OdontogramaState.puede_comparar,
                            rx.el.button(
                                rx.icon("git-compare-arrows", size=15, class_name="mr-1.5"),
                                "Comparar",
                                on_click=OdontogramaState.abrir_comparar,
                                class_name="inline-flex items-center px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                            ),
                            rx.fragment(),
                        ),
                        class_name="flex items-center gap-2",
                    ),
                    class_name="flex items-center justify-between flex-wrap gap-3 mb-4",
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
                # Historial de versiones
                _panel_historial(),
            ),
        ),
        on_mount=OdontogramaState.on_mount,
    )
