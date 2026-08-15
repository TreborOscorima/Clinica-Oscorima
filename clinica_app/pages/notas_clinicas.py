from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.notas_clinicas import NotasClinicasState

_TIPOS = ["evolucion", "anamnesis", "diagnostico", "indicacion", "otro"]
_TIPOS_LABELS = {
    "evolucion":   "Evolución",
    "anamnesis":   "Anamnesis",
    "diagnostico": "Diagnóstico",
    "indicacion":  "Indicación",
    "otro":        "Otro",
}

_TIPO_COLORS = {
    "evolucion":   "bg-sky-100 text-sky-700",
    "anamnesis":   "bg-purple-100 text-purple-700",
    "diagnostico": "bg-amber-100 text-amber-700",
    "indicacion":  "bg-green-100 text-green-700",
    "otro":        "bg-gray-100 text-gray-600",
}


def _tipo_badge(tipo: str) -> rx.Component:
    return rx.el.span(
        rx.match(
            tipo,
            ("evolucion",   "Evolución"),
            ("anamnesis",   "Anamnesis"),
            ("diagnostico", "Diagnóstico"),
            ("indicacion",  "Indicación"),
            "Otro",
        ),
        class_name=rx.match(
            tipo,
            ("evolucion",   "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-sky-100 text-sky-700"),
            ("anamnesis",   "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700"),
            ("diagnostico", "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700"),
            ("indicacion",  "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700"),
            "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600",
        ),
    )


