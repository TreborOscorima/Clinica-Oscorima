from __future__ import annotations

import reflex as rx

from clinica_app.components.badge import estado_badge
from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.pacientes import PacientesState


def _panel_detalle() -> rx.Component:
    """Slide-over lateral con historial del paciente."""
    return rx.cond(
        PacientesState.panel_detalle,
        rx.el.div(
            # Overlay
            rx.el.div(
                class_name="fixed inset-0 bg-black/30 z-40",
                on_click=PacientesState.cerrar_detalle,
            ),
            # Panel lateral
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.el.h2(
                            PacientesState.paciente_sel["nombre"],
                            class_name="text-lg font-semibold text-gray-900",
                        ),
                        rx.el.p(
                            PacientesState.paciente_sel["documento"],
                            class_name="text-sm text-gray-500",
                        ),
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=PacientesState.cerrar_detalle,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-start justify-between mb-6",
                ),
                # Alerta de alergias (destacada)
                rx.cond(
                    PacientesState.paciente_sel["alergias"],
                    rx.el.div(
                        rx.icon("triangle-alert", size=16, class_name="text-red-600 mr-2 shrink-0 mt-0.5"),
                        rx.el.div(
                            rx.el.p("Alergias", class_name="text-xs font-bold text-red-700 uppercase tracking-wide"),
                            rx.el.p(
                                PacientesState.paciente_sel["alergias"],
                                class_name="text-sm text-red-800 whitespace-pre-wrap",
                            ),
                        ),
                        class_name="flex items-start p-3 mb-4 bg-red-50 border border-red-200 rounded-xl",
                    ),
                ),
                # Ficha médica
                rx.cond(
                    PacientesState.paciente_sel["grupo_sanguineo"]
                    | PacientesState.paciente_sel["antecedentes"]
                    | PacientesState.paciente_sel["medicacion"]
                    | PacientesState.paciente_sel["habitos"],
                    rx.el.div(
                        rx.el.p("Ficha médica", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2"),
                        _ficha_row("Grupo sanguíneo", PacientesState.paciente_sel["grupo_sanguineo"]),
                        _ficha_row("Antecedentes",    PacientesState.paciente_sel["antecedentes"]),
                        _ficha_row("Medicación",      PacientesState.paciente_sel["medicacion"]),
                        _ficha_row("Hábitos",         PacientesState.paciente_sel["habitos"]),
                        class_name="mb-6 p-3 bg-rose-50/50 border border-rose-100 rounded-xl space-y-2",
                    ),
                ),
                # Datos rápidos
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Email", class_name="text-xs text-gray-500 uppercase"),
                        rx.el.p(PacientesState.paciente_sel["email"], class_name="text-sm text-gray-700"),
                        class_name="flex flex-col",
                    ),
                    rx.el.div(
                        rx.el.span("Teléfono", class_name="text-xs text-gray-500 uppercase"),
                        rx.el.p(PacientesState.paciente_sel["telefono"], class_name="text-sm text-gray-700"),
                        class_name="flex flex-col",
                    ),
                    rx.el.div(
                        rx.el.span("Emergencia", class_name="text-xs text-gray-500 uppercase"),
                        rx.el.p(PacientesState.paciente_sel["contacto_emergencia"], class_name="text-sm text-gray-700"),
                        class_name="flex flex-col",
                    ),
                    class_name="grid grid-cols-3 gap-3 mb-6 p-3 bg-gray-50 rounded-xl",
                ),
                # Turnos recientes
                rx.el.div(
                    rx.el.p("Últimos turnos", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2"),
                    rx.cond(
                        PacientesState.historial_turnos.length() == 0,
                        rx.el.p("Sin turnos", class_name="text-sm text-gray-400 italic"),
                        rx.el.div(
                            rx.foreach(
                                PacientesState.historial_turnos,
                                lambda t: rx.el.div(
                                    rx.el.div(
                                        rx.el.span(t["fecha_hora"], class_name="text-xs font-mono text-gray-500"),
                                        estado_badge(t["estado"]),
                                        class_name="flex items-center justify-between",
                                    ),
                                    rx.el.p(
                                        t["servicio_nombre"], " · ", t["profesional_nombre"],
                                        class_name="text-xs text-gray-500 mt-0.5",
                                    ),
                                    class_name="py-2 border-b border-gray-100 last:border-0",
                                ),
                            ),
                        ),
                    ),
                    class_name="mb-6",
                ),
                # Comprobantes
                rx.el.div(
                    rx.el.p("Últimos comprobantes", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2"),
                    rx.cond(
                        PacientesState.historial_comprobantes.length() == 0,
                        rx.el.p("Sin comprobantes", class_name="text-sm text-gray-400 italic"),
                        rx.el.div(
                            rx.foreach(
                                PacientesState.historial_comprobantes,
                                lambda c: rx.el.div(
                                    rx.el.div(
                                        rx.el.span(c["numero"], class_name="text-xs font-mono text-gray-500"),
                                        rx.el.div(
                                            rx.el.span(c["fecha"], class_name="text-xs text-gray-500"),
                                            rx.el.span(
                                                "$ ", c["total"],
                                                class_name="text-xs font-semibold text-green-700",
                                            ),
                                            class_name="flex items-center gap-3",
                                        ),
                                        class_name="flex-1 flex items-center justify-between",
                                    ),
                                    rx.el.a(
                                        rx.icon("file-down", size=14),
                                        href=f"/api/recibo/pdf?comp_id={c['id']}&clinica_id={PacientesState.clinica_id}&token={PacientesState.download_token}",
                                        target="_blank",
                                        title="Descargar PDF",
                                        class_name="p-1 text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 rounded cursor-pointer shrink-0",
                                    ),
                                    class_name="flex items-center gap-2 py-2 border-b border-gray-100 last:border-0",
                                ),
                            ),
                        ),
                    ),
                    class_name="mb-6",
                ),
                # Acceso rápido historia clínica
                rx.el.div(
                    rx.el.a(
                        rx.icon("clipboard-list", size=15, class_name="mr-2"),
                        "Ver historia clínica completa",
                        href=f"/historia-clinica?paciente_id={PacientesState.paciente_sel['id']}",
                        class_name="flex items-center w-full px-4 py-2.5 bg-sky-50 text-sky-700 text-sm font-medium rounded-lg hover:bg-sky-100 transition cursor-pointer border border-sky-200",
                    ),
                    class_name="mb-6",
                ),
                # Deudas activas
                rx.cond(
                    PacientesState.historial_deudas.length() > 0,
                    rx.el.div(
                        rx.el.p("Deudas activas", class_name="text-xs font-semibold text-red-500 uppercase tracking-wide mb-2"),
                        rx.el.div(
                            rx.foreach(
                                PacientesState.historial_deudas,
                                lambda d: rx.el.div(
                                    rx.el.span(
                                        rx.el.span("Estado: ", class_name="text-gray-500"),
                                        d["estado"],
                                        class_name="text-xs capitalize",
                                    ),
                                    rx.el.span(
                                        "Saldo: $ ", d["saldo"],
                                        class_name="text-xs font-semibold text-red-600",
                                    ),
                                    class_name="flex items-center justify-between py-2 border-b border-red-50 last:border-0",
                                ),
                            ),
                        ),
                        class_name="p-3 bg-red-50 rounded-xl",
                    ),
                ),
                class_name="absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl p-6 overflow-y-auto z-50",
            ),
            class_name="fixed inset-0 z-40 flex justify-end",
        ),
    )


