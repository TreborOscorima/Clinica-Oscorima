#!/usr/bin/env bash
# =============================================================================
# scripts/backup-db.sh — Backup de la BD MySQL de TUWAYKILIFE
#
# Hace un mysqldump del contenedor de MySQL, lo comprime, verifica su
# integridad y rota los viejos. Pensado para correr a diario por cron (Linux/
# EC2) o Task Scheduler (Windows), y también lo reusa scripts/deploy-prod.sh
# como backup pre-deploy.
#
# Uso:
#   bash scripts/backup-db.sh                 # backup a ./backups
#   BACKUP_DIR=/data/backups bash scripts/backup-db.sh
#
# Variables de entorno:
#   APP_DIR          Raíz del repo (default: padre de scripts/)
#   BACKUP_DIR       Destino de los dumps (default: $APP_DIR/backups)
#   BACKUP_KEEP      Backups .sql.gz a conservar (default: 14)
#   MYSQL_CONTAINER  Nombre del contenedor MySQL (default: life_mysql)
#
# Salida: crea $BACKUP_DIR/life_db_YYYYmmdd_HHMMSS.sql.gz
# Códigos: 0 OK · 1 error (contenedor caído, dump vacío/corrupto)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-life_mysql}"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
fail() { echo -e "${RED}[FAIL]${NC}  $*" >&2; exit 1; }

case "${1:-}" in -h|--help) sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;; esac

docker inspect "$MYSQL_CONTAINER" >/dev/null 2>&1 \
    || fail "El contenedor '$MYSQL_CONTAINER' no existe/no corre — no se puede respaldar"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEST="$BACKUP_DIR/life_db_${STAMP}.sql.gz"

info "Respaldando '$MYSQL_CONTAINER' → $DEST"
# mysqldump corre DENTRO del contenedor (usa sus propias env MYSQL_*), así el
# cliente coincide con la versión del server. --single-transaction = dump
# consistente sin lockear (InnoDB).
docker exec "$MYSQL_CONTAINER" sh -c \
    'mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" \
        --single-transaction --routines --triggers --no-tablespaces' \
    2>/dev/null | gzip > "$DEST"

# Verificaciones: no vacío + gzip íntegro (un dump truncado por OOM/disco lleno
# no debe pasar por bueno).
[[ -s "$DEST" ]]        || { rm -f "$DEST"; fail "Backup vacío — abortado"; }
gzip -t "$DEST" 2>/dev/null || { rm -f "$DEST"; fail "Backup corrupto (gzip -t falló) — abortado"; }

ok "Backup OK ($(du -h "$DEST" | cut -f1)) — $(basename "$DEST")"

# Rotación: conservar los BACKUP_KEEP más nuevos, borrar el resto.
BORRADOS="$(ls -t "$BACKUP_DIR"/life_db_*.sql.gz 2>/dev/null | tail -n +"$((BACKUP_KEEP + 1))" || true)"
if [[ -n "$BORRADOS" ]]; then
    echo "$BORRADOS" | xargs -r rm -f
    info "Rotación: borrados $(echo "$BORRADOS" | wc -l | tr -d ' ') backup(s) viejos (se conservan $BACKUP_KEEP)"
fi
