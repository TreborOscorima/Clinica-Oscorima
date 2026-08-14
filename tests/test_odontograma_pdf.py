"""Tests de la exportación del odontograma a PDF."""
from __future__ import annotations

import pytest

from clinica_app.services import odontograma as svc
from clinica_app.services.exceptions import NotFoundError
from clinica_app.services.pdf_odontograma import generar_odontograma_pdf


def _arcada_muestra():
    lay = svc.layout()

    def piezas(nums):
        out = []
        for n in nums:
            st = "caries" if n == "16" else "sano"
            info = svc.ESTADOS[st]
            out.append({
                "numero": n, "estado": st,
                "color": info["color"], "text_color": info["text"],
                "estado_label": info["label"], "nota": "control" if n == "16" else "",
            })
        return out

    return piezas(lay["superior"]), piezas(lay["inferior"])


# ── generar_odontograma_pdf (puro, sin DB) ────────────────────────────────────

def test_pdf_devuelve_bytes_validos():
    sup, inf = _arcada_muestra()
    pdf = generar_odontograma_pdf(
        paciente_nombre="Robert Oscorima", paciente_documento="12345678",
        superior=sup, inferior=inf, leyenda=svc.estados_catalogo(),
    )
    assert isinstance(pdf, bytes)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


def test_pdf_con_version():
    sup, inf = _arcada_muestra()
    pdf = generar_odontograma_pdf(
        paciente_nombre="Robert Oscorima",
        superior=sup, inferior=inf, leyenda=svc.estados_catalogo(),
        version_titulo="Estado inicial", version_fecha="2026-08-14 17:06",
    )
    assert pdf[:5] == b"%PDF-"


def test_pdf_arcada_vacia_sin_hallazgos():
    lay = svc.layout()
    sanas = lambda nums: [  # noqa: E731
        {**svc.ESTADOS["sano"], "numero": n, "estado": "sano",
         "color": svc.ESTADOS["sano"]["color"], "text_color": svc.ESTADOS["sano"]["text"],
         "estado_label": "Sano", "nota": ""}
        for n in nums
    ]
    pdf = generar_odontograma_pdf(
        paciente_nombre="Sin Hallazgos",
        superior=sanas(lay["superior"]), inferior=sanas(lay["inferior"]),
        leyenda=svc.estados_catalogo(),
    )
    assert pdf[:5] == b"%PDF-"


# ── datos_export (con DB) ─────────────────────────────────────────────────────

async def test_datos_export_vivo(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    datos = await svc.datos_export(session, clinica.id, paciente.id)
    assert datos["paciente_nombre"] == paciente.nombre
    assert len(datos["superior"]) == 16
    assert len(datos["inferior"]) == 16
    assert datos["version_titulo"] == ""
    # La leyenda trae el catálogo completo de estados.
    assert any(e["clave"] == "caries" for e in datos["leyenda"])
    # Y el PDF se genera con esos datos.
    pdf = generar_odontograma_pdf(clinica_nombre="TEST", **datos)
    assert pdf[:5] == b"%PDF-"


async def test_datos_export_de_version(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    v = await svc.crear_version(session, clinica.id, paciente.id, titulo="Antes", usuario_id=admin_user.id)
    # Cambia el estado vivo tras versionar.
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="obturado", usuario_id=admin_user.id)

    datos = await svc.datos_export(session, clinica.id, paciente.id, version_id=v["id"])
    assert datos["version_titulo"] == "Antes"
    assert datos["version_fecha"] != ""
    # La versión conserva 'caries' (inmutable), no el 'obturado' vivo.
    pieza16 = next(p for p in datos["superior"] if p["numero"] == "16")
    assert pieza16["estado"] == "caries"


async def test_datos_export_paciente_inexistente(session, clinica, paciente, admin_user):
    with pytest.raises(NotFoundError):
        await svc.datos_export(session, clinica.id, paciente.id + 9999)
