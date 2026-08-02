# AUDITORÍA COMPLETA + HANDOFF — WaykiSAC Clínica (Clinica-Oscorima)

> **Fecha:** 2026-07-06
> **Propósito:** Este documento es autosuficiente. Cualquier IA o desarrollador debe poder
> leerlo y continuar el proyecto sin contexto adicional. Cubre: qué es el sistema, cómo
> arranca (nativo y Docker), hallazgos de seguridad/backend/frontend con archivo:línea
> exactos, qué se cambió en esta auditoría, y el roadmap priorizado.

---

## 1. Qué es este sistema

**WaykiSAC Clínica** es un SaaS multi-tenant de gestión para clínicas con atenciones
variadas (estética, odontología, masajes, etc.). Repo: `https://github.com/TreborOscorima/Clinica-Oscorima.git`,
ruta local `D:\PROYECTOS\Clinica-Oscorima`.

Convive en el mismo servidor AWS con otros dos sistemas del mismo autor, con los que
comparte la **mecánica de deploy Docker + Nginx Proxy Manager (NPM)**:

| Sistema | Repo | Contenedor app | Dominio |
|---|---|---|---|
| Sistema de Ventas | TreborOscorima/Sistema-de-Ventas | `tuwayki_sys` | (ventas) |
| Food | TreborOscorima/Sistema-para-Food | `tuwayki_food:3000` | food.tuwayki.app |
| **Clínica / TUWAYKILIFE (este repo)** | TreborOscorima/Gestion-de-Clinica | `tuwayki_life:3000` | life.tuwayki.app *(ajustable)* |

### Stack
- **Reflex 0.9.4** (Python full-stack: frontend React/Vite compilado + backend FastAPI/WebSocket)
- **Python 3.13**, SQLModel + SQLAlchemy 2 async (**aiomysql**), MySQL 8
- TailwindCSS v4 (plugin), bcrypt, openpyxl (Excel), reportlab (PDF), Twilio (WhatsApp), SMTP (email)
- Alembic para migraciones (5 revisiones en `alembic/versions/`)
- Tests: pytest en `tests/` (auth, cobro, cuentas, pacientes, turnos)

### Multi-tenant / multi-sede
- Tenant = `clinica_id` (tabla `clinicas`). **Nunca viene del cliente**: se resuelve en login
  y vive en el estado servidor de Reflex (`BaseState.clinica_id`, `state/base.py`).
- Multi-sede: `sede_id` en 9+ modelos; selector de sucursal post-login (`state/auth.py`);
  todos los servicios filtran por `clinica_id` y opcionalmente `sede_id`.
- Roles: `administracion`, `recepcionista`, `profesional`, `contador` (`models/user.py`).

### Estructura del código
```
clinica_app/
├── clinica_app.py      # entry point: rx.App, rutas, endpoints Starlette (/health, /api/*)
├── config.py           # env vars (MYSQL_*, SECRET_KEY, SMTP, TWILIO, etc.)
├── database.py         # engine síncrono (Alembic/CLI) + asíncrono (event handlers)
├── models/             # SQLModel — 1 archivo por dominio; TenantSQLModel agrega clinica_id
├── services/           # lógica de negocio async; SIEMPRE reciben (session, clinica_id, ...)
├── state/              # Reflex States; BaseState = auth + tenant; 1 State por módulo
├── pages/              # UI Reflex (rx.el.* + Tailwind); shell() de components/layout.py
├── components/         # layout, sidebar, ui.py (page_header, empty_state, botones), badge, stat_card
└── tasks/              # reportes Excel (sync), recordatorios (cron script)
alembic/                # migraciones
tests/                  # pytest
scripts/                # docker-entrypoint.sh, deploy-prod.sh
```

