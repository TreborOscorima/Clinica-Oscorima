from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import empty_state, page_header
from clinica_app.state.mapa_estetico import MapaEsteticoState
from clinica_app.state.mapa_estetico import _FOTO_UPLOAD_ID


def _foto_src(f: dict):
    return (
        "/api/adjunto?id=" + f["id"].to_string()
        + "&clinica_id=" + MapaEsteticoState.clinica_id.to_string()
        + "&token=" + MapaEsteticoState.download_token
    )


def _select(label, value, options, on_change) -> rx.Component:
    return rx.el.label(
        rx.el.span(label, class_name="block text-xs font-medium text-gray-600 mb-1"),
        rx.el.select(
            rx.foreach(
                options,
                lambda o: rx.el.option(o["label"], value=o["value"]),
            ),
            value=value,
            on_change=on_change,
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white",
        ),
        class_name="block",
    )


def _text_input(label, value, on_change, placeholder="") -> rx.Component:
    return rx.el.label(
        rx.el.span(label, class_name="block text-xs font-medium text-gray-600 mb-1"),
        rx.el.input(
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
        ),
        class_name="block",
    )


# ── Panel de la zona seleccionada ─────────────────────────────────────────────

def _punto_row(p) -> rx.Component:
    return rx.el.div(
        rx.icon("map-pin", size=13, class_name="text-sky-600 mt-0.5 shrink-0"),
        rx.el.div(
            rx.el.p(
                rx.el.span(p["cantidad"], class_name="font-medium"),
                rx.el.span(" " + p["unidad"].to(str), class_name="text-gray-500"),
                rx.cond(
                    p["lote"].to(str) != "",
                    rx.el.span(" · lote " + p["lote"].to(str), class_name="text-gray-500"),
                    rx.fragment(),
                ),
                class_name="text-xs text-gray-700",
            ),
            rx.cond(
                p["observacion"] != "",
                rx.el.p(p["observacion"], class_name="text-xs text-gray-400"),
                rx.fragment(),
            ),
            class_name="flex-1",
        ),
        rx.cond(
            MapaEsteticoState.puede_editar,
            rx.el.button(
                rx.icon("x", size=13),
                on_click=lambda: MapaEsteticoState.eliminar_punto(p["id"]),
                class_name="text-gray-300 hover:text-red-500 cursor-pointer",
            ),
            rx.fragment(),
        ),
        class_name="flex items-start gap-2 py-1.5 px-2 bg-gray-50 rounded-lg",
    )


def _proc_card(pr) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("syringe", size=14, class_name="text-sky-600 mr-1.5"),
                rx.el.span(pr["tipo_label"], class_name="text-sm font-semibold text-gray-800"),
                class_name="inline-flex items-center",
            ),
            rx.cond(
                MapaEsteticoState.puede_editar,
                rx.el.div(
                    rx.el.button(
                        rx.icon("plus", size=13, class_name="mr-1"),
                        "Punto",
                        on_click=lambda: MapaEsteticoState.abrir_punto(pr["id"]),
                        class_name="inline-flex items-center px-2 py-1 text-xs text-sky-700 border border-sky-300 bg-sky-50 rounded-lg hover:bg-sky-100 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.icon("trash-2", size=13),
                        on_click=lambda: MapaEsteticoState.eliminar_proc(pr["id"]),
                        class_name="ml-1.5 text-gray-300 hover:text-red-500 cursor-pointer",
                    ),
                    class_name="inline-flex items-center",
                ),
                rx.fragment(),
            ),
            class_name="flex items-center justify-between mb-1.5",
        ),
        rx.cond(
            pr["observacion"].to(str) != "",
            rx.el.p(pr["observacion"], class_name="text-xs text-gray-500 mb-2"),
            rx.fragment(),
        ),
        rx.cond(
            pr["puntos"].to(list[dict]).length() > 0,
            rx.el.div(rx.foreach(pr["puntos"].to(list[dict]), _punto_row), class_name="space-y-1"),
            rx.el.p("Sin puntos de aplicación aún.", class_name="text-xs text-gray-400 italic"),
        ),
        class_name="border border-gray-200 rounded-xl p-3 bg-white",
    )


