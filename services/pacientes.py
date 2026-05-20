from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import joinedload

from extensions import db
from models.paciente import Paciente
from models.profesional import Profesional
from models.servicio import Servicio
from models.turno import EstadoTurno, Turno
from models.turno_servicio import TurnoServicio
from schemas.historial import HistorialResponseSchema
from schemas.paciente import PacienteSchema
from services.exceptions import ConflictError, NotFoundError


class PacienteService:
    def __init__(self, clinica_id: int):
        self.clinica_id = clinica_id
        self.schema = PacienteSchema()
        self.schema_many = PacienteSchema(many=True)
        self.historial_schema = HistorialResponseSchema()

    def listar(
        self,
        q: str = "",
        desde: datetime | None = None,
        hasta: datetime | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        stmt = self._base_query()

        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Paciente.nombre.ilike(like),
                    cast(Paciente.documento, String).ilike(like),
                )
            )

        if desde:
            stmt = stmt.where(Paciente.created_at >= desde)
        if hasta:
            if hasta.hour == 0 and hasta.minute == 0:
                hasta = hasta + timedelta(days=1)
            stmt = stmt.where(Paciente.created_at < hasta)

        stmt = stmt.order_by(Paciente.created_at.desc())
        pag = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

        return {
            "data": self.schema_many.dump(pag.items),
            "page": pag.page,
            "per_page": pag.per_page,
            "total": pag.total,
            "pages": pag.pages,
        }

    def crear(self, payload: dict[str, Any]) -> Paciente:
        payload = dict(payload)
        payload["clinica_id"] = self.clinica_id
        paciente: Paciente = self.schema.load(payload, session=db.session)
        self._validar_unicos(paciente)

        db.session.add(paciente)
        db.session.commit()
        return paciente

    def obtener(self, paciente_id: int) -> Paciente:
        paciente = db.session.execute(
            self._base_query().where(Paciente.id == paciente_id)
        ).scalar_one_or_none()
        if paciente is None:
            raise NotFoundError("Paciente no encontrado")
        return paciente

    def actualizar(self, paciente_id: int, payload: dict[str, Any]) -> Paciente:
        paciente = self.obtener(paciente_id)
        payload = dict(payload)
        payload["clinica_id"] = self.clinica_id

        nuevo_doc = payload.get("documento") or payload.get("dni")
        if nuevo_doc and nuevo_doc != (paciente.documento or None):
            self._assert_documento_disponible(nuevo_doc, exclude_id=paciente.id)

        nuevo_mail = payload.get("email")
        if nuevo_mail and nuevo_mail != (paciente.email or None):
            self._assert_email_disponible(nuevo_mail, exclude_id=paciente.id)

        self.schema.load(payload, instance=paciente, partial=True, session=db.session)
        db.session.commit()
        return paciente

    def eliminar(self, paciente_id: int) -> None:
        paciente = self.obtener(paciente_id)
        paciente.soft_delete()
        db.session.commit()

    def historial(self, paciente_id: int) -> dict[str, Any]:
        paciente = self.obtener(paciente_id)

        estados_historial = [EstadoTurno.ATENDIDO.value]
        estado_cobrado = getattr(EstadoTurno, "COBRADO", None)
        estados_historial.append(estado_cobrado.value if estado_cobrado else "cobrado")
        estados_historial = list(dict.fromkeys(estados_historial))

        # Turno sigue siendo db.Model hasta su migración — .query sigue siendo válido
        turnos = (
            Turno.query.options(
                joinedload(Turno.profesional),
                joinedload(Turno.items).joinedload(TurnoServicio.servicio),
                joinedload(Turno.servicio),
            )
            .filter(
                Turno.clinica_id == self.clinica_id,
                Turno.is_active.is_(True),
                Turno.paciente_id == paciente.id,
                Turno.estado.in_(estados_historial),
            )
            .order_by(Turno.fecha_hora.desc())
            .all()
        )

        registros: list[dict[str, str | int | None]] = []
        for turno in turnos:
            profesional: Profesional | None = turno.profesional
            profesional_nombre = (
                f"{(profesional.nombres or '').strip()} {(profesional.apellidos or '').strip()}".strip()
                if profesional else None
            )
            fecha_hora = turno.fecha_hora
            fecha = fecha_hora.strftime("%Y-%m-%d") if fecha_hora else ""
            hora = fecha_hora.strftime("%H:%M") if fecha_hora else ""

            if turno.items:
                for item in turno.items:
                    servicio: Servicio | None = item.servicio
                    registros.append(
                        {
                            "turno_id": turno.id,
                            "fecha": fecha,
                            "hora": hora,
                            "servicio": getattr(servicio, "nombre", None) or "",
                            "profesional": profesional_nombre,
                            "detalle": item.nota or getattr(servicio, "descripcion", None),
                        }
                    )
            else:
                servicio: Servicio | None = turno.servicio
                registros.append(
                    {
                        "turno_id": turno.id,
                        "fecha": fecha,
                        "hora": hora,
                        "servicio": getattr(servicio, "nombre", None) or "",
                        "profesional": profesional_nombre,
                        "detalle": getattr(servicio, "descripcion", None),
                    }
                )

        data = {
            "paciente_id": paciente.id,
            "paciente_nombre": paciente.nombre,
            "historial": registros,
            "total": len(registros),
        }
        return self.historial_schema.dump(data)

    def dump(self, paciente: Paciente) -> dict[str, Any]:
        return self.schema.dump(paciente)

    def _base_query(self):
        return select(Paciente).where(
            Paciente.clinica_id == self.clinica_id,
            Paciente.is_active.is_(True),
        )

    def _validar_unicos(self, paciente: Paciente) -> None:
        if paciente.documento:
            self._assert_documento_disponible(paciente.documento)
        if paciente.email:
            self._assert_email_disponible(paciente.email)

    def _assert_documento_disponible(self, documento: str, exclude_id: int | None = None) -> None:
        stmt = select(Paciente).where(
            Paciente.clinica_id == self.clinica_id,
            Paciente.documento == documento,
        )
        if exclude_id is not None:
            stmt = stmt.where(Paciente.id != exclude_id)
        if db.session.execute(stmt).scalar_one_or_none():
            raise ConflictError("Paciente ya registrado en esta clinica (DNI duplicado)")

    def _assert_email_disponible(self, email: str, exclude_id: int | None = None) -> None:
        stmt = select(Paciente).where(
            Paciente.clinica_id == self.clinica_id,
            Paciente.email == email,
        )
        if exclude_id is not None:
            stmt = stmt.where(Paciente.id != exclude_id)
        if db.session.execute(stmt).scalar_one_or_none():
            raise ConflictError("Email ya registrado en otro paciente de esta clinica")
