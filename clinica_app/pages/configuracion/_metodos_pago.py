from __future__ import annotations

import reflex as rx

from clinica_app.state.configuracion import ConfiguracionState

from ._helpers import _alert, _campo, _section_title, _select, _toggle_switch


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
        rx.el.div(
            rx.el.span("Visible en Venta", class_name="text-xs text-gray-500"),
            _toggle_switch(m["visible_en_venta"],
                           lambda: ConfiguracionState.toggle_visible_metodo(m["id"])),
            rx.el.button(
                rx.icon("trash-2", size=13),
                on_click=lambda: ConfiguracionState.confirmar_eliminar_metodo_pago(m),
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
