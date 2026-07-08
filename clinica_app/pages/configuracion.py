from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.configuracion import ConfiguracionState


# ══════════════════════════════════════════════════════════════════
# HELPERS GLOBALES
# ══════════════════════════════════════════════════════════════════

def _campo(label: str, tipo: str, value, on_change, placeholder: str = "") -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-xs font-medium text-gray-600 mb-1"),
        
        rx.el.input(
            type=tipo, default_value=value, on_change=on_change, placeholder=placeholder,
            class_name="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm "
                       "focus:outline-none focus:ring-2 focus:ring-sky-500 transition bg-white",
        ),
    )


def _select(label: str, value, on_change, options: list[tuple[str, str]]) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-xs font-medium text-gray-600 mb-1"),
        rx.el.select(
            *[rx.el.option(lbl, value=val) for val, lbl in options],
            default_value=value, on_change=on_change,
            class_name="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm "
                       "focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white",
        ),
    )


def _campo_pw(label: str, value, on_change) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-xs font-medium text-gray-600 mb-1"),
        
        rx.el.input(
            type="password", default_value=value, on_change=on_change, placeholder="••••••••",
            class_name="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm "
                       "focus:outline-none focus:ring-2 focus:ring-sky-500 transition",
        ),
    )


def _btn(label: str, on_click, color: str = "sky", size: str = "md") -> rx.Component:
    px = "px-4 py-2" if size == "md" else "px-3 py-1.5"
    return rx.el.button(
        label, on_click=on_click,
        class_name=f"{px} text-sm font-medium bg-{color}-600 text-white rounded-lg "
                   f"hover:bg-{color}-700 transition cursor-pointer",
    )


def _btn_spinner(label: str, loading_label: str, is_loading, on_click, **kwargs) -> rx.Component:
    return rx.el.button(
        rx.cond(
            is_loading,
            rx.el.div(
                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                loading_label, class_name="flex items-center",
            ),
            label,
        ),
        on_click=on_click, disabled=is_loading,
        class_name="px-4 py-2 text-sm bg-sky-600 text-white font-medium rounded-lg "
                   "hover:bg-sky-700 disabled:bg-sky-400 disabled:cursor-not-allowed transition cursor-pointer",
        **kwargs,
    )


def _alert(msg, color: str = "green") -> rx.Component:
    icon = "circle-check" if color == "green" else "circle-alert"
    return rx.el.div(
        rx.icon(icon, size=14, class_name=f"shrink-0 text-{color}-600"),
        rx.el.span(msg, class_name=f"text-sm text-{color}-700 ml-2"),
        class_name=f"flex items-center mt-3 px-3 py-2 rounded-lg bg-{color}-50 border border-{color}-200",
    )


def _toggle_switch(value: bool, on_click) -> rx.Component:
    return rx.el.button(
        rx.el.div(
            rx.el.div(
                class_name=rx.cond(
                    value,
                    "absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all",
                    "absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all",
                ),
            ),
            class_name=rx.cond(
                value,
                "relative w-9 h-5 bg-sky-600 rounded-full transition-colors",
                "relative w-9 h-5 bg-gray-300 rounded-full transition-colors",
            ),
        ),
        on_click=on_click,
        class_name="cursor-pointer focus:outline-none",
    )


def _section_title(title: str, subtitle: str) -> rx.Component:
    return rx.el.div(
        rx.el.h2(title, class_name="text-sm font-bold text-gray-700 uppercase tracking-wider"),
        rx.el.p(subtitle, class_name="text-xs text-gray-500 mt-0.5"),
        class_name="mb-5",
    )


# ══════════════════════════════════════════════════════════════════
# NAVEGACIÓN LATERAL IZQUIERDA
# ══════════════════════════════════════════════════════════════════

def _sub_nav() -> rx.Component:
    def _item(label: str, tab: str, icon: str) -> rx.Component:
        is_active = ConfiguracionState.tab_activo == tab
        return rx.el.button(
            rx.el.div(
                rx.icon(icon, size=15, class_name=rx.cond(is_active, "text-sky-600", "text-gray-400")),
                rx.el.span(label, class_name=rx.cond(is_active, "text-sky-700 font-medium", "text-gray-600")),
                class_name="flex items-center gap-2.5",
            ),
            on_click=lambda: ConfiguracionState.set_tab(tab),
            class_name=rx.cond(
                is_active,
                "w-full text-left px-3 py-2.5 rounded-lg bg-sky-50 border-l-2 border-sky-500 cursor-pointer",
                "w-full text-left px-3 py-2.5 rounded-lg text-sm hover:bg-gray-50 cursor-pointer transition",
            ),
        )

    return rx.el.div(
        _item("Datos de Empresa",    "empresa",    "building-2"),
        _item("Sucursales",          "sucursales", "map-pin"),
        _item("Gestion de Usuarios", "usuarios",   "users"),
        _item("Selector de Monedas", "monedas",    "circle-dollar-sign"),
        _item("Unidades de Medida",  "unidades",   "ruler"),
        _item("Metodos de Pago",     "pagos",      "credit-card"),
        _item("Impuestos",           "impuestos",  "percent"),
        class_name="w-52 shrink-0 bg-white rounded-xl border border-gray-100 shadow-sm p-2 space-y-0.5 self-start sticky top-4",
    )


# ══════════════════════════════════════════════════════════════════
# MODALES
# ══════════════════════════════════════════════════════════════════

