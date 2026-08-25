from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import page_header
from clinica_app.state.cuenta import CuentaState


def _campo_pw(label: str, value, on_change) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="block text-sm font-medium text-gray-700 mb-1"),
        rx.el.input(
            type="password",
            value=value,
            on_change=on_change,
            on_key_down=CuentaState.handle_key,
            class_name="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500",
        ),
    )


def _dato(label: str, value) -> rx.Component:
    return rx.el.div(
        rx.el.span(label, class_name="text-xs text-gray-500 uppercase tracking-wide"),
        rx.el.p(value, class_name="text-sm text-gray-800"),
        class_name="flex flex-col",
    )


def _tarjeta_datos() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("user", size=16, class_name="text-sky-600"),
            rx.el.h2("Mis datos", class_name="text-sm font-semibold text-gray-700"),
            class_name="flex items-center gap-2 mb-4",
        ),
        rx.el.div(
            _dato("Nombre", CuentaState.user_nombre),
            _dato("Email", CuentaState.user_email),
            _dato("Rol", CuentaState.rol_display),
            class_name="grid grid-cols-1 sm:grid-cols-3 gap-4",
        ),
        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-5",
    )


def _tarjeta_password() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("key-round", size=16, class_name="text-sky-600"),
            rx.el.h2("Cambiar mi contraseña", class_name="text-sm font-semibold text-gray-700"),
            class_name="flex items-center gap-2 mb-1",
        ),
        rx.el.p(
            "Mínimo 8 caracteres, con al menos una letra y un número.",
            class_name="text-xs text-gray-500 mb-4",
        ),
        rx.el.div(
            _campo_pw("Contraseña actual", CuentaState.form_actual, CuentaState.set_form_actual),
            _campo_pw("Nueva contraseña", CuentaState.form_nueva, CuentaState.set_form_nueva),
            _campo_pw("Confirmar nueva contraseña", CuentaState.form_nueva2, CuentaState.set_form_nueva2),
            class_name="space-y-4 max-w-sm",
        ),
        rx.cond(
            CuentaState.error != "",
            rx.el.p(CuentaState.error, class_name="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded max-w-sm"),
            rx.fragment(),
        ),
        rx.cond(
            CuentaState.success != "",
            rx.el.p(CuentaState.success, class_name="mt-3 text-sm text-green-700 bg-green-50 p-2 rounded max-w-sm"),
            rx.fragment(),
        ),
        rx.el.div(
            rx.el.button(
                rx.cond(
                    CuentaState.is_saving,
                    rx.el.div(
                        rx.icon("loader-circle", size=16, class_name="animate-spin mr-1"),
                        "Guardando...",
                        class_name="flex items-center",
                    ),
                    "Actualizar contraseña",
                ),
                on_click=CuentaState.cambiar_password,
                disabled=CuentaState.is_saving,
                class_name="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:bg-sky-400 transition cursor-pointer",
            ),
            class_name="mt-5",
        ),
        class_name="bg-white rounded-xl shadow-sm border border-gray-100 p-6",
    )


def cuenta_page() -> rx.Component:
    return shell(
        page_header("Mi cuenta", "Tus datos y seguridad"),
        _tarjeta_datos(),
        _tarjeta_password(),
        title="Mi cuenta",
        on_mount=CuentaState.on_mount,
    )