def _eval_row(e) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(e["categoria_label"], class_name="text-sm font-medium text-gray-800"),
            rx.cond(
                e["severidad"].to(str) != "",
                rx.el.span(
                    "sev. " + e["severidad"].to(str),
                    class_name="ml-2 text-xs px-1.5 py-0.5 rounded bg-violet-100 text-violet-700",
                ),
                rx.fragment(),
            ),
            class_name="inline-flex items-center",
        ),
        rx.cond(
            e["observacion"].to(str) != "",
            rx.el.p(e["observacion"], class_name="text-xs text-gray-500"),
            rx.fragment(),
        ),
        rx.cond(
            MapaEsteticoState.puede_editar,
            rx.el.button(
                rx.icon("x", size=13),
                on_click=lambda: MapaEsteticoState.eliminar_eval(e["id"]),
                class_name="text-gray-300 hover:text-red-500 cursor-pointer",
            ),
            rx.fragment(),
        ),
        class_name="flex items-center justify-between gap-2 py-2 border-b border-gray-100 last:border-0",
    )


# ── Fotos antes/después de la zona (E8) ───────────────────────────────────────

def _foto_card(f: dict) -> rx.Component:
    return rx.el.div(
        rx.el.img(
            src=_foto_src(f),
            alt=f["nombre"],
            class_name="w-full h-32 object-cover rounded-lg border border-gray-200 bg-gray-50",
        ),
        rx.cond(
            MapaEsteticoState.puede_editar,
            rx.el.button(
                rx.icon("x", size=13),
                on_click=lambda: MapaEsteticoState.eliminar_foto(f["id"]),
                title="Eliminar foto",
                class_name="absolute top-1.5 right-1.5 p-1 bg-black/50 text-white rounded-full hover:bg-red-500 cursor-pointer opacity-0 group-hover:opacity-100 transition",
            ),
            rx.fragment(),
        ),
        class_name="relative group",
    )


def _columna_fotos(titulo: str, fotos, color: str, vacio: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(class_name="w-2 h-2 rounded-full " + color),
            rx.el.span(titulo, class_name="text-xs font-semibold text-gray-700"),
            rx.el.span(fotos.length().to_string(), class_name="text-[10px] font-bold text-gray-400 ml-auto"),
            class_name="flex items-center gap-2 mb-2",
        ),
        rx.cond(
            fotos.length() > 0,
            rx.el.div(rx.foreach(fotos, _foto_card), class_name="grid grid-cols-2 gap-2"),
            rx.el.p(vacio, class_name="text-xs text-gray-400 italic"),
        ),
        class_name="flex-1 min-w-0",
    )


def _momento_btn(m: dict) -> rx.Component:
    return rx.el.button(
        m["label"],
        on_click=lambda: MapaEsteticoState.set_foto_momento(m["clave"]),
        class_name=rx.cond(
            MapaEsteticoState.foto_momento == m["clave"],
            "px-2.5 py-1 text-xs font-medium text-white bg-sky-600 rounded-lg cursor-pointer",
            "px-2.5 py-1 text-xs font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
        ),
    )


def _fotos_zona() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("images", size=14, class_name="text-sky-600 mr-1.5"),
            rx.el.span("Fotos antes / después", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide"),
            class_name="flex items-center mb-2 mt-5 pt-4 border-t border-gray-100",
        ),
        # Subida (solo con permiso de escritura).
        rx.cond(
            MapaEsteticoState.puede_editar,
            rx.el.div(
                rx.el.div(
                    rx.el.span("Subir como:", class_name="text-xs text-gray-500 mr-1"),
                    rx.foreach(MapaEsteticoState.momentos_cat, _momento_btn),
                    class_name="flex items-center gap-1.5 flex-wrap mb-2",
                ),
                rx.el.div(
                    rx.upload(
                        rx.el.div(
                            rx.icon("image-plus", size=15, class_name="mr-1.5"),
                            rx.el.span("Elegir fotos"),
                            class_name="flex items-center text-xs text-sky-700",
                        ),
                        id=_FOTO_UPLOAD_ID,
                        multiple=True,
                        class_name="flex-1 px-3 py-2 border border-dashed border-sky-300 rounded-lg bg-sky-50/40 hover:bg-sky-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            MapaEsteticoState.is_uploading,
                            rx.el.div(rx.icon("loader-circle", size=14, class_name="animate-spin mr-1"), "Subiendo…", class_name="flex items-center"),
                            rx.el.div(rx.icon("cloud-upload", size=14, class_name="mr-1"), "Subir", class_name="flex items-center"),
                        ),
                        on_click=MapaEsteticoState.handle_upload_foto(rx.upload_files(upload_id=_FOTO_UPLOAD_ID)),
                        disabled=MapaEsteticoState.is_uploading,
                        class_name="px-3 py-2 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer shrink-0",
                    ),
                    class_name="flex items-center gap-2",
                ),
                rx.cond(
                    MapaEsteticoState.foto_error != "",
                    rx.el.p(MapaEsteticoState.foto_error, class_name="text-xs text-red-500 mt-2"),
                    rx.fragment(),
                ),
                class_name="p-3 bg-gray-50 border border-gray-100 rounded-xl mb-3",
            ),
            rx.fragment(),
        ),
        # Comparativa antes / después.
        rx.el.div(
            _columna_fotos("Antes", MapaEsteticoState.fotos_antes, "bg-amber-400", "Sin fotos de «antes»."),
            _columna_fotos("Después", MapaEsteticoState.fotos_despues, "bg-green-500", "Sin fotos de «después»."),
            class_name="flex flex-col sm:flex-row gap-4",
        ),
        # Durante (opcional).
        rx.cond(
            MapaEsteticoState.fotos_durante.length() > 0,
            rx.el.div(
                _columna_fotos("Durante", MapaEsteticoState.fotos_durante, "bg-sky-400", ""),
                class_name="mt-4",
            ),
            rx.fragment(),
        ),
    )