def _modal_nuevo_usuario() -> rx.Component:
    return rx.cond(
        ConfiguracionState.modal_usuario,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40",
                      on_click=ConfiguracionState.cerrar_modal_usuario),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(rx.icon("user-plus", size=18, class_name="text-sky-600"),
                                  class_name="p-2 bg-sky-100 rounded-lg"),
                        rx.el.h2("Nuevo usuario",
                                 class_name="text-lg font-semibold text-gray-900 ml-3"),
                        class_name="flex items-center",
                    ),
                    rx.el.button(rx.icon("x", size=18), on_click=ConfiguracionState.cerrar_modal_usuario,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                rx.el.div(
                    _campo("Nombre completo *", "text", ConfiguracionState.form_u_nombre,
                           ConfiguracionState.set_form_u_nombre, "Ej: Ana García"),
                    _campo("Email *", "email", ConfiguracionState.form_u_email,
                           ConfiguracionState.set_form_u_email, "usuario@clinica.com"),
                    _select("Rol *", ConfiguracionState.form_u_rol, ConfiguracionState.set_form_u_rol,
                            [("recepcionista", "Recepcionista"), ("profesional", "Profesional"),
                             ("administracion", "Administrador"), ("contador", "Contador")]),
                    # Acceso a sucursales (solo para roles no-admin con múltiples sedes)
                    rx.cond(
                        (ConfiguracionState.form_u_rol != "administracion") &
                        (ConfiguracionState.sedes_form.length() > 1),
                        rx.el.div(
                            rx.el.label(
                                "Acceso a sucursales",
                                class_name="block text-xs font-medium text-gray-600 mb-2",
                            ),
                            rx.el.p(
                                "Sin selección = solo accede a la sucursal principal",
                                class_name="text-xs text-gray-400 mb-2",
                            ),
                            rx.foreach(
                                ConfiguracionState.sedes_form,
                                lambda sede: rx.el.label(
                                    rx.el.input(
                                        type="checkbox",
                                        checked=ConfiguracionState.form_u_sede_ids.contains(sede["id"]),
                                        on_change=lambda _: ConfiguracionState.toggle_u_sede(sede["id"]),
                                        class_name="mr-2 accent-sky-600",
                                    ),
                                    sede["nombre"],
                                    class_name="flex items-center text-sm text-gray-700 cursor-pointer py-1",
                                ),
                            ),
                            class_name="border border-gray-200 rounded-lg px-3 py-2",
                        ),
                    ),
                    _campo_pw("Contraseña *",         ConfiguracionState.form_u_password,
                              ConfiguracionState.set_form_u_password),
                    _campo_pw("Confirmar contraseña *", ConfiguracionState.form_u_password2,
                              ConfiguracionState.set_form_u_password2),
                    class_name="space-y-4",
                ),
                rx.cond(ConfiguracionState.form_u_error != "",
                        _alert(ConfiguracionState.form_u_error, "red")),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=ConfiguracionState.cerrar_modal_usuario,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 "
                                            "rounded-lg hover:bg-gray-50 transition cursor-pointer"),
                    _btn_spinner("Crear usuario", "Creando...",
                                 ConfiguracionState.is_saving_usuario,
                                 ConfiguracionState.guardar_usuario,
                                 data_modal_submit="1",
                                 title="Crear usuario (Ctrl+Enter)"),
                    class_name="flex gap-3 justify-end mt-5",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_password() -> rx.Component:
    return rx.cond(
        ConfiguracionState.modal_password,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40",
                      on_click=ConfiguracionState.cerrar_modal_password),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(rx.icon("key-round", size=18, class_name="text-sky-600"),
                                  class_name="p-2 bg-sky-100 rounded-lg"),
                        rx.el.div(
                            rx.el.h2("Cambiar contraseña",
                                     class_name="text-lg font-semibold text-gray-900"),
                            rx.el.p(ConfiguracionState.pw_user_nombre,
                                    class_name="text-sm text-gray-500"),
                            class_name="ml-3",
                        ),
                        class_name="flex items-center",
                    ),
                    rx.el.button(rx.icon("x", size=18), on_click=ConfiguracionState.cerrar_modal_password,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                rx.el.div(
                    _campo_pw("Nueva contraseña *",      ConfiguracionState.form_pw_nueva,
                              ConfiguracionState.set_form_pw_nueva),
                    _campo_pw("Confirmar contraseña *",  ConfiguracionState.form_pw_nueva2,
                              ConfiguracionState.set_form_pw_nueva2),
                    class_name="space-y-4",
                ),
                rx.cond(ConfiguracionState.form_pw_error   != "", _alert(ConfiguracionState.form_pw_error,   "red")),
                rx.cond(ConfiguracionState.form_pw_success != "", _alert(ConfiguracionState.form_pw_success, "green")),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=ConfiguracionState.cerrar_modal_password,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 "
                                            "rounded-lg hover:bg-gray-50 transition cursor-pointer"),
                    _btn_spinner("Guardar", "Guardando...",
                                 ConfiguracionState.is_saving_pw,
                                 ConfiguracionState.guardar_password,
                                 data_modal_submit="1",
                                 title="Guardar contraseña (Ctrl+Enter)"),
                    class_name="flex gap-3 justify-end mt-5",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_sede() -> rx.Component:
    return rx.cond(
        ConfiguracionState.modal_sede,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40",
                      on_click=ConfiguracionState.cerrar_modal_sede),
            rx.el.div(
                rx.el.div(
                    rx.el.h2(
                        rx.cond(ConfiguracionState.sede_editar_id != 0, "Editar sucursal", "Nueva sucursal"),
                        class_name="text-lg font-semibold text-gray-900",
                    ),
                    rx.el.button(rx.icon("x", size=18), on_click=ConfiguracionState.cerrar_modal_sede,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                rx.el.div(
                    _campo("Nombre *",    "text",  ConfiguracionState.form_sede_nombre,
                           ConfiguracionState.set_form_sede_nombre, "Ej: Casa Matriz, Sucursal Centro"),
                    _campo("Dirección",   "text",  ConfiguracionState.form_sede_dir,
                           ConfiguracionState.set_form_sede_dir,    "Ej: Av. Principal 123"),
                    _campo("Teléfono",    "tel",   ConfiguracionState.form_sede_tel,
                           ConfiguracionState.set_form_sede_tel),
                    _campo("Email",       "email", ConfiguracionState.form_sede_email,
                           ConfiguracionState.set_form_sede_email),
                    rx.el.div(
                        rx.el.input(type="checkbox", checked=ConfiguracionState.form_sede_principal,
                                    on_change=ConfiguracionState.set_form_sede_principal,
                                    class_name="mr-2 cursor-pointer"),
                        rx.el.label("Marcar como sede principal",
                                    class_name="text-sm text-gray-700 cursor-pointer"),
                        class_name="flex items-center",
                    ),
                    class_name="space-y-4",
                ),
                rx.cond(ConfiguracionState.form_sede_error != "",
                        rx.el.p(ConfiguracionState.form_sede_error,
                                class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded")),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=ConfiguracionState.cerrar_modal_sede,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 "
                                            "rounded-lg hover:bg-gray-50 cursor-pointer"),
                    rx.el.button(
                        rx.cond(ConfiguracionState.is_saving_sede,
                                rx.el.div(rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                                          "Guardando…", class_name="flex items-center"),
                                "Guardar"),
                        on_click=ConfiguracionState.guardar_sede,
                        disabled=ConfiguracionState.is_saving_sede,
                        data_modal_submit="1",
                        title="Guardar (Ctrl+Enter)",
                        class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg "
                                   "hover:bg-sky-700 disabled:bg-sky-400 cursor-pointer",
                    ),
                    class_name="flex gap-3 justify-end mt-5",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


def _modal_impuesto() -> rx.Component:
    return rx.cond(
        ConfiguracionState.modal_impuesto,
        rx.el.div(
            rx.el.div(class_name="fixed inset-0 bg-black/40 z-40",
                      on_click=ConfiguracionState.cerrar_modal_impuesto),
            rx.el.div(
                rx.el.div(
                    rx.el.h2("Nueva tasa de impuesto",
                             class_name="text-lg font-semibold text-gray-900"),
                    rx.el.button(rx.icon("x", size=18), on_click=ConfiguracionState.cerrar_modal_impuesto,
                                 class_name="text-gray-400 hover:text-gray-600 cursor-pointer"),
                    class_name="flex items-center justify-between pb-4 mb-5 border-b border-gray-100",
                ),
                rx.el.div(
                    _select("Tipo de impuesto", ConfiguracionState.form_it_tipo,
                            ConfiguracionState.set_form_it_tipo,
                            [("IVA", "IVA"), ("IGV", "IGV"), ("ISC", "ISC"), ("Otro", "Otro")]),
                    _campo("Nombre de la tasa *", "text", ConfiguracionState.form_it_nombre,
                           ConfiguracionState.set_form_it_nombre, "Ej: Estándar, Reducida"),
                    _campo("Porcentaje (%)", "number", ConfiguracionState.form_it_porcentaje,
                           ConfiguracionState.set_form_it_porcentaje, "Ej: 21"),
                    rx.el.div(
                        rx.el.input(type="checkbox", checked=ConfiguracionState.form_it_es_default,
                                    on_change=ConfiguracionState.set_form_it_es_default,
                                    class_name="mr-2 cursor-pointer"),
                        rx.el.label("Establecer como tasa por defecto",
                                    class_name="text-sm text-gray-700"),
                        class_name="flex items-center",
                    ),
                    class_name="space-y-4",
                ),
                rx.cond(ConfiguracionState.it_error != "",
                        _alert(ConfiguracionState.it_error, "red")),
                rx.el.div(
                    rx.el.button("Cancelar", on_click=ConfiguracionState.cerrar_modal_impuesto,
                                 class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 "
                                            "rounded-lg hover:bg-gray-50 transition cursor-pointer"),
                    _btn_spinner("Guardar tasa", "Guardando...",
                                 ConfiguracionState.is_saving_it,
                                 ConfiguracionState.guardar_impuesto,
                                 data_modal_submit="1",
                                 title="Guardar tasa (Ctrl+Enter)"),
                    class_name="flex gap-3 justify-end mt-5",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 1: DATOS DE EMPRESA
# ══════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 2: SUCURSALES
# ══════════════════════════════════════════════════════════════════

def _fila_sede(s: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.div(
                rx.el.p(s["nombre"], class_name="text-sm font-medium text-gray-800"),
                rx.cond(
                    s["es_principal"],
                    rx.el.span("Principal",
                               class_name="ml-0 inline-flex items-center px-1.5 py-0.5 rounded text-xs "
                                          "font-medium bg-sky-100 text-sky-700"),
                ),
                class_name="flex items-center gap-2",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.cond(s["direccion"] != "", s["direccion"], rx.el.span("—", class_name="text-gray-400")),
            class_name="px-4 py-3 text-sm text-gray-600",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", size=14),
                    on_click=lambda: ConfiguracionState.abrir_editar_sede(s),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded cursor-pointer transition",
                    title="Editar",
                ),
                rx.el.button(
                    rx.icon("trash-2", size=14),
                    on_click=lambda: ConfiguracionState.eliminar_sede(s["id"]),
                    class_name="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer transition",
                    title="Eliminar",
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50 transition-colors",
    )


def _seccion_sucursales() -> rx.Component:
    return rx.el.div(
        _section_title("SUCURSALES", "Crea sucursales y asigna usuarios por empresa."),
        # Formulario rápido de creación
        rx.el.div(
            _campo("Nombre de Sucursal", "text",
                   ConfiguracionState.form_sede_nombre,
                   ConfiguracionState.set_form_sede_nombre, "Ej: Casa Matriz, Sucursal Centro"),
            _campo("Dirección", "text",
                   ConfiguracionState.form_sede_dir,
                   ConfiguracionState.set_form_sede_dir, "Ej: Av. Principal 123"),
            rx.el.button(
                "Crear",
                on_click=ConfiguracionState.guardar_sede,
                class_name="self-end px-5 py-2 bg-emerald-600 text-white text-sm font-medium "
                           "rounded-lg hover:bg-emerald-700 transition cursor-pointer",
            ),
            class_name="grid grid-cols-3 gap-3 items-end mb-6",
        ),
        # Tabla de sucursales
        rx.cond(
            ConfiguracionState.sedes.length() == 0,
            rx.el.div(
                rx.icon("map-pin", size=32, class_name="text-gray-300 mb-2"),
                rx.el.p("Sin sucursales registradas", class_name="text-sm text-gray-400"),
                class_name="flex flex-col items-center py-12 bg-gray-50 rounded-xl",
            ),
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            *[rx.el.th(h, class_name="px-4 py-3 text-left text-xs font-semibold "
                                                     "text-gray-500 uppercase tracking-wide")
                              for h in ["Sucursal", "Dirección", "Acciones"]],
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(
                        rx.foreach(ConfiguracionState.sedes.to(list[dict]), _fila_sede),
                    ),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto rounded-xl border border-gray-100 shadow-sm",
            ),
        ),
        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6",
    )


# ══════════════════════════════════════════════════════════════════
# MODAL: PERMISOS DE ROL
# ══════════════════════════════════════════════════════════════════

def _modal_permisos_rol() -> rx.Component:
    def _fila_permiso(m: dict) -> rx.Component:
        return rx.el.div(
            rx.el.span(m["label"], class_name="text-sm text-gray-700 flex-1 min-w-0"),
            rx.el.div(
                rx.el.span("Ver", class_name="text-xs text-gray-500 w-8 text-right"),
                _toggle_switch(m["can_read"],
                               lambda: ConfiguracionState.toggle_permiso_rol(m["module"], "read")),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.el.span("Editar", class_name="text-xs text-gray-500 w-10 text-right"),
                _toggle_switch(m["can_write"],
                               lambda: ConfiguracionState.toggle_permiso_rol(m["module"], "write")),
                class_name="flex items-center gap-2",
            ),
            class_name="flex items-center gap-4 py-2.5 border-b border-gray-100 last:border-0",
        )

    return rx.cond(
        ConfiguracionState.modal_permisos,
        rx.el.div(
            rx.el.div(
                # Header
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.icon("shield", size=16, class_name="text-indigo-600"),
                            class_name="p-1.5 bg-indigo-50 rounded-lg",
                        ),
                        rx.el.div(
                            rx.el.h3("Permisos de Acceso",
                                     class_name="text-base font-semibold text-gray-900"),
                            rx.el.p(
                                "Rol: " + ConfiguracionState.permisos_rol_label +
                                " · Aplica a todos los usuarios con este rol",
                                class_name="text-xs text-gray-500 mt-0.5",
                            ),
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    rx.el.button(
                        rx.icon("x", size=16),
                        on_click=ConfiguracionState.cerrar_modal_permisos,
                        class_name="text-gray-400 hover:text-gray-700 cursor-pointer p-1",
                    ),
                    class_name="flex items-center justify-between p-5 border-b border-gray-100",
                ),
                # Cabecera columnas
                rx.el.div(
                    rx.el.span("Módulo",
                               class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide flex-1"),
                    rx.el.span("Ver",
                               class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide w-20 text-center"),
                    rx.el.span("Editar",
                               class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide w-24 text-center"),
                    class_name="flex items-center gap-4 px-5 pt-3 pb-1",
                ),
                # Filas de módulos
                rx.el.div(
                    rx.foreach(
                        ConfiguracionState.permisos_rol_modulos.to(list[dict]),
                        _fila_permiso,
                    ),
                    class_name="px-5 overflow-y-auto max-h-80",
                ),
                # Footer
                rx.el.div(
                    rx.el.p("Los cambios se guardan automáticamente.",
                            class_name="text-xs text-gray-400"),
                    rx.el.button(
                        "Cerrar",
                        on_click=ConfiguracionState.cerrar_modal_permisos,
                        class_name="px-4 py-2 text-sm font-medium bg-gray-100 text-gray-700 "
                                   "rounded-lg hover:bg-gray-200 transition cursor-pointer",
                    ),
                    class_name="flex items-center justify-between px-5 py-4 border-t border-gray-100",
                ),
                class_name="bg-white rounded-xl shadow-xl w-full max-w-md mx-4",
            ),
            class_name="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm",
        ),
    )


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 3: GESTIÓN DE USUARIOS
# ══════════════════════════════════════════════════════════════════

def _rol_badge(rol: str) -> rx.Component:
    return rx.match(
        rol,
        ("administracion", rx.el.span("Administrador",
                                      class_name="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700")),
        ("recepcionista",  rx.el.span("Recepcionista",
                                      class_name="px-2 py-0.5 rounded-full text-xs font-medium bg-sky-100 text-sky-700")),
        ("profesional",    rx.el.span("Profesional",
                                      class_name="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700")),
        ("contador",       rx.el.span("Contador",
                                      class_name="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700")),
        rx.el.span(rol,    class_name="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600"),
    )


def _modulo_tag(tag: str) -> rx.Component:
    return rx.el.span(
        tag,
        class_name="inline-flex px-2 py-0.5 rounded-full text-xs font-medium "
                   "bg-sky-50 text-sky-700 border border-sky-100 mr-1 mb-1",
    )


def _fila_usuario(u: dict) -> rx.Component:
    return rx.el.tr(
        # Columna usuario
        rx.el.td(
            rx.el.div(
                rx.el.div(
                    rx.icon("user", size=14),
                    class_name="w-8 h-8 rounded-full bg-sky-100 text-sky-700 "
                               "flex items-center justify-center shrink-0",
                ),
                rx.el.div(
                    rx.el.p(u["nombre"], class_name="text-sm font-medium text-gray-900"),
                    rx.el.p(u["email"],  class_name="text-xs text-gray-400"),
                ),
                class_name="flex items-center gap-3",
            ),
            class_name="px-4 py-3",
        ),
        # Columna rol
        rx.el.td(_rol_badge(u["rol"]), class_name="px-4 py-3"),
        # Columna acceso a módulos
        rx.el.td(
            rx.el.div(
                rx.foreach(u["modulos"].to(list[str]), _modulo_tag),
                class_name="flex flex-wrap max-w-xs",
            ),
            class_name="px-4 py-3",
        ),
        # Columna acciones
        rx.el.td(
            rx.el.div(
                # Gestionar permisos del rol
                rx.el.button(
                    rx.icon("shield", size=14),
                    on_click=lambda: ConfiguracionState.abrir_modal_permisos(u),
                    class_name="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 "
                               "rounded transition cursor-pointer",
                    title="Gestionar permisos del rol",
                ),
                # Cambiar contraseña
                rx.el.button(
                    rx.icon("key-round", size=14),
                    on_click=lambda: ConfiguracionState.abrir_modal_password(u),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 "
                               "rounded transition cursor-pointer",
                    title="Cambiar contraseña",
                ),
                # Activar / Desactivar
                rx.el.button(
                    rx.cond(u["is_active"],
                            rx.icon("user-x",     size=14),
                            rx.icon("user-check", size=14)),
                    on_click=lambda: ConfiguracionState.toggle_activo_usuario(u["id"]),
                    class_name=rx.cond(
                        u["is_active"],
                        "p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition cursor-pointer",
                        "p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition cursor-pointer",
                    ),
                    title=rx.cond(u["is_active"], "Desactivar", "Activar"),
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50 transition-colors",
    )


def _seccion_usuarios() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            _section_title("GESTION DE USUARIOS", "Crea usuarios, roles y ajusta sus privilegios."),
            rx.el.button(
                rx.icon("user-plus", size=15),
                "Crear Nuevo Usuario",
                on_click=ConfiguracionState.abrir_modal_usuario,
                class_name="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm "
                           "font-medium rounded-lg hover:bg-sky-700 transition cursor-pointer shrink-0",
            ),
            class_name="flex items-start justify-between",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        *[rx.el.th(h, class_name="px-4 py-3 text-left text-xs font-semibold "
                                                  "text-gray-500 uppercase tracking-wide")
                          for h in ["Usuario", "Rol", "Acceso a Módulos", "Acciones"]],
                    ),
                    class_name="bg-gray-50 border-b border-gray-200",
                ),
                rx.el.tbody(
                    rx.foreach(ConfiguracionState.usuarios.to(list[dict]), _fila_usuario),
                ),
                class_name="w-full border-collapse",
            ),
            class_name="overflow-x-auto rounded-xl border border-gray-100 shadow-sm",
        ),
        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-5",
    )


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 4: SELECTOR DE MONEDAS
# ══════════════════════════════════════════════════════════════════

def _tarjeta_moneda(m: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(m["codigo"], class_name="font-bold text-sm text-gray-800"),
                rx.el.span(m["simbolo"],
                           class_name="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-0.5 rounded"),
                class_name="flex items-center justify-between",
            ),
            rx.el.p(m["nombre"], class_name="text-xs text-gray-500 mt-0.5"),
        ),
        rx.el.div(
            rx.cond(
                m["es_activa"],
                rx.el.span("Activa",
                           class_name="text-xs font-medium text-sky-600 bg-sky-50 px-2 py-0.5 rounded-full"),
                rx.el.button(
                    "Seleccionar",
                    on_click=lambda: ConfiguracionState.seleccionar_moneda(m["id"]),
                    class_name="text-xs text-sky-600 hover:text-sky-700 font-medium cursor-pointer underline-offset-2 hover:underline",
                ),
            ),
            rx.el.button(
                rx.icon("trash-2", size=13),
                on_click=lambda: ConfiguracionState.eliminar_moneda(m["id"]),
                class_name="text-gray-300 hover:text-red-500 cursor-pointer transition ml-auto",
            ),
            class_name="flex items-center justify-between mt-3",
        ),
        class_name=rx.cond(
            m["es_activa"],
            "border border-sky-200 bg-sky-50 rounded-xl p-3",
            "border border-gray-200 bg-white rounded-xl p-3 hover:border-gray-300 transition",
        ),
    )


def _seccion_monedas() -> rx.Component:
    return rx.el.div(
        _section_title("SELECTOR DE MONEDAS",
                       "Configura las monedas disponibles y el símbolo que se muestra en los módulos."),
        # Formulario de agregar
        rx.el.div(
            _campo("Codigo",  "text", ConfiguracionState.form_moneda_codigo,
                   ConfiguracionState.set_form_moneda_codigo, "PEN, USD, EUR"),
            _campo("Nombre",  "text", ConfiguracionState.form_moneda_nombre,
                   ConfiguracionState.set_form_moneda_nombre, "Sol peruano, Dólar, Peso"),
            _campo("Símbolo", "text", ConfiguracionState.form_moneda_simbolo,
                   ConfiguracionState.set_form_moneda_simbolo, "S/, $, EUR"),
            rx.el.button(
                rx.icon("plus", size=15),
                "+ Agregar moneda",
                on_click=ConfiguracionState.agregar_moneda,
                class_name="self-end px-4 py-2 bg-emerald-600 text-white text-sm font-medium "
                           "rounded-lg hover:bg-emerald-700 transition cursor-pointer flex items-center gap-1.5",
            ),
            class_name="grid grid-cols-4 gap-3 items-end",
        ),
        rx.cond(ConfiguracionState.moneda_error != "",
                _alert(ConfiguracionState.moneda_error, "red")),
        # Moneda activa
        rx.el.div(
            rx.el.span("Moneda activa:", class_name="text-xs text-gray-500"),
            rx.el.span(ConfiguracionState.moneda_activa_nombre,
                       class_name="text-xs font-medium text-sky-600 ml-1"),
            class_name="flex items-center py-1",
        ),
        # Grid de monedas
        rx.cond(
            ConfiguracionState.monedas.length() == 0,
            rx.el.div(
                rx.icon("circle-dollar-sign", size=28, class_name="text-gray-300 mb-2"),
                rx.el.p("Sin monedas configuradas", class_name="text-sm text-gray-400"),
                class_name="flex flex-col items-center py-10 bg-gray-50 rounded-xl",
            ),
            rx.el.div(
                rx.foreach(ConfiguracionState.monedas.to(list[dict]), _tarjeta_moneda),
                class_name="grid grid-cols-3 gap-3",
            ),
        ),
        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4",
    )


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 5: UNIDADES DE MEDIDA
# ══════════════════════════════════════════════════════════════════

def _tarjeta_unidad(u: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(u["nombre"], class_name="text-sm font-medium text-gray-800"),
            rx.cond(
                u["permite_decimales"],
                rx.el.span("Si", class_name="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-medium"),
                rx.el.span("No", class_name="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded"),
            ),
            class_name="flex items-center gap-2 mb-2",
        ),
        rx.el.div(
            rx.el.span("Decimales", class_name="text-xs text-gray-400"),
            _toggle_switch(u["permite_decimales"],
                           lambda: ConfiguracionState.toggle_unidad_decimales(u["id"])),
            rx.el.button(
                rx.icon("trash-2", size=13),
                on_click=lambda: ConfiguracionState.eliminar_unidad(u["id"]),
                class_name="text-gray-300 hover:text-red-500 cursor-pointer transition ml-auto",
            ),
            class_name="flex items-center gap-2",
        ),
        class_name="border border-gray-200 rounded-xl p-3 bg-white hover:border-gray-300 transition",
    )


def _seccion_unidades() -> rx.Component:
    return rx.el.div(
        _section_title("UNIDADES DE MEDIDA",
                       "Define las unidades que podrás seleccionar en inventario, ingresos y ventas."),
        # Formulario
        rx.el.div(
            _campo("Nombre de la unidad", "text",
                   ConfiguracionState.form_unidad_nombre,
                   ConfiguracionState.set_form_unidad_nombre, "Ej: Caja, Paquete, Docena"),
            rx.el.div(
                rx.el.label("Permite decimales", class_name="block text-xs font-medium text-gray-600 mb-1"),
                rx.el.div(
                    rx.el.span("Permite decimales", class_name="text-sm text-gray-600"),
                    _toggle_switch(ConfiguracionState.form_unidad_decimales,
                                   ConfiguracionState.toggle_form_unidad_decimales),
                    class_name="flex items-center gap-3 px-3 py-2 border border-gray-200 rounded-lg bg-white",
                ),
            ),
            rx.el.button(
                rx.icon("plus", size=15),
                "+ Agregar unidad",
                on_click=ConfiguracionState.agregar_unidad,
                class_name="self-end px-4 py-2 bg-emerald-600 text-white text-sm font-medium "
                           "rounded-lg hover:bg-emerald-700 transition cursor-pointer flex items-center gap-1.5",
            ),
            class_name="grid grid-cols-3 gap-3 items-end",
        ),
        rx.cond(ConfiguracionState.unidad_error != "",
                _alert(ConfiguracionState.unidad_error, "red")),
        # Grid de unidades
        rx.cond(
            ConfiguracionState.unidades.length() == 0,
            rx.el.div(
                rx.icon("ruler", size=28, class_name="text-gray-300 mb-2"),
                rx.el.p("Sin unidades configuradas", class_name="text-sm text-gray-400"),
                class_name="flex flex-col items-center py-10 bg-gray-50 rounded-xl",
            ),
            rx.el.div(
                rx.foreach(ConfiguracionState.unidades.to(list[dict]), _tarjeta_unidad),
                class_name="grid grid-cols-4 gap-3",
            ),
        ),
        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4",
    )


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 6: MÉTODOS DE PAGO
# ══════════════════════════════════════════════════════════════════

_TIPOS_MP = [
    ("efectivo",      "Efectivo"),
    ("tarjeta",       "Tarjeta"),
    ("transferencia", "Transferencia"),
    ("billetera",     "Billetera Digital"),
    ("otro",          "Otro"),
]


def _tipo_mp_badge(tipo: str) -> rx.Component:
    return rx.match(
        tipo,
        ("efectivo",      rx.el.span("Efectivo",      class_name="px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-700")),
        ("tarjeta",       rx.el.span("Tarjeta",       class_name="px-1.5 py-0.5 rounded text-xs bg-purple-100 text-purple-700")),
        ("transferencia", rx.el.span("Transferencia", class_name="px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700")),
        ("billetera",     rx.el.span("Billetera",     class_name="px-1.5 py-0.5 rounded text-xs bg-amber-100 text-amber-700")),
        rx.el.span("Otro", class_name="px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-600"),
    )


def _tarjeta_mp(m: dict) -> rx.Component:
    return rx.el.div(
        # Cabecera
        rx.el.div(
            rx.el.p(m["nombre"], class_name="text-sm font-semibold text-gray-800"),
            rx.el.div(
                _tipo_mp_badge(m["tipo"]),
                rx.cond(
                    m["is_active"],
                    rx.el.span("Activo",   class_name="px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-700"),
                    rx.el.span("Inactivo", class_name="px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-500"),
                ),
                class_name="flex gap-1",
            ),
            class_name="flex items-center justify-between",
        ),
        rx.cond(
            m["descripcion"] != "",
            rx.el.p(m["descripcion"], class_name="text-xs text-gray-500 mt-0.5"),
        ),
        # Footer: visible toggle + delete
        rx.el.div(
            rx.el.span("Visible en Venta", class_name="text-xs text-gray-500"),
            _toggle_switch(m["visible_en_venta"],
                           lambda: ConfiguracionState.toggle_visible_metodo(m["id"])),
            rx.el.button(
                rx.icon("trash-2", size=13),
                on_click=lambda: ConfiguracionState.eliminar_metodo_pago(m["id"]),
                class_name="text-gray-300 hover:text-red-500 cursor-pointer transition ml-auto",
            ),
            class_name="flex items-center gap-3 mt-3",
        ),
        class_name="border border-gray-200 rounded-xl p-3 bg-white hover:border-gray-300 transition",
    )


def _seccion_metodos_pago() -> rx.Component:
    return rx.el.div(
        _section_title("METODOS DE PAGO",
                       "Activa, crea o elimina los botones que verás en el módulo de Cobro."),
        # Formulario
        rx.el.div(
            _campo("Nombre",      "text", ConfiguracionState.form_mp_nombre,
                   ConfiguracionState.set_form_mp_nombre, "Ej: Transferencia, Depósito"),
            _campo("Descripcion", "text", ConfiguracionState.form_mp_descripcion,
                   ConfiguracionState.set_form_mp_descripcion, "Breve detalle del método"),
            _select("Tipo", ConfiguracionState.form_mp_tipo,
                    ConfiguracionState.set_form_mp_tipo, _TIPOS_MP),
            rx.el.button(
                rx.icon("plus", size=15),
                "+ Agregar método",
                on_click=ConfiguracionState.agregar_metodo_pago,
                class_name="self-end px-4 py-2 bg-emerald-600 text-white text-sm font-medium "
                           "rounded-lg hover:bg-emerald-700 transition cursor-pointer flex items-center gap-1.5",
            ),
            class_name="grid grid-cols-4 gap-3 items-end",
        ),
        rx.cond(ConfiguracionState.mp_error != "",
                _alert(ConfiguracionState.mp_error, "red")),
        # Grid
        rx.cond(
            ConfiguracionState.metodos_pago.length() == 0,
            rx.el.div(
                rx.icon("credit-card", size=28, class_name="text-gray-300 mb-2"),
                rx.el.p("Sin métodos de pago configurados", class_name="text-sm text-gray-400"),
                class_name="flex flex-col items-center py-10 bg-gray-50 rounded-xl",
            ),
            rx.el.div(
                rx.foreach(ConfiguracionState.metodos_pago.to(list[dict]), _tarjeta_mp),
                class_name="grid grid-cols-3 gap-3",
            ),
        ),
        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4",
    )


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 7: IMPUESTOS
# ══════════════════════════════════════════════════════════════════

_PAISES = [
    ("peru",      "pe Perú (IGV 18%)"),
    ("argentina", "ar Argentina (IVA 21%/10.5%/27%)"),
    ("colombia",  "co Colombia (IVA 19%/5%)"),
    ("chile",     "cl Chile (IVA 19%)"),
    ("ecuador",   "ec Ecuador (IVA 12%/5%)"),
    ("bolivia",   "bo Bolivia (IVA 13%)"),
    ("uruguay",   "uy Uruguay (IVA 22%/10%)"),
    ("paraguay",  "py Paraguay (IVA 10%/5%)"),
    ("mexico",    "mx México (IVA 16%)"),
]


def _fila_impuesto(t: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(t["tipo_impuesto"],
                       class_name="px-2 py-0.5 rounded text-xs font-bold bg-indigo-100 text-indigo-700 mr-2"),
            rx.el.span(t["nombre"],
                       class_name="text-sm font-medium text-gray-800"),
            rx.cond(
                t["is_default"],
                rx.el.span("Default",
                           class_name="ml-2 px-1.5 py-0.5 rounded text-xs bg-amber-100 text-amber-700 font-medium"),
            ),
            class_name="flex items-center",
        ),
        rx.el.div(
            rx.el.span(t["porcentaje"].to(str) + "%",
                       class_name="text-sm font-semibold text-gray-700 mr-3"),
            rx.cond(
                ~t["is_default"],
                rx.el.button(
                    rx.icon("star", size=13),
                    on_click=lambda: ConfiguracionState.set_default_impuesto(t["id"]),
                    class_name="text-gray-300 hover:text-amber-500 cursor-pointer transition mr-1",
                    title="Establecer como default",
                ),
            ),
            rx.el.button(
                rx.icon("trash-2", size=13),
                on_click=lambda: ConfiguracionState.eliminar_impuesto(t["id"]),
                class_name="text-gray-300 hover:text-red-500 cursor-pointer transition",
                title="Eliminar",
            ),
            class_name="flex items-center",
        ),
        class_name="flex items-center justify-between py-2.5 px-4 border-b border-gray-100 "
                   "last:border-0 hover:bg-gray-50 transition",
    )


def _btn_pais(codigo: str, label: str) -> rx.Component:
    return rx.el.button(
        label,
        on_click=lambda: ConfiguracionState.cargar_impuestos_pais(codigo),
        class_name="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 "
                   "bg-white text-gray-700 hover:bg-indigo-50 hover:border-indigo-300 "
                   "hover:text-indigo-700 transition cursor-pointer",
    )


def _seccion_impuestos() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("percent", size=18, class_name="text-sky-600"),
                    class_name="p-2 bg-sky-100 rounded-lg shrink-0",
                ),
                rx.el.div(
                    rx.el.h2("Configuración de Impuestos",
                             class_name="text-sm font-bold text-gray-800"),
                    rx.el.p("Define las tasas aplicables a tus ventas. Puedes cargar defaults por país "
                            "o crear tasas personalizadas.",
                            class_name="text-xs text-gray-500 mt-0.5"),
                    class_name="ml-3",
                ),
                class_name="flex items-center",
            ),
        ),

        # Carga por país
        rx.el.div(
            rx.el.p("Cargar configuración por país",
                    class_name="text-sm font-medium text-gray-700 mb-1"),
            rx.el.p("Reemplaza las tasas actuales con los valores predefinidos del país seleccionado.",
                    class_name="text-xs text-gray-500 mb-3"),
            rx.el.div(
                *[_btn_pais(c, l) for c, l in _PAISES],
                class_name="flex flex-wrap gap-2",
            ),
            class_name="p-4 bg-gray-50 rounded-xl border border-gray-100",
        ),

        # Tasas configuradas
        rx.el.div(
            rx.el.div(
                rx.el.h3("Tasas configuradas",
                         class_name="text-sm font-semibold text-gray-700"),
                rx.el.button(
                    rx.icon("plus", size=14),
                    "Agregar tasa",
                    on_click=ConfiguracionState.abrir_modal_impuesto,
                    class_name="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium "
                               "text-sky-600 border border-sky-200 rounded-lg hover:bg-sky-50 "
                               "transition cursor-pointer",
                ),
                class_name="flex items-center justify-between mb-3",
            ),
            rx.cond(
                ConfiguracionState.it_error != "",
                _alert(ConfiguracionState.it_error, "red"),
            ),
            rx.cond(
                ConfiguracionState.impuesto_tasas.length() == 0,
                rx.el.p("Sin tasas configuradas. Carga por país o agrega una manualmente.",
                        class_name="text-sm text-gray-400 text-center py-6"),
                rx.el.div(
                    rx.foreach(ConfiguracionState.impuesto_tasas.to(list[dict]), _fila_impuesto),
                    class_name="rounded-xl border border-gray-100 overflow-hidden shadow-sm",
                ),
            ),
        ),

        # Mostrar impuesto en recibo
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("receipt", size=16, class_name="text-gray-500"),
                    class_name="p-1.5 bg-gray-100 rounded shrink-0",
                ),
                rx.el.div(
                    rx.el.p("Mostrar impuesto en recibo",
                            class_name="text-sm font-medium text-gray-800"),
                    rx.el.p("Muestra el desglose del impuesto (base + impuesto + total) "
                            "en los recibos de venta.",
                            class_name="text-xs text-gray-500"),
                    class_name="ml-3 flex-1",
                ),
                _toggle_switch(ConfiguracionState.mostrar_impuesto_recibo,
                               ConfiguracionState.toggle_mostrar_impuesto_recibo),
                class_name="flex items-center",
            ),
            class_name="flex items-center p-4 bg-gray-50 rounded-xl border border-gray-100",
        ),

        # Vista previa
        rx.el.div(
            rx.el.p("Vista previa", class_name="text-sm font-medium text-gray-700 mb-3"),
            rx.el.div(
                rx.el.div(
                    rx.el.span("Subtotal:", class_name="text-sm text-gray-600"),
                    rx.el.span("100.00",    class_name="text-sm text-gray-800"),
                    class_name="flex justify-between py-1",
                ),
                rx.el.div(
                    rx.el.span(ConfiguracionState.impuesto_default_label + ":",
                               class_name="text-sm text-indigo-600"),
                    rx.el.span(ConfiguracionState.impuesto_preview_monto,
                               class_name="text-sm font-medium text-indigo-600"),
                    class_name="flex justify-between py-1",
                ),
                rx.el.div(
                    rx.el.span("Total:", class_name="text-sm font-bold text-gray-900"),
                    rx.el.span(ConfiguracionState.impuesto_preview_total,
                               class_name="text-sm font-bold text-gray-900"),
                    class_name="flex justify-between py-1 border-t border-gray-200 mt-1",
                ),
                class_name="bg-white rounded-lg p-4 border border-gray-200",
            ),
            class_name="p-4 bg-gray-50 rounded-xl border border-gray-100",
        ),

        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-5",
    )


