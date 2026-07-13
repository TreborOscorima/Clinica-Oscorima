from __future__ import annotations

import reflex as rx

from clinica_app.state.configuracion import ConfiguracionState

from ._helpers import (
    _alert,
    _btn_spinner,
    _campo,
    _campo_pw,
    _section_title,
    _select,
    _toggle_switch,
)


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
                rx.el.div(
                    rx.el.span("Módulo",
                               class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide flex-1"),
                    rx.el.span("Ver",
                               class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide w-20 text-center"),
                    rx.el.span("Editar",
                               class_name="text-xs font-semibold text-gray-400 uppercase tracking-wide w-24 text-center"),
                    class_name="flex items-center gap-4 px-5 pt-3 pb-1",
                ),
                rx.el.div(
                    rx.foreach(
                        ConfiguracionState.permisos_rol_modulos.to(list[dict]),
                        _fila_permiso,
                    ),
                    class_name="px-5 overflow-y-auto max-h-80",
                ),
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
        rx.el.td(_rol_badge(u["rol"]), class_name="px-4 py-3"),
        rx.el.td(
            rx.el.div(
                rx.foreach(u["modulos"].to(list[str]), _modulo_tag),
                class_name="flex flex-wrap max-w-xs",
            ),
            class_name="px-4 py-3",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("shield", size=14),
                    on_click=lambda: ConfiguracionState.abrir_modal_permisos(u),
                    class_name="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 "
                               "rounded transition cursor-pointer",
                    title="Gestionar permisos del rol",
                ),
                rx.el.button(
                    rx.icon("key-round", size=14),
                    on_click=lambda: ConfiguracionState.abrir_modal_password(u),
                    class_name="p-1.5 text-gray-400 hover:text-sky-600 hover:bg-sky-50 "
                               "rounded transition cursor-pointer",
                    title="Cambiar contraseña",
                ),
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
