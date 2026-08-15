"""Estado del laboratorio del Motor Anatómico (Etapa E1).

Valida el puente JS↔Reflex en aislamiento, sin tocar datos clínicos: un click en
una pieza 3D llega como `on_pick` (JSON del input-puente), Python cicla el color
de esa pieza y lo devuelve al visor con `setData`. Es el prototipo del mecanismo
que E3 usará sobre `OdontogramaState` real.
"""
from __future__ import annotations

import json

import reflex as rx

from clinica_app.components.anatomy_viewer import (
    anatomy_boot_script,
    anatomy_setdata_script,
)
from clinica_app.state.base import BaseState

# Ciclo de estados de demo (hex). "" = sin estado (gris por defecto en el viewer).
_CICLO = ["#dc2626", "#f59e0b", "#16a34a", ""]  # rojo → ámbar → verde → limpio
_ETIQUETA = {"#dc2626": "caries", "#f59e0b": "observación", "#16a34a": "sano", "": "sin estado"}


class AnatomyLabState(BaseState):
    picked_id:    str            = ""
    colores:      dict[str, str] = {}
    seleccionado: str            = ""
    eventos:      list[str]      = []

    def _payload(self) -> str:
        return json.dumps({"colores": self.colores, "seleccionado": self.seleccionado})

    async def on_mount(self):
        self._expirar_si_vencio()
        if not self.is_authenticated:
            yield rx.redirect("/login")
            return
        if not self.tiene_permiso("historia"):
            yield rx.redirect("/")
            return
        yield rx.call_script(anatomy_boot_script(self._payload()))

    def on_pick(self, value: str):
        try:
            data = json.loads(value or "{}")
        except (ValueError, TypeError):
            return
        aid = str(data.get("anatomy_id") or "")
        if not aid:
            return

        actual = self.colores.get(aid, "")
        idx = _CICLO.index(actual) if actual in _CICLO else -1
        nuevo = _CICLO[(idx + 1) % len(_CICLO)]

        nuevos = dict(self.colores)
        if nuevo:
            nuevos[aid] = nuevo
        else:
            nuevos.pop(aid, None)
        self.colores = nuevos
        self.seleccionado = aid
        self.picked_id = aid

        self.eventos = ([f"Pieza {aid} → {_ETIQUETA[nuevo]}"] + self.eventos)[:8]
        yield rx.call_script(anatomy_setdata_script(self._payload()))
