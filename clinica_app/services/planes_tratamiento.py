"""Plan de tratamiento por fases + presupuesto (B2).

Un plan (`PlanTratamiento`) agrupa tratamientos propuestos (`PlanTratamientoItem`)
organizados en fases. Cada item puede referir una pieza del odontograma (B1) y un
servicio del catálogo (para heredar precio). El presupuesto y el avance se calculan
desde los items; el `estado` del plan resume su ciclo de vida.

Reutiliza tenant + auditoría. El cobro del plan (`cobrar_plan`) NO reimplementa
Caja: arma el payload y delega en `services.cobro.crear`, y luego enlaza cada
item cobrado con el `comprobante_id` resultante.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.plan_tratamiento import PlanTratamiento, PlanTratamientoItem
from clinica_app.models.servicio import Servicio
from clinica_app.models.paciente import Paciente
from clinica_app.services import auditoria
from clinica_app.services import cobro as _cobro
from clinica_app.services.exceptions import NotFoundError, ServiceError, ValidationError

# Estados de item que se pueden cobrar (propuesto = aún no aprobado, no se cobra).
_ITEM_COBRABLE = frozenset({"aprobado", "en_curso", "terminado"})

# ── Catálogos de estado ───────────────────────────────────────────────────────
# Estado global del plan (lo fija el profesional).
ESTADOS_PLAN: dict[str, dict[str, str]] = {
    "borrador":   {"label": "Borrador",   "color": "#e5e7eb", "text": "#374151"},
    "aprobado":   {"label": "Aprobado",   "color": "#3b82f6", "text": "#ffffff"},
    "en_curso":   {"label": "En curso",   "color": "#f59e0b", "text": "#ffffff"},
    "terminado":  {"label": "Terminado",  "color": "#22c55e", "text": "#ffffff"},
    "cancelado":  {"label": "Cancelado",  "color": "#9ca3af", "text": "#ffffff"},
}

# Avance de cada tratamiento (item).
ESTADOS_ITEM: dict[str, dict[str, str]] = {
    "propuesto":  {"label": "Propuesto",  "color": "#e5e7eb", "text": "#374151"},
    "aprobado":   {"label": "Aprobado",   "color": "#3b82f6", "text": "#ffffff"},
    "en_curso":   {"label": "En curso",   "color": "#f59e0b", "text": "#ffffff"},
    "terminado":  {"label": "Terminado",  "color": "#22c55e", "text": "#ffffff"},
}


def estados_plan_catalogo() -> list[dict[str, str]]:
    return [{"clave": k, **v} for k, v in ESTADOS_PLAN.items()]


def estados_item_catalogo() -> list[dict[str, str]]:
    return [{"clave": k, **v} for k, v in ESTADOS_ITEM.items()]


# ── Validaciones ──────────────────────────────────────────────────────────────

def _validar_estado_plan(estado: str) -> str:
    if estado not in ESTADOS_PLAN:
        raise ValidationError(f"Estado de plan inválido: {estado}")
    return estado


def _validar_estado_item(estado: str) -> str:
    if estado not in ESTADOS_ITEM:
        raise ValidationError(f"Estado de tratamiento inválido: {estado}")
    return estado


def _parse_precio(valor: Any) -> Decimal:
    if valor is None or valor == "":
        return Decimal("0")
    try:
        precio = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Precio inválido")
    if precio < 0:
        raise ValidationError("El precio no puede ser negativo")
    return precio.quantize(Decimal("0.01"))


def _parse_fase(valor: Any) -> int:
    try:
        fase = int(valor)
    except (ValueError, TypeError):
        fase = 1
    return fase if fase >= 1 else 1


# ── Serialización ─────────────────────────────────────────────────────────────

def _dump_item(it: PlanTratamientoItem) -> dict[str, Any]:
    info = ESTADOS_ITEM.get(it.estado or "propuesto", ESTADOS_ITEM["propuesto"])
    return {
        "id":            it.id or 0,
        "plan_id":       it.plan_id,
        "fase":          it.fase or 1,
        "orden":         it.orden or 0,
        "pieza_numero":  it.pieza_numero or "",
        "servicio_id":   it.servicio_id or 0,
        "descripcion":   it.descripcion or "",
        "precio":        f"{it.precio or Decimal('0'):.2f}",
        "precio_num":    float(it.precio or 0),
        "estado":        it.estado or "propuesto",
        "estado_label":  info["label"],
        "color":         info["color"],
        "text_color":    info["text"],
        "comprobante_id": it.comprobante_id or 0,
        "cobrado":       bool(it.comprobante_id),
        # Cobrable = aprobado/en_curso/terminado, con precio > 0 y no cobrado aún.
        "cobrable":      (not it.comprobante_id)
                          and (it.estado in _ITEM_COBRABLE)
                          and (it.precio or Decimal("0")) > 0,
    }


def _totales(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum((Decimal(i["precio"]) for i in items), Decimal("0"))
    aprobado = sum(
        (Decimal(i["precio"]) for i in items if i["estado"] in ("aprobado", "en_curso", "terminado")),
        Decimal("0"),
    )
    terminado = sum(
        (Decimal(i["precio"]) for i in items if i["estado"] == "terminado"),
        Decimal("0"),
    )
    cobrado = sum((Decimal(i["precio"]) for i in items if i.get("cobrado")), Decimal("0"))
    por_cobrar = sum((Decimal(i["precio"]) for i in items if i.get("cobrable")), Decimal("0"))
    n = len(items)
    n_term = sum(1 for i in items if i["estado"] == "terminado")
    n_por_cobrar = sum(1 for i in items if i.get("cobrable"))
    avance = round(100 * n_term / n) if n else 0
    return {
        "total":            f"{total:.2f}",
        "total_num":        float(total),
        "total_aprobado":   f"{aprobado:.2f}",
        "total_terminado":  f"{terminado:.2f}",
        "total_cobrado":    f"{cobrado:.2f}",
        "total_por_cobrar": f"{por_cobrar:.2f}",
        "n_items":          n,
        "n_terminados":     n_term,
        "n_por_cobrar":     n_por_cobrar,
        "avance":           avance,
    }


def _dump_plan(p: PlanTratamiento, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    info = ESTADOS_PLAN.get(p.estado or "borrador", ESTADOS_PLAN["borrador"])
    base = {
        "id":           p.id or 0,
        "paciente_id":  p.paciente_id,
        "titulo":       p.titulo or "",
        "estado":       p.estado or "borrador",
        "estado_label": info["label"],
        "color":        info["color"],
        "text_color":   info["text"],
        "notas":        p.notas or "",
        "fecha":        p.created_at.strftime("%Y-%m-%d") if p.created_at else "",
    }
    if items is not None:
        base.update(_totales(items))
    return base


# ── Consultas ─────────────────────────────────────────────────────────────────

async def _get_plan(session: AsyncSession, clinica_id: int, plan_id: int) -> PlanTratamiento:
    p = (await session.execute(
        select(PlanTratamiento).where(
            PlanTratamiento.id == plan_id,
            PlanTratamiento.clinica_id == clinica_id,
            PlanTratamiento.is_active.is_(True),
        )
    )).scalars().first()
    if p is None:
        raise NotFoundError("Plan de tratamiento no encontrado")
    return p


async def _items_de(session: AsyncSession, clinica_id: int, plan_id: int) -> list[PlanTratamientoItem]:
    stmt = (
        select(PlanTratamientoItem)
        .where(
            PlanTratamientoItem.clinica_id == clinica_id,
            PlanTratamientoItem.plan_id == plan_id,
            PlanTratamientoItem.is_active.is_(True),
        )
        .order_by(PlanTratamientoItem.fase, PlanTratamientoItem.orden, PlanTratamientoItem.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def listar_planes(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
) -> list[dict[str, Any]]:
    """Lista los planes de un paciente (más reciente primero) con totales/avance."""
    stmt = (
        select(PlanTratamiento)
        .where(
            PlanTratamiento.clinica_id == clinica_id,
            PlanTratamiento.paciente_id == paciente_id,
            PlanTratamiento.is_active.is_(True),
        )
        .order_by(PlanTratamiento.created_at.desc(), PlanTratamiento.id.desc())
    )
    planes = list((await session.execute(stmt)).scalars().all())
    salida = []
    for p in planes:
        items = [_dump_item(it) for it in await _items_de(session, clinica_id, p.id)]
        salida.append(_dump_plan(p, items))
    return salida


async def obtener_plan(
    session: AsyncSession,
    clinica_id: int,
    plan_id: int,
) -> dict[str, Any]:
    """Devuelve el plan completo con items agrupados por fase + totales."""
    p = await _get_plan(session, clinica_id, plan_id)
    items = [_dump_item(it) for it in await _items_de(session, clinica_id, plan_id)]

    fases: dict[int, list[dict[str, Any]]] = {}
    for it in items:
        fases.setdefault(it["fase"], []).append(it)

    fases_out = [
        {
            "fase":   fase,
            "items":  its,
            **{f"fase_{k}": v for k, v in _totales(its).items()},
            "subtotal": _totales(its)["total"],
        }
        for fase, its in sorted(fases.items())
    ]

    plan = _dump_plan(p, items)
    plan["fases"] = fases_out
    plan["items"] = items
    return plan


# ── Mutaciones de plan ────────────────────────────────────────────────────────

async def crear_plan(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    titulo: str,
    notas: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    titulo = (titulo or "").strip()
    if not titulo:
        raise ValidationError("El título del plan es obligatorio")

    # El paciente debe existir en la clínica.
    pac = (await session.execute(
        select(Paciente.id).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
            Paciente.is_active.is_(True),
        )
    )).first()
    if pac is None:
        raise NotFoundError("Paciente no encontrado")

    p = PlanTratamiento(
        clinica_id=clinica_id,
        paciente_id=paciente_id,
        sede_id=sede_id or None,
        titulo=titulo[:160],
        estado="borrador",
        notas=(notas or "").strip() or None,
        created_by_id=usuario_id,
    )
    session.add(p)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="crear", entidad="plan_tratamiento", entidad_id=p.id,
        detalle={"paciente_id": paciente_id, "titulo": titulo[:160]},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_plan(p, [])


async def actualizar_plan(
    session: AsyncSession,
    clinica_id: int,
    plan_id: int,
    *,
    titulo: str | None = None,
    estado: str | None = None,
    notas: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    p = await _get_plan(session, clinica_id, plan_id)
    if titulo is not None:
        t = titulo.strip()
        if not t:
            raise ValidationError("El título del plan es obligatorio")
        p.titulo = t[:160]
    if estado is not None:
        p.estado = _validar_estado_plan(estado)
    if notas is not None:
        p.notas = notas.strip() or None
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="editar", entidad="plan_tratamiento", entidad_id=p.id,
        detalle={"estado": p.estado, "titulo": p.titulo},
        sede_id=sede_id or None,
    )
    items = [_dump_item(it) for it in await _items_de(session, clinica_id, plan_id)]
    await session.flush()
    return _dump_plan(p, items)


async def eliminar_plan(
    session: AsyncSession,
    clinica_id: int,
    plan_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> None:
    p = await _get_plan(session, clinica_id, plan_id)
    for it in await _items_de(session, clinica_id, plan_id):
        it.soft_delete()
    p.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar", entidad="plan_tratamiento", entidad_id=p.id,
        detalle={"paciente_id": p.paciente_id, "titulo": p.titulo},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Mutaciones de item ────────────────────────────────────────────────────────

async def agregar_item(
    session: AsyncSession,
    clinica_id: int,
    plan_id: int,
    *,
    descripcion: str,
    fase: Any = 1,
    pieza_numero: str | None = None,
    servicio_id: int | None = None,
    precio: Any = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    p = await _get_plan(session, clinica_id, plan_id)
    descripcion = (descripcion or "").strip()
    servicio_id = servicio_id or None

    # Si viene un servicio del catálogo, hereda nombre/precio cuando no se dieron.
    if servicio_id:
        serv = (await session.execute(
            select(Servicio).where(
                Servicio.id == servicio_id,
                Servicio.clinica_id == clinica_id,
                Servicio.is_active.is_(True),
            )
        )).scalars().first()
        if serv is None:
            raise NotFoundError("Servicio no encontrado")
        if not descripcion:
            descripcion = serv.nombre
        if precio is None or precio == "":
            precio = serv.precio

    if not descripcion:
        raise ValidationError("La descripción del tratamiento es obligatoria")

    precio_dec = _parse_precio(precio)
    fase_n = _parse_fase(fase)

    # orden = siguiente dentro de la fase
    max_orden = (await session.execute(
        select(func.coalesce(func.max(PlanTratamientoItem.orden), 0)).where(
            PlanTratamientoItem.clinica_id == clinica_id,
            PlanTratamientoItem.plan_id == plan_id,
            PlanTratamientoItem.fase == fase_n,
            PlanTratamientoItem.is_active.is_(True),
        )
    )).scalar_one()

    it = PlanTratamientoItem(
        clinica_id=clinica_id,
        plan_id=plan_id,
        fase=fase_n,
        orden=int(max_orden) + 1,
        pieza_numero=(pieza_numero or "").strip()[:4] or None,
        servicio_id=servicio_id,
        descripcion=descripcion[:200],
        precio=precio_dec,
        estado="propuesto",
    )
    session.add(it)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="agregar_item", entidad="plan_tratamiento", entidad_id=p.id,
        detalle={"item_id": it.id, "descripcion": descripcion[:200], "precio": str(precio_dec)},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_item(it)


async def _get_item(
    session: AsyncSession, clinica_id: int, plan_id: int, item_id: int
) -> PlanTratamientoItem:
    it = (await session.execute(
        select(PlanTratamientoItem).where(
            PlanTratamientoItem.id == item_id,
            PlanTratamientoItem.plan_id == plan_id,
            PlanTratamientoItem.clinica_id == clinica_id,
            PlanTratamientoItem.is_active.is_(True),
        )
    )).scalars().first()
    if it is None:
        raise NotFoundError("Tratamiento no encontrado")
    return it


async def actualizar_item(
    session: AsyncSession,
    clinica_id: int,
    plan_id: int,
    item_id: int,
    *,
    descripcion: str | None = None,
    fase: Any = None,
    pieza_numero: str | None = None,
    precio: Any = None,
    estado: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    it = await _get_item(session, clinica_id, plan_id, item_id)
    if descripcion is not None:
        d = descripcion.strip()
        if not d:
            raise ValidationError("La descripción del tratamiento es obligatoria")
        it.descripcion = d[:200]
    if fase is not None:
        it.fase = _parse_fase(fase)
    if pieza_numero is not None:
        it.pieza_numero = pieza_numero.strip()[:4] or None
    if precio is not None:
        it.precio = _parse_precio(precio)
    if estado is not None:
        it.estado = _validar_estado_item(estado)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="editar_item", entidad="plan_tratamiento", entidad_id=plan_id,
        detalle={"item_id": item_id, "estado": it.estado},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_item(it)


async def cambiar_estado_item(
    session: AsyncSession,
    clinica_id: int,
    plan_id: int,
    item_id: int,
    *,
    estado: str,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    return await actualizar_item(
        session, clinica_id, plan_id, item_id,
        estado=estado, usuario_id=usuario_id, sede_id=sede_id,
    )


async def eliminar_item(
    session: AsyncSession,
    clinica_id: int,
    plan_id: int,
    item_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> None:
    it = await _get_item(session, clinica_id, plan_id, item_id)
    it.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar_item", entidad="plan_tratamiento", entidad_id=plan_id,
        detalle={"item_id": item_id},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Cobro del plan → Caja ──────────────────────────────────────────────────────

async def cobrar_plan(
    session: AsyncSession,
    clinica_id: int,
    plan_id: int,
    *,
    forma_pago: str = "efectivo",
    item_ids: list[int] | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Genera un comprobante en Caja por los tratamientos cobrables del plan
    (aprobado/en_curso/terminado, precio > 0 y no cobrados) y enlaza cada item con
    el `comprobante_id` resultante. NO reimplementa Caja: delega en cobro.crear,
    en la misma transacción. Si se pasan `item_ids`, solo cobra esos."""
    plan = await _get_plan(session, clinica_id, plan_id)
    items = await _items_de(session, clinica_id, plan_id)

    elegibles = [
        it for it in items
        if not it.comprobante_id
        and it.estado in _ITEM_COBRABLE
        and (it.precio or Decimal("0")) > 0
    ]
    if item_ids:
        ids = {int(x) for x in item_ids}
        elegibles = [it for it in elegibles if it.id in ids]
    if not elegibles:
        raise ServiceError("No hay tratamientos aprobados pendientes de cobro en este plan")

    payload = {
        "paciente_id": plan.paciente_id,
        "forma_pago": forma_pago,
        "observacion": f"Plan de tratamiento: {plan.titulo}"[:240],
        "items": [
            {
                "tipo": "servicio",
                "ref_id": it.servicio_id or 0,
                "nombre": it.descripcion,
                "cantidad": "1",
                "precio_unit": str(it.precio or Decimal("0")),
            }
            for it in elegibles
        ],
    }
    comp = await _cobro.crear(session, clinica_id, payload, sede_id=sede_id, usuario_id=usuario_id)
    comp_id = comp["id"]

    for it in elegibles:
        it.comprobante_id = comp_id
    await session.flush()

    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="cobrar", entidad="plan_tratamiento", entidad_id=plan_id,
        detalle={
            "comprobante_id": comp_id,
            "numero": comp.get("numero"),
            "total": comp.get("total"),
            "items": len(elegibles),
        },
        sede_id=sede_id or None,
    )
    await session.flush()
    return {"comprobante": comp, "cobrados": len(elegibles)}
