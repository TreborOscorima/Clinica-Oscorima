"""add_licencia_saas_to_clinicas

Campos de licencia SaaS en `clinicas`, gestionados por el panel Owner de
TUWAYKI vía /api/admin/*: plan, licencia_activa, trial_ends_at, plan_expires_at.

Revision ID: c3f1a2b4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-08-02 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3f1a2b4d5e6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [r[0] for r in conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clinicas'"
    )).fetchall()]

    if 'plan' not in cols:
        op.add_column('clinicas', sa.Column(
            'plan', sa.String(length=20), nullable=False, server_default='trial'
        ))
    if 'licencia_activa' not in cols:
        op.add_column('clinicas', sa.Column(
            'licencia_activa', sa.Boolean(), nullable=False, server_default=sa.text('1')
        ))
    if 'trial_ends_at' not in cols:
        op.add_column('clinicas', sa.Column('trial_ends_at', sa.DateTime(), nullable=True))
    if 'plan_expires_at' not in cols:
        op.add_column('clinicas', sa.Column('plan_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('clinicas', 'plan_expires_at')
    op.drop_column('clinicas', 'trial_ends_at')
    op.drop_column('clinicas', 'licencia_activa')
    op.drop_column('clinicas', 'plan')