def _panel_zona() -> rx.Component:
    return rx.el.div(
        rx.cond(
            MapaEsteticoState.tiene_zona,
            rx.el.div(
                # Cabecera de la zona.
                rx.el.div(
                    rx.el.h3(MapaEsteticoState.zona_sel_label, class_name="text-lg font-bold text-gray-900"),
                    rx.cond(
                        MapaEsteticoState.puede_editar,
                        rx.el.div(
                            rx.el.button(
                                rx.icon("clipboard-check", size=14, class_name="mr-1"),
                                "Evaluar",
                                on_click=MapaEsteticoState.abrir_eval,
                                class_name="inline-flex items-center px-3 py-1.5 text-xs font-medium text-violet-700 border border-violet-300 bg-violet-50 rounded-lg hover:bg-violet-100 cursor-pointer",
                            ),
                            rx.el.button(
                                rx.icon("syringe", size=14, class_name="mr-1"),
                                "Procedimiento",
                                on_click=MapaEsteticoState.abrir_proc,
                                class_name="ml-1.5 inline-flex items-center px-3 py-1.5 text-xs font-medium text-sky-700 border border-sky-300 bg-sky-50 rounded-lg hover:bg-sky-100 cursor-pointer",
                            ),
                            class_name="flex items-center",
                        ),
                        rx.fragment(),
                    ),
                    class_name="flex items-start justify-between mb-4",
                ),
                # Evaluaciones.
                rx.el.p("Evaluaciones", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1"),
                rx.cond(
                    MapaEsteticoState.evaluaciones.length() > 0,
                    rx.el.div(rx.foreach(MapaEsteticoState.evaluaciones, _eval_row), class_name="mb-4"),
                    rx.el.p("Sin evaluaciones en esta zona.", class_name="text-xs text-gray-400 italic mb-4"),
                ),
                # Procedimientos.
                rx.el.p("Procedimientos", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5"),
                rx.cond(
                    MapaEsteticoState.procedimientos.length() > 0,
                    rx.el.div(rx.foreach(MapaEsteticoState.procedimientos, _proc_card), class_name="space-y-2"),
                    rx.el.p("Sin procedimientos en esta zona.", class_name="text-xs text-gray-400 italic"),
                ),
                # Fotos antes/después de la zona.
                _fotos_zona(),
            ),
            empty_state("mouse-pointer-click", "Elegí una zona", "Seleccioná una zona del rostro o del cuerpo en la lista."),
        ),
        class_name="bg-white border border-gray-200 rounded-2xl p-5",
    )


# ── Selector de zonas (rostro + cuerpo) ───────────────────────────────────────

def _zona_btn(z) -> rx.Component:
    """Botón de zona: punto de color por actividad + resaltado si está seleccionada."""
    dot = rx.match(
        z["estado"],
        ("proc", rx.el.span(class_name="w-2 h-2 rounded-full bg-sky-500 shrink-0")),
        ("eval", rx.el.span(class_name="w-2 h-2 rounded-full bg-violet-500 shrink-0")),
        rx.el.span(class_name="w-2 h-2 rounded-full bg-gray-300 shrink-0"),
    )
    return rx.el.button(
        dot,
        rx.el.span(z["label"], class_name="truncate"),
        on_click=lambda: MapaEsteticoState.seleccionar_zona(z["codigo"]),
        class_name=rx.cond(
            MapaEsteticoState.zona_sel == z["codigo"],
            "flex items-center gap-2 w-full text-left px-2.5 py-1.5 text-xs rounded-lg bg-sky-600 text-white cursor-pointer",
            "flex items-center gap-2 w-full text-left px-2.5 py-1.5 text-xs rounded-lg text-gray-700 hover:bg-gray-100 cursor-pointer",
        ),
    )


def _grupo_zonas(titulo: str, icono: str, zonas) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icono, size=13, class_name="text-gray-400 mr-1.5"),
            rx.el.span(titulo, class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide"),
            class_name="flex items-center mb-2",
        ),
        rx.el.div(rx.foreach(zonas, _zona_btn), class_name="grid grid-cols-1 sm:grid-cols-2 gap-1"),
        class_name="mb-4",
    )


