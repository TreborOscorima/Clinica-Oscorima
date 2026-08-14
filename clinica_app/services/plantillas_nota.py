"""Plantillas de nota clínica por tipo/especialidad (A3).

Esqueletos de texto que el profesional inserta en el contenido de la nota para
estructurar la historia clínica. Son puramente de UI (no tocan BD); se pueden
ampliar sin migraciones. Cubren lo transversal (anamnesis, evolución) y los dos
rubros objetivo (odontología, estética).
"""
from __future__ import annotations

PLANTILLAS: dict[str, dict[str, str]] = {
    "anamnesis": {
        "label": "Anamnesis general",
        "contenido": (
            "Motivo de consulta:\n\n"
            "Enfermedad actual:\n\n"
            "Antecedentes personales:\n\n"
            "Antecedentes familiares:\n\n"
            "Examen físico:\n\n"
            "Diagnóstico presuntivo:\n"
        ),
    },
    "evolucion": {
        "label": "Evolución",
        "contenido": (
            "Evolución:\n\n"
            "Conducta / plan:\n"
        ),
    },
    "odontologia": {
        "label": "Odontología — procedimiento",
        "contenido": (
            "Pieza(s) dental(es):\n"
            "Diagnóstico:\n"
            "Procedimiento realizado:\n"
            "Materiales utilizados:\n"
            "Anestesia:\n"
            "Indicaciones / próxima cita:\n"
        ),
    },
    "estetica": {
        "label": "Estética — sesión",
        "contenido": (
            "Zona tratada:\n"
            "Producto / equipo:\n"
            "Parámetros (energía / dosis / disparos):\n"
            "Reacción inmediata:\n"
            "Recomendaciones post-tratamiento:\n"
            "N° de sesión / próxima recomendada:\n"
        ),
    },
}


def opciones() -> list[dict[str, str]]:
    """Lista para poblar el selector de plantillas en la UI."""
    return [{"clave": k, "label": v["label"]} for k, v in PLANTILLAS.items()]


def contenido(clave: str) -> str:
    return PLANTILLAS.get(clave, {}).get("contenido", "")
