#!/usr/bin/env bash
# =============================================================================
# scripts/deploy-prod.sh — Deploy Docker producción WaykiSAC Clínica
#
# Uso:
#   bash scripts/deploy-prod.sh                      # Deploy completo
#   bash scripts/deploy-prod.sh --skip-backup        # Sin backup de MySQL
#   bash scripts/deploy-prod.sh --skip-build         # Solo recreate (sin rebuild)
#   bash scripts/deploy-prod.sh --skip-npm           # Sin reiniciar NPM al final
#   bash scripts/deploy-prod.sh --skip-public-check  # Sin verificar URL pública (primer deploy / NPM pendiente)
#
# Variables de entorno opcionales:
#   APP_DIR              Directorio del proyecto (default: padre de scripts/)
#   BRANCH               Rama a desplegar (default: main)
#   HEALTH_WAIT_MAX      Iteraciones de espera × 15s (default: 80 → 20 min)
#   BACKUP_KEEP          Backups .sql.gz a conservar (default: 5)
#   NPM_NETWORK          Red externa de NPM (default: nginx-proxy-manager_default)
#   PUBLIC_URL           URL pública para health check (default: https://clinica.tuwayki.app)
#
# Requisitos en el servidor:
#   - .env con MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD, SECRET_KEY
#   - NO definir MYSQL_HOST=localhost (compose inyecta clinica_mysql)
#   - Red externa nginx-proxy-manager_default (compartida con Ventas/Food)
#   - NPM: Proxy Host → wayki_clinica:3000, WebSockets ON
#
# Convive con Sistema-de-Ventas y TUWAYKIFOOD — DB y red internas propias.
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BRANCH="${BRANCH:-main}"
HEALTH_WAIT_MAX="${HEALTH_WAIT_MAX:-80}"
BACKUP_KEEP="${BACKUP_KEEP:-5}"
NPM_NETWORK="${NPM_NETWORK:-nginx-proxy-manager_default}"
PUBLIC_URL="${PUBLIC_URL:-https://clinica.tuwayki.app}"

SKIP_BACKUP=false
SKIP_BUILD=false
SKIP_NPM=false
SKIP_PUBLIC_CHECK=false

for arg in "$@"; do
    case "$arg" in
        --skip-backup) SKIP_BACKUP=true ;;
        --skip-build)  SKIP_BUILD=true ;;
        --skip-npm)    SKIP_NPM=true ;;
        --skip-public-check) SKIP_PUBLIC_CHECK=true ;;
        -h|--help)
            sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            fail "Argumento desconocido: $arg (usa --help)"
            ;;
    esac
done

cd "$APP_DIR"
info "Deploy WaykiSAC Clínica prod en: $APP_DIR"
info "Branch: $BRANCH | NPM: $NPM_NETWORK | URL: $PUBLIC_URL"

# ─── Prerrequisitos ───────────────────────────────────────────────────────────
command -v git    >/dev/null 2>&1 || fail "git no encontrado"
command -v docker >/dev/null 2>&1 || fail "docker no encontrado"
docker compose version >/dev/null 2>&1 || fail "docker compose no disponible"
[[ -f "$APP_DIR/.env" ]] || fail "No existe .env — copiar desde .env.example"
[[ -f "$APP_DIR/docker-compose.yml" ]] || fail "No existe docker-compose.yml"