### Módulos implementados (16, todos funcionales)
Login (rate-limit persistente), Dashboard (KPIs+gráficos), Pacientes, Profesionales,
Turnos (notif. email/WhatsApp), Calendario semanal, Servicios (historial precios),
Cobro/POS (carrito, cuotas, comprobante, PDF), Caja (cierres diarios), Cuentas corrientes,
Compras (recepción→stock), Inventario, Promociones, Reportes (Excel), Configuración
(clínica, usuarios, permisos, sedes, monedas, impuestos, métodos de pago, unidades),
Historia Clínica.

### Cómo arrancar
**Desarrollo nativo (Windows):**
```bash
# .env con MYSQL_HOST=127.0.0.1, MYSQL_PORT=3307 (MySQL local), ENV=dev
.venv\Scripts\activate
python -m reflex run          # → http://localhost:3003
```
**Docker local:**
```bash
cp .env.example .env   # completar MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD, SECRET_KEY
docker network create nginx-proxy-manager_default   # una sola vez
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
# → http://localhost:3004  (MySQL en localhost:33308)
```
**Producción (AWS):**
```bash
bash scripts/deploy-prod.sh   # backup → git pull → build → health → NPM
```
Usuario de prueba: `admin@wayki.com` (rol administracion, clinica_id=1).

---

## 2. Cambios aplicados en ESTA auditoría (2026-07-06)

Se replicó la mecánica Docker de Ventas/Food (el Dockerfile anterior estaba **roto**:
referenciaba `requirements_reflex.txt` inexistente, y el compose montaba Redis/worker RQ
que el código nunca usa).

| Archivo | Cambio |
|---|---|
| `Dockerfile` | **Reescrito**: multi-stage python 3.13-slim, usuario no-root `app`, `tini`, healthcheck `/api/ping`, CMD `reflex run --env prod --single-port` en puerto 3000 |
| `scripts/docker-entrypoint.sh` | **Nuevo**: espera MySQL → `alembic upgrade head` → `reflex init` → shims es-toolkit (fix Vite/Rolldown, idéntico a Food) |
| `docker-compose.yml` | **Reescrito**: servicios `life_mysql` + `tuwayki_life`, red interna + red externa `nginx-proxy-manager_default`, healthchecks, límites de memoria, log rotation |
| `docker-compose.local.yml` | **Nuevo**: override local — app en `3004:3000`, MySQL en `33308:3306` (evita choque con Food local 3003/33307 y dev nativo 3003) |
| `scripts/deploy-prod.sh` | **Nuevo**: adaptado de Food — valida .env, backup MySQL, git reset a rama (default `main`), build, espera healthy, verifica `/api/health` público |
| `.env.example` | **Reescrito**: agrega `MYSQL_ROOT_PASSWORD`, `ENV`, `PUBLIC_API_URL`, `CLINICA_NOMBRE`, SMTP/Twilio; documenta los 3 modos de arranque |
| `rxconfig.py` | Env-driven: `FRONTEND_PORT` (3003 nativo / 3000 Docker), `api_url` desde `PUBLIC_API_URL`, **fail-hard en prod si faltan `MYSQL_PASSWORD` o `SECRET_KEY`**, telemetría off en prod |
| `clinica_app/clinica_app.py` | Agregados `/api/ping` (healthcheck contenedor) y `/api/health` (devuelve `app: waykisac-clinica`, usado por deploy-prod.sh) |
| `requirements.txt` | **Agregados `aiomysql` y `greenlet`** (estaban instalados a mano — la imagen Docker no arrancaba sin ellos) y `twilio`; **removidos `redis` y `rq`** (no se usan en ningún archivo) |

**Pendiente manual (bloqueado por permisos en esta sesión):** borrar `Dockerfile.worker`
(worker RQ nunca usado; el compose ya no lo referencia) y el archivo basura `=1.13.0`
en la raíz (residuo de un `pip install alembic>=1.13.0` sin comillas). También
`start_redis.bat` quedó obsoleto.

