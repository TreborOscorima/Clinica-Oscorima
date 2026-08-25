from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TipoMovimiento(str, Enum):
    INGRESO = "ingreso"
    EGRESO  = "egreso"


class MetodoPago(str, Enum):
    EFECTIVO      = "efectivo"
    TARJETA       = "tarjeta"
    TRANSFERENCIA = "transferencia"
    OTRO          = "otro"


class Comprobante(SQLModel, table=True):
    __tablename__ = "comprobantes"

    id: int | None = Field(default=None, primary_key=True)
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    sede_id: int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    tipo: str | None = Field(default="recibo", max_length=20, nullable=True)
    numero: str | None = Field(default=None, max_length=40, nullable=True, unique=True)
    fecha: datetime | None = Field(
        default=None, sa_column=Column(DateTime, default=_utcnow, nullable=True)
    )
    paciente_id: int | None = Field(default=None, foreign_key="pacientes.id", nullable=True)
    total: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    total_bruto: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    descuento_global: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    # Impuesto (IGV/IVA) aplicado a esta venta, congelado en el comprobante.
    # tasa = porcentaje aplicado; monto = importe del impuesto. base = total - monto.
    impuesto_tasa: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(5, 2), default=0, nullable=True)
    )
    impuesto_monto: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    forma_pago: MetodoPago | None = Field(
        sa_column=Column(SAEnum(MetodoPago), default=MetodoPago.EFECTIVO, nullable=True)
    )
    observacion: str | None = Field(default=None, max_length=240, nullable=True)
    # Anulación de la venta: el comprobante no se borra, queda marcado ANULADO
    # con fecha y motivo. La reversión (caja/stock/deuda) la hace cobro.anular.
    anulado: bool = Field(default=False, nullable=False, sa_column_kwargs={"server_default": "0"})
    anulado_en: datetime | None = Field(default=None, nullable=True)
    anulado_motivo: str | None = Field(default=None, max_length=240, nullable=True)
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, nullable=True, index=True)
    idempotency_key: str | None = Field(
        default=None, max_length=64, nullable=True, unique=True, index=True
    )

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()


class CajaMovimiento(SQLModel, table=True):
    __tablename__ = "caja_movimientos"

    id: int | None = Field(default=None, primary_key=True)
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    sede_id: int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    fecha: datetime | None = Field(
        default=None, sa_column=Column(DateTime, default=_utcnow, index=True, nullable=True)
    )
    tipo: TipoMovimiento = Field(
        sa_column=Column(SAEnum(TipoMovimiento), nullable=False, default=TipoMovimiento.INGRESO)
    )
    monto: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    metodo_pago: MetodoPago | None = Field(
        sa_column=Column(SAEnum(MetodoPago), default=MetodoPago.EFECTIVO, nullable=True)
    )
    paciente_id:    int | None = Field(default=None, foreign_key="pacientes.id", nullable=True)
    profesional_id: int | None = Field(default=None, foreign_key="profesionales.id", nullable=True)
    servicio_id:    int | None = Field(default=None, foreign_key="servicios.id", nullable=True)
    comprobante_id: int | None = Field(default=None, foreign_key="comprobantes.id", nullable=True)
    turno_id:       int | None = Field(default=None, foreign_key="turnos.id", nullable=True)
    observacion: str | None = Field(default=None, max_length=240, nullable=True)
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, nullable=True, index=True)

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()


class CierreCaja(SQLModel, table=True):
    __tablename__ = "cierres_caja"
    __table_args__ = (
        UniqueConstraint("clinica_id", "sede_id", "fecha", name="uq_cierres_caja_clinica_sede_fecha"),
    )

    id: int | None = Field(default=None, primary_key=True)
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    sede_id: int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    fecha: date | None = Field(
        default=None, sa_column=Column(Date, default=date.today, nullable=True)
    )
    total_ingresos: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    total_egresos: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    saldo: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    usuario_id: int | None = Field(default=None, foreign_key="usuarios.id", nullable=True)
    creado_en: datetime | None = Field(
        default=None, sa_column=Column(DateTime, default=_utcnow, nullable=True)
    )
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, nullable=True, index=True)

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()


class ComprobanteItem(SQLModel, table=True):
    __tablename__ = "comprobante_items"

    id: int | None = Field(default=None, primary_key=True)
    comprobante_id: int = Field(foreign_key="comprobantes.id", nullable=False, index=True)
    tipo: str = Field(max_length=20, nullable=False)
    ref_id: int = Field(nullable=False)
    nombre: str = Field(max_length=200, nullable=False)
    cantidad: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 3), default=0, nullable=True)
    )
    precio_unit: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    subtotal: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )


class DeudaPaciente(SQLModel, table=True):
    __tablename__ = "deudas_paciente"

    id: int | None = Field(default=None, primary_key=True)
    clinica_id: int = Field(foreign_key="clinicas.id", nullable=False, index=True)
    sede_id: int | None = Field(default=None, foreign_key="sedes.id", nullable=True, index=True)
    paciente_id: int = Field(foreign_key="pacientes.id", nullable=False, index=True)
    comprobante_id: int = Field(foreign_key="comprobantes.id", nullable=False, index=True)
    total: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    pagado: Decimal | None = Field(
        default=Decimal("0"), sa_column=Column(Numeric(10, 2), default=0, nullable=True)
    )
    saldo: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    estado: str | None = Field(default="pendiente", max_length=20, nullable=True)
    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(default=None, nullable=True, index=True)
    creado_en: datetime | None = Field(
        default=None, sa_column=Column(DateTime, default=_utcnow, nullable=True)
    )
    actualizado_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=True),
    )

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = _utcnow()
