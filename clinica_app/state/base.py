from __future__ import annotations

import reflex as rx

from clinica_app.services.download_token import crear_token


class BaseState(rx.State):
    """
    Raíz del árbol de estados.
    Contiene la sesión autenticada y el contexto de tenant (clinica_id).

    SEGURIDAD: clinica_id nunca se expone al cliente — vive exclusivamente
    en el servidor Python de Reflex y se propaga a todos los SubStates.
    """

    user_id:            int  = 0
    clinica_id:         int  = 0
    user_email:         str  = ""
    user_nombre:        str  = ""
    user_role:          str  = ""
    profesional_id:     int  = 0
    is_authenticated:   bool = False
    sidebar_open:       bool = False
    sede_actual_id:     int  = 0
    sede_actual_nombre: str  = ""

    # RBAC — permisos cacheados al login
    _permisos: dict[str, dict[str, bool]] = {}
    modulos_permitidos: list[str] = []
    # Módulos que el owner deshabilitó para esta clínica (Fase 3 Owner Panel).
    # El módulo se ve si (el rol lo permite) AND (no está acá).
    _modulos_owner_off: set[str] = set()

    @rx.var(cache=False)
    def download_token(self) -> str:
        if not self.is_authenticated:
            return ""
        return crear_token(self.user_id, self.clinica_id)

    @rx.var
    def is_admin(self) -> bool:
        return self.user_role == "administracion"

    @rx.var
    def is_staff(self) -> bool:
        return self.user_role in ("administracion", "recepcionista")

    @rx.var
    def is_profesional(self) -> bool:
        return self.user_role == "profesional"

    def tiene_permiso(self, module: str, write: bool = False) -> bool:
        # El owner puede deshabilitar el módulo para toda la clínica (Fase 3).
        if module in self._modulos_owner_off:
            return False
        perm = self._permisos.get(module)
        if perm is None:
            return False
        if write:
            return perm.get("write", False)
        return perm.get("read", False)

    def _aplicar_permisos(
        self,
        permisos: dict[str, dict[str, bool]],
        modulos_off: set[str] | None = None,
    ) -> None:
        self._permisos = permisos
        self._modulos_owner_off = set(modulos_off or set())
        self.modulos_permitidos = [
            m for m, p in permisos.items()
            if p.get("read") and m not in self._modulos_owner_off
        ]

    @rx.var
    def rol_display(self) -> str:
        mapping = {
            "administracion": "Administrador",
            "recepcionista":  "Recepcionista",
            "profesional":    "Profesional",
            "contador":       "Contador",
        }
        return mapping.get(self.user_role, self.user_role)

    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    def close_sidebar(self):
        self.sidebar_open = False

    def require_auth(self):
        """Retorna redirect si no autenticado, None si OK."""
        if not self.is_authenticated:
            return rx.redirect("/login")

    def require_admin(self):
        """Retorna redirect si no es admin, None si OK."""
        if not self.is_admin:
            return rx.redirect("/")

    def require_permiso(self, module: str, write: bool = False):
        """Retorna redirect si no tiene permiso, None si OK."""
        if not self.tiene_permiso(module, write):
            return rx.redirect("/")

    def logout(self):
        self.reset()
        return rx.redirect("/login")

    def setup_keyboard_shortcuts(self):
        js = """
(function() {
    if (window.__waykiSC) return;
    window.__waykiSC = true;
    document.addEventListener('keydown', function(e) {
        var active = document.activeElement || document.body;
        var tag = active.tagName.toLowerCase();
        var isEditable = tag === 'input' || tag === 'textarea' || tag === 'select' || !!active.isContentEditable;

        // Alt+1..7 — navegación entre módulos
        if (e.altKey && !e.ctrlKey && !e.metaKey) {
            var nav = {'1':'/', '2':'/pacientes', '3':'/turnos', '4':'/cobro', '5':'/calendario', '6':'/caja', '7':'/reportes'};
            if (nav[e.key]) { e.preventDefault(); window.location.href = nav[e.key]; return; }
        }

        // Escape — cierra el modal visible con mayor z-index
        if (e.key === 'Escape') {
            var bs = document.querySelectorAll('[data-modal-close]');
            var target = null, topZ = -1;
            for (var i = 0; i < bs.length; i++) {
                var z = parseInt(window.getComputedStyle(bs[i]).zIndex) || 0;
                if (z > topZ) { topZ = z; target = bs[i]; }
            }
            if (!target) {
                var fbs = document.querySelectorAll('.z-40.fixed.inset-0');
                for (var j = fbs.length - 1; j >= 0; j--) {
                    if (window.getComputedStyle(fbs[j]).display !== 'none') { target = fbs[j]; break; }
                }
            }
            if (target) { e.preventDefault(); target.click(); return; }
        }

        // Ctrl/Cmd+Enter — envía el formulario del modal más arriba (último en DOM)
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            var sbs = document.querySelectorAll('[data-modal-submit]:not([disabled])');
            if (sbs.length) { e.preventDefault(); sbs[sbs.length - 1].click(); return; }
        }

        // N — acción "nuevo" de la página actual
        if ((e.key === 'n' || e.key === 'N') && !isEditable && !e.ctrlKey && !e.altKey && !e.metaKey) {
            var nb = document.querySelector('[data-new-action]');
            if (nb) { e.preventDefault(); nb.click(); return; }
        }

        // P — gestionar proveedores (módulo Compras)
        if ((e.key === 'p' || e.key === 'P') && !isEditable && !e.ctrlKey && !e.altKey && !e.metaKey) {
            var pb = document.querySelector('[data-prov-action]');
            if (pb) { e.preventDefault(); pb.click(); return; }
        }

        // / — enfocar buscador de la página
        if (e.key === '/' && !isEditable && !e.ctrlKey && !e.altKey && !e.metaKey) {
            var si = document.querySelector('[data-search-input]');
            if (si) { e.preventDefault(); si.focus(); si.select(); return; }
        }
    });
})();
"""
        return rx.call_script(js)
