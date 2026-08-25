from __future__ import annotations

import reflex as rx

from clinica_app.components.layout import shell
from clinica_app.components.ui import confirm_dialog, page_header
from clinica_app.state.configuracion import ConfiguracionState

from ._empresa import _seccion_empresa
from ._impuestos import _modal_impuesto, _seccion_impuestos
from ._metodos_pago import _seccion_metodos_pago
from ._monedas import _seccion_monedas
from ._sucursales import _modal_sede, _seccion_sucursales
from ._unidades import _seccion_unidades
from ._usuarios import (
    _modal_nuevo_usuario,
    _modal_password,
    _modal_permisos_rol,
    _seccion_usuarios,
)


def _sub_nav() -> rx.Component:
    def _item(label: str, tab: str, icon: str) -> rx.Component:
        is_active = ConfiguracionState.tab_activo == tab
        return rx.el.button(
            rx.el.div(
                rx.icon(icon, size=15, class_name=rx.cond(is_active, "text-sky-600", "text-gray-400")),
                rx.el.span(label, class_name=rx.cond(is_active, "text-sky-700 font-medium", "text-gray-600")),
                class_name="flex items-center gap-2.5",
            ),
            on_click=lambda: ConfiguracionState.set_tab(tab),
            class_name=rx.cond(
                is_active,
                "w-full text-left px-3 py-2.5 rounded-lg bg-sky-50 border-l-2 border-sky-500 cursor-pointer",
                "w-full text-left px-3 py-2.5 rounded-lg text-sm hover:bg-gray-50 cursor-pointer transition",
            ),
        )

    return rx.el.div(
        _item("Datos de Empresa",    "empresa",    "building-2"),
        _item("Sucursales",          "sucursales", "map-pin"),
        _item("Gestion de Usuarios", "usuarios",   "users"),
        _item("Selector de Monedas", "monedas",    "circle-dollar-sign"),
        _item("Unidades de Medida",  "unidades",   "ruler"),
        _item("Metodos de Pago",     "pagos",      "credit-card"),
        _item("Impuestos",           "impuestos",  "percent"),
        class_name="w-52 shrink-0 bg-white rounded-xl border border-gray-100 shadow-sm p-2 space-y-0.5 self-start sticky top-4",
    )


def configuracion_page() -> rx.Component:
    return shell(
        _modal_nuevo_usuario(),
        _modal_password(),
        _modal_sede(),
        _modal_impuesto(),
        _modal_permisos_rol(),
        confirm_dialog(ConfiguracionState),

        page_header(
            "Configuración del Sistema",
            "Gestiona usuarios, monedas, unidades y métodos de pago desde un solo lugar.",
        ),

        rx.cond(
            ConfiguracionState.is_admin,
            rx.el.div(
                _sub_nav(),
                rx.el.div(
                    rx.cond(ConfiguracionState.tab_activo == "empresa",    _seccion_empresa()),
                    rx.cond(ConfiguracionState.tab_activo == "sucursales", _seccion_sucursales()),
                    rx.cond(ConfiguracionState.tab_activo == "usuarios",   _seccion_usuarios()),
                    rx.cond(ConfiguracionState.tab_activo == "monedas",    _seccion_monedas()),
                    rx.cond(ConfiguracionState.tab_activo == "unidades",   _seccion_unidades()),
                    rx.cond(ConfiguracionState.tab_activo == "pagos",      _seccion_metodos_pago()),
                    rx.cond(ConfiguracionState.tab_activo == "impuestos",  _seccion_impuestos()),
                    class_name="flex-1 min-w-0",
                ),
                class_name="flex gap-4 items-start",
            ),
            rx.el.div(
                rx.icon("shield-off", size=32, class_name="text-gray-300 mb-3"),
                rx.el.p("Acceso restringido a administradores.",
                        class_name="text-sm text-gray-500"),
                class_name="flex flex-col items-center justify-center py-24 text-center "
                           "bg-white rounded-xl shadow-sm border border-gray-100",
            ),
        ),
        on_mount=ConfiguracionState.on_mount,
    )