def _leyenda() -> rx.Component:
    def _chip(cls, txt):
        return rx.el.div(
            rx.el.span(class_name="w-2.5 h-2.5 rounded-full inline-block mr-1.5 " + cls),
            rx.el.span(txt, class_name="text-xs text-gray-600"),
            class_name="inline-flex items-center mr-3",
        )
    return rx.el.div(
        _chip("bg-gray-300", "Sin actividad"),
        _chip("bg-violet-500", "Evaluada"),
        _chip("bg-sky-500", "Con procedimiento"),
        class_name="flex items-center flex-wrap mt-1",
    )


def _selector_zonas() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span("Zonas", class_name="text-sm font-semibold text-gray-700"),
            _leyenda(),
            class_name="flex items-center justify-between gap-3 flex-wrap mb-4",
        ),
        _grupo_zonas("Rostro", "smile", MapaEsteticoState.zonas_faciales),
        _grupo_zonas("Cuerpo", "person-standing", MapaEsteticoState.zonas_corporales),
        # Totales.
        rx.el.div(
            rx.el.span("Evaluaciones: " + MapaEsteticoState.n_evaluaciones.to_string(), class_name="text-xs text-gray-500 mr-3"),
            rx.el.span("Procedimientos: " + MapaEsteticoState.n_procedimientos.to_string(), class_name="text-xs text-gray-500 mr-3"),
            rx.el.span("Puntos: " + MapaEsteticoState.n_puntos.to_string(), class_name="text-xs text-gray-500 mr-3"),
            rx.el.span("Fotos: " + MapaEsteticoState.n_fotos.to_string(), class_name="text-xs text-gray-500"),
            class_name="mt-2 pt-4 border-t border-gray-100 flex flex-wrap",
        ),
        class_name="bg-white border border-gray-200 rounded-2xl p-5",
    )


# ── Modales ───────────────────────────────────────────────────────────────────

def _modal(abierto, titulo, cuerpo, on_cerrar, on_guardar, guardar_label="Guardar") -> rx.Component:
    return rx.cond(
        abierto,
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.h3(titulo, class_name="text-base font-bold text-gray-900 mb-4"),
                    cuerpo,
                    rx.el.div(
                        rx.el.button(
                            "Cancelar", on_click=on_cerrar,
                            class_name="px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg cursor-pointer",
                        ),
                        rx.el.button(
                            guardar_label, on_click=on_guardar,
                            disabled=MapaEsteticoState.is_saving,
                            class_name="px-4 py-2 text-sm font-medium text-white bg-sky-600 hover:bg-sky-700 disabled:bg-sky-400 rounded-lg cursor-pointer",
                        ),
                        class_name="flex items-center justify-end gap-2 mt-5",
                    ),
                    class_name="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl",
                ),
                class_name="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40",
                on_click=on_cerrar,
            ),
        ),
        rx.fragment(),
    )


