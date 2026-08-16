"""add zona_codigo a adjuntos (E8 — fotos antes/después por zona)

Permite colgar una foto (`Adjunto` categoría "foto") directamente de una zona
anatómica (`zona_codigo`, del catálogo de services/anatomia) para la comparativa
antes/después por zona del mapa estético, sin depender de una `SesionEstetica`.

Aditiva e idempotente. Solo agrega una columna nullable + su índice; no toca
datos ni otras columnas.

Revision ID: c3d4e5f6a7b8
Revises: d7e8f9a0b1c2
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columnas(conn, tabla: str) -> set[str]:
    return {
        r[0] for r in conn.execute(sa.text(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
        ), {"t": tabla}).fetchall()
    }


def _indices(conn, tabla: str) -> set[str]:
    return {
        r[0] for r in conn.execute(sa.text(
            "SELECT INDEX_NAME FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
        ), {"t": tabla}).fetchall()
    }


def upgrade() -> None:
    conn = op.get_bind()
    if "zona_codigo" not in _columnas(conn, "adjuntos"):
        op.add_column("adjuntos", sa.Column("zona_codigo", sa.String(length=40), nullable=True))
    if "ix_adjuntos_zona_codigo" not in _indices(conn, "adjuntos"):
        op.create_index(op.f("ix_adjuntos_zona_codigo"), "adjuntos", ["zona_codigo"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if "ix_adjuntos_zona_codigo" in _indices(conn, "adjuntos"):
        op.drop_index(op.f("ix_adjuntos_zona_codigo"), table_name="adjuntos")
    if "zona_codigo" in _columnas(conn, "adjuntos"):
        op.drop_column("adjuntos", "zona_codigo")
