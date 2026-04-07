"""renombrar_tablas_a_espanol

Revision ID: 6cf17fdcc226
Revises: b4288f6adaf9
Create Date: 2026-04-07 20:06:17.997620

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '6cf17fdcc226'
down_revision = 'b4288f6adaf9'
branch_labels = None
depends_on = None

def upgrade():
    # Renombrar tablas preservando los datos
    op.rename_table('users', 'usuarios')
    op.rename_table('role_permissions', 'permisos_rol')
    op.rename_table('audit_logs', 'auditoria')

def downgrade():
    op.rename_table('usuarios', 'users')
    op.rename_table('permisos_rol', 'role_permissions')
    op.rename_table('auditoria', 'audit_logs')

