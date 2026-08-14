from __future__ import annotations

import reflex as rx

from clinica_app.pages.configuracion._helpers import (
    _campo,
    _select,
    _section_title,
    _btn_spinner,
    _alert,
)
from clinica_app.state.configuracion import ConfiguracionState


_ZONAS = [
    ("", "Zona del país (auto)"),
    ("America/Lima", "América/Lima (Perú)"),
    ("America/Argentina/Buenos_Aires", "América/Buenos_Aires (Argentina)"),
    ("America/Bogota", "América/Bogotá (Colombia)"),
    ("America/Santiago", "América/Santiago (Chile)"),
    ("America/Guayaquil", "América/Guayaquil (Ecuador)"),
    ("America/La_Paz", "América/La_Paz (Bolivia)"),
    ("America/Montevideo", "América/Montevideo (Uruguay)"),
    ("America/Asuncion", "América/Asunción (Paraguay)"),
    ("America/Mexico_City", "América/México_City (México)"),
    ("America/Caracas", "América/Caracas (Venezuela)"),
]

_RUBROS = [
    ("", "Seleccionar rubro"),
    ("general", "General (Multi-rubro)"),
    ("clinica_estetica", "Clínica Estética"),
    ("consultorio_medico", "Consultorio Médico"),
    ("odontologia", "Odontología"),
    ("fisioterapia", "Fisioterapia"),
    ("psicologia", "Psicología"),
    ("nutricion", "Nutrición"),
    ("veterinaria", "Veterinaria"),
    ("spa_bienestar", "Spa / Bienestar"),
    ("otro", "Otro"),
]

_PAPELES = [
    ("80mm", "80 mm (default)"),
    ("58mm", "58 mm"),
    ("a4",   "A4"),
]