**NPM en el servidor (primer deploy):** Proxy Host → Domain `life.tuwayki.app`
(o el dominio real; ajustar `PUBLIC_URL` en deploy y `PUBLIC_API_URL` en compose),
Forward `tuwayki_life:3000`, WebSockets **ON**, red `nginx-proxy-manager_default`.

---

## 3. AUDITORÍA DE SEGURIDAD

### 🔴 CRÍTICOS (corregir antes de producción)

**S1.** ~~`/api/recibo/pdf` sin autenticación~~ ✅ RESUELTO — token HMAC firmado (TTL 120s)
en `services/download_token.py`, validado en endpoint; `clinica_id` del token vs query param.

**S2.** ~~`/api/reportes/descargar/{filename}` sin autenticación~~ ✅ RESUELTO — mismo
esquema de token firmado HMAC que S1.

**S3. ~~RBAC decorativo — los permisos por rol NO se aplican~~ ✅ RESUELTO**
`services/permisos.py` carga `PermisoRol` al login → `BaseState._permisos` (cache) +
`modulos_permitidos` (var reactiva). `tiene_permiso(module, write)` se usa en `on_mount`
de las 15 páginas y en write guards de handlers críticos. Sidebar filtra links con
`rx.cond(BaseState.modulos_permitidos.contains(module))`. Auto-seed de defaults por rol.

**S4. ~~`PermisoRol` es global — cruza tenants~~ ✅ RESUELTO**
`clinica_id` agregado a `permisos_rol` (migración `a1b2c3d4e5f6`). Todos los queries
en `services/permisos.py` y `state/configuracion.py` filtran por `clinica_id`.

### 🟠 ALTOS

**S5.** ~~Numeración de comprobantes con race condition~~ ✅ RESUELTO — `_numero()` usa
`SELECT MAX(numero) ... FOR UPDATE` + `Comprobante.numero` con UNIQUE constraint.

**S6.** ~~Generación de Excel bloquea todo el servidor~~ ✅ RESUELTO — `state/reportes.py`
usa `await asyncio.to_thread(svc.generar_reporte, ...)` y `clinica_app.py` usa
`await asyncio.to_thread(generar_recibo_pdf, ...)` para PDF.

**S7.** ~~Drift de esquema: `create_all` + ALTER manuales vs Alembic~~ ✅ RESUELTO —
`_migrate_columns()` eliminado; columnas `margen_global`/`margen_local` capturadas en
migración `074568f4cfb8`. `create_all` permanece como fallback dev (normal en Reflex).

**S8.** ~~Venta descuenta stock sin validar~~ ✅ RESUELTO — `_descontar_stock()` retorna
warnings de stock negativo/agotado; `crear()` los incluye en el resultado; el modal de
recibo en `pages/cobro.py` muestra alerta visual amber. No bloquea la venta (decisión
de negocio: una clínica no puede dejar de atender por falta de stock).

### 🟡 MEDIOS

- **S9.** ~~`LoginIntento` nunca se purga~~ ✅ RESUELTO — purge oportunista > 24h en cada login.
- **S10.** ~~`app._api` es API privada~~ ✅ RESUELTO — migrado a `rx.App(api_transformer=...)`.
- **S11.** `models/user.py` `set_password`: `raw[:72]` trunca por *caracteres*; bcrypt
  limita 72 *bytes*. ✅ YA CORRECTO — el código usa `raw.encode("utf-8")[:72]` (bytes).
- **S12.** Email de usuario único **global** (`uq_usuarios_email`) — decisión de diseño
  coherente con login sin selector de tenant. ✅ DOCUMENTADO, no requiere fix.
- **S13.** ~~83 archivos sin commit~~ ✅ RESUELTO — todo commiteado y pusheado.
- **S14.** Headers de seguridad (HSTS, X-Frame-Options, etc.): ✅ DOCUMENTADO — configurar
  en NPM → Proxy Host → Advanced → Custom Nginx Configuration:
  ```
  add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
  ```
  ⚠️ INFRAESTRUCTURA — no es cambio de código, aplicar manualmente en NPM.

