"""add_clinica_id_to_permisos_rol

Revision ID: a1b2c3d4e5f6
Revises: 7996301d409a
Create Date: 2026-07-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7996301d409a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [r[0] for r in conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'permisos_rol'"
    )).fetchall()]

    if 'clinica_id' not in cols:
        op.add_column('permisos_rol', sa.Column('clinica_id', sa.Integer(), nullable=True))

    op.execute("UPDATE permisos_rol SET clinica_id = (SELECT id FROM clinicas LIMIT 1) WHERE clinica_id IS NULL")

    op.alter_column('permisos_rol', 'clinica_id', nullable=False, existing_type=sa.Integer())

    constraints = [r[0] for r in conn.execute(sa.text(
        "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'permisos_rol' AND CONSTRAINT_TYPE = 'UNIQUE'"
    )).fetchall()]

    if 'uq_permisos_rol' in constraints:
        op.drop_constraint('uq_permisos_rol', 'permisos_rol', type_='unique')

    if 'uq_permisos_rol_clinica' not in constraints:
        op.create_unique_constraint('uq_permisos_rol_clinica', 'permisos_rol', ['clinica_id', 'role', 'module'])

    fks = [r[0] for r in conn.execute(sa.text(
        "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'permisos_rol' AND CONSTRAINT_TYPE = 'FOREIGN KEY'"
    )).fetchall()]

    if 'fk_permisos_rol_clinica' not in fks:
        op.create_foreign_key('fk_permisos_rol_clinica', 'permisos_rol', 'clinicas', ['clinica_id'], ['id'])

    indexes = [r[2] for r in conn.execute(sa.text("SHOW INDEX FROM permisos_rol")).fetchall()]
    if 'ix_permisos_rol_clinica_id' not in indexes:
        op.create_index('ix_permisos_rol_clinica_id', 'permisos_rol', ['clinica_id'])


def downgrade() -> None:
    op.drop_constraint('uq_permisos_rol_clinica', 'permisos_rol', type_='unique')
    op.drop_index('ix_permisos_rol_clinica_id', 'permisos_rol')
    op.drop_constraint('fk_permisos_rol_clinica', 'permisos_rol', type_='foreignkey')
    op.drop_column('permisos_rol', 'clinica_id')
    op.create_unique_constraint('uq_permisos_rol', 'permisos_rol', ['role', 'module'])
