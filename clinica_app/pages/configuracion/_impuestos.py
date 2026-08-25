from __future__ import annotations

import reflex as rx

from clinica_app.state.configuracion import ConfiguracionState

from ._helpers import _alert, _btn_spinner, _campo, _select, _toggle_switch


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


def _btn_modo(valor: str, label: str) -> rx.Component:
    return rx.el.button(
        label,
        on_click=lambda: ConfiguracionState.set_impuesto_modo(valor),
        class_name=rx.cond(
            ConfiguracionState.impuesto_modo == valor,
            "px-3 py-1.5 text-xs font-medium rounded-lg border border-sky-500 "
            "bg-sky-50 text-sky-700 cursor-pointer transition",
            "px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 "
            "bg-white text-gray-600 hover:bg-gray-50 cursor-pointer transition",
        ),
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

        # Modo del impuesto: incluido en el precio vs agregado.
        rx.el.div(
            rx.el.p("Cómo se aplica el impuesto",
                    class_name="text-sm font-medium text-gray-700 mb-1"),
            rx.el.p(ConfiguracionState.impuesto_modo_desc,
                    class_name="text-xs text-gray-500 mb-3"),
            rx.el.div(
                _btn_modo("incluido", "Incluido en el precio"),
                _btn_modo("agregado", "Agregado al precio"),
                class_name="flex flex-wrap gap-2",
            ),
            class_name="p-4 bg-gray-50 rounded-xl border border-gray-100",
        ),

        rx.el.div(
            rx.el.p("Vista previa", class_name="text-sm font-medium text-gray-700 mb-3"),
            rx.el.div(
                rx.el.div(
                    rx.el.span("Precio:", class_name="text-sm text-gray-600"),
                    rx.el.span("100.00", class_name="text-sm text-gray-800"),
                    class_name="flex justify-between py-1",
                ),
                rx.el.div(
                    rx.el.span("Op. gravada:", class_name="text-sm text-gray-600"),
                    rx.el.span(ConfiguracionState.impuesto_preview_base,
                               class_name="text-sm text-gray-800"),
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