### ✅ Lo que está BIEN en seguridad
- `.env` correctamente en `.gitignore` y `.dockerignore`; sin secretos commiteados.
- bcrypt con salt; comparación en `asyncio.to_thread` (no bloquea el loop).
- Rate limiting de login **persistente en DB** (5 intentos/60s) con mensaje genérico
  anti user-enumeration (`services/auth.py`).
- Tenant (`clinica_id`) resuelto solo en servidor; todos los servicios auditados filtran
  por `clinica_id` (356 usos verificados en `services/`).
- SQL 100% parametrizado vía SQLModel/SQLAlchemy — sin inyección detectada.
- Contenedor: usuario no-root, tini, imagen slim (desde hoy).

---

## 4. AUDITORÍA BACKEND / RENDIMIENTO

- **Arquitectura sana**: separación estricta pages → state → services → models; servicios
  async puros que reciben `(session, clinica_id, ...)` — fácil de testear y de portar.
- **Pools**: async 10+20 overflow, `pool_recycle=1800` (aiomysql sin pre-ping — correcto,
  incompatible); sync 5+10 solo para Alembic/CLI. Adecuado para 1 contenedor con 1G RAM.
- **Paginación** en todos los listados; `selectinload` donde hubo N+1 (notas clínicas).
- **Mejoras recomendadas**:
  1. `asyncio.to_thread` para openpyxl/reportlab (ver S6 — es lo más urgente).
  2. Revisar índices compuestos: los WHERE típicos son `(clinica_id, sede_id, fecha)`
     en `caja_movimientos`, `turnos`, `comprobantes`. Verificar con `EXPLAIN` y agregar
     índices via Alembic si falta.
  3. `except Exception: pass` silencioso en varios States (ej. `state/reportes.py`
     `_cargar_kpis`) — loggear como mínimo (`logging.exception`).
  4. Si algún día hay >1 contenedor app: Reflex necesita `REFLEX_REDIS_URL` para estado
     compartido (hoy todo en memoria de 1 proceso — correcto para 1 réplica).
- **Tests**: existen 5 suites pytest; correrlas en CI (GitHub Actions como en Ventas/Food)
  antes de cada deploy. No se ejecutaron en esta sesión.

---

## 5. AUDITORÍA FRONTEND / UI-UX

**Veredicto general: bueno y consistente.** Design system informal pero disciplinado:
Tailwind sky-600 como acento, `components/ui.py` (page_header, empty_state, primary_btn,
secondary_btn, table_header), badges consistentes, stat_cards, estados vacíos en todas
las tablas, responsive real (sidebar desktop + drawer/topbar mobile), atajos de teclado
globales (Alt+1..7, N, /, Esc, Ctrl+Enter) — nivel superior al típico CRUD.

**Hallazgos:**

- **F1:** ~~tarjeta Egresos mostraba var de ingresos~~ ✅ RESUELTO — usa `egresos_mes_ant`.
- **F2:** ~~viewport `maximum-scale=1` bloqueaba zoom~~ ✅ RESUELTO — viewport sin restricción.
- **F3 (mantenibilidad):** ~~páginas monolíticas~~ ✅ RESUELTO — `compras.py` dividido en
  `pages/compras/` (5 submódulos) y `configuracion.py` dividido en `pages/configuracion/`
  (9 submódulos). Imports en `clinica_app.py` sin cambios.
- **F4:** ~~fuente Inter desde Google Fonts CDN~~ ✅ RESUELTO — self-hosted en `assets/fonts/`.
- **F5:** ~~variación 0% pintaba rojo~~ ✅ RESUELTO — lógica invertida: rojo solo si
  empieza con "-", verde para 0% y positivos.
- **F6:** el gráfico de barras artesanal (divs) funciona; si se piden más gráficos,
  wrappear recharts en vez de crecer el hack.