def _seccion_empresa() -> rx.Component:
    return rx.el.div(
        # ── Datos básicos ──────────────────────────────────────────────────────
        _section_title("DATOS DE MI EMPRESA",
                       "Actualiza la informacion que aparece en recibos y reportes."),
        rx.el.div(
            rx.el.div(
                _campo("Razón Social / Nombre de Empresa *", "text",
                       ConfiguracionState.form_nombre,
                       ConfiguracionState.set_form_nombre, "Ej: Clínica Oscorima S.A.C."),
                _campo("N° de Registro de Empresa", "text",
                       ConfiguracionState.form_documento_fiscal,
                       ConfiguracionState.set_form_documento_fiscal, "RUC / CUIT / NIF"),
                class_name="grid grid-cols-2 gap-4",
            ),
            _campo("Dirección Fiscal", "text",
                   ConfiguracionState.form_direccion_fiscal,
                   ConfiguracionState.set_form_direccion_fiscal, "Ej: Av. Pueyrredón 863"),
            rx.el.div(
                _campo("Teléfono / Celular", "tel",
                       ConfiguracionState.form_telefono,
                       ConfiguracionState.set_form_telefono, "+54 911 6837 6517"),
                _select("Zona Horaria (IANA)", ConfiguracionState.form_zona_horaria,
                        ConfiguracionState.set_form_zona_horaria, _ZONAS),
                class_name="grid grid-cols-2 gap-4",
            ),
            _select("Rubro del Negocio", ConfiguracionState.form_rubro,
                    ConfiguracionState.set_form_rubro, _RUBROS),
            # ── Perfil de especialidad (D1) ────────────────────────────────────
            rx.el.div(
                rx.el.div(
                    rx.icon("stethoscope", size=15, class_name="text-sky-600 mr-2"),
                    rx.el.span("Perfil de especialidad", class_name="text-sm font-semibold text-gray-700"),
                    class_name="flex items-center mb-2",
                ),
                rx.el.p(
                    "El rubro define qué módulos clínicos ve el equipo en la Historia Clínica.",
                    class_name="text-xs text-gray-500 mb-2",
                ),
                rx.el.div(
                    rx.el.span(
                        rx.icon("check", size=12, class_name="mr-1"),
                        "Odontograma + Plan de tratamiento",
                        class_name=rx.cond(
                            ConfiguracionState.perfil_dental_sel,
                            "inline-flex items-center text-xs px-2 py-1 rounded-full bg-green-50 text-green-700 border border-green-200",
                            "inline-flex items-center text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-400 border border-gray-200 line-through",
                        ),
                    ),
                    rx.el.span(
                        rx.icon("check", size=12, class_name="mr-1"),
                        "Galería + Ficha estética",
                        class_name=rx.cond(
                            ConfiguracionState.perfil_estetica_sel,
                            "inline-flex items-center text-xs px-2 py-1 rounded-full bg-green-50 text-green-700 border border-green-200",
                            "inline-flex items-center text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-400 border border-gray-200 line-through",
                        ),
                    ),
                    class_name="flex flex-wrap gap-2 mb-3",
                ),
                rx.el.button(
                    rx.icon("sprout", size=14, class_name="mr-1.5"),
                    "Sembrar catálogo de servicios de la especialidad",
                    on_click=ConfiguracionState.sembrar_catalogo,
                    type="button",
                    class_name="inline-flex items-center px-3 py-2 text-sm text-sky-700 border border-sky-300 rounded-lg hover:bg-sky-50 cursor-pointer",
                ),
                rx.cond(
                    ConfiguracionState.semilla_msg != "",
                    rx.el.p(ConfiguracionState.semilla_msg, class_name="text-xs text-sky-700 mt-2"),
                ),
                class_name="p-4 bg-gray-50 border border-gray-100 rounded-xl",
            ),
            _campo("Mensaje en Recibo/Ticket", "text",
                   ConfiguracionState.form_mensaje_recibo,
                   ConfiguracionState.set_form_mensaje_recibo, "¡GRACIAS POR SU PREFERENCIA!"),
            rx.el.div(
                _select("Papel de Impresion", ConfiguracionState.form_papel_impresion,
                        ConfiguracionState.set_form_papel_impresion, _PAPELES),
                _campo("Ancho de Recibo (opcional)", "number",
                       ConfiguracionState.form_ancho_recibo,
                       ConfiguracionState.set_form_ancho_recibo, "Ej: 42"),
                class_name="grid grid-cols-2 gap-4",
            ),
            class_name="space-y-4",
        ),
        rx.el.p("Estos datos se muestran en recibos y reportes.",
                class_name="text-xs text-gray-400 mt-3"),
        rx.cond(ConfiguracionState.empresa_error   != "", _alert(ConfiguracionState.empresa_error,   "red")),
        rx.cond(ConfiguracionState.empresa_success != "", _alert(ConfiguracionState.empresa_success, "green")),
        rx.el.div(
            _btn_spinner("Guardar Configuracion", "Guardando...",
                         ConfiguracionState.is_saving_empresa,
                         ConfiguracionState.guardar_empresa),
            class_name="mt-4 flex justify-end",
        ),

        # ── Márgenes de Ganancia ───────────────────────────────────────────────
        rx.el.div(
            rx.el.div(
                rx.icon("trending-up", size=16, class_name="text-sky-600 mr-2"),
                rx.el.h3("MARGENES DE GANANCIA",
                         class_name="text-sm font-bold text-gray-700 uppercase tracking-wider"),
                class_name="flex items-center mb-1",
            ),
            rx.el.p("Porcentaje aplicado al precio de compra para calcular el precio de venta sugerido.",
                    class_name="text-xs text-gray-500 mb-4"),
            rx.el.div(
                rx.el.div(
                    _campo("Margen Global de Empresa (%)", "number",
                           ConfiguracionState.form_margen_global,
                           ConfiguracionState.set_form_margen_global),
                    rx.el.p("Se aplica a todas las sucursales que no tengan margen propio.",
                            class_name="text-xs text-gray-400 mt-1"),
                ),
                rx.el.div(
                    rx.el.label("Margen de Esta Sucursal (%) — opcional",
                                class_name="block text-xs font-medium text-gray-400 mb-1"),
                    rx.el.input(type="number", placeholder="Vacío = usa margen de empresa",
                                class_name="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm "
                                           "bg-gray-50 text-gray-400 cursor-not-allowed",
                                disabled=True),
                    rx.el.p("Deja en blanco para heredar el margen global de empresa.",
                            class_name="text-xs text-gray-400 mt-1"),
                ),
                class_name="grid grid-cols-2 gap-4",
            ),
            rx.el.div(
                rx.icon("trending-up", size=14, class_name="text-green-600"),
                rx.el.span("Margen efectivo de esta sucursal: ",
                           class_name="text-sm text-gray-600"),
                rx.el.span(ConfiguracionState.form_margen_global + "%",
                           class_name="text-sm font-bold text-green-600 ml-1"),
                rx.el.span(" — precio de compra $10 genera precio de venta ",
                           class_name="text-xs text-gray-400 ml-2"),
                rx.el.span(
                    "$", ConfiguracionState.precio_ejemplo_venta,
                    class_name="text-xs font-semibold text-green-700",
                ),
                class_name="flex items-center mt-3 p-3 bg-green-50 rounded-lg border border-green-100",
            ),
            rx.cond(ConfiguracionState.margenes_error   != "", _alert(ConfiguracionState.margenes_error,   "red")),
            rx.cond(ConfiguracionState.margenes_success != "", _alert(ConfiguracionState.margenes_success, "green")),
            rx.el.div(
                _btn_spinner("Guardar Margenes", "Guardando...",
                             ConfiguracionState.is_saving_margenes,
                             ConfiguracionState.guardar_margenes),
                class_name="mt-4",
            ),
            class_name="mt-8 pt-6 border-t border-gray-100",
        ),

        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6",
    )
