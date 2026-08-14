from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.sesiones_esteticas import SesionesEsteticasState as S
from clinica_app.state.sesiones_esteticas import _FOTO_UPLOAD_ID


def _foto_src(f: dict):
    return (
        "/api/adjunto?id=" + f["id"].to_string()
        + "&clinica_id=" + S.clinica_id.to_string()
        + "&token=" + S.download_token
    )


# ── Piezas de UI ──────────────────────────────────────────────────────────────

def _sesion_chip(s: dict) -> rx.Component:
    activo = s["id"] == S.sesion_actual_id
    return rx.el.button(
        rx.el.div(
            rx.el.span(s["fecha_fmt"], class_name="text-xs font-bold text-sky-700"),
            rx.el.span(
                s["n_fotos"].to_string() + " fotos",
                class_name="text-[10px] text-gray-400 ml-auto",
            ),
            class_name="flex items-center w-full",
        ),
        rx.el.span(s["titulo"], class_name="text-sm font-semibold text-gray-800 truncate max-w-[14rem] mt-0.5"),
        rx.cond(
            s["zona"] != "",
            rx.el.span(s["zona"], class_name="text-xs text-gray-400"),
        ),
        rx.el.div(
            rx.el.span("Antes " + s["n_antes"].to_string(), class_name="text-[10px] text-gray-500 bg-gray-100 rounded px-1.5 py-0.5"),
            rx.el.span("Después " + s["n_despues"].to_string(), class_name="text-[10px] text-gray-500 bg-gray-100 rounded px-1.5 py-0.5"),
            class_name="flex items-center gap-1 mt-1",
        ),
        on_click=lambda: S.seleccionar_sesion(s["id"]),
        class_name=rx.cond(
            activo,
            "flex flex-col items-start p-3 rounded-xl border-2 border-sky-500 bg-sky-50 text-left w-full cursor-pointer transition",
            "flex flex-col items-start p-3 rounded-xl border border-gray-200 bg-white hover:border-sky-300 text-left w-full cursor-pointer transition",
        ),
    )


def _foto_card(f: dict) -> rx.Component:
    return rx.el.div(
        rx.el.img(
            src=_foto_src(f),
            alt=f["nombre"],
            class_name="w-full h-40 object-cover rounded-lg border border-gray-200 bg-gray-50",
        ),
        rx.el.button(
            rx.icon("x", size=14),
            on_click=lambda: S.eliminar_foto(f["id"]),
            title="Eliminar foto",
            class_name="absolute top-1.5 right-1.5 p-1 bg-black/50 text-white rounded-full hover:bg-red-500 cursor-pointer opacity-0 group-hover:opacity-100 transition",
        ),
        class_name="relative group",
    )


def _columna_fotos(titulo: str, fotos, color: str, vacio: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(class_name="w-2 h-2 rounded-full " + color),
            rx.el.span(titulo, class_name="text-sm font-semibold text-gray-700"),
            rx.el.span(fotos.length().to_string(), class_name="text-xs font-bold text-gray-400 ml-auto"),
            class_name="flex items-center gap-2 mb-2",
        ),
        rx.cond(
            fotos.length() > 0,
            rx.el.div(
                rx.foreach(fotos.to(list[dict]), _foto_card),
                class_name="grid grid-cols-2 gap-2",
            ),
            rx.el.p(vacio, class_name="text-xs text-gray-400 italic py-6 text-center border border-dashed border-gray-200 rounded-lg"),
        ),
        class_name="flex-1 min-w-0",
    )


def _momento_btn(m: dict) -> rx.Component:
    activo = m["clave"] == S.upload_momento
    return rx.el.button(
        m["label"],
        on_click=lambda: S.set_upload_momento(m["clave"]),
        class_name=rx.cond(
            activo,
            "px-3 py-1.5 text-sm rounded-lg bg-sky-600 text-white cursor-pointer",
            "px-3 py-1.5 text-sm rounded-lg bg-white border border-gray-300 text-gray-600 hover:bg-gray-50 cursor-pointer",
        ),
    )


def _dato(label: str, valor, placeholder: str = "—") -> rx.Component:
    return rx.el.div(
        rx.el.span(label, class_name="text-xs text-gray-400 uppercase tracking-wide"),
        rx.el.span(
            rx.cond((valor != "") & (valor != 0), valor, placeholder),
            class_name="text-sm text-gray-800",
        ),
        class_name="flex flex-col",
    )