- **F7:** ~~sidebar muestra TODOS los módulos a todos los roles~~ ✅ RESUELTO con S3.

**Patrones Reflex críticos del proyecto (respetarlos al continuar):**
1. `session.execute()` (no `session.exec()`) para agregados con subquery (`.scalar_one()`).
2. En Vars de Reflex NUNCA `dict.get()` — usar `State.d["key"]` con dicts inicializados
   con todas las claves.
3. `rx.foreach` sobre listas anidadas: extraerlas como var tipada `list[dict]` separada.
4. Si React falla con `useContext null`: borrar `.web/` y re-correr.
5. Reflex 0.9.x NO autogenera setters en sub-states — declararlos explícitos.
6. Listas/carrito: reasignar la lista completa (inmutabilidad), no mutar in-place.
7. NO usar `rx.debounce_input` (crashea React en 0.9.x).

---

## 6. ROADMAP PRIORIZADO

### ✅ Completados
1. ~~Commitear trabajo pendiente~~ — todo commiteado y pusheado.
2. ~~S1 + S2 (endpoints sin auth)~~ — tokens HMAC firmados.
3. ~~S3 + S4 (RBAC real)~~ — `clinica_id` en permisos + enforcement en States y sidebar.
4. ~~S5 (race condition comprobantes)~~ — `SELECT ... FOR UPDATE` + UNIQUE.
5. ~~S6 (`asyncio.to_thread`)~~ — reportes Excel y PDF ya async.
6. ~~S7 (drift Alembic)~~ — `_migrate_columns()` eliminado, columnas en migraciones.
7. ~~F1-F5, S9-S14, F3-F4, F7~~ — todos resueltos o documentados.
8. ~~Archivos basura~~ — `Dockerfile.worker`, `=1.13.0`, `start_redis.bat` ya eliminados.

### Pendientes
- ~~**S8 (stock)**~~ ✅ — warnings de stock negativo/agotado en modal recibo post-venta.
- ~~**CI**~~ ✅ — `.github/workflows/ci.yml` (Python 3.13, pytest, push a main/docker-deploy-prod).
- ~~**Docker local**~~ ✅ — build + login + cobro + PDF verificados en `localhost:3004`.
  Fix: RBAC módulos faltantes auto-seeded; API routes via ASGI middleware (single-port).
- **Deploy AWS**: primer deploy con `scripts/deploy-prod.sh` + configurar NPM.
- **S14 (infraestructura)**: aplicar headers de seguridad en NPM (documentado arriba).
- ~~**Tests**~~ ✅ — 35 tests migrados a `pytest-asyncio` con `aiosqlite` (0 failures).

## 7. Notas operativas para quien continúe

- Variables de entorno: ver `.env.example` (completo y comentado). En prod son
  obligatorias `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `SECRET_KEY` (≥32 chars) —
  `rxconfig.py` y `deploy-prod.sh` fallan si faltan.
- El contenedor sirve **todo en el puerto 3000** (`--single-port`); NPM hace TLS y proxy.
  Las rutas custom (`/api/*`) funcionan via ASGI middleware (intercepta antes del SPA fallback).
  El healthcheck interno es `GET /api/ping`; el externo `GET /api/health` debe devolver
  `{"status":"ok","app":"waykisac-clinica"}`.
- El entrypoint corre `alembic upgrade head` en cada arranque (`SKIP_MIGRATE=true` lo salta).
- MySQL nativo local del desarrollador corre en puerto **3307**; el Docker local publica
  **33308** — no confundir.
- Los es-toolkit-shims del entrypoint son un workaround conocido de Reflex 0.9.x +
  Vite/Rolldown (idéntico en Food) — no eliminarlos sin verificar que Reflex lo arregló.
- Memoria persistente del proyecto (para Claude Code): 
  `~/.claude/projects/D--PROYECTOS-Clinica-Oscorima/memory/` (contexto, patrones Reflex,
  pendientes).
