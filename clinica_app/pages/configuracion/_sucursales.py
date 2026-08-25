from __future__ import annotations

import reflex as rx

from clinica_app.state.configuracion import ConfiguracionState

from ._helpers import _campo, _section_title


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
                    on_click=lambda: ConfiguracionState.confirmar_eliminar_sede(s),
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
