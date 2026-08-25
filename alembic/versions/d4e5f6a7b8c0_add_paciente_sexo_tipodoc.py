"""add paciente.sexo + paciente.tipo_documento y relaja el CHECK del documento

Agrega dos campos demográficos opcionales al paciente (sexo y tipo de
documento) y relaja el CHECK del documento de solo-dígitos a alfanumérico, para
poder registrar pasaportes y otros documentos con letras. La regla fina por
tipo (DNI/CE/RUC numéricos; pasaporte/otro alfanuméricos) vive en el servicio.

Aditiva e idempotente: solo agrega lo que falta y no toca datos existentes.

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a7b9
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c0'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columnas(conn, tabla: str) -> set[str]:
    return {
        r[0] for r in conn.execute(sa.text(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
        ), {"t": tabla}).fetchall()
    }


def _checks(conn, tabla: str) -> set[str]:
    return {
        r[0] for r in conn.execute(sa.text(
            "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = :t "
            "AND CONSTRAINT_TYPE = 'CHECK'"
        ), {"t": tabla}).fetchall()
    }


def upgrade() -> None:
    conn = op.get_bind()
    cols = _columnas(conn, "pacientes")
    if "tipo_documento" not in cols:
        op.add_column("pacientes", sa.Column("tipo_documento", sa.String(length=16), nullable=True))
    if "sexo" not in cols:
        op.add_column("pacientes", sa.Column("sexo", sa.String(length=16), nullable=True))

    checks = _checks(conn, "pacientes")
    if "chk_documento_digits" in checks:
        op.execute("ALTER TABLE pacientes DROP CHECK chk_documento_digits")
    if "chk_documento_alnum" not in _checks(conn, "pacientes"):
        op.execute(
            "ALTER TABLE pacientes ADD CONSTRAINT chk_documento_alnum "
            "CHECK (regexp_like(documento, '^[A-Za-z0-9]+$'))"
        )


def downgrade() -> None:
    conn = op.get_bind()
    checks = _checks(conn, "pacientes")
    if "chk_documento_alnum" in checks:
        op.execute("ALTER TABLE pacientes DROP CHECK chk_documento_alnum")
    if "chk_documento_digits" not in _checks(conn, "pacientes"):
        op.execute(
            "ALTER TABLE pacientes ADD CONSTRAINT chk_documento_digits "
            "CHECK (regexp_like(documento, '^[0-9]+$'))"
        )

    cols = _columnas(conn, "pacientes")
    if "sexo" in cols:
        op.drop_column("pacientes", "sexo")
    if "tipo_documento" in cols:
        op.drop_column("pacientes", "tipo_documento")