def _modal_nota() -> rx.Component:
    return rx.cond(
        NotasClinicasState.modal_abierto,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=NotasClinicasState.cerrar_modal,
            ),
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.h2(
                        rx.cond(NotasClinicasState.editar_id != 0, "Editar nota", "Nueva nota clínica"),
                        class_name="text-lg font-semibold text-gray-900",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=NotasClinicasState.cerrar_modal,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                # Paciente info
                rx.el.div(
                    rx.icon("user", size=14, class_name="text-gray-400 mr-1"),
                    rx.el.span(NotasClinicasState.paciente_nombre, class_name="text-sm text-gray-600"),
                    class_name="flex items-center mb-4 bg-gray-50 px-3 py-2 rounded-lg",
                ),
                # Tipo
                rx.el.div(
                    rx.el.label("Tipo de nota", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.select(
                        rx.el.option("Evolución",   value="evolucion"),
                        rx.el.option("Anamnesis",   value="anamnesis"),
                        rx.el.option("Diagnóstico", value="diagnostico"),
                        rx.el.option("Indicación",  value="indicacion"),
                        rx.el.option("Otro",        value="otro"),
                        default_value=NotasClinicasState.form_tipo,
                        on_change=NotasClinicasState.set_form_tipo,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    class_name="mb-4",
                ),
                # Turno ID (opcional)
                rx.el.div(
                    rx.el.label("ID de turno (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    
                    rx.el.input(
                        type="text",
                        placeholder="Ej: 42",
                        default_value=NotasClinicasState.form_turno_id,
                        on_change=NotasClinicasState.set_form_turno_id,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
                    ),
                    class_name="mb-4",
                ),
                # Contenido
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Contenido *", class_name="block text-sm font-medium text-gray-700"),
                        # Selector de plantilla por especialidad
                        rx.el.select(
                            rx.el.option("Insertar plantilla…", value=""),
                            rx.foreach(
                                NotasClinicasState.plantillas_cat.to(list[dict]),
                                lambda p: rx.el.option(p["label"], value=p["clave"]),
                            ),
                            value="",
                            on_change=NotasClinicasState.aplicar_plantilla,
                            title="Inserta un esqueleto estructurado en el contenido",
                            class_name="text-xs px-2 py-1 border border-gray-200 rounded-lg text-gray-600 focus:outline-none focus:ring-2 focus:ring-sky-500 cursor-pointer",
                        ),
                        class_name="flex items-center justify-between mb-1",
                    ),
                    rx.el.textarea(
                        placeholder="Escribí la nota clínica aquí…",
                        value=NotasClinicasState.form_contenido,
                        on_change=NotasClinicasState.set_form_contenido,
                        rows=8,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none",
                    ),
                    class_name="mb-4",
                ),
                # Error
                rx.cond(
                    NotasClinicasState.form_error != "",
                    rx.el.p(
                        NotasClinicasState.form_error,
                        class_name="mb-3 text-sm text-red-600 bg-red-50 p-2 rounded",
                    ),
                ),
                # Botones
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=NotasClinicasState.cerrar_modal,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            NotasClinicasState.is_saving,
                            rx.el.div(
                                rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                "Guardando…",
                                class_name="flex items-center",
                            ),
                            "Guardar nota",
                        ),
                        on_click=NotasClinicasState.guardar,
                        disabled=NotasClinicasState.is_saving,
                        data_modal_submit="1",
                        title="Guardar nota (Ctrl+Enter)",
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_consentimiento() -> rx.Component:
    return rx.cond(
        NotasClinicasState.modal_cons_abierto,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=NotasClinicasState.cerrar_consentimiento,
            ),
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.icon("signature", size=18, class_name="text-green-600 mr-2"),
                        rx.el.h2("Consentimiento informado", class_name="text-lg font-semibold text-gray-900"),
                        class_name="flex items-center",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=NotasClinicasState.cerrar_consentimiento,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                # Paciente info
                rx.el.div(
                    rx.icon("user", size=14, class_name="text-gray-400 mr-1"),
                    rx.el.span(NotasClinicasState.paciente_nombre, class_name="text-sm text-gray-600"),
                    class_name="flex items-center mb-4 bg-gray-50 px-3 py-2 rounded-lg",
                ),
                # Tipo
                rx.el.div(
                    rx.el.label("Tipo de consentimiento", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.select(
                        rx.foreach(
                            NotasClinicasState.cons_tipos_cat.to(list[dict]),
                            lambda t: rx.el.option(t["label"], value=t["clave"]),
                        ),
                        default_value=NotasClinicasState.cons_tipo,
                        on_change=NotasClinicasState.set_cons_tipo,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500",
                    ),
                    class_name="mb-4",
                ),
                # Procedimiento
                rx.el.div(
                    rx.el.label("Procedimiento *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.input(
                        type="text",
                        placeholder="Ej: Aplicación de toxina botulínica en tercio superior",
                        default_value=NotasClinicasState.cons_procedimiento,
                        on_change=NotasClinicasState.set_cons_procedimiento,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500",
                    ),
                    class_name="mb-4",
                ),
                # Profesional (aclaración de la firma)
                rx.el.div(
                    rx.el.label("Profesional (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.input(
                        type="text",
                        placeholder="Nombre y matrícula del profesional",
                        default_value=NotasClinicasState.cons_profesional,
                        on_change=NotasClinicasState.set_cons_profesional,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500",
                    ),
                    class_name="mb-4",
                ),
                # Observaciones
                rx.el.div(
                    rx.el.label("Observaciones (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.textarea(
                        placeholder="Aclaraciones específicas para este paciente…",
                        default_value=NotasClinicasState.cons_observaciones,
                        on_change=NotasClinicasState.set_cons_observaciones,
                        rows=3,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 resize-none",
                    ),
                    class_name="mb-4",
                ),
                rx.el.p(
                    rx.icon("info", size=12, class_name="inline mr-1 -mt-0.5"),
                    "Se generará un PDF y quedará archivado como adjunto del paciente, listo para imprimir y firmar.",
                    class_name="text-xs text-gray-400 mb-3",
                ),
                # Error
                rx.cond(
                    NotasClinicasState.cons_error != "",
                    rx.el.p(
                        NotasClinicasState.cons_error,
                        class_name="mb-3 text-sm text-red-600 bg-red-50 p-2 rounded",
                    ),
                ),
                # Botones
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=NotasClinicasState.cerrar_consentimiento,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            NotasClinicasState.is_generating_cons,
                            rx.el.div(
                                rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                "Generando…",
                                class_name="flex items-center",
                            ),
                            rx.el.div(
                                rx.icon("file-down", size=16, class_name="mr-1"),
                                "Generar PDF",
                                class_name="flex items-center",
                            ),
                        ),
                        on_click=NotasClinicasState.generar_consentimiento,
                        disabled=NotasClinicasState.is_generating_cons,
                        class_name="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-green-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_receta() -> rx.Component:
    return rx.cond(
        NotasClinicasState.modal_rec_abierto,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=NotasClinicasState.cerrar_receta,
            ),
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.icon("pill", size=18, class_name="text-rose-500 mr-2"),
                        rx.el.h2("Receta / Indicación", class_name="text-lg font-semibold text-gray-900"),
                        class_name="flex items-center",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=NotasClinicasState.cerrar_receta,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                # Paciente info
                rx.el.div(
                    rx.icon("user", size=14, class_name="text-gray-400 mr-1"),
                    rx.el.span(NotasClinicasState.paciente_nombre, class_name="text-sm text-gray-600"),
                    class_name="flex items-center mb-4 bg-gray-50 px-3 py-2 rounded-lg",
                ),
                # Tipo
                rx.el.div(
                    rx.el.label("Tipo de documento", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.select(
                        rx.foreach(
                            NotasClinicasState.rec_tipos_cat.to(list[dict]),
                            lambda t: rx.el.option(t["label"], value=t["clave"]),
                        ),
                        default_value=NotasClinicasState.rec_tipo,
                        on_change=NotasClinicasState.set_rec_tipo,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-rose-500",
                    ),
                    class_name="mb-4",
                ),
                # Diagnóstico (opcional)
                rx.el.div(
                    rx.el.label("Diagnóstico (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.input(
                        type="text",
                        placeholder="Ej: Faringitis aguda",
                        default_value=NotasClinicasState.rec_diagnostico,
                        on_change=NotasClinicasState.set_rec_diagnostico,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-rose-500",
                    ),
                    class_name="mb-4",
                ),
                # Cuerpo
                rx.el.div(
                    rx.el.label(
                        rx.cond(
                            NotasClinicasState.rec_tipo == "receta",
                            "Medicación (una por renglón) *",
                            "Indicaciones (una por renglón) *",
                        ),
                        class_name="block text-sm font-medium text-gray-700 mb-1",
                    ),
                    rx.el.textarea(
                        placeholder="Ej: Amoxicilina 500mg — 1 comp c/8h por 7 días",
                        default_value=NotasClinicasState.rec_cuerpo,
                        on_change=NotasClinicasState.set_rec_cuerpo,
                        rows=6,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 resize-none",
                    ),
                    class_name="mb-4",
                ),
                # Profesional (firma)
                rx.el.div(
                    rx.el.label("Profesional (opcional)", class_name="block text-sm font-medium text-gray-700 mb-1"),
                    rx.el.input(
                        type="text",
                        placeholder="Nombre y matrícula del profesional",
                        default_value=NotasClinicasState.rec_profesional,
                        on_change=NotasClinicasState.set_rec_profesional,
                        class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-rose-500",
                    ),
                    class_name="mb-4",
                ),
                rx.el.p(
                    rx.icon("info", size=12, class_name="inline mr-1 -mt-0.5"),
                    "Se generará un PDF y quedará archivado como adjunto del paciente, listo para imprimir y firmar.",
                    class_name="text-xs text-gray-400 mb-3",
                ),
                # Error
                rx.cond(
                    NotasClinicasState.rec_error != "",
                    rx.el.p(
                        NotasClinicasState.rec_error,
                        class_name="mb-3 text-sm text-red-600 bg-red-50 p-2 rounded",
                    ),
                ),
                # Botones
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=NotasClinicasState.cerrar_receta,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            NotasClinicasState.is_generating_rec,
                            rx.el.div(
                                rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                "Generando…",
                                class_name="flex items-center",
                            ),
                            rx.el.div(
                                rx.icon("file-down", size=16, class_name="mr-1"),
                                "Generar PDF",
                                class_name="flex items-center",
                            ),
                        ),
                        on_click=NotasClinicasState.generar_receta,
                        disabled=NotasClinicasState.is_generating_rec,
                        class_name="px-4 py-2 text-sm bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:bg-rose-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


_ADJ_UPLOAD_ID = "hc_adjuntos"


def _cat_icon(cat: str) -> rx.Component:
    return rx.match(
        cat,
        ("foto",          rx.icon("image", size=16, class_name="text-sky-500")),
        ("radiografia",   rx.icon("scan", size=16, class_name="text-indigo-500")),
        ("estudio",       rx.icon("file-text", size=16, class_name="text-amber-500")),
        ("consentimiento", rx.icon("signature", size=16, class_name="text-green-600")),
        ("receta",        rx.icon("pill", size=16, class_name="text-rose-500")),
        ("informe",       rx.icon("clipboard-list", size=16, class_name="text-purple-500")),
        rx.icon("paperclip", size=16, class_name="text-gray-400"),
    )


def _fila_adjunto(a: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            _cat_icon(a["categoria"]),
            rx.el.div(
                rx.el.p(a["nombre"], class_name="text-sm font-medium text-gray-800 truncate max-w-[220px]"),
                rx.el.p(
                    a["categoria"], " · ", a["tamano_fmt"], " · ", a["created_at"],
                    class_name="text-xs text-gray-400 capitalize",
                ),
                class_name="min-w-0",
            ),
            class_name="flex items-center gap-2 min-w-0",
        ),
        rx.el.div(
            rx.el.a(
                rx.icon("download", size=15),
                href=f"/api/adjunto?id={a['id']}&clinica_id={NotasClinicasState.clinica_id}&token={NotasClinicasState.download_token}",
                target="_blank",
                title="Descargar",
                class_name="p-1.5 text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 rounded cursor-pointer",
            ),
            rx.el.button(
                rx.icon("trash-2", size=15),
                on_click=lambda: NotasClinicasState.eliminar_adjunto(a["id"]),
                title="Eliminar",
                class_name="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer",
            ),
            class_name="flex items-center gap-1 shrink-0",
        ),
        class_name="flex items-center justify-between gap-2 py-2 px-3 bg-white border border-gray-100 rounded-lg hover:shadow-sm transition",
    )