def _insumo_row(i: dict) -> rx.Component:
    return rx.el.div(
        rx.icon("syringe", size=14, class_name="text-sky-500 mr-2 shrink-0"),
        rx.el.span(i["descripcion"], class_name="text-sm text-gray-800 flex-1 min-w-0 truncate"),
        rx.cond(
            i["cantidad"] != "0",
            rx.el.span(
                i["cantidad"].to(str) + " " + i["unidad"].to(str),
                class_name="text-sm font-medium text-gray-600 mr-2 shrink-0",
            ),
        ),
        rx.el.button(
            rx.icon("x", size=14),
            on_click=lambda: S.eliminar_insumo(i["id"]),
            title="Quitar insumo",
            class_name="text-gray-300 hover:text-red-500 cursor-pointer shrink-0",
        ),
        class_name="flex items-center py-2 px-3 border-b border-gray-100 last:border-0 hover:bg-gray-50",
    )


def _ficha_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("clipboard-pen-line", size=15, class_name="text-sky-600 mr-1.5"),
                rx.el.span("Ficha del tratamiento", class_name="text-sm font-semibold text-gray-700"),
                class_name="flex items-center",
            ),
            rx.el.button(
                rx.icon("pencil", size=13, class_name="mr-1"),
                "Editar ficha",
                on_click=S.abrir_modal_ficha,
                class_name="flex items-center px-2.5 py-1 text-xs text-sky-700 border border-sky-300 rounded-lg hover:bg-sky-50 cursor-pointer",
            ),
            class_name="flex items-center justify-between mb-3",
        ),
        rx.el.div(
            _dato("N.º de sesión", S.sa_numero_sesion),
            _dato("Zonas tratadas", S.sa_zona),
            _dato("Próxima recomendada", S.sa_proxima_fmt),
            class_name="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-3",
        ),
        _dato("Parámetros del equipo", S.sa_parametros),
        rx.cond(
            S.sa_proxima_fmt != "",
            rx.el.a(
                rx.icon("calendar-plus", size=14, class_name="mr-1.5"),
                "Agendar próxima sesión (" + S.sa_proxima_fmt + ")",
                href="/turnos?paciente_id=" + S.paciente_id.to_string(),
                class_name="inline-flex items-center mt-3 px-3 py-1.5 text-xs text-sky-700 bg-sky-50 border border-sky-200 rounded-lg hover:bg-sky-100 cursor-pointer",
            ),
        ),
        # Insumos aplicados
        rx.el.div(
            rx.el.div(
                rx.el.span("Insumos / productos aplicados", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                rx.el.button(
                    rx.icon("plus", size=13, class_name="mr-1"),
                    "Agregar",
                    on_click=S.abrir_modal_insumo,
                    class_name="flex items-center px-2.5 py-1 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
                class_name="flex items-center justify-between mb-2",
            ),
            rx.cond(
                S.insumos.length() > 0,
                rx.el.div(
                    rx.foreach(S.insumos.to(list[dict]), _insumo_row),
                    class_name="border border-gray-200 rounded-lg overflow-hidden",
                ),
                rx.el.p("Sin insumos registrados.", class_name="text-xs text-gray-400 italic"),
            ),
            class_name="mt-4 pt-4 border-t border-gray-100",
        ),
        class_name="p-4 bg-white border border-gray-100 rounded-xl shadow-sm mb-5",
    )


def _panel_sesion() -> rx.Component:
    return rx.el.div(
        # Cabecera
        rx.el.div(
            rx.el.div(
                rx.el.h2(S.sa_titulo, class_name="text-lg font-semibold text-gray-900"),
                rx.el.div(
                    rx.icon("calendar", size=13, class_name="text-gray-400 mr-1"),
                    rx.el.span(S.sa_fecha, class_name="text-sm text-gray-500"),
                    rx.cond(
                        S.sa_zona != "",
                        rx.el.span(" · " + S.sa_zona, class_name="text-sm text-gray-400"),
                    ),
                    class_name="flex items-center mt-0.5",
                ),
                rx.cond(
                    S.sa_notas != "",
                    rx.el.p(S.sa_notas, class_name="text-sm text-gray-400 mt-1"),
                ),
                class_name="min-w-0",
            ),
            rx.el.button(
                rx.icon("trash-2", size=16),
                on_click=S.eliminar_sesion,
                title="Eliminar sesión",
                class_name="p-2 text-gray-400 hover:text-red-500 border border-gray-300 rounded-lg cursor-pointer shrink-0",
            ),
            class_name="flex items-start justify-between gap-4 mb-4",
        ),
        # Ficha clínica (C2)
        _ficha_card(),
        # Subida
        rx.el.div(
            rx.el.div(
                rx.el.span("Agregar fotos como:", class_name="text-sm font-medium text-gray-600 mr-1"),
                rx.foreach(S.momentos_cat.to(list[dict]), _momento_btn),
                class_name="flex items-center gap-2 flex-wrap mb-3",
            ),
            rx.el.div(
                rx.upload(
                    rx.el.div(
                        rx.icon("image-plus", size=16, class_name="mr-1.5"),
                        rx.el.span("Elegir fotos"),
                        class_name="flex items-center text-sm text-sky-700",
                    ),
                    id=_FOTO_UPLOAD_ID,
                    multiple=True,
                    class_name="flex-1 px-3 py-2 border border-dashed border-sky-300 rounded-lg bg-sky-50/40 hover:bg-sky-50 cursor-pointer",
                ),
                rx.el.button(
                    rx.cond(
                        S.is_uploading,
                        rx.el.div(rx.icon("loader-circle", size=15, class_name="animate-spin mr-1"), "Subiendo…", class_name="flex items-center"),
                        rx.el.div(rx.icon("cloud-upload", size=15, class_name="mr-1"), "Subir", class_name="flex items-center"),
                    ),
                    on_click=S.handle_upload(rx.upload_files(upload_id=_FOTO_UPLOAD_ID)),
                    disabled=S.is_uploading,
                    class_name="px-3 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer shrink-0",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.cond(
                S.upload_error != "",
                rx.el.p(S.upload_error, class_name="text-xs text-red-500 mt-2"),
            ),
            class_name="p-4 bg-gray-50 border border-gray-100 rounded-xl mb-5",
        ),
        # Comparativa antes / después
        rx.el.div(
            _columna_fotos("Antes", S.fotos_antes, "bg-amber-400", "Sin fotos de «antes»."),
            _columna_fotos("Después", S.fotos_despues, "bg-green-500", "Sin fotos de «después»."),
            class_name="flex flex-col sm:flex-row gap-5",
        ),
        # Durante (opcional)
        rx.cond(
            S.fotos_durante.length() > 0,
            rx.el.div(
                _columna_fotos("Durante", S.fotos_durante, "bg-sky-400", ""),
                class_name="mt-5",
            ),
        ),
        class_name="flex-1 min-w-0",
    )


# ── Modal nueva sesión ────────────────────────────────────────────────────────

def _modal_sesion() -> rx.Component:
    return rx.cond(
        S.modal_sesion,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=S.cerrar_modal_sesion),
            rx.el.div(
                rx.el.h2("Nueva sesión estética", class_name="text-lg font-semibold text-gray-900 mb-4"),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Fecha", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            type="date", default_value=S.ns_fecha, on_change=S.set_ns_fecha,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    rx.el.div(
                        rx.el.label("Zona (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            placeholder="Ej: Labios, frente…", default_value=S.ns_zona, on_change=S.set_ns_zona,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    class_name="flex gap-3 mb-4",
                ),
                rx.el.label("Título", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.input(
                    placeholder="Ej: Relleno con ácido hialurónico",
                    default_value=S.ns_titulo, on_change=S.set_ns_titulo,
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.label("Notas (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.textarea(
                    placeholder="Producto, dosis, observaciones…",
                    default_value=S.ns_notas, on_change=S.set_ns_notas, rows="3",
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-5 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=S.cerrar_modal_sesion,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        rx.cond(S.is_uploading, "Creando…", "Crear sesión"),
                        on_click=S.guardar_sesion,
                        disabled=S.is_uploading,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_ficha() -> rx.Component:
    return rx.cond(
        S.modal_ficha,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=S.cerrar_modal_ficha),
            rx.el.div(
                rx.el.h2("Editar ficha del tratamiento", class_name="text-lg font-semibold text-gray-900 mb-4"),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("N.º de sesión", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            type="number", min="1", placeholder="Ej: 2",
                            default_value=S.ef_numero, on_change=S.set_ef_numero,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    rx.el.div(
                        rx.el.label("Próxima recomendada", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            type="date", default_value=S.ef_proxima, on_change=S.set_ef_proxima,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    class_name="flex gap-3 mb-4",
                ),
                rx.el.label("Zonas tratadas", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.input(
                    placeholder="Ej: Frente, entrecejo, patas de gallo",
                    default_value=S.ef_zona, on_change=S.set_ef_zona,
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.label("Parámetros del equipo", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.textarea(
                    placeholder="Ej: Toxina 50 UI, 5 puntos; láser 8 J/cm², 3 disparos…",
                    default_value=S.ef_parametros, on_change=S.set_ef_parametros, rows="3",
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-5 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=S.cerrar_modal_ficha,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        "Guardar ficha", on_click=S.guardar_ficha,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_insumo() -> rx.Component:
    return rx.cond(
        S.modal_insumo,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40", on_click=S.cerrar_modal_insumo),
            rx.el.div(
                rx.el.h2("Agregar insumo aplicado", class_name="text-lg font-semibold text-gray-900 mb-4"),
                rx.el.label("Producto de inventario (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.select(
                    rx.el.option("— Manual —", value="0"),
                    rx.foreach(
                        S.productos.to(list[dict]),
                        lambda p: rx.el.option(p["nombre"], value=p["id"]),
                    ),
                    value=S.ni_producto_id,
                    on_change=S.set_ni_producto,
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.label("Descripción", class_name="block text-sm font-medium text-gray-700 mb-1"),
                rx.el.input(
                    placeholder="Ej: Ácido hialurónico",
                    value=S.ni_descripcion, on_change=S.set_ni_descripcion,
                    class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-sky-500",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Cantidad", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            type="number", min="0", step="0.001", placeholder="0",
                            default_value=S.ni_cantidad, on_change=S.set_ni_cantidad,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    rx.el.div(
                        rx.el.label("Unidad", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.input(
                            placeholder="ml, UI, disparos…",
                            default_value=S.ni_unidad, on_change=S.set_ni_unidad,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                        class_name="flex-1",
                    ),
                    class_name="flex gap-3 mb-5",
                ),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=S.cerrar_modal_insumo,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        "Agregar", on_click=S.guardar_insumo,
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer",
                    ),
                    class_name="flex justify-end gap-3",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


# ── Página ────────────────────────────────────────────────────────────────────

def sesiones_esteticas_page() -> rx.Component:
    return shell(
        _modal_sesion(),
        _modal_ficha(),
        _modal_insumo(),
        page_header(
            "Galería estética",
            "Fotos antes/después por sesión y evolución del paciente",
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
                rx.icon("images", size=48, class_name="text-gray-300 mb-4"),
                rx.el.p("No hay paciente seleccionado", class_name="text-gray-500 font-medium"),
                rx.el.p("Accedé a la galería estética desde la Historia Clínica de un paciente",
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
                    # Timeline
                    rx.el.div(
                        rx.el.div(
                            rx.el.span("Línea de tiempo", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                            rx.el.button(
                                rx.icon("plus", size=14, class_name="mr-1"),
                                "Nueva",
                                on_click=S.abrir_modal_sesion,
                                class_name="flex items-center px-2.5 py-1 text-xs bg-sky-600 text-white rounded-lg hover:bg-sky-700 cursor-pointer",
                            ),
                            class_name="flex items-center justify-between mb-3",
                        ),
                        rx.cond(
                            S.sesiones.length() > 0,
                            rx.el.div(
                                rx.foreach(S.sesiones.to(list[dict]), _sesion_chip),
                                class_name="flex flex-col gap-2",
                            ),
                            rx.el.p("Sin sesiones todavía.", class_name="text-sm text-gray-400 italic"),
                        ),
                        class_name="w-full lg:w-72 shrink-0",
                    ),
                    # Panel de sesión
                    rx.cond(
                        S.sesion_actual_id != 0,
                        _panel_sesion(),
                        rx.el.div(
                            rx.icon("images", size=40, class_name="text-gray-300 mb-3"),
                            rx.el.p("Seleccioná una sesión o creá una nueva", class_name="text-sm text-gray-400"),
                            class_name="flex-1 flex flex-col items-center justify-center py-16 border border-dashed border-gray-200 rounded-xl",
                        ),
                    ),
                    class_name="flex flex-col lg:flex-row gap-6 items-start",
                ),
            ),
        ),
        on_mount=S.on_mount,
    )