# ─── Validar .env ─────────────────────────────────────────────────────────────
validate_env() {
    local env_file="$APP_DIR/.env"
    local missing=()

    for var in MYSQL_PASSWORD MYSQL_ROOT_PASSWORD SECRET_KEY; do
        if ! grep -qE "^${var}=.+" "$env_file" 2>/dev/null; then
            missing+=("$var")
        fi
    done
    [[ ${#missing[@]} -eq 0 ]] || fail "Variables faltantes en .env: ${missing[*]}"

    if grep -qE '^MYSQL_HOST=(localhost|127\.0\.0\.1)' "$env_file" 2>/dev/null; then
        fail "MYSQL_HOST=localhost en .env rompe Docker — comentar esa línea"
    fi

    if grep -qE '^MYSQL_USER=root' "$env_file" 2>/dev/null; then
        fail "MYSQL_USER=root no permitido en Docker — usar 'clinica' (ver .env.example)"
    fi

    local secret_len
    secret_len="$(grep -E '^SECRET_KEY=' "$env_file" | cut -d= -f2- | tr -d '[:space:]' | wc -c)"
    [[ "$secret_len" -ge 32 ]] || fail "SECRET_KEY debe tener mínimo 32 caracteres"
}
validate_env
ok "Validación .env OK"

# ─── Red NPM ──────────────────────────────────────────────────────────────────
if ! docker network inspect "$NPM_NETWORK" >/dev/null 2>&1; then
    warn "Red $NPM_NETWORK no existe — creando..."
    docker network create "$NPM_NETWORK"
fi
ok "Red NPM disponible: $NPM_NETWORK"

# ─── 1. Backup BD ─────────────────────────────────────────────────────────────
if $SKIP_BACKUP; then
    warn "Backup omitido (--skip-backup)"
else
    if docker inspect clinica_mysql >/dev/null 2>&1; then
        BACKUP_DIR="$APP_DIR/backups"
        mkdir -p "$BACKUP_DIR"
        BACKUP="$BACKUP_DIR/clinica_db_$(date +%Y%m%d_%H%M%S).sql.gz"
        info "Backup clinica_mysql → $BACKUP"
        docker exec clinica_mysql sh -c \
            'mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" --single-transaction --routines --triggers --no-tablespaces' \
            | gzip > "$BACKUP"
        [[ -s "$BACKUP" ]] || { rm -f "$BACKUP"; fail "Backup vacío — abortado"; }
        ok "Backup OK ($(du -h "$BACKUP" | cut -f1))"
        ls -t "$BACKUP_DIR"/clinica_db_*.sql.gz 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | xargs -r rm -f
    else
        warn "clinica_mysql no corre — backup omitido (primer deploy?)"
    fi
fi

# ─── 2. Código ────────────────────────────────────────────────────────────────
# reset --hard: el servidor no debe tener edits locales; evita fallo en CD/Actions.
info "Actualizando código: origin/$BRANCH"
git fetch origin "$BRANCH"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout -f "$BRANCH"
else
    git checkout -B "$BRANCH" "origin/$BRANCH"
fi
git reset --hard "origin/$BRANCH"
ok "Commit: $(git log --oneline -1)"

# ─── 3. Build + deploy ────────────────────────────────────────────────────────
SERVICE=wayki_clinica

if $SKIP_BUILD; then
    warn "Build omitido (--skip-build)"
else
    info "Building imagen Docker ($SERVICE)..."
    docker compose build "$SERVICE"
fi

info "Levantando stack (prod + NPM)..."
docker compose up -d --remove-orphans

# ─── 4. Esperar healthy ─────────────────────────────────────────────────────
info "Esperando healthy de $SERVICE (máx $((HEALTH_WAIT_MAX * 15 / 60)) min)..."
all_healthy=false
for i in $(seq 1 "$HEALTH_WAIT_MAX"); do
    h="$(docker inspect --format='{{.State.Health.Status}}' "$SERVICE" 2>/dev/null || echo "missing")"
    if [[ "$h" == "healthy" ]]; then
        all_healthy=true
        ok "$SERVICE healthy (iteración $i)"
        break
    fi
    if (( i % 4 == 0 )); then
        info "  ...${i}/${HEALTH_WAIT_MAX} $SERVICE=$h"
    fi
    sleep 15
done

docker compose ps

if ! $all_healthy; then
    warn "Timeout de health — últimos logs:"
    docker compose logs "$SERVICE" --tail=40
    fail "$SERVICE no llegó a healthy"
fi

# ─── 5. Verificación interna (/api/ping) ────────────────────────────────────
info "Verificando /api/ping dentro del contenedor..."
docker exec "$SERVICE" curl -sf http://localhost:3000/api/ping >/dev/null \
    || fail "Ping falló en $SERVICE"
ok "Ping OK: $SERVICE"

# ─── 6. NPM + health externo ──────────────────────────────────────────────────
if ! $SKIP_NPM; then
    NPM_CONTAINER="$(docker ps --format '{{.Names}}' | grep -iE 'nginx-proxy-manager|npm' | head -1 || true)"
    if [[ -n "$NPM_CONTAINER" ]]; then
        info "Reiniciando proxy: $NPM_CONTAINER"
        docker restart "$NPM_CONTAINER" >/dev/null
        sleep 15
        ok "NPM reiniciado"
    else
        warn "Contenedor NPM no encontrado — omitiendo restart"
    fi
fi

info "Verificando endpoint público..."
if $SKIP_PUBLIC_CHECK; then
    warn "Health externo omitido (--skip-public-check)"
else
    HEALTH_URL="${PUBLIC_URL%/}/api/health"
    health_body="$(curl -sf --max-time 15 "$HEALTH_URL" 2>/dev/null || true)"
    app_id="$(echo "$health_body" | grep -o '"app":"[^"]*"' || true)"
    health_status="$(echo "$health_body" | grep -o '"status":"[^"]*"' || true)"
    if [[ "$app_id" == *waykisac-clinica* && "$health_status" == *ok* ]]; then
        ok "clinica → ${health_status} ${app_id}"
    else
        warn "Health externo falló: $HEALTH_URL"
        [[ -n "$health_body" ]] && echo "  Respuesta: $health_body"
        echo ""
        echo "  El contenedor está OK internamente. Si es el primer deploy, configurá NPM:"
        echo "    Domain: clinica.tuwayki.app"
        echo "    Forward Hostname: wayki_clinica"
        echo "    Forward Port: 3000"
        echo "    Websockets: ON"
        echo "    Red: nginx-proxy-manager_default (misma que tuwayki_sys y tuwayki_food)"
        echo ""
        echo "  Verificá red del contenedor:"
        echo "    docker inspect wayki_clinica --format '{{range \$k,\$v := .NetworkSettings.Networks}}{{printf \"%s \" \$k}}{{end}}'"
        echo ""
        fail "Health externo no devolvió app=waykisac-clinica status=ok — revisá NPM/DNS/SSL o usá --skip-public-check"
    fi
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  DEPLOY WAYKISAC CLÍNICA PROD COMPLETADO${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo "  Commit:  $(git rev-parse --short HEAD)"
echo "  Branch:  $BRANCH"
echo "  URL:     $PUBLIC_URL"
echo "  NPM:     wayki_clinica:3000 en red $NPM_NETWORK"
echo "  Logs:    docker logs wayki_clinica -f"
echo ""
