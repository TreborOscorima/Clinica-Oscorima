#!/usr/bin/env bash
# =============================================================================
# docker-entrypoint.sh — Pre-arranque del contenedor WaykiSAC Clínica
#
# 1. Espera a que MySQL esté disponible.
# 2. Ejecuta migraciones Alembic (upgrade head).
# 3. Pre-init Reflex + es-toolkit-shims (fix Vite/Rolldown CJS).
# 4. Arranca Reflex con los argumentos pasados por CMD.
#
# Misma mecánica que Sistema-de-Ventas / TUWAYKIFOOD.
# =============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${CYAN}[ENTRYPOINT]${NC} $*"; }
ok()    { echo -e "${GREEN}[ENTRYPOINT]${NC} $*"; }
warn()  { echo -e "${YELLOW}[ENTRYPOINT]${NC} $*"; }
fail()  { echo -e "${RED}[ENTRYPOINT]${NC} $*"; exit 1; }

# ─── 1. Esperar MySQL ───────────────────────────────────────────────────────
# La clínica usa variables MYSQL_* (ver clinica_app/config.py)
DB_HOST="${MYSQL_HOST:-life_mysql}"
DB_PORT="${MYSQL_PORT:-3306}"
MAX_WAIT=120
SOCKET_TIMEOUT=5

sleep 3

info "Esperando MySQL en ${DB_HOST}:${DB_PORT}..."
WAITED=0
while [[ $WAITED -lt $MAX_WAIT ]]; do
    if python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(${SOCKET_TIMEOUT})
try:
    s.connect(('${DB_HOST}', ${DB_PORT}))
    s.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [[ $WAITED -ge $MAX_WAIT ]]; then
    fail "MySQL no disponible después de ${MAX_WAIT}s"
fi
ok "MySQL disponible"

# ─── 2. Esquema de base de datos ───────────────────────────────────────────
SKIP_MIGRATE="${SKIP_MIGRATE:-false}"
if [[ "$SKIP_MIGRATE" != "true" ]]; then
    # Detectar si la DB está vacía (primer deploy / volumen nuevo)
    TABLE_COUNT=$(python3 -c "
import pymysql, os
conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST','life_mysql'),
    port=int(os.getenv('MYSQL_PORT','3306')),
    user=os.getenv('MYSQL_USER','clinica'),
    password=os.getenv('MYSQL_PASSWORD',''),
    database=os.getenv('MYSQL_DB','life_db')
)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s', (os.getenv('MYSQL_DB','life_db'),))
print(cur.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")

    if [[ "$TABLE_COUNT" -eq 0 ]]; then
        info "DB vacía detectada — creando esquema completo con SQLModel create_all..."
        python3 -c "
from clinica_app.models import *
from clinica_app.database import _sync_engine
from sqlmodel import SQLModel
SQLModel.metadata.create_all(_sync_engine)
print('create_all OK')
"
        if [[ $? -ne 0 ]]; then
            fail "create_all falló — abortando"
        fi
        info "Marcando Alembic head (stamp)..."
        alembic stamp head || fail "alembic stamp head falló"
        ok "Esquema creado + Alembic stamp head OK"
    else
        info "DB existente ($TABLE_COUNT tablas) — ejecutando migraciones Alembic..."
        if ! alembic upgrade head; then
            fail "Migraciones fallaron — abortando arranque"
        fi
        ok "Migraciones aplicadas correctamente"
    fi
else
    warn "Migraciones saltadas (SKIP_MIGRATE=true)"
fi

# ─── 3. Pre-init Reflex ─────────────────────────────────────────────────────
info "Pre-inicializando frontend (reflex init)..."
reflex init 2>&1 | tail -3 && ok "reflex init OK" || warn "reflex init con error — continuando"

# ─── 4. Ejecutar CMD (reflex run ...) ───────────────────────────────────────
info "Iniciando Reflex: $*"
exec "$@"