def _modal_paciente() -> rx.Component:
    titulo = rx.cond(PacientesState.editando_id, "Editar paciente", "Nuevo paciente")
    return rx.cond(
        PacientesState.modal_abierto,
        rx.el.div(
            # Overlay
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=PacientesState.cerrar_modal,
            ),
            # Panel
            rx.el.div(
                rx.el.div(
                    rx.el.h2(titulo, class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=PacientesState.cerrar_modal,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer",
                    ),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                # Campos del formulario
                rx.el.div(
                    _campo("Nombre *",          "text",  PacientesState.form_nombre,    PacientesState.set_form_nombre),
                    _campo("Documento / DNI",   "text",  PacientesState.form_documento, PacientesState.set_form_documento),
                    _campo("Email",             "email", PacientesState.form_email,     PacientesState.set_form_email),
                    _campo("Teléfono",          "text",  PacientesState.form_telefono,  PacientesState.set_form_telefono),
                    _campo("Dirección",         "text",  PacientesState.form_direccion, PacientesState.set_form_direccion),
                    _campo("Fecha nacimiento",  "date",  PacientesState.form_nacimiento, PacientesState.set_form_nacimiento),
                    _campo("Contacto emergencia", "text", PacientesState.form_emergencia, PacientesState.set_form_emergencia),
                    # ── Ficha médica (A1) ──
                    rx.el.div(
                        rx.icon("stethoscope", size=14, class_name="text-rose-500 mr-1.5"),
                        rx.el.span("Ficha médica", class_name="text-xs font-semibold text-gray-500 uppercase tracking-wide"),
                        class_name="flex items-center pt-2 mt-2 border-t border-gray-100",
                    ),
                    _campo("Grupo sanguíneo",   "text",  PacientesState.form_grupo,       PacientesState.set_form_grupo),
                    _campo_area("Alergias",     PacientesState.form_alergias,     PacientesState.set_form_alergias,
                                "Ej: Penicilina, látex, lidocaína…"),
                    _campo_area("Antecedentes", PacientesState.form_antecedentes, PacientesState.set_form_antecedentes,
                                "Personales y familiares relevantes"),
                    _campo_area("Medicación habitual", PacientesState.form_medicacion, PacientesState.set_form_medicacion,
                                "Medicamentos que toma actualmente"),
                    _campo_area("Hábitos",      PacientesState.form_habitos,      PacientesState.set_form_habitos,
                                "Ej: tabaquismo, alcohol…"),
                    class_name="space-y-4 max-h-[60vh] overflow-y-auto pr-1",
                ),
                rx.cond(
                    PacientesState.form_error != "",
                    rx.el.p(
                        PacientesState.form_error,
                        class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded",
                    ),
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=PacientesState.cerrar_modal,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition cursor-pointer",
                    ),
                    rx.el.button(
                        rx.cond(
                            PacientesState.is_saving,
                            rx.el.div(
                                rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                "Guardando...",
                                class_name="flex items-center",
                            ),
                            "Guardar",
                        ),
                        on_click=PacientesState.guardar,
                        disabled=PacientesState.is_saving,
                        data_modal_submit="1",
                        title="Guardar (Ctrl+Enter)",
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 transition cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _campo(label: str, tipo: str, value, on_change) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.input(
            type=tipo,
            default_value=value,
            on_change=on_change,
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
        ),
    )


def _campo_area(label: str, value, on_change, placeholder: str = "") -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.textarea(
            default_value=value,
            on_change=on_change,
            placeholder=placeholder,
            rows=2,
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none",
        ),
    )


def _ficha_row(label: str, value) -> rx.Component:
    """Fila de la ficha médica; se muestra solo si hay valor."""
    return rx.cond(
        value,
        rx.el.div(
            rx.el.span(label, class_name="text-xs text-gray-500 uppercase"),
            rx.el.p(value, class_name="text-sm text-gray-700 whitespace-pre-wrap"),
            class_name="flex flex-col",
        ),
    )


def _fila_paciente(p: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(p["nombre"], class_name="px-4 py-3 text-sm font-medium text-gray-900"),
        rx.el.td(rx.cond(p["documento"], p["documento"], "—"), class_name="px-4 py-3 text-sm text-gray-600"),
        rx.el.td(rx.cond(p["email"], p["email"], "—"), class_name="px-4 py-3 text-sm text-gray-600"),
        rx.el.td(rx.cond(p["telefono"], p["telefono"], "—"), class_name="px-4 py-3 text-sm text-gray-600"),
        rx.el.td(
            rx.el.span(
                rx.cond(p["edad"], rx.el.span(p["edad"], " años"), "—"),
                class_name="text-sm text-gray-600",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("eye", size=15),
                    on_click=lambda: PacientesState.abrir_detalle(p),
                    class_name="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition cursor-pointer",
                    title="Ver detalle",
                ),
                rx.el.button(
                    rx.icon("pencil", size=15),
                    on_click=lambda: PacientesState.abrir_editar(p),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded transition cursor-pointer",
                    title="Editar",
                ),
                rx.el.button(
                    rx.icon("trash-2", size=15),
                    on_click=lambda: PacientesState.eliminar(p["id"]),
                    class_name="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition cursor-pointer",
                    title="Eliminar",
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50 transition-colors",
    )


def pacientes_page() -> rx.Component:
    return shell(
        _modal_paciente(),
        _panel_detalle(),
        page_header(
            "Pacientes",
            "Gestioná la base de datos de pacientes",
            action=rx.el.button(
                rx.icon("plus", size=16),
                rx.el.span("Nuevo paciente", class_name="ml-1.5"),
                on_click=PacientesState.abrir_nuevo,
                data_new_action="1",
                title="Nuevo paciente (N)",
                class_name="inline-flex items-center px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded-lg hover:bg-sky-700 transition cursor-pointer shadow-sm",
            ),
        ),
        # Buscador
        rx.el.div(
            rx.el.div(
                rx.icon("search", size=16, class_name="text-gray-400"),
                
                rx.el.input(
                    type="text",
                    placeholder="Buscar por nombre o documento...",
                    on_change=PacientesState.set_busqueda,
                    on_key_down=PacientesState.handle_busqueda_key,
                    data_search_input="1",
                    title="Buscar (/)",
                    class_name="w-full outline-none text-sm text-gray-700 placeholder-gray-400 ml-2",
                ),
                class_name="flex items-center px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-sky-500",
            ),
            class_name="mb-5 max-w-md",
        ),
        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Nombre",    class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Documento", class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Email",     class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Teléfono",  class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Edad",      class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                            rx.el.th("Acciones",  class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"),
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(
                        rx.cond(
                            PacientesState.pacientes,
                            rx.foreach(PacientesState.pacientes.to(list[dict]), _fila_paciente),
                            rx.el.tr(rx.el.td(
                                rx.el.div(
                                    rx.icon("users", size=28, class_name="text-gray-300 mx-auto mb-2"),
                                    rx.el.p("No se encontraron pacientes", class_name="text-sm text-gray-500"),
                                    class_name="py-10 text-center",
                                ),
                                col_span=6,
                            )),
                        )
                    ),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto",
            ),
            # Paginación
            rx.el.div(
                rx.el.button(
                    rx.icon("chevron-left", size=15), "Anterior",
                    on_click=PacientesState.prev_page,
                    disabled=PacientesState.page <= 1,
                    class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition",
                ),
                rx.el.span(
                    rx.el.span("Página "),
                    PacientesState.page,
                    rx.el.span(" de "),
                    PacientesState.total_pages,
                    class_name="text-sm text-gray-500",
                ),
                rx.el.button(
                    "Siguiente", rx.icon("chevron-right", size=15),
                    on_click=PacientesState.next_page,
                    disabled=PacientesState.page >= PacientesState.total_pages,
                    class_name="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition",
                ),
                class_name="flex items-center justify-between px-4 py-3 border-t border-gray-100",
            ),
            class_name="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden",
        ),
        on_mount=PacientesState.on_mount,
    )
