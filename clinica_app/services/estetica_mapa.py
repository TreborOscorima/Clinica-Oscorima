"""Mapa estético — evaluaciones, procedimientos y puntos de aplicación (E5).

Capa de negocio del modelo espacial estético. Todo es async puro (recibe
`session`), multi-tenant (`clinica_id`), auditado en la misma transacción y
soft-delete, igual que el resto de `services/*`. El renderer 3D nunca llama
aquí: la UI (state) traduce el pick de zona (`zona_codigo`, del catálogo en
`services/anatomia.py`) y las coordenadas normalizadas a estas funciones.

Reutiliza `Paciente`, `SesionEstetica`, `Producto` (trazabilidad + lote). No
mueve stock: el punto de aplicación es descriptivo (la baja de inventario sigue
por la ficha de sesión, `sesiones_esteticas.agregar_insumo`).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.adjunto import Adjunto
from clinica_app.models.evaluacion_estetica import EvaluacionEstetica
from clinica_app.models.inventario import Producto
from clinica_app.models.paciente import Paciente
from clinica_app.models.procedimiento_estetico import ProcedimientoEstetico, PuntoAplicacion
from clinica_app.services import anatomia
from clinica_app.services import auditoria
from clinica_app.services.exceptions import NotFoundError, ValidationError
from clinica_app.services.sesiones_esteticas import _validar_momento


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_cantidad(valor: Any) -> Decimal:
    if valor is None or valor == "":
        return Decimal("0")
    try:
        cant = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Cantidad inválida")
    if cant < 0:
        raise ValidationError("La cantidad no puede ser negativa")
    return cant.quantize(Decimal("0.001"))


def _parse_coord(valor: Any) -> float:
    """Coordenada normalizada 0..1 sobre la vista/modelo. Fuera de rango → clamp."""
    try:
        c = float(valor)
    except (ValueError, TypeError):
        raise ValidationError("Coordenada inválida")
    return max(0.0, min(1.0, c))


def _validar_zona(codigo: str) -> str:
    codigo = (codigo or "").strip()
    if not anatomia.es_zona_valida(codigo):
        raise ValidationError(f"Zona anatómica inválida: {codigo}")
    return codigo


async def _validar_paciente(session: AsyncSession, clinica_id: int, paciente_id: int) -> None:
    pac = (await session.execute(
        select(Paciente.id).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
            Paciente.is_active.is_(True),
        )
    )).first()
    if pac is None:
        raise NotFoundError("Paciente no encontrado")


# ── Serialización ─────────────────────────────────────────────────────────────

def _dump_evaluacion(e: EvaluacionEstetica) -> dict[str, Any]:
    return {
        "id":            e.id or 0,
        "paciente_id":   e.paciente_id,
        "sesion_id":     e.sesion_id or 0,
        "zona_codigo":   e.zona_codigo,
        "zona_label":    anatomia.zona_label(e.zona_codigo),
        "categoria":     e.categoria,
        "categoria_label": anatomia.CATEGORIAS_EVALUACION.get(e.categoria, e.categoria),
        "severidad":     e.severidad if e.severidad is not None else "",
        "observacion":   e.observacion or "",
    }


def _dump_punto(p: PuntoAplicacion) -> dict[str, Any]:
    return {
        "id":            p.id or 0,
        "procedimiento_id": p.procedimiento_id,
        "zona_codigo":   p.zona_codigo,
        "coord_x":       round(p.coord_x or 0.0, 4),
        "coord_y":       round(p.coord_y or 0.0, 4),
        "producto_id":   p.producto_id or 0,
        "lote":          p.lote or "",
        "cantidad":      f"{(p.cantidad or Decimal('0')).normalize():f}",
        "unidad":        p.unidad or "",
        "observacion":   p.observacion or "",
    }


def _dump_foto(a: Adjunto) -> dict[str, Any]:
    return {
        "id":          a.id or 0,
        "nombre":      a.nombre or "",
        "momento":     a.momento or "antes",
        "zona_codigo": a.zona_codigo or "",
        "mime":        a.mime or "",
    }


def _dump_procedimiento(pr: ProcedimientoEstetico) -> dict[str, Any]:
    return {
        "id":          pr.id or 0,
        "paciente_id": pr.paciente_id,
        "sesion_id":   pr.sesion_id or 0,
        "zona_codigo": pr.zona_codigo,
        "zona_label":  anatomia.zona_label(pr.zona_codigo),
        "tipo":        pr.tipo,
        "tipo_label":  anatomia.TIPOS_PROCEDIMIENTO.get(pr.tipo, pr.tipo),
        "observacion": pr.observacion or "",
    }


# ── Consultas internas ────────────────────────────────────────────────────────

async def _get_procedimiento(session: AsyncSession, clinica_id: int, procedimiento_id: int) -> ProcedimientoEstetico:
    pr = (await session.execute(
        select(ProcedimientoEstetico).where(
            ProcedimientoEstetico.id == procedimiento_id,
            ProcedimientoEstetico.clinica_id == clinica_id,
            ProcedimientoEstetico.is_active.is_(True),
        )
    )).scalars().first()
    if pr is None:
        raise NotFoundError("Procedimiento no encontrado")
    return pr


async def _puntos_de(session: AsyncSession, clinica_id: int, procedimiento_id: int) -> list[PuntoAplicacion]:
    stmt = (
        select(PuntoAplicacion)
        .where(
            PuntoAplicacion.clinica_id == clinica_id,
            PuntoAplicacion.procedimiento_id == procedimiento_id,
            PuntoAplicacion.is_active.is_(True),
        )
        .order_by(PuntoAplicacion.created_at.asc(), PuntoAplicacion.id.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


# ── Evaluaciones ──────────────────────────────────────────────────────────────

async def registrar_evaluacion(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    zona_codigo: str,
    categoria: str,
    severidad: Any = None,
    observacion: str | None = None,
    sesion_id: int | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    await _validar_paciente(session, clinica_id, paciente_id)
    zona = _validar_zona(zona_codigo)
    categoria = (categoria or "").strip()
    if not anatomia.es_categoria_valida(categoria):
        raise ValidationError(f"Categoría de evaluación inválida: {categoria}")
    sev = anatomia.normalizar_severidad(severidad)

    e = EvaluacionEstetica(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        paciente_id=paciente_id,
        sesion_id=sesion_id or None,
        zona_codigo=zona,
        categoria=categoria,
        severidad=sev,
        observacion=(observacion or "").strip() or None,
        created_by_id=usuario_id,
    )
    session.add(e)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="crear", entidad="evaluacion_estetica", entidad_id=e.id,
        detalle={"paciente_id": paciente_id, "zona": zona, "categoria": categoria, "severidad": sev},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_evaluacion(e)


async def listar_evaluaciones(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    zona_codigo: str | None = None,
) -> list[dict[str, Any]]:
    stmt = select(EvaluacionEstetica).where(
        EvaluacionEstetica.clinica_id == clinica_id,
        EvaluacionEstetica.paciente_id == paciente_id,
        EvaluacionEstetica.is_active.is_(True),
    )
    if zona_codigo:
        stmt = stmt.where(EvaluacionEstetica.zona_codigo == zona_codigo)
    stmt = stmt.order_by(EvaluacionEstetica.created_at.desc(), EvaluacionEstetica.id.desc())
    filas = (await session.execute(stmt)).scalars().all()
    return [_dump_evaluacion(e) for e in filas]


async def eliminar_evaluacion(
    session: AsyncSession,
    clinica_id: int,
    evaluacion_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> None:
    e = (await session.execute(
        select(EvaluacionEstetica).where(
            EvaluacionEstetica.id == evaluacion_id,
            EvaluacionEstetica.clinica_id == clinica_id,
            EvaluacionEstetica.is_active.is_(True),
        )
    )).scalars().first()
    if e is None:
        raise NotFoundError("Evaluación no encontrada")
    e.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar", entidad="evaluacion_estetica", entidad_id=e.id,
        detalle={"paciente_id": e.paciente_id, "zona": e.zona_codigo},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Procedimientos ────────────────────────────────────────────────────────────

async def crear_procedimiento(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    zona_codigo: str,
    tipo: str,
    observacion: str | None = None,
    sesion_id: int | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    await _validar_paciente(session, clinica_id, paciente_id)
    zona = _validar_zona(zona_codigo)
    tipo = (tipo or "").strip()
    if not anatomia.es_tipo_valido(tipo):
        raise ValidationError(f"Tipo de procedimiento inválido: {tipo}")

    pr = ProcedimientoEstetico(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        paciente_id=paciente_id,
        sesion_id=sesion_id or None,
        zona_codigo=zona,
        tipo=tipo,
        observacion=(observacion or "").strip() or None,
        created_by_id=usuario_id,
    )
    session.add(pr)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="crear", entidad="procedimiento_estetico", entidad_id=pr.id,
        detalle={"paciente_id": paciente_id, "zona": zona, "tipo": tipo},
        sede_id=sede_id or None,
    )
    await session.flush()
    d = _dump_procedimiento(pr)
    d["puntos"] = []
    return d


async def listar_procedimientos(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    zona_codigo: str | None = None,
) -> list[dict[str, Any]]:
    stmt = select(ProcedimientoEstetico).where(
        ProcedimientoEstetico.clinica_id == clinica_id,
        ProcedimientoEstetico.paciente_id == paciente_id,
        ProcedimientoEstetico.is_active.is_(True),
    )
    if zona_codigo:
        stmt = stmt.where(ProcedimientoEstetico.zona_codigo == zona_codigo)
    stmt = stmt.order_by(ProcedimientoEstetico.created_at.desc(), ProcedimientoEstetico.id.desc())
    filas = (await session.execute(stmt)).scalars().all()
    salida = []
    for pr in filas:
        d = _dump_procedimiento(pr)
        puntos = await _puntos_de(session, clinica_id, pr.id)
        d["puntos"] = [_dump_punto(p) for p in puntos]
        d["n_puntos"] = len(puntos)
        salida.append(d)
    return salida


async def obtener_procedimiento(
    session: AsyncSession,
    clinica_id: int,
    procedimiento_id: int,
) -> dict[str, Any]:
    pr = await _get_procedimiento(session, clinica_id, procedimiento_id)
    d = _dump_procedimiento(pr)
    puntos = await _puntos_de(session, clinica_id, pr.id)
    d["puntos"] = [_dump_punto(p) for p in puntos]
    d["n_puntos"] = len(puntos)
    return d


async def eliminar_procedimiento(
    session: AsyncSession,
    clinica_id: int,
    procedimiento_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> None:
    """Soft-delete del procedimiento y de sus puntos de aplicación."""
    pr = await _get_procedimiento(session, clinica_id, procedimiento_id)
    for p in await _puntos_de(session, clinica_id, procedimiento_id):
        p.soft_delete()
    pr.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar", entidad="procedimiento_estetico", entidad_id=pr.id,
        detalle={"paciente_id": pr.paciente_id, "zona": pr.zona_codigo},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Puntos de aplicación ──────────────────────────────────────────────────────

async def agregar_punto(
    session: AsyncSession,
    clinica_id: int,
    procedimiento_id: int,
    *,
    coord_x: Any,
    coord_y: Any,
    producto_id: int | None = None,
    lote: str | None = None,
    cantidad: Any = None,
    unidad: str | None = None,
    observacion: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Agrega un punto de aplicación al procedimiento. Si viene `producto_id`,
    valida que el producto exista en la clínica (trazabilidad). NO mueve stock."""
    pr = await _get_procedimiento(session, clinica_id, procedimiento_id)
    producto_id = producto_id or None
    if producto_id:
        prod = (await session.execute(
            select(Producto.id).where(
                Producto.id == producto_id,
                Producto.clinica_id == clinica_id,
                Producto.is_active.is_(True),
            )
        )).first()
        if prod is None:
            raise NotFoundError("Producto no encontrado")

    p = PuntoAplicacion(
        clinica_id=clinica_id,
        sede_id=sede_id or None,
        procedimiento_id=procedimiento_id,
        zona_codigo=pr.zona_codigo,
        coord_x=_parse_coord(coord_x),
        coord_y=_parse_coord(coord_y),
        producto_id=producto_id,
        lote=(lote or "").strip()[:60] or None,
        cantidad=_parse_cantidad(cantidad),
        unidad=(unidad or "").strip()[:20] or None,
        observacion=(observacion or "").strip()[:200] or None,
    )
    session.add(p)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="agregar_punto", entidad="procedimiento_estetico", entidad_id=procedimiento_id,
        detalle={
            "punto_id": p.id, "zona": pr.zona_codigo,
            "producto_id": producto_id, "lote": p.lote, "cantidad": str(p.cantidad),
        },
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_punto(p)


