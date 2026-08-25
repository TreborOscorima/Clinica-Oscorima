"""Línea de tiempo unificada del paciente (auditoría #6)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from clinica_app.models.adjunto import Adjunto
from clinica_app.models.caja import Comprobante, MetodoPago
from clinica_app.models.evaluacion_estetica import EvaluacionEstetica
from clinica_app.models.nota_clinica import NotaClinica, TipoNota
from clinica_app.models.odontograma_version import OdontogramaVersion
from clinica_app.models.plan_tratamiento import PlanTratamiento
from clinica_app.models.sesion_estetica import SesionEstetica
from clinica_app.models.turno import EstadoTurno, Turno
from clinica_app.services import historia_clinica as svc


async def _nota(session, clinica, paciente, *, cuando, contenido="Evolución del paciente"):
    n = NotaClinica(
        clinica_id=clinica.id, paciente_id=paciente.id,
        tipo=TipoNota.EVOLUCION, contenido=contenido, created_at=cuando,
    )
    session.add(n)
    await session.flush()
    return n


# ── vacío ─────────────────────────────────────────────────────────────────────

async def test_timeline_vacio(session, clinica, paciente):
    data = await svc.timeline(session, clinica.id, paciente.id)
    assert data["eventos"] == []
    assert data["total"] == 0
    assert all(v == 0 for v in data["conteos"].values())


# ── agregación multi-fuente ────────────────────────────────────────────────────

async def test_timeline_agrega_todas_las_fuentes(session, clinica, paciente):
    session.add(Turno(
        clinica_id=clinica.id, paciente_id=paciente.id,
        fecha_hora=datetime(2026, 1, 5, 9, 0), estado=EstadoTurno.ATENDIDO,
    ))
    await _nota(session, clinica, paciente, cuando=datetime(2026, 1, 6, 10, 0))
    session.add(Comprobante(
        clinica_id=clinica.id, paciente_id=paciente.id, numero="R-1",
        fecha=datetime(2026, 1, 7, 11, 0), total=Decimal("500.00"),
        forma_pago=MetodoPago.EFECTIVO,
    ))
    session.add(Adjunto(
        clinica_id=clinica.id, paciente_id=paciente.id, nombre="consent.pdf",
        stored_name="x.pdf", categoria="consentimiento",
    ))
    session.add(Adjunto(
        clinica_id=clinica.id, paciente_id=paciente.id, nombre="receta.pdf",
        stored_name="y.pdf", categoria="receta",
    ))
    session.add(Adjunto(
        clinica_id=clinica.id, paciente_id=paciente.id, nombre="rx.jpg",
        stored_name="z.jpg", categoria="radiografia",
    ))
    session.add(OdontogramaVersion(
        clinica_id=clinica.id, paciente_id=paciente.id, titulo="Inicial",
        piezas="[]", con_datos=3,
    ))
    session.add(PlanTratamiento(
        clinica_id=clinica.id, paciente_id=paciente.id, titulo="Ortodoncia", estado="activo",
    ))
    session.add(SesionEstetica(
        clinica_id=clinica.id, paciente_id=paciente.id, fecha=date(2026, 1, 8), titulo="Botox",
    ))
    session.add(EvaluacionEstetica(
        clinica_id=clinica.id, paciente_id=paciente.id, zona_codigo="frente",
        categoria="arrugas", severidad=2,
    ))
    await session.flush()

    data = await svc.timeline(session, clinica.id, paciente.id)
    c = data["conteos"]
    assert data["total"] == 10
    assert c["turno"] == 1
    assert c["nota"] == 1
    assert c["cobro"] == 1
    assert c["consentimiento"] == 1
    assert c["receta"] == 1
    assert c["adjunto"] == 1          # la radiografía cae en "adjunto"
    assert c["odontograma"] == 1
    assert c["plan"] == 1
    assert c["sesion"] == 1
    assert c["evaluacion"] == 1


# ── ordenamiento cronológico descendente ───────────────────────────────────────

async def test_timeline_ordena_mas_reciente_primero(session, clinica, paciente):
    session.add(Turno(
        clinica_id=clinica.id, paciente_id=paciente.id,
        fecha_hora=datetime(2026, 1, 1, 9, 0),
    ))
    await _nota(session, clinica, paciente, cuando=datetime(2026, 3, 1, 10, 0))
    session.add(Comprobante(
        clinica_id=clinica.id, paciente_id=paciente.id,
        fecha=datetime(2026, 2, 1, 11, 0), total=Decimal("100.00"),
    ))
    await session.flush()

    eventos = (await svc.timeline(session, clinica.id, paciente.id))["eventos"]
    assert [e["tipo"] for e in eventos] == ["nota", "cobro", "turno"]


# ── aislamiento por paciente y por sede ─────────────────────────────────────────

async def test_timeline_aisla_por_paciente(session, clinica, paciente):
    from clinica_app.models.paciente import Paciente
    otro = Paciente(clinica_id=clinica.id, nombre="Otro", documento="88000002")
    session.add(otro)
    await session.flush()
    await _nota(session, clinica, otro, cuando=datetime(2026, 1, 1, 9, 0))
    await _nota(session, clinica, paciente, cuando=datetime(2026, 1, 2, 9, 0), contenido="Mía")

    data = await svc.timeline(session, clinica.id, paciente.id)
    assert data["total"] == 1
    assert data["eventos"][0]["detalle"] == "Mía"


async def test_timeline_respeta_sede(session, clinica, paciente):
    session.add(NotaClinica(
        clinica_id=clinica.id, paciente_id=paciente.id, sede_id=7,
        tipo=TipoNota.EVOLUCION, contenido="sede 7", created_at=datetime(2026, 1, 1, 9, 0),
    ))
    session.add(NotaClinica(
        clinica_id=clinica.id, paciente_id=paciente.id, sede_id=9,
        tipo=TipoNota.EVOLUCION, contenido="sede 9", created_at=datetime(2026, 1, 2, 9, 0),
    ))
    await session.flush()

    data = await svc.timeline(session, clinica.id, paciente.id, sede_id=7)
    assert data["total"] == 1
    assert data["eventos"][0]["detalle"] == "sede 7"


# ── el evento trae los campos que la UI necesita ───────────────────────────────

async def test_evento_trae_href_y_estado(session, clinica, paciente):
    session.add(Comprobante(
        clinica_id=clinica.id, paciente_id=paciente.id, numero="R-9",
        fecha=datetime(2026, 5, 1, 12, 0), total=Decimal("250.00"),
        forma_pago=MetodoPago.TARJETA, anulado=True,
    ))
    await session.flush()

    ev = (await svc.timeline(session, clinica.id, paciente.id))["eventos"][0]
    assert ev["tipo"] == "cobro"
    assert ev["estado"] == "anulado"
    assert f"paciente_id={paciente.id}" in ev["href"]
    assert "250.00" in ev["detalle"]
    assert "orden" not in ev   # el datetime de orden no se serializa al front
