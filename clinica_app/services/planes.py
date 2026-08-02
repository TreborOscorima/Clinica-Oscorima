"""Planes SaaS y control de acceso de la clínica (licencia gestionada por el
panel Owner de TUWAYKI). Los nombres de plan coinciden con TUWAYKIFOOD para
consistencia en todo el ecosistema."""
from __future__ import annotations

from datetime import datetime, timezone

PLAN_TRIAL       = "trial"
PLAN_STANDARD    = "standard"
PLAN_PROFESIONAL = "profesional"

PLANES_VALIDOS = {PLAN_TRIAL, PLAN_STANDARD, PLAN_PROFESIONAL}

_LABELS = {
    PLAN_TRIAL:       "Trial",
    PLAN_STANDARD:    "Standard",
    PLAN_PROFESIONAL: "Profesional",
}


def plan_label(plan: str) -> str:
    return _LABELS.get(plan, (plan or "—").capitalize())


def _now_naive() -> datetime:
    # MySQL almacena DATETIME sin tz; comparamos siempre en UTC naive.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clinica_acceso_permitido(clinica) -> tuple[bool, str]:
    """Determina si una clínica puede iniciar sesión según su licencia.

    Retorna (permitido, motivo). `motivo` solo es relevante cuando NO se permite.
    """
    if not getattr(clinica, "licencia_activa", True):
        return False, "Esta cuenta está suspendida. Contactá al administrador."

    ahora = _now_naive()
    plan = getattr(clinica, "plan", None) or PLAN_TRIAL

    if plan == PLAN_TRIAL:
        fin = getattr(clinica, "trial_ends_at", None)
        if fin is not None and fin < ahora:
            return False, "El período de prueba venció. Contactá al administrador."
    else:
        fin = getattr(clinica, "plan_expires_at", None)
        if fin is not None and fin < ahora:
            return False, "La suscripción venció. Renová el plan para continuar."

    return True, ""
