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


def anatomy_viewer(
    on_pick,
    *,
    height: str = "440px",
    fullscreen=None,
    on_toggle_fullscreen=None,
) -> rx.Component:
    """Visor 3D + puente. `on_pick` recibe el value del input (JSON string).

    El módulo `viewer.js` NO se incluye con `rx.el.script`: React no ejecuta los
    <script> insertados vía JSX. Se inyecta dinámicamente en `anatomy_boot_script`
    (document.createElement → sí ejecuta), de forma lazy y solo en páginas 3D.

    `fullscreen` (Var[bool]) + `on_toggle_fullscreen` habilitan un botón de
    pantalla completa: el lienzo pasa a `fixed inset-0` y llena el viewport (el
    ResizeObserver del viewer reajusta el canvas solo). Sin ellos, tamaño fijo.
    """
    has_fs = fullscreen is not None

    canvas = rx.el.div(
        id=CANVAS_ID,
        class_name=(
            rx.cond(
                fullscreen,
                "w-full flex-1 min-h-0 rounded-xl border border-gray-200 overflow-hidden",
                "w-full rounded-xl border border-gray-200 overflow-hidden",
            )
            if has_fs
            else "w-full rounded-xl border border-gray-200 overflow-hidden"
        ),
        style=(
            rx.cond(
                fullscreen,
                {"background_color": "#f9fafb"},
                {"height": height, "background_color": "#f9fafb"},
            )
            if has_fs
            else {"height": height, "background_color": "#f9fafb"}
        ),
    )

    toggle_btn = (
        rx.el.button(
            rx.cond(fullscreen, rx.icon("minimize", size=16), rx.icon("maximize", size=16)),
            on_click=on_toggle_fullscreen,
            title="Pantalla completa",
            type="button",
            class_name=(
                "absolute top-2 right-2 z-10 p-2 bg-white/90 backdrop-blur border "
                "border-gray-200 rounded-lg text-gray-600 hover:bg-white shadow-sm "
                "cursor-pointer transition"
            ),
        )
        if on_toggle_fullscreen is not None
        else rx.fragment()
    )

    return rx.el.div(
        canvas,
        toggle_btn,
        # Puente oculto JS→Reflex: el viewer escribe aquí y dispara `input`.
        rx.el.input(
            id=BRIDGE_ID,
            default_value="",
            on_change=on_pick,
            class_name="hidden",
            aria_hidden="true",
            tab_index=-1,
        ),
        class_name=(
            rx.cond(
                fullscreen,
                "fixed inset-0 z-50 bg-gray-100 p-4 flex flex-col",
                "relative w-full",
            )
            if has_fs
            else "relative w-full"
        ),
    )


def anatomy_boot_script(
    payload_json: str, scene_type: str = "dental", model_url: str = ""
) -> str:
    """JS que inyecta el módulo (si falta), espera a que cargue y arranca init()+setData().

    Inyecta viewer.js con document.createElement (React no ejecutaría un <script>
    renderizado por JSX). Idempotente: no re-inyecta si ya está cargando/cargado.
    `scene_type` selecciona la escena del motor: "dental" (arcadas) o "facial"
    (rostro con zonas estéticas). `model_url` (opcional) apunta a un `.glb` realista
    servido desde /assets; si está vacío el motor usa la geometría procedural.
    """
    model_js = f"'{model_url}'" if model_url else "''"
    return (
        "(function(){"
        f"  var P={payload_json};"
        "  function start(n){"
        f"    if(window.AnatomyViewer){{window.AnatomyViewer.init('{CANVAS_ID}','{BRIDGE_ID}','{scene_type}',{model_js});"
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
