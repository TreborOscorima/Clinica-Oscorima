from __future__ import annotations

import reflex as rx

from clinica_app.state.auth import AuthState


def _feature(icon: str, text: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, size=16, class_name="text-sky-200"),
            class_name="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0",
        ),
        rx.el.p(text, class_name="text-sm text-sky-100 ml-3"),
        class_name="flex items-center",
    )


def login_page() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            # ── Panel izquierdo: branding (solo lg+) ──────────────────────────
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.icon("stethoscope", size=28, color="white"),
                        class_name=(
                            "w-14 h-14 bg-white/20 rounded-2xl "
                            "flex items-center justify-center mb-6 shadow-lg"
                        ),
                    ),
                    rx.el.h2(
                        "WaykiSAC",
                        class_name="text-3xl font-bold text-white mb-2",
                    ),
                    rx.el.p(
                        "Sistema de Gestión para Clínicas Estéticas",
                        class_name="text-sky-100 text-base leading-relaxed",
                    ),
                    rx.el.div(
                        _feature("users",          "Gestión de pacientes y profesionales"),
                        _feature("calendar-clock", "Agenda y turnos en tiempo real"),
                        _feature("credit-card",    "Punto de cobro integrado"),
                        _feature("bar-chart-2",    "Reportes y análisis financiero"),
                        class_name="mt-8 space-y-3",
                    ),
                    class_name="max-w-sm",
                ),
                class_name=(
                    "hidden lg:flex flex-col justify-center px-16 "
                    "bg-gradient-to-br from-sky-600 via-sky-700 to-indigo-700"
                ),
            ),

            # ── Panel derecho: formulario ─────────────────────────────────────
            rx.el.div(
                rx.el.div(
                    # Logo móvil (oculto en lg+)
                    rx.el.div(
                        rx.el.div(
                            rx.icon("stethoscope", size=24, color="white"),
                            class_name=(
                                "w-12 h-12 bg-sky-600 rounded-xl "
                                "flex items-center justify-center mx-auto mb-4 shadow-md"
                            ),
                        ),
                        class_name="lg:hidden",
                    ),

                    rx.el.h1(
                        "Bienvenido de nuevo",
                        class_name="text-2xl font-bold text-gray-900 text-center lg:text-left mb-1",
                    ),
                    rx.el.p(
                        "Ingresá tus credenciales para continuar",
                        class_name="text-sm text-gray-500 text-center lg:text-left mb-8",
                    ),

                    # Formulario
                    rx.el.form(
                        # Email
                        rx.el.div(
                            rx.el.label(
                                "Email",
                                class_name="block text-sm font-medium text-gray-700 mb-1.5",
                            ),
                            rx.el.div(
                                rx.icon(
                                    "mail", size=16,
                                    class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400",
                                ),
                                rx.el.input(
                                    type="email",
                                    name="email",
                                    placeholder="admin@clinica.local",
                                    auto_complete="email",
                                    class_name=(
                                        "w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg "
                                        "text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 "
                                        "focus:border-transparent transition"
                                    ),
                                ),
                                class_name="relative",
                            ),
                            class_name="mb-4",
                        ),

                        # Contraseña
                        rx.el.div(
                            rx.el.label(
                                "Contraseña",
                                class_name="block text-sm font-medium text-gray-700 mb-1.5",
                            ),
                            rx.el.div(
                                rx.icon(
                                    "lock", size=16,
                                    class_name="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400",
                                ),
                                rx.el.input(
                                    type="password",
                                    name="password",
                                    placeholder="••••••••",
                                    auto_complete="current-password",
                                    class_name=(
                                        "w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg "
                                        "text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 "
                                        "focus:border-transparent transition"
                                    ),
                                ),
                                class_name="relative",
                            ),
                            class_name="mb-4",
                        ),

                        # Error
                        rx.cond(
                            AuthState.error_msg != "",
                            rx.el.div(
                                rx.icon("circle-alert", size=15, class_name="shrink-0 text-red-500"),
                                rx.el.p(
                                    AuthState.error_msg,
                                    class_name="text-sm text-red-600 ml-2",
                                ),
                                class_name=(
                                    "flex items-center mb-4 p-3 "
                                    "bg-red-50 border border-red-200 rounded-lg"
                                ),
                            ),
                        ),

                        # Botón submit
                        rx.el.button(
                            rx.cond(
                                AuthState.is_loading,
                                rx.el.div(
                                    rx.icon("loader-circle", size=18, class_name="animate-spin mr-2"),
                                    "Ingresando...",
                                    class_name="flex items-center justify-center",
                                ),
                                rx.el.div(
                                    rx.icon("log-in", size=16, class_name="mr-2"),
                                    "Iniciar sesión",
                                    class_name="flex items-center justify-center",
                                ),
                            ),
                            type="submit",
                            disabled=AuthState.is_loading,
                            class_name=(
                                "w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-700 "
                                "disabled:bg-sky-400 text-white font-medium rounded-lg "
                                "text-sm transition-colors cursor-pointer "
                                "disabled:cursor-not-allowed shadow-sm"
                            ),
                        ),
                        on_submit=AuthState.handle_login,
                        class_name="space-y-0",
                    ),
                    class_name="w-full max-w-sm",
                ),
                class_name=(
                    "flex flex-col items-center lg:items-start justify-center "
                    "px-8 sm:px-12 lg:px-16 bg-white "
                    "min-h-screen lg:min-h-0"
                ),
            ),

            class_name="grid lg:grid-cols-2 min-h-screen",
        ),
    )