def _modal_eval() -> rx.Component:
    return _modal(
        MapaEsteticoState.modal_eval,
        "Nueva evaluación — " + MapaEsteticoState.zona_sel_label,
        rx.el.div(
            _select("Categoría", MapaEsteticoState.ev_categoria, MapaEsteticoState.categorias_cat, MapaEsteticoState.set_ev_categoria),
            _select("Severidad", MapaEsteticoState.ev_severidad, MapaEsteticoState.severidades_cat, MapaEsteticoState.set_ev_severidad),
            rx.el.label(
                rx.el.span("Observación", class_name="block text-xs font-medium text-gray-600 mb-1"),
                rx.el.textarea(
                    value=MapaEsteticoState.ev_obs,
                    on_change=MapaEsteticoState.set_ev_obs,
                    rows="2",
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                ),
            ),
            class_name="space-y-3",
        ),
        MapaEsteticoState.cerrar_eval,
        MapaEsteticoState.guardar_eval,
    )


def _modal_proc() -> rx.Component:
    return _modal(
        MapaEsteticoState.modal_proc,
        "Nuevo procedimiento — " + MapaEsteticoState.zona_sel_label,
        rx.el.div(
            _select("Tipo", MapaEsteticoState.pr_tipo, MapaEsteticoState.tipos_cat, MapaEsteticoState.set_pr_tipo),
            rx.el.label(
                rx.el.span("Observación", class_name="block text-xs font-medium text-gray-600 mb-1"),
                rx.el.textarea(
                    value=MapaEsteticoState.pr_obs,
                    on_change=MapaEsteticoState.set_pr_obs,
                    rows="2",
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm",
                ),
            ),
            class_name="space-y-3",
        ),
        MapaEsteticoState.cerrar_proc,
        MapaEsteticoState.guardar_proc,
    )


def _modal_punto() -> rx.Component:
    return _modal(
        MapaEsteticoState.modal_punto,
        "Punto de aplicación",
        rx.el.div(
            _select("Producto (trazabilidad)", MapaEsteticoState.pt_producto, MapaEsteticoState.productos_cat, MapaEsteticoState.set_pt_producto),
            rx.el.div(
                _text_input("Lote", MapaEsteticoState.pt_lote, MapaEsteticoState.set_pt_lote, "LOT-…"),
                _text_input("Cantidad", MapaEsteticoState.pt_cantidad, MapaEsteticoState.set_pt_cantidad, "0"),
                _text_input("Unidad", MapaEsteticoState.pt_unidad, MapaEsteticoState.set_pt_unidad, "UI / ml"),
                class_name="grid grid-cols-3 gap-2",
            ),
            _text_input("Observación", MapaEsteticoState.pt_obs, MapaEsteticoState.set_pt_obs),
            class_name="space-y-3",
        ),
        MapaEsteticoState.cerrar_punto,
        MapaEsteticoState.guardar_punto,
    )


# ── Página ────────────────────────────────────────────────────────────────────

def _export_pdf_btn() -> rx.Component:
    """Link a la exportación PDF del mapa estético (protegido por token efímero)."""
    return rx.cond(
        MapaEsteticoState.paciente_id != 0,
        rx.el.a(
            rx.icon("file-down", size=15, class_name="mr-1.5"),
            "Exportar PDF",
            href=(
                "/api/estetica/pdf?paciente_id=" + MapaEsteticoState.paciente_id.to_string()
                + "&clinica_id=" + MapaEsteticoState.clinica_id.to_string()
                + "&token=" + MapaEsteticoState.download_token
            ),
            target="_blank",
            class_name="inline-flex items-center px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
        ),
        rx.fragment(),
    )


def mapa_estetico_page() -> rx.Component:
    return shell(
        rx.el.div(
            page_header(
                "Mapa estético",
                rx.cond(
                    MapaEsteticoState.paciente_nombre != "",
                    "Paciente: " + MapaEsteticoState.paciente_nombre,
                    "Evaluaciones y puntos de aplicación por zona",
                ),
                action=_export_pdf_btn(),
            ),
            rx.cond(
                MapaEsteticoState.paciente_id != 0,
                rx.el.div(
                    # Columna izquierda: selector de zonas.
                    rx.el.div(_selector_zonas(), class_name="lg:col-span-2"),
                    # Columna derecha: panel de la zona.
                    _panel_zona(),
                    class_name="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start",
                ),
                empty_state("user-round-search", "Sin paciente", "Abrí el mapa desde la Historia Clínica de un paciente."),
            ),
            _modal_eval(),
            _modal_proc(),
            _modal_punto(),
            class_name="p-6 max-w-6xl mx-auto",
        ),
        on_mount=MapaEsteticoState.on_mount,
    )
