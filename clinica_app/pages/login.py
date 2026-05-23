from __future__ import annotations

import reflex as rx

from clinica_app.state.auth import AuthState


def login_page() -> rx.Component:
    return rx.el.div(
        # Fondo gradiente
        rx.el.div(
            rx.el.div(
                # Card de login
                rx.el.div(
                    # Logo / título
                    rx.el.div(
                        rx.el.div(
                            rx.icon("stethoscope", size=32, color="white"),
                            class_name="w-16 h-16 bg-sky-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg",
                        ),
                        rx.el.h1(
                            "WaykiSAC",
                            class_name="text-2xl font-bold text-gray-900 text-center",
                        ),
                        rx.el.p(
                            "Sistema de Gestión para Clínicas",
                            class_name="text-sm text-gray-500 text-center mt-1",
                        ),
                        class_name="mb-8",
                    ),
                    # Formulario
                    rx.el.form(
                        rx.el.div(
                            rx.el.label(
                                "Email",
                                class_name="block text-sm font-medium text-gray-700 mb-1",
                            ),
                            rx.debounce_input(
                                rx.el.input(
                                    type="email",
                                    placeholder="admin@clinica.local",
                                    value=AuthState.email,
                                    on_change=AuthState.set_email,
                                    class_name="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition",
                                ),
                                debounce_timeout=300,
                            ),
                            class_name="mb-4",
                        ),
                        rx.el.div(
                            rx.el.label(
                                "Contraseña",
                                class_name="block text-sm font-medium text-gray-700 mb-1",
                            ),
                            rx.debounce_input(
                                rx.el.input(
                                    type="password",
                                    placeholder="••••••••",
                                    value=AuthState.password,
                                    on_change=AuthState.set_password,
                                    class_name="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition",
                                ),
                                debounce_timeout=300,
                            ),
                            class_name="mb-4",
                        ),
                        # Mensaje de error
                        rx.cond(
                            AuthState.error_msg != "",
                            rx.el.div(
                                rx.el.p(
                                    AuthState.error_msg,
                                    class_name="text-sm text-red-600",
                                ),
                                class_name="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg",
                            ),
                        ),
                        # Botón de submit
                        rx.el.button(
                            rx.cond(
                                AuthState.is_loading,
                                rx.el.div(
                                    rx.icon("loader-circle", size=18, class_name="animate-spin mr-2"),
                                    "Ingresando...",
                                    class_name="flex items-center justify-center",
                                ),
                                "Iniciar sesión",
                            ),
                            type="submit",
                            disabled=AuthState.is_loading,
                            class_name="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-400 text-white font-medium rounded-lg text-sm transition-colors cursor-pointer disabled:cursor-not-allowed",
                        ),
                        on_submit=lambda _: AuthState.handle_login(),
                        class_name="space-y-0",
                    ),
                    class_name="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm",
                ),
                class_name="flex items-center justify-center min-h-screen px-4",
            ),
            class_name="min-h-screen bg-gradient-to-br from-sky-50 via-white to-indigo-50",
        ),
    )
