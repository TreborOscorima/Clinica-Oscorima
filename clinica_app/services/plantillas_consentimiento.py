"""Plantillas de consentimiento informado por especialidad (A4).

Textos base que se vuelcan en el PDF de consentimiento. Son puramente de UI/
documento (no tocan BD) y se pueden ampliar sin migraciones. El marcador
`{procedimiento}` se reemplaza por el procedimiento concreto que carga el
profesional. Cubren lo transversal (general) y los dos rubros objetivo
(odontología, estética), más una variante quirúrgica menor.

Aviso: son plantillas de referencia que cada clínica debe adecuar a la
normativa local y a su criterio profesional; no constituyen asesoría legal.
"""
from __future__ import annotations

PLANTILLAS: dict[str, dict[str, str]] = {
    "general": {
        "label":  "General",
        "titulo": "Consentimiento informado",
        "cuerpo": (
            "Declaro que el/la profesional me ha explicado en lenguaje claro la "
            "naturaleza del procedimiento propuesto: {procedimiento}.\n\n"
            "He sido informado/a sobre los beneficios esperados, las alternativas "
            "disponibles y los riesgos y complicaciones que, aunque infrecuentes, "
            "pueden presentarse. Tuve la oportunidad de realizar todas las preguntas "
            "que consideré necesarias y fueron respondidas satisfactoriamente.\n\n"
            "Entiendo que la medicina no es una ciencia exacta y que no se me ha "
            "garantizado un resultado determinado. Presto mi consentimiento de forma "
            "libre y voluntaria, y sé que puedo revocarlo en cualquier momento antes "
            "del procedimiento sin que ello afecte mi atención."
        ),
    },
    "estetica": {
        "label":  "Estética",
        "titulo": "Consentimiento informado — Tratamiento estético",
        "cuerpo": (
            "Declaro que se me ha informado en detalle sobre el tratamiento estético "
            "propuesto: {procedimiento}.\n\n"
            "Comprendo que los resultados pueden variar según las características "
            "individuales de mi piel y organismo, que pueden requerirse varias "
            "sesiones y que son posibles reacciones como enrojecimiento, inflamación, "
            "hematomas, cambios de pigmentación o molestias transitorias.\n\n"
            "Me comprometo a seguir las indicaciones previas y posteriores al "
            "tratamiento y a informar cualquier antecedente, alergia o medicación "
            "relevante. Declaro no haber omitido información sobre mi estado de salud. "
            "Presto mi consentimiento de forma libre y voluntaria."
        ),
    },
    "odontologia": {
        "label":  "Odontología",
        "titulo": "Consentimiento informado — Tratamiento odontológico",
        "cuerpo": (
            "Declaro que el/la odontólogo/a me ha explicado el diagnóstico y el plan "
            "de tratamiento propuesto: {procedimiento}.\n\n"
            "He sido informado/a sobre el uso de anestesia local, los beneficios del "
            "tratamiento, las alternativas y los riesgos posibles, entre ellos dolor "
            "o inflamación posoperatoria, sensibilidad, sangrado, infección o la "
            "eventual necesidad de tratamientos adicionales.\n\n"
            "Me comprometo a cumplir las indicaciones y los controles posteriores. "
            "Declaro haber informado mis antecedentes médicos, alergias y medicación "
            "actual. Presto mi consentimiento de forma libre y voluntaria."
        ),
    },
    "quirurgico": {
        "label":  "Quirúrgico menor",
        "titulo": "Consentimiento informado — Procedimiento quirúrgico menor",
        "cuerpo": (
            "Declaro que se me ha explicado la naturaleza del procedimiento "
            "quirúrgico menor propuesto: {procedimiento}.\n\n"
            "Entiendo los objetivos, las alternativas y los riesgos inherentes, que "
            "incluyen sangrado, infección, cicatrización anómala, reacción a la "
            "anestesia y la posibilidad de resultados distintos a los esperados.\n\n"
            "Autorizo la realización del procedimiento y de aquellas maniobras "
            "adicionales que resulten necesarias ante hallazgos imprevistos, según el "
            "criterio profesional y para preservar mi salud. Presto mi consentimiento "
            "de forma libre y voluntaria."
        ),
    },
}

_DEFAULT = "general"


def opciones() -> list[dict[str, str]]:
    """Lista para poblar el selector de tipo de consentimiento en la UI."""
    return [{"clave": k, "label": v["label"]} for k, v in PLANTILLAS.items()]


def _plantilla(clave: str) -> dict[str, str]:
    return PLANTILLAS.get(clave) or PLANTILLAS[_DEFAULT]


def titulo(clave: str) -> str:
    return _plantilla(clave)["titulo"]


def cuerpo(clave: str, procedimiento: str = "") -> str:
    """Texto del consentimiento con el `{procedimiento}` ya reemplazado."""
    proc = (procedimiento or "").strip() or "el procedimiento indicado por el profesional"
    return _plantilla(clave)["cuerpo"].replace("{procedimiento}", proc)
