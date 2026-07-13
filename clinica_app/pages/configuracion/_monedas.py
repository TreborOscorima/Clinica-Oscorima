from __future__ import annotations

import reflex as rx

from clinica_app.state.configuracion import ConfiguracionState

from ._helpers import _alert, _campo, _section_title


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
        rx.el.div(
            rx.el.span("Moneda activa:", class_name="text-xs text-gray-500"),
            rx.el.span(ConfiguracionState.moneda_activa_nombre,
                       class_name="text-xs font-medium text-sky-600 ml-1"),
            class_name="flex items-center py-1",
        ),
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
