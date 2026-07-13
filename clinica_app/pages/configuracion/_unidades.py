from __future__ import annotations

import reflex as rx

from clinica_app.state.configuracion import ConfiguracionState

from ._helpers import _alert, _campo, _section_title, _toggle_switch


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
