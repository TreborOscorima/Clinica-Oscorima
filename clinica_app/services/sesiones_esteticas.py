"""Galería antes/después estética por sesión (C1).

Cada `SesionEstetica` agrupa fotos (`Adjunto` categoría "foto") por fecha/zona,
etiquetadas con un `momento` (antes/durante/después). Reutiliza el
almacenamiento y el endpoint de descarga de A2; la lista de sesiones ordenada
por fecha es la línea de tiempo de evolución del paciente.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from clinica_app.models.adjunto import Adjunto
from clinica_app.models.inventario import Producto
from clinica_app.models.paciente import Paciente
from clinica_app.models.sesion_estetica import SesionEstetica, SesionInsumo
from clinica_app.services import auditoria
from clinica_app.services import turnos as _turnos
from clinica_app.services.exceptions import NotFoundError, ValidationError

# ── Momentos (etiqueta de la foto dentro de la sesión) ────────────────────────
MOMENTOS: dict[str, str] = {
    "antes":   "Antes",
    "durante": "Durante",
    "despues": "Después",
}


def momentos_catalogo() -> list[dict[str, str]]:
    return [{"clave": k, "label": v} for k, v in MOMENTOS.items()]


def _validar_momento(momento: str) -> str:
    if momento not in MOMENTOS:
        raise ValidationError(f"Momento inválido: {momento}")
    return momento


def _parse_fecha(valor: Any) -> date:
    if isinstance(valor, date):
        return valor
    txt = (str(valor) if valor is not None else "").strip()
    if not txt:
        raise ValidationError("La fecha de la sesión es obligatoria")
    try:
        return datetime.strptime(txt[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Fecha inválida (use AAAA-MM-DD)")


def _parse_fecha_opcional(valor: Any) -> date | None:
    """Fecha que puede quedar vacía (p. ej. próxima sesión recomendada)."""
    if isinstance(valor, date):
        return valor
    txt = (str(valor) if valor is not None else "").strip()
    if not txt:
        return None
    try:
        return datetime.strptime(txt[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Fecha inválida (use AAAA-MM-DD)")


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


def _parse_hora(valor: Any) -> time:
    """Hora 'HH:MM' → time. Vacío → 09:00."""
    txt = (str(valor) if valor is not None else "").strip()
    if not txt:
        return time(9, 0)
    try:
        hh, mm = txt[:5].split(":")
        h, m = int(hh), int(mm)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return time(h, m)
    except (ValueError, TypeError):
        raise ValidationError("Hora inválida (use HH:MM)")


def _parse_numero_sesion(valor: Any) -> int | None:
    txt = (str(valor) if valor is not None else "").strip()
    if not txt:
        return None
    try:
        n = int(txt)
    except (ValueError, TypeError):
        return None
    return n if n > 0 else None


# ── Serialización ─────────────────────────────────────────────────────────────

def _dump_foto(a: Adjunto) -> dict[str, Any]:
    return {
        "id":       a.id or 0,
        "nombre":   a.nombre or "",
        "momento":  a.momento or "antes",
        "mime":     a.mime or "",
    }


def _dump_insumo(i: SesionInsumo) -> dict[str, Any]:
    return {
        "id":          i.id or 0,
        "sesion_id":   i.sesion_id,
        "producto_id": i.producto_id or 0,
        "descripcion": i.descripcion or "",
        "cantidad":    f"{(i.cantidad or Decimal('0')).normalize():f}",
        "unidad":      i.unidad or "",
    }


def _dump_sesion(s: SesionEstetica) -> dict[str, Any]:
    return {
        "id":          s.id or 0,
        "paciente_id": s.paciente_id,
        "fecha":       s.fecha.strftime("%Y-%m-%d") if s.fecha else "",
        "fecha_fmt":   s.fecha.strftime("%d/%m/%Y") if s.fecha else "",
        "titulo":      s.titulo or "",
        "zona":        s.zona or "",
        "notas":       s.notas or "",
        # Ficha clínica (C2)
        "numero_sesion":     s.numero_sesion or 0,
        "parametros":        s.parametros or "",
        "proxima":           s.proxima_recomendada.strftime("%Y-%m-%d") if s.proxima_recomendada else "",
        "proxima_fmt":       s.proxima_recomendada.strftime("%d/%m/%Y") if s.proxima_recomendada else "",
    }


# ── Consultas de fotos ────────────────────────────────────────────────────────

async def _fotos_de(session: AsyncSession, clinica_id: int, sesion_id: int) -> list[Adjunto]:
    stmt = (
        select(Adjunto)
        .where(
            Adjunto.clinica_id == clinica_id,
            Adjunto.sesion_id == sesion_id,
            Adjunto.is_active.is_(True),
        )
        .order_by(Adjunto.created_at.asc(), Adjunto.id.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def _insumos_de(session: AsyncSession, clinica_id: int, sesion_id: int) -> list[SesionInsumo]:
    stmt = (
        select(SesionInsumo)
        .where(
            SesionInsumo.clinica_id == clinica_id,
            SesionInsumo.sesion_id == sesion_id,
            SesionInsumo.is_active.is_(True),
        )
        .order_by(SesionInsumo.created_at.asc(), SesionInsumo.id.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def _get_sesion(session: AsyncSession, clinica_id: int, sesion_id: int) -> SesionEstetica:
    s = (await session.execute(
        select(SesionEstetica).where(
            SesionEstetica.id == sesion_id,
            SesionEstetica.clinica_id == clinica_id,
            SesionEstetica.is_active.is_(True),
        )
    )).scalars().first()
    if s is None:
        raise NotFoundError("Sesión estética no encontrada")
    return s


# ── Consultas de sesión ───────────────────────────────────────────────────────

async def listar_sesiones(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
) -> list[dict[str, Any]]:
    """Línea de tiempo: sesiones del paciente (más reciente primero) con conteos."""
    stmt = (
        select(SesionEstetica)
        .where(
            SesionEstetica.clinica_id == clinica_id,
            SesionEstetica.paciente_id == paciente_id,
            SesionEstetica.is_active.is_(True),
        )
        .order_by(SesionEstetica.fecha.desc(), SesionEstetica.id.desc())
    )
    sesiones = list((await session.execute(stmt)).scalars().all())
    salida = []
    for s in sesiones:
        fotos = await _fotos_de(session, clinica_id, s.id)
        d = _dump_sesion(s)
        d["n_fotos"]   = len(fotos)
        d["n_antes"]   = sum(1 for f in fotos if (f.momento or "") == "antes")
        d["n_despues"] = sum(1 for f in fotos if (f.momento or "") == "despues")
        salida.append(d)
    return salida


async def obtener_sesion(
    session: AsyncSession,
    clinica_id: int,
    sesion_id: int,
) -> dict[str, Any]:
    """Sesión completa con sus fotos agrupadas por momento."""
    s = await _get_sesion(session, clinica_id, sesion_id)
    fotos = [_dump_foto(f) for f in await _fotos_de(session, clinica_id, sesion_id)]
    d = _dump_sesion(s)
    d["antes"]   = [f for f in fotos if f["momento"] == "antes"]
    d["durante"] = [f for f in fotos if f["momento"] == "durante"]
    d["despues"] = [f for f in fotos if f["momento"] == "despues"]
    d["n_fotos"] = len(fotos)
    d["insumos"] = [_dump_insumo(i) for i in await _insumos_de(session, clinica_id, sesion_id)]
    return d


# ── Mutaciones de sesión ──────────────────────────────────────────────────────

async def crear_sesion(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    *,
    fecha: Any,
    titulo: str,
    zona: str | None = None,
    notas: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    titulo = (titulo or "").strip()
    if not titulo:
        raise ValidationError("El título de la sesión es obligatorio")
    fecha_d = _parse_fecha(fecha)

    pac = (await session.execute(
        select(Paciente.id).where(
            Paciente.id == paciente_id,
            Paciente.clinica_id == clinica_id,
            Paciente.is_active.is_(True),
        )
    )).first()
    if pac is None:
        raise NotFoundError("Paciente no encontrado")

    s = SesionEstetica(
        clinica_id=clinica_id,
        paciente_id=paciente_id,
        sede_id=sede_id or None,
        fecha=fecha_d,
        titulo=titulo[:160],
        zona=(zona or "").strip()[:120] or None,
        notas=(notas or "").strip() or None,
        created_by_id=usuario_id,
    )
    session.add(s)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="crear", entidad="sesion_estetica", entidad_id=s.id,
        detalle={"paciente_id": paciente_id, "titulo": titulo[:160], "fecha": fecha_d.isoformat()},
        sede_id=sede_id or None,
    )
    d = _dump_sesion(s)
    d.update({"n_fotos": 0, "n_antes": 0, "n_despues": 0})
    return d


async def actualizar_sesion(
    session: AsyncSession,
    clinica_id: int,
    sesion_id: int,
    *,
    fecha: Any = None,
    titulo: str | None = None,
    zona: str | None = None,
    notas: str | None = None,
    numero_sesion: Any = None,
    parametros: str | None = None,
    proxima: Any = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    s = await _get_sesion(session, clinica_id, sesion_id)
    if fecha is not None and str(fecha).strip():
        s.fecha = _parse_fecha(fecha)
    if titulo is not None:
        t = titulo.strip()
        if not t:
            raise ValidationError("El título de la sesión es obligatorio")
        s.titulo = t[:160]
    if zona is not None:
        s.zona = zona.strip()[:120] or None
    if notas is not None:
        s.notas = notas.strip() or None
    if numero_sesion is not None:
        s.numero_sesion = _parse_numero_sesion(numero_sesion)
    if parametros is not None:
        s.parametros = parametros.strip() or None
    if proxima is not None:
        s.proxima_recomendada = _parse_fecha_opcional(proxima)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="editar", entidad="sesion_estetica", entidad_id=s.id,
        detalle={"titulo": s.titulo},
        sede_id=sede_id or None,
    )
    return _dump_sesion(s)


async def eliminar_sesion(
    session: AsyncSession,
    clinica_id: int,
    sesion_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> list[str]:
    """Soft-delete de la sesión y de sus fotos. Devuelve los `stored_name` para
    que la capa que llama borre los archivos físicos."""
    s = await _get_sesion(session, clinica_id, sesion_id)
    stored: list[str] = []
    for f in await _fotos_de(session, clinica_id, sesion_id):
        stored.append(f.stored_name)
        f.soft_delete()
    for i in await _insumos_de(session, clinica_id, sesion_id):
        i.soft_delete()
    s.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar", entidad="sesion_estetica", entidad_id=s.id,
        detalle={"paciente_id": s.paciente_id, "titulo": s.titulo, "fotos": len(stored)},
        sede_id=sede_id or None,
    )
    await session.flush()
    return stored


# ── Fotos ─────────────────────────────────────────────────────────────────────

async def registrar_foto(
    session: AsyncSession,
    clinica_id: int,
    paciente_id: int,
    sesion_id: int,
    *,
    momento: str,
    nombre: str,
    stored_name: str,
    mime: str | None = None,
    tamano: int = 0,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Cuelga una foto ya almacenada (stored_name) de una sesión + momento."""
    momento = _validar_momento(momento)
    s = await _get_sesion(session, clinica_id, sesion_id)  # valida pertenencia

    a = Adjunto(
        clinica_id=clinica_id,
        paciente_id=paciente_id or s.paciente_id,
        sede_id=sede_id or None,
        sesion_id=sesion_id,
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
        accion="agregar_foto", entidad="sesion_estetica", entidad_id=sesion_id,
        detalle={"foto_id": a.id, "momento": momento, "nombre": a.nombre},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_foto(a)


async def eliminar_foto(
    session: AsyncSession,
    clinica_id: int,
    foto_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> str:
    """Soft-delete de una foto. Devuelve el `stored_name` para borrar el archivo."""
    a = (await session.execute(
        select(Adjunto).where(
            Adjunto.id == foto_id,
            Adjunto.clinica_id == clinica_id,
            Adjunto.is_active.is_(True),
        )
    )).scalars().first()
    if a is None:
        raise NotFoundError("Foto no encontrada")
    stored_name = a.stored_name
    sesion_id = a.sesion_id
    a.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar_foto", entidad="sesion_estetica", entidad_id=sesion_id,
        detalle={"foto_id": foto_id},
        sede_id=sede_id or None,
    )
    await session.flush()
    return stored_name


# ── Insumos aplicados (ficha C2) ──────────────────────────────────────────────

async def agregar_insumo(
    session: AsyncSession,
    clinica_id: int,
    sesion_id: int,
    *,
    descripcion: str,
    producto_id: int | None = None,
    cantidad: Any = None,
    unidad: str | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Registra un insumo/producto aplicado en la sesión (descriptivo, no mueve
    stock). Si viene `producto_id`, hereda el nombre cuando falta descripción."""
    await _get_sesion(session, clinica_id, sesion_id)  # valida pertenencia
    descripcion = (descripcion or "").strip()
    producto_id = producto_id or None

    if producto_id:
        prod = (await session.execute(
            select(Producto).where(
                Producto.id == producto_id,
                Producto.clinica_id == clinica_id,
                Producto.is_active.is_(True),
            )
        )).scalars().first()
        if prod is None:
            raise NotFoundError("Producto no encontrado")
        if not descripcion:
            descripcion = prod.nombre

    if not descripcion:
        raise ValidationError("La descripción del insumo es obligatoria")

    cant = _parse_cantidad(cantidad)
    i = SesionInsumo(
        clinica_id=clinica_id,
        sesion_id=sesion_id,
        sede_id=sede_id or None,
        producto_id=producto_id,
        descripcion=descripcion[:200],
        cantidad=cant,
        unidad=(unidad or "").strip()[:20] or None,
    )
    session.add(i)
    await session.flush()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="agregar_insumo", entidad="sesion_estetica", entidad_id=sesion_id,
        detalle={"insumo_id": i.id, "descripcion": descripcion[:200], "cantidad": str(cant)},
        sede_id=sede_id or None,
    )
    await session.flush()
    return _dump_insumo(i)


async def eliminar_insumo(
    session: AsyncSession,
    clinica_id: int,
    insumo_id: int,
    *,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> None:
    i = (await session.execute(
        select(SesionInsumo).where(
            SesionInsumo.id == insumo_id,
            SesionInsumo.clinica_id == clinica_id,
            SesionInsumo.is_active.is_(True),
        )
    )).scalars().first()
    if i is None:
        raise NotFoundError("Insumo no encontrado")
    sesion_id = i.sesion_id
    i.soft_delete()
    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="eliminar_insumo", entidad="sesion_estetica", entidad_id=sesion_id,
        detalle={"insumo_id": insumo_id},
        sede_id=sede_id or None,
    )
    await session.flush()


# ── Agenda: turno de la próxima sesión ────────────────────────────────────────

async def agendar_proxima_sesion(
    session: AsyncSession,
    clinica_id: int,
    sesion_id: int,
    *,
    fecha: Any = None,
    hora: Any = None,
    profesional_id: int | None = None,
    usuario_id: int | None = None,
    sede_id: int = 0,
) -> dict[str, Any]:
    """Crea un turno para la próxima sesión recomendada de la ficha estética.

    NO reimplementa la agenda: arma el payload y delega en `services.turnos.crear`
    (misma transacción). `fecha` es opcional (por defecto usa
    `proxima_recomendada`); `hora` 'HH:MM' por defecto 09:00.
    """
    s = await _get_sesion(session, clinica_id, sesion_id)
    fecha_d = _parse_fecha_opcional(fecha) if fecha not in (None, "") else s.proxima_recomendada
    if fecha_d is None:
        raise ValidationError("No hay fecha de próxima sesión para agendar")
    hora_t = _parse_hora(hora)
    fecha_hora = datetime.combine(fecha_d, hora_t)

    turno = await _turnos.crear(
        session, clinica_id,
        {
            "paciente_id": s.paciente_id,
            "fecha_hora": fecha_hora.isoformat(),
            "profesional_id": profesional_id or None,
        },
        created_by_id=usuario_id,
        sede_id=sede_id,
    )

    await auditoria.registrar(
        session, clinica_id,
        usuario_id=usuario_id,
        accion="agendar_turno", entidad="sesion_estetica", entidad_id=sesion_id,
        detalle={"turno_id": turno.get("id"), "fecha_hora": fecha_hora.isoformat()},
        sede_id=sede_id or None,
    )
    await session.flush()
    return turno
