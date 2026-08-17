#!/usr/bin/env bash
# =============================================================================
# scripts/restore-db.sh — Restaurar un backup de MySQL de TUWAYKILIFE
#
# Descomprime un dump .sql.gz y lo carga en MySQL. Por defecto restaura sobre la
# BD de producción (DESTRUCTIVO: reemplaza los datos actuales) y PIDE
# confirmación. Con --db NAME restaura en una BD alterna (la crea si no existe),
# ideal para PROBAR un backup sin tocar los datos reales.
#
# Uso:
#   bash scripts/restore-db.sh backups/life_db_20260817_030000.sql.gz
#   bash scripts/restore-db.sh <archivo> --db life_db_restore_test   # prueba
#   bash scripts/restore-db.sh <archivo> --yes                       # sin prompt
#
# Variables de entorno:
#   MYSQL_CONTAINER  Nombre del contenedor MySQL (default: life_mysql)
#
# Códigos: 0 OK · 1 error/abortado
# =============================================================================
set -euo pipefail

MYSQL_CONTAINER="${MYSQL_CONTAINER:-life_mysql}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail() { echo -e "${RED}[FAIL]${NC}  $*" >&2; exit 1; }

FILE=""
TARGET_DB=""
ASSUME_YES=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes|-y)  ASSUME_YES=true ;;
        --db=*)    TARGET_DB="${1#*=}" ;;
        --db)      shift; TARGET_DB="${1:-}" ;;
        -h|--help) sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)        fail "Opción desconocida: $1 (usa --help)" ;;
        *)         [[ -z "$FILE" ]] && FILE="$1" || fail "Argumento extra: $1" ;;
    esac
    shift
done

[[ -n "$FILE" ]]      || fail "Falta el archivo de backup (.sql.gz). Usá --help."
[[ -f "$FILE" ]]      || fail "No existe el archivo: $FILE"
gzip -t "$FILE" 2>/dev/null || fail "El archivo no es un gzip válido: $FILE"
docker inspect "$MYSQL_CONTAINER" >/dev/null 2>&1 \
    || fail "El contenedor '$MYSQL_CONTAINER' no existe/no corre"

# BD destino: la de prod (env del contenedor) salvo que se pase --db.
MAIN_DB="$(docker exec "$MYSQL_CONTAINER" sh -c 'printf %s "$MYSQL_DATABASE"')"
DB="${TARGET_DB:-$MAIN_DB}"
IS_PROD=false
[[ "$DB" == "$MAIN_DB" ]] && IS_PROD=true

echo ""
info "Archivo : $FILE ($(du -h "$FILE" | cut -f1))"
info "Destino : base '$DB' en contenedor '$MYSQL_CONTAINER'"
$IS_PROD && warn "¡Es la BD de PRODUCCIÓN! Se REEMPLAZAN los datos actuales."

if ! $ASSUME_YES; then
    printf "¿Continuar? Escribí 'restaurar' para confirmar: "
    read -r RESP
    [[ "$RESP" == "restaurar" ]] || fail "Abortado por el usuario"
fi

# Si es una BD alterna (prueba), crearla vacía primero (necesita root).
if ! $IS_PROD; then
    info "Creando/limpiando BD de prueba '$DB'..."
    docker exec "$MYSQL_CONTAINER" sh -c \
        'mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS \`'"$DB"'\`; CREATE DATABASE \`'"$DB"'\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"' \
        2>/dev/null || fail "No se pudo crear la BD de prueba '$DB'"
fi

info "Restaurando… (puede tardar según el tamaño)"
# Se copia el dump AL contenedor y se descomprime/carga ADENTRO, en vez de
# pipear stdin con `docker exec -i` (que se cuelga en Git Bash/MSYS por el
# manejo de EOF). Así funciona igual en Linux/EC2 y en Windows.
TMP_C="/tmp/life_restore_$$.sql.gz"
MSYS_NO_PATHCONV=1 docker cp "$FILE" "$MYSQL_CONTAINER:$TMP_C" >/dev/null \
    || fail "No se pudo copiar el dump al contenedor"
if ! MSYS_NO_PATHCONV=1 docker exec "$MYSQL_CONTAINER" sh -c \
        'gunzip -c "'"$TMP_C"'" | mysql -u root -p"$MYSQL_ROOT_PASSWORD" "'"$DB"'"' 2>/dev/null; then
    MSYS_NO_PATHCONV=1 docker exec "$MYSQL_CONTAINER" rm -f "$TMP_C" 2>/dev/null || true
    fail "Falló la restauración"
fi
MSYS_NO_PATHCONV=1 docker exec "$MYSQL_CONTAINER" rm -f "$TMP_C" 2>/dev/null || true

TABLAS="$(docker exec "$MYSQL_CONTAINER" sh -c \
    'mysql -u root -p"$MYSQL_ROOT_PASSWORD" -N -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='"'"''"$DB"''"'"';"' 2>/dev/null)"
ok "Restauración OK — base '$DB' con ${TABLAS:-?} tablas"
$IS_PROD || info "Era una prueba: podés borrar la BD con: docker exec $MYSQL_CONTAINER mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" -e \"DROP DATABASE \\\`$DB\\\`;\""