async def eliminar_punto(
    session: AsyncSession,
    clinica_id: int,
    punto_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> None:
    p = (await session.execute(
        select(PuntoAplicacion).where(
            PuntoAplicacion.id == punto_id,
            PuntoAplicacion.clinica_id == clinica_id,
            PuntoAplicacion.is_active.is_(True),
        )
    )).scalars().first()
    if p is None:
        raise NotFoundError("Punto de aplicación no encontrado")
    procedimiento_id = p.procedimiento_id
    p.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar_punto", entidad="procedimiento_estetico", entidad_id=procedimiento_id,
        detalle={"punto_id": punto_id},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Fotos antes/después por zona (E8) ─────────────────────────────────────────

async def _fotos_zona_query(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    zona_codigo: str | None = None,
) -> list[Adjunto]:
    """Adjuntos categoría "foto" colgados de una zona (zona_codigo no nulo)."""
    stmt = select(Adjunto).where(
        Adjunto.clinica_id == clinica_id,
        Adjunto.paciente_id == paciente_id,
        Adjunto.categoria == "foto",
        Adjunto.zona_codigo.is_not(None),
        Adjunto.is_active.is_(True),
    )
    if zona_codigo:
        stmt = stmt.where(Adjunto.zona_codigo == zona_codigo)
    stmt = stmt.order_by(Adjunto.created_at.asc(), Adjunto.id.asc())
    return list((await session.execute(stmt)).scalars().all())


async def registrar_foto_zona(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    zona_codigo: str,
    momento: str,
    nombre: str,
    stored_name: str,
    mime: str | None = None,
    tamano: int = 0,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Cuelga una foto ya almacenada (stored_name) de una zona + momento
    (antes/durante/después), para la comparativa antes/después del mapa estético.
    No pasa por una `SesionEstetica`."""
    await _validar_paciente(session, clinica_id, paciente_id)
    zona = _validar_zona(zona_codigo)
    momento = _validar_momento(momento)

    a = Adjunto(
        clinica_id=clinica_id,
        paciente_id=paciente_id,
        sede_id=sede_id or None,
        zona_codigo=zona,
        momento=momento,
        nombre=(nombre or "foto")[:255],
        stored_name=stored_name,
        mime=(mime or None) and mime[:120],
        tamano=int(tamano or 0),
        categoria="foto",
        created_by_id=usuario_id or None,
    )
    session.add(a)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="agregar_foto", entidad="mapa_estetico", entidad_id=a.id,
        detalle={"paciente_id": paciente_id, "zona": zona, "momento": momento, "nombre": a.nombre},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_foto(a)


async def listar_fotos_zona(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    zona_codigo: str | None = None,
) -> list[dict[str, Any]]:
    filas = await _fotos_zona_query(session, clinica_id, paciente_id, zona_codigo=zona_codigo)
    return [_dump_foto(a) for a in filas]


async def eliminar_foto_zona(
    session: AsyncSession,
    clinica_id: int,
    foto_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> str:
    """Soft-delete de una foto de zona. Devuelve el `stored_name` para que la
    capa que llama borre el archivo físico. Solo alcanza a fotos de zona
    (zona_codigo no nulo): no puede tocar las fotos de sesión de la galería C1."""
    a = (await session.execute(
        select(Adjunto).where(
            Adjunto.id == foto_id,
            Adjunto.clinica_id == clinica_id,
            Adjunto.zona_codigo.is_not(None),
            Adjunto.is_active.is_(True),
        )
    )).scalars().first()
    if a is None:
        raise NotFoundError("Foto no encontrada")
    stored_name = a.stored_name
    zona = a.zona_codigo
    a.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar_foto", entidad="mapa_estetico", entidad_id=foto_id,
        detalle={"paciente_id": a.paciente_id, "zona": zona},
        sede_id=sede_id or None,
    )
    await session.flush()
    return stored_name


# ── Resumen del mapa (para pintar zonas con actividad) ────────────────────────

async def resumen_mapa(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
) -> dict[str, Any]:
    """Por zona: conteo de evaluaciones, procedimientos y puntos, para colorear
    el mapa 3D/2D. Devuelve también los totales del paciente."""
    evals = await listar_evaluaciones(session, clinica_id, paciente_id)
    procs = await listar_procedimientos(session, clinica_id, paciente_id)
    fotos = await _fotos_zona_query(session, clinica_id, paciente_id)

    def _nueva() -> dict[str, int]:
        return {"evaluaciones": 0, "procedimientos": 0, "puntos": 0, "fotos": 0}

    zonas: dict[str, dict[str, int]] = {}
    for e in evals:
        zonas.setdefault(e["zona_codigo"], _nueva())["evaluaciones"] += 1
    for pr in procs:
        z = zonas.setdefault(pr["zona_codigo"], _nueva())
        z["procedimientos"] += 1
        z["puntos"] += pr.get("n_puntos", 0)
    for a in fotos:
        if a.zona_codigo:
            zonas.setdefault(a.zona_codigo, _nueva())["fotos"] += 1

    return {
        "zonas": {
            codigo: {**cont, "zona_label": anatomia.zona_label(codigo)}
            for codigo, cont in zonas.items()
        },
        "n_evaluaciones":   len(evals),
        "n_procedimientos": len(procs),
        "n_puntos":         sum(pr.get("n_puntos", 0) for pr in procs),
        "n_fotos":          len(fotos),
    }


# ── Export para el reporte PDF (E9) ───────────────────────────────────────────

async def _nombres_productos(
    session: AsyncSession, clinica_id: int, ids: set[int]
) -> dict[int, str]:
    """Mapa producto_id → nombre (para etiquetar los puntos en el reporte)."""
    ids = {i for i in ids if i}
    if not ids:
        return {}
    filas = (await session.execute(
        select(Producto.id, Producto.nombre).where(
            Producto.clinica_id == clinica_id,
            Producto.id.in_(ids),
        )
    )).all()
    return {pid: nombre for pid, nombre in filas}


async def datos_export(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
) -> dict[str, Any]:
    """Reúne todo lo que el PDF del mapa estético necesita: datos del paciente,
    evaluaciones y procedimientos (con puntos + nombre de producto) agrupados por
    zona, y el conteo de fotos antes/durante/después por zona. Lanza
    NotFoundError si el paciente no existe en la clínica.

    Espeja `odontograma.datos_export`: el renderer no interviene, todo sale de BD.
    """
    pac = (await session.execute(
        select(Paciente).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
        )
    )).scalars().first()
    if pac is None:
        raise NotFoundError("El paciente no existe")

    evals = await listar_evaluaciones(session, clinica_id, paciente_id)
    procs = await listar_procedimientos(session, clinica_id, paciente_id)
    fotos = await _fotos_zona_query(session, clinica_id, paciente_id)

    # Nombre de producto en cada punto (trazabilidad legible)
    prod_ids = {
        p.get("producto_id", 0)
        for pr in procs for p in pr.get("puntos", [])
    }
    nombres = await _nombres_productos(session, clinica_id, prod_ids)
    for e in evals:
        e["severidad_label"] = anatomia.severidad_label(e.get("severidad"))
    for pr in procs:
        for p in pr.get("puntos", []):
            p["producto_nombre"] = nombres.get(p.get("producto_id", 0), "")

    # Fotos por zona → {zona_label: {antes, durante, despues}}
    fotos_por_zona: dict[str, dict[str, int]] = {}
    for a in fotos:
        z = a.zona_codigo or ""
        cont = fotos_por_zona.setdefault(
            anatomia.zona_label(z), {"antes": 0, "durante": 0, "despues": 0}
        )
        momento = a.momento if a.momento in cont else "antes"
        cont[momento] += 1

    return {
        "paciente_nombre":    pac.nombre,
        "paciente_documento": pac.documento or "",
        "evaluaciones":       evals,
        "procedimientos":     procs,
        "fotos_por_zona":     fotos_por_zona,
        "n_evaluaciones":     len(evals),
        "n_procedimientos":   len(procs),
        "n_puntos":           sum(pr.get("n_puntos", 0) for pr in procs),
        "n_fotos":            len(fotos),
    }