# ══════════════════════════════════════════════════════════════════
# PÁGINA PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def configuracion_page() -> rx.Component:
    return shell(
        # Modales siempre en el DOM
        _modal_nuevo_usuario(),
        _modal_password(),
        _modal_sede(),
        _modal_impuesto(),
        _modal_permisos_rol(),

        page_header(
            "Configuración del Sistema",
            "Gestiona usuarios, monedas, unidades y métodos de pago desde un solo lugar.",
        ),

        # Guard: solo admins
        rx.cond(
            ConfiguracionState.is_admin,
            rx.el.div(
                # Sidebar izquierdo de sub-navegación
                _sub_nav(),
                # Panel de contenido derecho
                rx.el.div(
                    rx.cond(ConfiguracionState.tab_activo == "empresa",    _seccion_empresa()),
                    rx.cond(ConfiguracionState.tab_activo == "sucursales", _seccion_sucursales()),
                    rx.cond(ConfiguracionState.tab_activo == "usuarios",   _seccion_usuarios()),
                    rx.cond(ConfiguracionState.tab_activo == "monedas",    _seccion_monedas()),
                    rx.cond(ConfiguracionState.tab_activo == "unidades",   _seccion_unidades()),
                    rx.cond(ConfiguracionState.tab_activo == "pagos",      _seccion_metodos_pago()),
                    rx.cond(ConfiguracionState.tab_activo == "impuestos",  _seccion_impuestos()),
                    class_name="flex-1 min-w-0",
                ),
                class_name="flex gap-4 items-start",
            ),
            # Sin acceso
            rx.el.div(
                rx.icon("shield-off", size=32, class_name="text-gray-300 mb-3"),
                rx.el.p("Acceso restringido a administradores.",
                        class_name="text-sm text-gray-500"),
                class_name="flex flex-col items-center justify-center py-24 text-center "
                           "bg-white rounded-xl shadow-sm border border-gray-100",
            ),
        ),
        on_mount=ConfiguracionState.on_mount,
    )