def _seccion_adjuntos() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("paperclip", size=15, class_name="text-gray-500 mr-1.5"),
                rx.el.span("Archivos del paciente", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                class_name="flex items-center",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("pill", size=14, class_name="mr-1.5"),
                    rx.el.span("Receta / Indicación", class_name="text-sm"),
                    on_click=NotasClinicasState.abrir_receta,
                    title="Emitir una receta o indicación en PDF",
                    class_name="inline-flex items-center px-2.5 py-1 text-rose-700 border border-rose-300 bg-rose-50 rounded-lg hover:bg-rose-100 cursor-pointer",
                ),
                rx.el.button(
                    rx.icon("signature", size=14, class_name="mr-1.5"),
                    rx.el.span("Consentimiento", class_name="text-sm"),
                    on_click=NotasClinicasState.abrir_consentimiento,
                    title="Generar un consentimiento informado en PDF",
                    class_name="inline-flex items-center px-2.5 py-1 text-green-700 border border-green-300 bg-green-50 rounded-lg hover:bg-green-100 cursor-pointer",
                ),
                class_name="flex items-center gap-2",
            ),
            class_name="flex items-center justify-between mb-2",
        ),
        # Controles de subida
        rx.el.div(
            rx.el.select(
                rx.el.option("Foto",           value="foto"),
                rx.el.option("Estudio",        value="estudio"),
                rx.el.option("Radiografía",    value="radiografia"),
                rx.el.option("Consentimiento", value="consentimiento"),
                rx.el.option("Receta",         value="receta"),
                rx.el.option("Informe",        value="informe"),
                rx.el.option("Otro",           value="otro"),
                default_value=NotasClinicasState.adj_categoria,
                on_change=NotasClinicasState.set_adj_categoria,
                class_name="px-2 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
            ),
            rx.upload(
                rx.el.div(
                    rx.icon("upload", size=14, class_name="mr-1.5"),
                    rx.el.span("Elegir archivos"),
                    class_name="flex items-center text-sm text-sky-700",
                ),
                id=_ADJ_UPLOAD_ID,
                multiple=True,
                class_name="flex-1 px-3 py-1.5 border border-dashed border-sky-300 rounded-lg bg-sky-50/40 hover:bg-sky-50 cursor-pointer",
            ),
            rx.el.button(
                rx.cond(
                    NotasClinicasState.is_uploading,
                    rx.el.div(
                        rx.icon("loader-circle", size=15, class_name="animate-spin mr-1"),
                        "Subiendo…",
                        class_name="flex items-center",
                    ),
                    rx.el.div(rx.icon("cloud-upload", size=15, class_name="mr-1"), "Subir", class_name="flex items-center"),
                ),
                on_click=NotasClinicasState.handle_upload(
                    rx.upload_files(upload_id=_ADJ_UPLOAD_ID)
                ),
                disabled=NotasClinicasState.is_uploading,
                class_name="px-3 py-1.5 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer shrink-0",
            ),
            class_name="flex items-center gap-2 mb-2",
        ),
        rx.el.p(
            "Formatos: imágenes, PDF, doc/docx, txt, dcm · máx 10 MB c/u",
            class_name="text-xs text-gray-400 mb-2",
        ),
        rx.cond(
            NotasClinicasState.adj_error != "",
            rx.el.p(
                NotasClinicasState.adj_error,
                class_name="text-sm text-red-600 bg-red-50 p-2 rounded mb-2",
            ),
        ),
        # Lista de adjuntos
        rx.cond(
            NotasClinicasState.adjuntos.length() > 0,
            rx.el.div(
                rx.foreach(NotasClinicasState.adjuntos.to(list[dict]), _fila_adjunto),
                class_name="space-y-2",
            ),
            rx.el.p("Sin archivos adjuntos", class_name="text-sm text-gray-400 italic"),
        ),
        class_name="mb-6 p-4 bg-gray-50 border border-gray-100 rounded-xl",
    )


