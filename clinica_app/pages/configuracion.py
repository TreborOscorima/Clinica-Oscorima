from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.state.configuracion import ConfiguracionState


# ── Helpers ────────────────────────────────────────────────────────────────────

def _campo(label: str, tipo: str, value, on_change, placeholder: str = "") -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.input(
            type=tipo, value=value, on_change=on_change, placeholder=placeholder,
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm "
                       "focus:outline-none focus:ring-2 focus:ring-sky-500 transition",
        ),
    )


def _campo_password(label: str, value, on_change) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.input(
            type="password", value=value, on_change=on_change,
            placeholder="••••••••",
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm "
                       "focus:outline-none focus:ring-2 focus:ring-sky-500 transition",
        ),
    )


def _rol_badge(rol: str) -> rx.Component:
    return rx.match(
        rol,
        ("administracion", rx.el.span("Administrador", class_name="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700")),
        ("recepcionista",  rx.el.span("Recepcionista",  class_name="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-sky-100 text-sky-700")),
        ("profesional",    rx.el.span("Profesional",    class_name="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700")),
        ("contador",       rx.el.span("Contador",       class_name="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700")),
        rx.el.span(rol,    class_name="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600"),
    )


def _alert(msg, color: str = "green") -> rx.Component:
    icon = "circle-check" if color == "green" else "circle-alert"
    return rx.el.div(
        rx.icon(icon, size=14, class_name=f"shrink-0 text-{color}-600"),
        rx.el.span(msg, class_name=f"text-sm text-{color}-700 ml-2"),
        class_name=f"flex items-center mt-4 px-3 py-2 rounded-lg bg-{color}-50 border border-{color}-200",
    )


def _btn_spinner(label: str, loading_label: str, is_loading, on_click) -> rx.Component:
    return rx.el.button(
        rx.cond(
            is_loading,
            rx.el.div(
                rx.icon("loader-circle", size=15, class_name="animate-spin mr-1.5"),
                loading_label,
                class_name="flex items-center",
            ),
            label,
        ),
        on_click=on_click,
        disabled=is_loading,
        class_name="px-4 py-2 text-sm bg-sky-600 text-white font-medium rounded-lg "
                   "hover:bg-sky-700 disabled:bg-sky-400 disabled:cursor-not-allowed transition cursor-pointer",
    )


# ── Tab selector ───────────────────────────────────────────────────────────────

def _tab_btn(label: str, tab: str, icon: str) -> rx.Component:
    return rx.el.button(
        rx.icon(icon, size=16),
        label,
        on_click=lambda: ConfiguracionState.set_tab(tab),
        class_name=rx.cond(
            ConfiguracionState.tab_activo == tab,
            "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-sky-600 text-white",
            "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg text-gray-600 "
            "bg-white border border-gray-300 hover:bg-gray-50 transition cursor-pointer",
        ),
    )


# ── Modal: crear usuario ───────────────────────────────────────────────────────

