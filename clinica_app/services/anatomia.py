"""Catálogos anatómicos para el mapa estético (E5).

Siguiendo la convención del repo (FDI y ESTADOS son constantes en
`services/odontograma.py`), las **zonas faciales/corporales**, los **tipos de
procedimiento** y las **categorías de evaluación** se definen aquí como
constantes en código —no como tablas— para versionarlas con el código y sin
migraciones al ajustar el catálogo.

Cada zona tiene un `codigo` estable (el que se guarda en BD), una `label`
legible, un `grupo` ("facial" | "corporal") y una `region` (tercio del rostro o
segmento corporal) para agrupar en la UI. El `anatomy_id` que emite el visor 3D
al hacer pick es exactamente este `codigo` → cero traducción, igual que FDI.
"""
from __future__ import annotations

from typing import Any

# ── Zonas faciales (tercios estéticos del rostro) ─────────────────────────────
_FACIAL: list[dict[str, str]] = [
    # Tercio superior
    {"codigo": "frente",            "label": "Frente",                 "region": "tercio_superior"},
    {"codigo": "entrecejo",         "label": "Entrecejo (glabela)",    "region": "tercio_superior"},
    {"codigo": "cola_ceja",         "label": "Cola de ceja",           "region": "tercio_superior"},
    {"codigo": "patas_gallo",       "label": "Patas de gallo",         "region": "tercio_superior"},
    # Tercio medio
    {"codigo": "surco_lagrimal",    "label": "Surco lagrimal (ojera)", "region": "tercio_medio"},
    {"codigo": "pomulo",            "label": "Pómulo",                 "region": "tercio_medio"},
    {"codigo": "dorso_nasal",       "label": "Dorso nasal",            "region": "tercio_medio"},
    {"codigo": "surco_nasogeniano", "label": "Surco nasogeniano",      "region": "tercio_medio"},
    # Tercio inferior
    {"codigo": "labios",            "label": "Labios",                 "region": "tercio_inferior"},
    {"codigo": "codigo_barras",     "label": "Código de barras",       "region": "tercio_inferior"},
    {"codigo": "comisuras",         "label": "Comisuras",              "region": "tercio_inferior"},
    {"codigo": "menton",            "label": "Mentón",                 "region": "tercio_inferior"},
    {"codigo": "linea_mandibular",  "label": "Línea mandibular",       "region": "tercio_inferior"},
    {"codigo": "cuello",            "label": "Cuello",                 "region": "tercio_inferior"},
]

# ── Zonas corporales ──────────────────────────────────────────────────────────
_CORPORAL: list[dict[str, str]] = [
    {"codigo": "abdomen",       "label": "Abdomen",            "region": "tronco"},
    {"codigo": "flancos",       "label": "Flancos",            "region": "tronco"},
    {"codigo": "espalda_alta",  "label": "Espalda alta",       "region": "tronco"},
    {"codigo": "espalda_baja",  "label": "Espalda baja",       "region": "tronco"},
    {"codigo": "brazos",        "label": "Brazos",             "region": "extremidades_superiores"},
    {"codigo": "gluteos",       "label": "Glúteos",            "region": "extremidades_inferiores"},
    {"codigo": "muslos",        "label": "Muslos",             "region": "extremidades_inferiores"},
    {"codigo": "rodillas",      "label": "Rodillas",           "region": "extremidades_inferiores"},
]

ZONAS: dict[str, dict[str, str]] = {
    **{z["codigo"]: {**z, "grupo": "facial"} for z in _FACIAL},
    **{z["codigo"]: {**z, "grupo": "corporal"} for z in _CORPORAL},
}
ZONAS_VALIDAS: frozenset[str] = frozenset(ZONAS.keys())

# ── Tipos de procedimiento estético ───────────────────────────────────────────
TIPOS_PROCEDIMIENTO: dict[str, str] = {
    "toxina_botulinica": "Toxina botulínica",
    "acido_hialuronico": "Ácido hialurónico (relleno)",
    "bioestimulador":    "Bioestimulador de colágeno",
    "mesoterapia":       "Mesoterapia",
    "hilos_tensores":    "Hilos tensores",
    "peeling":           "Peeling químico",
    "enzimas":           "Enzimas (lipolítico)",
    "otro":              "Otro",
}

# ── Categorías de evaluación por zona ─────────────────────────────────────────
CATEGORIAS_EVALUACION: dict[str, str] = {
    "simetria":     "Simetría",
    "volumen":      "Volumen",
    "arrugas":      "Arrugas",
    "flacidez":     "Flacidez",
    "pigmentacion": "Pigmentación",
    "textura":      "Textura",
    "hidratacion":  "Hidratación",
}

# Escala de severidad 0–4 (0 = sin hallazgo).
SEVERIDADES: list[dict[str, Any]] = [
    {"valor": 0, "label": "Sin hallazgo"},
    {"valor": 1, "label": "Leve"},
    {"valor": 2, "label": "Moderado"},
    {"valor": 3, "label": "Marcado"},
    {"valor": 4, "label": "Severo"},
]
_SEVERIDAD_VALORES: frozenset[int] = frozenset(s["valor"] for s in SEVERIDADES)
_SEVERIDAD_LABELS: dict[int, str] = {s["valor"]: s["label"] for s in SEVERIDADES}


# ── Helpers de catálogo (para la UI y validación) ─────────────────────────────

def zonas_catalogo(grupo: str | None = None) -> list[dict[str, str]]:
    """Zonas del catálogo, opcionalmente filtradas por grupo (facial|corporal)."""
    grupo_de = {"facial": _FACIAL, "corporal": _CORPORAL}
    salida = []
    for g_nombre, lista in grupo_de.items():
        if grupo and grupo != g_nombre:
            continue
        for z in lista:
            salida.append({**z, "grupo": g_nombre})
    return salida


def zona_label(codigo: str) -> str:
    z = ZONAS.get(codigo)
    return z["label"] if z else (codigo or "")


def tipos_catalogo() -> list[dict[str, str]]:
    return [{"clave": k, "label": v} for k, v in TIPOS_PROCEDIMIENTO.items()]


def categorias_catalogo() -> list[dict[str, str]]:
    return [{"clave": k, "label": v} for k, v in CATEGORIAS_EVALUACION.items()]


def catalogos(grupo: str | None = None) -> dict[str, Any]:
    """Todo lo que la UI del mapa estético necesita en una sola llamada."""
    return {
        "zonas":       zonas_catalogo(grupo),
        "tipos":       tipos_catalogo(),
        "categorias":  categorias_catalogo(),
        "severidades": list(SEVERIDADES),
    }


def es_zona_valida(codigo: str) -> bool:
    return (codigo or "").strip() in ZONAS_VALIDAS


def es_tipo_valido(tipo: str) -> bool:
    return (tipo or "").strip() in TIPOS_PROCEDIMIENTO


def es_categoria_valida(categoria: str) -> bool:
    return (categoria or "").strip() in CATEGORIAS_EVALUACION


def severidad_label(valor: Any) -> str:
    """Label legible de una severidad 0–4 (vacío si no aplica)."""
    n = normalizar_severidad(valor)
    return _SEVERIDAD_LABELS.get(n, "") if n is not None else ""


def normalizar_severidad(valor: Any) -> int | None:
    """Severidad → int 0–4 válido, o None si viene vacía/ inválida."""
    if valor is None or valor == "":
        return None
    try:
        n = int(valor)
    except (ValueError, TypeError):
        return None
    return n if n in _SEVERIDAD_VALORES else None