def _fila_nota(n: dict) -> rx.Component:
    return rx.el.div(
        # Header de la nota
        rx.el.div(
            rx.el.div(
                _tipo_badge(n["tipo"]),
                rx.cond(
                    n["turno_id"],
                    rx.el.span(
                        rx.icon("calendar-clock", size=12, class_name="mr-1"),
                        "Turno #", n["turno_id"],
                        class_name="flex items-center text-xs text-gray-400 ml-2",
                    ),
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.el.span(n["created_at"], class_name="text-xs text-gray-400 mr-3"),
                rx.cond(
                    n["profesional_nombre"],
                    rx.el.span(n["profesional_nombre"], class_name="text-xs text-gray-500 mr-3"),
                ),
                rx.cond(
                    n["firmada"],
                    # Nota firmada → candado + firmante, sin acciones de edición
                    rx.el.span(
                        rx.icon("lock", size=12, class_name="mr-1"),
                        "Firmada",
                        class_name="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-700",
                    ),
                    # Nota sin firmar → firmar / editar / eliminar
                    rx.el.div(
                        rx.el.button(
                            rx.icon("pen-line", size=14),
                            on_click=lambda: NotasClinicasState.firmar_nota(n["id"]),
                            class_name="p-1 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded cursor-pointer transition",
                            title="Firmar (la nota quedará inmutable)",
                        ),
                        rx.el.button(
                            rx.icon("pencil", size=14),
                            on_click=lambda: NotasClinicasState.abrir_editar(n),
                            class_name="p-1 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded cursor-pointer transition",
                            title="Editar",
                        ),
                        rx.el.button(
                            rx.icon("trash-2", size=14),
                            on_click=lambda: NotasClinicasState.eliminar(n["id"]),
                            class_name="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer transition",
                            title="Eliminar",
                        ),
                        class_name="flex items-center gap-1",
                    ),
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="flex items-center justify-between",
        ),
        # Contenido
        rx.el.p(
            n["contenido"],
            class_name="mt-2 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed",
        ),
        # Pie de firma
        rx.cond(
            n["firmada"],
            rx.el.p(
                rx.icon("shield-check", size=12, class_name="mr-1 text-emerald-600"),
                "Firmada por ", n["firmada_por_nombre"], " · ", n["firmada_en"],
                class_name="flex items-center mt-2 pt-2 border-t border-gray-100 text-xs text-emerald-700",
            ),
        ),
        class_name="bg-white rounded-xl border border-gray-100 shadow-sm p-4 hover:shadow-md transition",
    )


def notas_clinicas_page() -> rx.Component:
    return shell(
        _modal_nota(),
        _modal_consentimiento(),
        _modal_receta(),
        page_header(
            "Historia Clínica",
            "Evoluciones, diagnósticos e indicaciones por paciente",
            action=rx.cond(
                NotasClinicasState.paciente_id != 0,
                rx.el.div(
                    # Módulos dentales (D1): solo si el perfil de la clínica los activa.
                    rx.cond(
                        NotasClinicasState.esp_dental,
                        rx.fragment(
                            rx.el.a(
                                rx.icon("smile", size=16),
                                rx.el.span("Odontograma", class_name="ml-1.5"),
                                href="/odontograma?paciente_id=" + NotasClinicasState.paciente_id.to_string(),
                                title="Abrir odontograma del paciente",
                                class_name="inline-flex items-center px-4 py-2 text-sky-700 border border-sky-300 bg-sky-50 text-sm font-medium rounded-lg hover:bg-sky-100 cursor-pointer",
                            ),
                            rx.el.a(
                                rx.icon("clipboard-list", size=16),
                                rx.el.span("Plan de tratamiento", class_name="ml-1.5"),
                                href="/plan-tratamiento?paciente_id=" + NotasClinicasState.paciente_id.to_string(),
                                title="Abrir plan de tratamiento del paciente",
                                class_name="inline-flex items-center px-4 py-2 text-sky-700 border border-sky-300 bg-sky-50 text-sm font-medium rounded-lg hover:bg-sky-100 cursor-pointer",
                            ),
                        ),
                    ),
                    # Módulos estéticos (D1): solo si el perfil de la clínica los activa.
                    rx.cond(
                        NotasClinicasState.esp_estetica,
                        rx.fragment(
                            rx.el.a(
                                rx.icon("images", size=16),
                                rx.el.span("Galería estética", class_name="ml-1.5"),
                                href="/galeria-estetica?paciente_id=" + NotasClinicasState.paciente_id.to_string(),
                                title="Abrir galería antes/después del paciente",
                                class_name="inline-flex items-center px-4 py-2 text-sky-700 border border-sky-300 bg-sky-50 text-sm font-medium rounded-lg hover:bg-sky-100 cursor-pointer",
                            ),
                            rx.el.a(
                                rx.icon("scan-face", size=16),
                                rx.el.span("Mapa estético", class_name="ml-1.5"),
                                href="/mapa-estetico?paciente_id=" + NotasClinicasState.paciente_id.to_string(),
                                title="Abrir mapa facial 3D del paciente",
                                class_name="inline-flex items-center px-4 py-2 text-sky-700 border border-sky-300 bg-sky-50 text-sm font-medium rounded-lg hover:bg-sky-100 cursor-pointer",
                            ),
                        ),
                    ),
                    rx.el.button(
                        rx.icon("plus", size=16),
                        rx.el.span("Nueva nota", class_name="ml-1.5"),
                        on_click=NotasClinicasState.abrir_nueva,
                        data_new_action="1",
                        title="Nueva nota (N)",
                        class_name="inline-flex items-center px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 cursor-pointer shadow-sm",
                    ),
                    class_name="flex items-center gap-2",
                ),
                rx.fragment(),
            ),
        ),
        # Sin paciente seleccionado
        rx.cond(
            NotasClinicasState.paciente_id == 0,
            rx.el.div(
                rx.icon("file-text", size=48, class_name="text-gray-300 mb-4"),
                rx.el.p("No hay paciente seleccionado", class_name="text-gray-500 font-medium"),
                rx.el.p(
                    "Accedé a esta sección desde la ficha de un paciente",
                    class_name="text-sm text-gray-400 mt-1",
                ),
                rx.el.a(
                    rx.icon("users", size=14, class_name="mr-2"),
                    "Ir a Pacientes",
                    href="/pacientes",
                    class_name="flex items-center mt-4 px-4 py-2 bg-sky-600 text-white text-sm rounded-lg hover:bg-sky-700 cursor-pointer",
                ),
                class_name="flex flex-col items-center justify-center py-20 text-center",
            ),
            # Lista de notas
            rx.el.div(
                # Alerta de alergias del paciente (A1)
                rx.cond(
                    NotasClinicasState.paciente_alergias != "",
                    rx.el.div(
                        rx.icon("triangle-alert", size=18, class_name="text-red-600 mr-2 shrink-0 mt-0.5"),
                        rx.el.div(
                            rx.el.p("Alergias del paciente", class_name="text-xs font-bold text-red-700 uppercase tracking-wide"),
                            rx.el.p(
                                NotasClinicasState.paciente_alergias,
                                class_name="text-sm text-red-800 whitespace-pre-wrap",
                            ),
                        ),
                        class_name="flex items-start p-3 mb-4 bg-red-50 border border-red-200 rounded-xl",
                    ),
                ),
                # Archivos del paciente (A2)
                _seccion_adjuntos(),
                rx.cond(
                    NotasClinicasState.total == 0,
                    rx.el.div(
                        rx.icon("clipboard", size=40, class_name="text-gray-300 mb-3"),
                        rx.el.p("Sin notas clínicas", class_name="text-gray-500"),
                        rx.el.p("Creá la primera nota para este paciente", class_name="text-sm text-gray-400"),
                        class_name="flex flex-col items-center py-16 text-center",
                    ),
                    rx.el.div(
                        rx.foreach(NotasClinicasState.notas.to(list[dict]), _fila_nota),
                        class_name="space-y-3",
                    ),
                ),
                # Paginación
                rx.cond(
                    NotasClinicasState.total_pages > 1,
                    rx.el.div(
                        rx.el.button(
                            rx.icon("chevron-left", size=15), "Anterior",
                            on_click=NotasClinicasState.prev_page,
                            disabled=NotasClinicasState.page <= 1,
                            class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 cursor-pointer",
                        ),
                        rx.el.span(
                            NotasClinicasState.page, " / ", NotasClinicasState.total_pages,
                            class_name="text-sm text-gray-500",
                        ),
                        rx.el.button(
                            "Siguiente", rx.icon("chevron-right", size=15),
                            on_click=NotasClinicasState.next_page,
                            disabled=NotasClinicasState.page >= NotasClinicasState.total_pages,
                            class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 cursor-pointer",
                        ),
                        class_name="flex items-center justify-between mt-4",
                    ),
                ),
            ),
        ),
        on_mount=NotasClinicasState.on_mount,
    )