def _modal_nuevo_usuario() -> rx.Component:
    return rx.cond(
        ConfiguracionState.modal_usuario,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=ConfiguracionState.cerrar_modal_usuario,
            ),
            rx.el.div(
                # Encabezado del modal
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.icon("user-plus", size=18, class_name="text-sky-600"),
                            class_name="p-2 bg-sky-100 rounded-lg",
                        ),
                        rx.el.h2("Nuevo usuario", class_name="text-lg font-semibold text-gray-900 ml-3"),
                        class_name="flex items-center",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=ConfiguracionState.cerrar_modal_usuario,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer transition",
                    ),
                    class_name="flex items-center justify-between mb-6",
                ),
                # Campos
                rx.el.div(
                    _campo("Nombre completo *", "text", ConfiguracionState.form_u_nombre,
                           ConfiguracionState.set_form_u_nombre, "Ej: Ana García"),
                    _campo("Email *", "email", ConfiguracionState.form_u_email,
                           ConfiguracionState.set_form_u_email, "usuario@clinica.com"),
                    # Selector de rol
                    rx.el.div(
                        rx.el.label("Rol *", class_name="block text-sm font-medium text-gray-700 mb-1"),
                        rx.el.select(
                            rx.el.option("Recepcionista",  value="recepcionista"),
                            rx.el.option("Profesional",    value="profesional"),
                            rx.el.option("Administrador",  value="administracion"),
                            rx.el.option("Contador",       value="contador"),
                            value=ConfiguracionState.form_u_rol,
                            on_change=ConfiguracionState.set_form_u_rol,
                            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm "
                                       "focus:outline-none focus:ring-2 focus:ring-sky-500",
                        ),
                    ),
                    _campo_password("Contraseña *",        ConfiguracionState.form_u_password,
                                    ConfiguracionState.set_form_u_password),
                    _campo_password("Confirmar contraseña *", ConfiguracionState.form_u_password2,
                                    ConfiguracionState.set_form_u_password2),
                    class_name="space-y-4",
                ),
                # Feedback
                rx.cond(
                    ConfiguracionState.form_u_error != "",
                    _alert(ConfiguracionState.form_u_error, "red"),
                ),
                # Acciones
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=ConfiguracionState.cerrar_modal_usuario,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 "
                                   "rounded-lg hover:bg-gray-50 transition cursor-pointer",
                    ),
                    _btn_spinner(
                        "Crear usuario", "Creando...",
                        ConfiguracionState.is_saving_usuario,
                        ConfiguracionState.guardar_usuario,
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


# ── Modal: cambiar contraseña ──────────────────────────────────────────────────

def _modal_password() -> rx.Component:
    return rx.cond(
        ConfiguracionState.modal_password,
        rx.el.div(
            rx.el.div(
                class_name="fixed inset-0 bg-black/40 z-40",
                on_click=ConfiguracionState.cerrar_modal_password,
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.icon("key-round", size=18, class_name="text-sky-600"),
                            class_name="p-2 bg-sky-100 rounded-lg",
                        ),
                        rx.el.div(
                            rx.el.h2("Cambiar contraseña", class_name="text-lg font-semibold text-gray-900"),
                            rx.el.p(ConfiguracionState.pw_user_nombre, class_name="text-sm text-gray-500"),
                            class_name="ml-3",
                        ),
                        class_name="flex items-center",
                    ),
                    rx.el.button(
                        rx.icon("x", size=18),
                        on_click=ConfiguracionState.cerrar_modal_password,
                        class_name="text-gray-400 hover:text-gray-600 cursor-pointer transition",
                    ),
                    class_name="flex items-center justify-between mb-6",
                ),
                rx.el.div(
                    _campo_password("Nueva contraseña *",    ConfiguracionState.form_pw_nueva,
                                    ConfiguracionState.set_form_pw_nueva),
                    _campo_password("Confirmar contraseña *", ConfiguracionState.form_pw_nueva2,
                                    ConfiguracionState.set_form_pw_nueva2),
                    class_name="space-y-4",
                ),
                rx.cond(ConfiguracionState.form_pw_error   != "", _alert(ConfiguracionState.form_pw_error,   "red")),
                rx.cond(ConfiguracionState.form_pw_success != "", _alert(ConfiguracionState.form_pw_success, "green")),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=ConfiguracionState.cerrar_modal_password,
                        class_name="px-4 py-2 text-sm text-gray-600 border border-gray-300 "
                                   "rounded-lg hover:bg-gray-50 transition cursor-pointer",
                    ),
                    _btn_spinner(
                        "Guardar", "Guardando...",
                        ConfiguracionState.is_saving_pw,
                        ConfiguracionState.guardar_password,
                    ),
                    class_name="flex gap-3 justify-end mt-6",
                ),
                class_name="relative bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 z-50",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50",
        ),
    )


# ── Sección: datos de la clínica ───────────────────────────────────────────────

def _seccion_clinica() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                "Actualiza el nombre, datos fiscales y contacto de tu clínica.",
                class_name="text-sm text-gray-500",
            ),
            class_name="mb-5",
        ),
        rx.el.div(
            _campo("Nombre *",          "text",  ConfiguracionState.form_nombre,
                   ConfiguracionState.set_form_nombre, "Clínica Estética..."),
            _campo("Razón social",      "text",  ConfiguracionState.form_razon_social,
                   ConfiguracionState.set_form_razon_social, "S.A.C. / S.R.L...."),
            _campo("Documento fiscal",  "text",  ConfiguracionState.form_documento_fiscal,
                   ConfiguracionState.set_form_documento_fiscal, "RUC / CUIT / NIF..."),
            _campo("Email de contacto", "email", ConfiguracionState.form_email_clinica,
                   ConfiguracionState.set_form_email_clinica, "correo@clinica.com"),
            _campo("Teléfono",          "tel",   ConfiguracionState.form_telefono,
                   ConfiguracionState.set_form_telefono, "+51 999 999 999"),
            class_name="grid grid-cols-1 gap-4 sm:grid-cols-2",
        ),
        rx.cond(ConfiguracionState.clinica_error   != "", _alert(ConfiguracionState.clinica_error,   "red")),
        rx.cond(ConfiguracionState.clinica_success != "", _alert(ConfiguracionState.clinica_success, "green")),
        rx.el.div(
            _btn_spinner(
                "Guardar cambios", "Guardando...",
                ConfiguracionState.is_saving_clinica,
                ConfiguracionState.guardar_clinica,
            ),
            class_name="mt-5 flex justify-end",
        ),
    )


# ── Sección: usuarios ──────────────────────────────────────────────────────────

