"""add impuesto al comprobante + modo de impuesto por clínica

Habilita el desglose de IGV/IVA en el punto de cobro:
- `clinicas.impuesto_modo` ('incluido' | 'agregado'): si el precio ya incluye
  el impuesto (se desglosa, el total no cambia) o si se agrega sobre el precio.
- `comprobantes.impuesto_tasa` y `comprobantes.impuesto_monto`: la tasa aplicada
  y el monto de impuesto de esa venta, congelados en el comprobante.

Aditiva e idempotente: solo agrega columnas que no existan; no toca datos.
El default 'incluido' + tasa 0 preserva el comportamiento anterior (total =
bruto − descuento) para las clínicas que no activen el impuesto.

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(conn, tabla: str) -> set[str]:
    return {
        r[0] for r in conn.execute(sa.text(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
        ), {"t": tabla}).fetchall()
    }


def upgrade() -> None:
    conn = op.get_bind()

    clinicas = _cols(conn, "clinicas")
    if "impuesto_modo" not in clinicas:
        op.add_column("clinicas", sa.Column(
            "impuesto_modo", sa.String(length=12),
            nullable=False, server_default="incluido",
        ))

    comprobantes = _cols(conn, "comprobantes")
    if "impuesto_tasa" not in comprobantes:
        op.add_column("comprobantes", sa.Column(
            "impuesto_tasa", sa.Numeric(5, 2), nullable=True, server_default="0",
        ))
    if "impuesto_monto" not in comprobantes:
        op.add_column("comprobantes", sa.Column(
            "impuesto_monto", sa.Numeric(10, 2), nullable=True, server_default="0",
        ))


def downgrade() -> None:
    conn = op.get_bind()

    comprobantes = _cols(conn, "comprobantes")
    if "impuesto_monto" in comprobantes:
        op.drop_column("comprobantes", "impuesto_monto")
    if "impuesto_tasa" in comprobantes:
        op.drop_column("comprobantes", "impuesto_tasa")

    clinicas = _cols(conn, "clinicas")
    if "impuesto_modo" in clinicas:
        op.drop_column("clinicas", "impuesto_modo")
