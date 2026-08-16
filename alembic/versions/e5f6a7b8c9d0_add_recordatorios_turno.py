"""add tabla recordatorios_turno (estado de envío de recordatorios)

Registra cada envío de recordatorio de turno (por canal) para dar idempotencia
al worker (no re-recordar un turno ya notificado) y trazabilidad del estado de
envío (enviado/fallido, destino, error).

Aditiva e idempotente: solo crea la tabla si no existe; no toca datos ni otras
tablas.

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tablas(conn) -> set[str]:
    return {
        r[0] for r in conn.execute(sa.text(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE()"
        )).fetchall()
    }


def upgrade() -> None:
    conn = op.get_bind()
    if "recordatorios_turno" in _tablas(conn):
        return
    op.create_table(
        "recordatorios_turno",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("clinica_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("turno_id", sa.Integer(), nullable=False),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("destino", sa.String(length=160), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["clinica_id"], ["clinicas.id"]),
        sa.ForeignKeyConstraint(["turno_id"], ["turnos.id"]),
    )
    op.create_index(op.f("ix_recordatorios_turno_created_at"), "recordatorios_turno", ["created_at"])
    op.create_index(op.f("ix_recordatorios_turno_clinica_id"), "recordatorios_turno", ["clinica_id"])
    op.create_index(op.f("ix_recordatorios_turno_is_active"), "recordatorios_turno", ["is_active"])
    op.create_index(op.f("ix_recordatorios_turno_deleted_at"), "recordatorios_turno", ["deleted_at"])
    op.create_index(op.f("ix_recordatorios_turno_turno_id"), "recordatorios_turno", ["turno_id"])


def downgrade() -> None:
    conn = op.get_bind()
    if "recordatorios_turno" not in _tablas(conn):
        return
    op.drop_table("recordatorios_turno")