def _fila_usuario(u: dict) -> rx.Component:
    return rx.el.tr(
        # Avatar + nombre
        rx.el.td(
            rx.el.div(
                rx.el.div(
                    rx.icon("user", size=14),
                    class_name="w-8 h-8 rounded-full bg-sky-100 text-sky-700 flex items-center "
                               "justify-center text-sm font-bold shrink-0",
                ),
                rx.el.div(
                    rx.el.p(u["nombre"], class_name="text-sm font-medium text-gray-900"),
                    rx.el.p(u["created_at"], class_name="text-xs text-gray-400"),
                    class_name="min-w-0",
                ),
                class_name="flex items-center gap-3",
            ),
            class_name="px-4 py-3",
        ),
        # Email
        rx.el.td(u["email"], class_name="px-4 py-3 text-sm text-gray-600"),
        # Rol
        rx.el.td(_rol_badge(u["rol"]), class_name="px-4 py-3"),
        # Estado
        rx.el.td(
            rx.cond(
                u["is_active"],
                rx.el.span("Activo",   class_name="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700"),
                rx.el.span("Inactivo", class_name="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500"),
            ),
            class_name="px-4 py-3",
        ),
        # Acciones
        rx.el.td(
            rx.el.div(
                # Cambiar contraseña
                rx.el.button(
                    rx.icon("key-round", size=15),
                    on_click=lambda: ConfiguracionState.abrir_modal_password(u),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 rounded transition cursor-pointer",
                    title="Cambiar contraseña",
                ),
                # Toggle activo / inactivo
                rx.el.button(
                    rx.cond(
                        u["is_active"],
                        rx.icon("user-x",     size=15),
                        rx.icon("user-check", size=15),
                    ),
                    on_click=lambda: ConfiguracionState.toggle_activo_usuario(u["id"]),
                    class_name=rx.cond(
                        u["is_active"],
                        "p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition cursor-pointer",
                        "p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition cursor-pointer",
                    ),
                    title=rx.cond(u["is_active"], "Desactivar usuario", "Activar usuario"),
                ),
                class_name="flex items-center gap-1",
            ),
            class_name="px-4 py-3",
        ),
        class_name="border-t border-gray-100 hover:bg-gray-50 transition-colors",
    )


def _seccion_usuarios() -> rx.Component:
    return rx.el.div(
        # Sub-encabezado
        rx.el.div(
            rx.el.p(
                "Gestiona los miembros del equipo y sus niveles de acceso.",
                class_name="text-sm text-gray-500",
            ),
            rx.el.button(
                rx.icon("user-plus", size=16),
                "Nuevo usuario",
                on_click=ConfiguracionState.abrir_modal_usuario,
                class_name="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm "
                           "font-medium rounded-lg hover:bg-sky-700 transition cursor-pointer",
            ),
            class_name="flex items-center justify-between mb-5",
        ),
        # Tabla
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            *[
                                rx.el.th(
                                    h,
                                    class_name="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide",
                                )
                                for h in ["Usuario", "Email", "Rol", "Estado", "Acciones"]
                            ],
                        ),
                        class_name="bg-gray-50 border-b border-gray-200",
                    ),
                    rx.el.tbody(
                        rx.foreach(ConfiguracionState.usuarios.to(list[dict]), _fila_usuario),
                    ),
                    class_name="w-full border-collapse",
                ),
                class_name="overflow-x-auto",
            ),
            class_name="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden",
        ),
    )


# ── Página principal ───────────────────────────────────────────────────────────

def configuracion_page() -> rx.Component:
    return shell(
        # Modales (siempre presentes en el DOM)
        _modal_nuevo_usuario(),
        _modal_password(),

        # Encabezado
        rx.el.div(
            rx.el.div(
                rx.el.h1("Configuración", class_name="text-xl font-semibold text-gray-900"),
                rx.el.p(
                    "Administra los datos de tu clínica y el equipo",
                    class_name="text-sm text-gray-500 mt-0.5",
                ),
            ),
            class_name="mb-6",
        ),

        # Guard visual — solo admins
        rx.cond(
            ConfiguracionState.is_admin,
            rx.el.div(
                # Selector de tabs
                rx.el.div(
                    _tab_btn("Clínica",  "clinica",  "building-2"),
                    _tab_btn("Usuarios", "usuarios", "users"),
                    class_name="flex gap-2 mb-6",
                ),
                # Panel de contenido
                rx.el.div(
                    # Tab: Clínica
                    rx.cond(
                        ConfiguracionState.tab_activo == "clinica",
                        rx.el.div(
                            _seccion_clinica(),
                            class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6",
                        ),
                    ),
                    # Tab: Usuarios
                    rx.cond(
                        ConfiguracionState.tab_activo == "usuarios",
                        _seccion_usuarios(),
                    ),
                ),
            ),
            # Sin acceso
            rx.el.div(
                rx.el.div(
                    rx.icon("shield-off", size=32, class_name="text-gray-300 mb-3"),
                    rx.el.p(
                        "Acceso restringido a administradores.",
                        class_name="text-sm text-gray-500",
                    ),
                    class_name="flex flex-col items-center justify-center py-24 text-center",
                ),
                class_name="bg-white rounded-xl shadow-sm border border-gray-100",
            ),
        ),
        on_mount=ConfiguracionState.on_mount,
    )
