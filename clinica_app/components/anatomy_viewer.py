"""Componente Reflex del Motor Anatómico 3D (reutilizable).

Renderiza el lienzo 3D + el <input> oculto que hace de puente JS→Reflex, y expone
helpers para arrancar/actualizar el visor desde Python vía `rx.call_script`.

El renderer (assets/js/anatomy/viewer.js) NUNCA toca la BD: solo emite el
`anatomy_id` seleccionado (por el puente) y pinta los colores/estado que Python le
pasa ya calculados con `setData`. El 2D sigue siendo la fuente de verdad y el
fallback si no hay WebGL.
"""
from __future__ import annotations

import reflex as rx

CANVAS_ID = "anatomy-canvas"
BRIDGE_ID = "anatomy-bridge"


def anatomy_viewer(on_pick, *, height: str = "440px") -> rx.Component:
    """Visor 3D + puente. `on_pick` recibe el value del input (JSON string).

    El módulo `viewer.js` NO se incluye con `rx.el.script`: React no ejecuta los
    <script> insertados vía JSX. Se inyecta dinámicamente en `anatomy_boot_script`
    (document.createElement → sí ejecuta), de forma lazy y solo en páginas 3D.
    """
    return rx.el.div(
        # Lienzo donde monta el <canvas> WebGL.
        rx.el.div(
            id=CANVAS_ID,
            class_name="w-full rounded-xl border border-gray-200 overflow-hidden",
            style={"height": height, "background_color": "#f9fafb"},
        ),
        # Puente oculto JS→Reflex: el viewer escribe aquí y dispara `input`.
        rx.el.input(
            id=BRIDGE_ID,
            default_value="",
            on_change=on_pick,
            class_name="hidden",
            aria_hidden="true",
            tab_index=-1,
        ),
        class_name="w-full",
    )


def anatomy_boot_script(payload_json: str) -> str:
    """JS que inyecta el módulo (si falta), espera a que cargue y arranca init()+setData().

    Inyecta viewer.js con document.createElement (React no ejecutaría un <script>
    renderizado por JSX). Idempotente: no re-inyecta si ya está cargando/cargado.
    """
    return (
        "(function(){"
        f"  var P={payload_json};"
        "  function start(n){"
        f"    if(window.AnatomyViewer){{window.AnatomyViewer.init('{CANVAS_ID}','{BRIDGE_ID}');"
        "      window.AnatomyViewer.setData(P);return;}"
        "    if(n<=0)return;setTimeout(function(){start(n-1);},100);}"
        "  if(!window.AnatomyViewer&&!window.__anatomyLoading){"
        "    window.__anatomyLoading=true;"
        "    var s=document.createElement('script');s.type='module';"
        "    s.src='/js/anatomy/viewer.js';"
        "    s.onerror=function(){console.error('[anatomy] no se pudo cargar viewer.js');};"
        "    document.head.appendChild(s);}"
        "  start(80);"
        "})();"
    )


def anatomy_setdata_script(payload_json: str) -> str:
    """JS para repintar el visor con nuevo estado calculado en Python."""
    return f"window.AnatomyViewer&&window.AnatomyViewer.setData({payload_json});"
