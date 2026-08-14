"""Tests de la comparación de versiones del odontograma (lado a lado)."""
from __future__ import annotations

from clinica_app.services import odontograma as svc


async def _pieza(cmp_list, numero):
    return next(p for p in cmp_list if p["numero"] == numero)


async def test_comparar_dos_versiones_detecta_cambio(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    v1 = await svc.crear_version(session, clinica.id, paciente.id, titulo="Antes", usuario_id=admin_user.id)
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="obturado", usuario_id=admin_user.id)
    v2 = await svc.crear_version(session, clinica.id, paciente.id, titulo="Después", usuario_id=admin_user.id)

    cmp = await svc.comparar(session, clinica.id, paciente.id, v1["id"], v2["id"])
    assert cmp["n_cambios"] == 1
    assert cmp["titulo_a"] == "Antes"
    assert cmp["titulo_b"] == "Después"
    # El cambio es en la pieza 16: caries → obturado.
    dif = cmp["cambios"][0]
    assert dif["numero"] == "16"
    assert dif["a_label"] == "Caries"
    assert dif["b_label"] == "Obturado"
    # La pieza 16 aparece marcada como cambio en ambas arcadas.
    p16_a = await _pieza(cmp["superior_a"], "16")
    p16_b = await _pieza(cmp["superior_b"], "16")
    assert p16_a["cambio"] is True
    assert p16_b["cambio"] is True
    # Una pieza sin cambios no está marcada.
    p11_a = await _pieza(cmp["superior_a"], "11")
    assert p11_a["cambio"] is False


async def test_comparar_version_vs_actual(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    v1 = await svc.crear_version(session, clinica.id, paciente.id, titulo="Snapshot", usuario_id=admin_user.id)
    # Estado vivo cambia tras el snapshot.
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="corona", usuario_id=admin_user.id)

    cmp = await svc.comparar(session, clinica.id, paciente.id, v1["id"], 0)
    assert cmp["titulo_a"] == "Snapshot"
    assert cmp["titulo_b"] == "Estado actual"
    assert cmp["n_cambios"] == 1
    assert cmp["cambios"][0]["a_label"] == "Caries"
    assert cmp["cambios"][0]["b_label"] == "Corona"


async def test_comparar_identicas_sin_cambios(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    v1 = await svc.crear_version(session, clinica.id, paciente.id, titulo="A", usuario_id=admin_user.id)

    cmp = await svc.comparar(session, clinica.id, paciente.id, v1["id"], v1["id"])
    assert cmp["n_cambios"] == 0
    assert cmp["cambios"] == []
    assert all(not p["cambio"] for p in cmp["superior_a"] + cmp["inferior_a"])


async def test_comparar_actual_vs_actual_sin_cambios(session, clinica, paciente, admin_user):
    await svc.guardar_pieza(session, clinica.id, paciente.id, "16", estado="caries", usuario_id=admin_user.id)
    cmp = await svc.comparar(session, clinica.id, paciente.id, 0, 0)
    assert cmp["titulo_a"] == "Estado actual"
    assert cmp["titulo_b"] == "Estado actual"
    assert cmp["n_cambios"] == 0
