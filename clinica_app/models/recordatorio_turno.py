from __future__ import annotations

from enum import Enum

from sqlalchemy import Column, Text
from sqlmodel import Field

from clinica_app.models.base import TenantSQLModel


class CanalRecordatorio(str, Enum):
    EMAIL    = "email"
    WHATSAPP = "whatsapp"


class EstadoRecordatorio(str, Enum):
    ENVIADO = "enviado"   # el proveedor aceptó el mensaje
    FALLIDO = "fallido"   # se intentó pero el envío falló (reintentable)


class RecordatorioTurno(TenantSQLModel, table=True):
    """Registro de envío de un recordatorio de turno (estado de envío).

    Una fila por turno y canal efectivamente intentado. Sirve de:
      1. **idempotencia** — el worker no vuelve a recordar un turno que ya tiene
         al menos un canal `ENVIADO` (evita spamear al paciente si el scheduler
         dispara dos veces o se corre a mano);
      2. **trazabilidad** — queda registrado a dónde se envió, con qué resultado
         y el error si falló, para auditar y reintentar los fallidos.

    Los canales deshabilitados o sin destino NO generan fila (no son un envío).
    """

    __tablename__ = "recordatorios_turno"

    turno_id: int = Field(foreign_key="turnos.id", nullable=False, index=True)
    canal:    str = Field(max_length=20, nullable=False)   # CanalRecordatorio
    estado:   str = Field(max_length=20, nullable=False)   # EstadoRecordatorio
    destino:  str | None = Field(default=None, max_length=160, nullable=True)
    error:    str | None = Field(default=None, sa_column=Column(Text, nullable=True))
