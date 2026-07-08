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
| **Clínica (este repo)** | TreborOscorima/Clinica-Oscorima | `wayki_clinica:3000` | clinica.tuwayki.app *(ajustable)* |

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
| `docker-compose.yml` | **Reescrito**: servicios `clinica_mysql` + `wayki_clinica`, red interna + red externa `nginx-proxy-manager_default`, healthchecks, límites de memoria, log rotation |
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

**NPM en el servidor (primer deploy):** Proxy Host → Domain `clinica.tuwayki.app`
(o el dominio real; ajustar `PUBLIC_URL` en deploy y `PUBLIC_API_URL` en compose),
Forward `wayki_clinica:3000`, WebSockets **ON**, red `nginx-proxy-manager_default`.

---

## 3. AUDITORÍA DE SEGURIDAD

### 🔴 CRÍTICOS (corregir antes de producción)

**S1. `/api/recibo/pdf` sin autenticación — IDOR entre clínicas**
`clinica_app/clinica_app.py` (`_generar_pdf_recibo`): acepta `?comp_id=X&clinica_id=Y`
por query string sin validar sesión. Cualquier persona puede enumerar IDs y descargar
recibos (nombres de pacientes + montos) de **cualquier clínica**.
*Fix sugerido:* firmar un token de un solo uso con `SECRET_KEY` (ej.
`hmac.new(SECRET_KEY, f"{clinica_id}:{comp_id}:{expiry}")`) generado por el State al
hacer clic en "Descargar PDF", y validarlo en el endpoint. Alternativa: generar el PDF
dentro del event handler y entregarlo con `rx.download`.

**S2. `/api/reportes/descargar/{filename}` sin autenticación**
`clinica_app/clinica_app.py` (`_descargar_reporte`): los Excel exportados (datos de
pacientes, caja, turnos) se sirven a quien conozca/adivine el filename. Los nombres
son predecibles (tipo + timestamp). `os.path.basename` evita path traversal, pero no
hay control de acceso ni de tenant.
*Fix:* mismo esquema de token firmado que S1, o `rx.download` con los bytes en memoria.

**S3. RBAC decorativo — los permisos por rol NO se aplican**
La tabla `PermisoRol` (`models/user.py`) se administra desde Configuración → Permisos,
pero **ningún** State/página/servicio la consulta (verificado por grep: solo
`state/configuracion.py` la lee para pintarla). El único control real es:
`shell()` exige login y el link + `on_mount` de Configuración exigen admin
(`state/configuracion.py:173`). Resultado: un usuario rol `profesional` o `contador`
puede entrar a `/caja`, `/cobro`, `/compras`, `/cuentas`, anular comprobantes y
registrar egresos manuales navegando directo a la URL.
*Fix:* helper en `BaseState` (ej. `tiene_permiso(module, write=False)`) que cachee
`PermisoRol` al login, llamado en cada `on_mount` de State y en los handlers de
escritura; ocultar además los links del sidebar según permiso.

**S4. `PermisoRol` es global — cruza tenants**
La tabla no tiene `clinica_id`: si el admin de la clínica A cambia un permiso, se lo
cambia a **todas** las clínicas del SaaS.
*Fix:* agregar `clinica_id` a `permisos_rol` (+ migración) y filtrar por él.

### 🟠 ALTOS

**S5. Numeración de comprobantes con carrera (race condition)**
`services/cobro.py` `_numero()`: calcula `COUNT(*)+1` de los comprobantes del día. Dos
cobros simultáneos (dos recepcionistas) obtienen el mismo número → recibos duplicados,
problema fiscal.
*Fix:* tabla de contadores con `SELECT ... FOR UPDATE`, o constraint UNIQUE en
`comprobantes.numero` + retry en `IntegrityError`.

**S6. Generación de Excel bloquea todo el servidor**
`state/reportes.py` (handler `generar_reporte`) llama `svc.generar_reporte(...)` que es
**síncrono** (openpyxl + engine síncrono, `tasks/reportes.py`) dentro del event loop
async de Reflex. Mientras se genera un reporte grande, la app entera se congela para
todos los usuarios (los WebSockets no procesan eventos).
*Fix mínimo (1 línea):* `filename = await asyncio.to_thread(svc.generar_reporte, ...)`.
Lo mismo aplica a `services/pdf_recibo.py` si `generar_recibo_pdf` (reportlab, sync) se
llama desde un handler.

**S7. Drift de esquema: `create_all` + ALTER manuales vs Alembic**
`clinica_app/clinica_app.py` ejecuta al importar: `SQLModel.metadata.create_all()` y
`_migrate_columns()` (ALTERs ad-hoc para `clinicas.margen_global`, `sedes.margen_local`,
etc.). Esas columnas **no existen en ninguna revisión Alembic**. El entrypoint Docker
corre `alembic upgrade head` y luego el import complementa — funciona, pero el estado
del esquema ya no es reproducible desde las migraciones.
*Fix:* `alembic revision --autogenerate -m "sync drift"` para capturar las columnas
faltantes; luego eliminar `_migrate_columns()` y (en prod) el `create_all`.

**S8. Venta descuenta stock sin validar**
`services/cobro.py` `_descontar_stock()`: si el producto no existe **retorna en
silencio** (se cobra el ítem sin movimiento de stock) y permite **stock negativo** sin
aviso. Decisión de negocio pendiente: ¿bloquear venta sin stock o permitir con warning?

### 🟡 MEDIOS

- **S9.** `LoginIntento` nunca se purga → la tabla crece para siempre. Agregar DELETE de
  registros > 24h (al validar login o cron).
- **S10.** `app._api` es API privada de Reflex — puede romperse en upgrades. Migrar a
  `rx.App(api_transformer=...)` cuando se toque ese código.
- **S11.** `models/user.py` `set_password`: `raw[:72]` trunca por *caracteres*; bcrypt
  limita 72 *bytes*. Un password con multibyte (ñ, emoji) >72 bytes lanza excepción en
  `checkpw` → capturada → login falla. Truncar con `raw.encode()[:72]`.
- **S12.** Email de usuario único **global** (`uq_usuarios_email`): el mismo email no
  puede existir en dos clínicas. Es coherente con el login sin selector de tenant —
  decisión de diseño, dejar documentado.
- **S13.** 83 archivos modificados sin commit en `main` (trabajo de varias sesiones).
  Riesgo real de pérdida. **Commitear ya** (ver roadmap).
- **S14.** Headers de seguridad (HSTS, X-Frame-Options, etc.): agregarlos en NPM
  (Advanced config del Proxy Host), igual que en los otros dos sistemas.

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

- **F1 (bug de datos):** `pages/dashboard.py:80` — la tarjeta **Egresos del mes** muestra
  `"Mes anterior: $ {ingresos_mes_ant}"` (ingresos en la card de egresos). Falta var
  `egresos_mes_ant` en `state/dashboard.py` o cambiar el label.
- **F2 (accesibilidad):** `rxconfig.py` meta viewport con `maximum-scale=1` bloquea el
  zoom en móviles — malo para usuarios con baja visión. Quitar `maximum-scale=1`.
- **F3 (mantenibilidad):** páginas monolíticas: `pages/configuracion.py` (1.257 líneas),
  `pages/compras.py` (1.012). Dividir en submódulos por tab (`pages/configuracion/…`).
- **F4:** fuente Inter desde Google Fonts CDN — en consultorio con internet inestable la
  UI carga con fallback. Considerar self-host en `assets/`.
- **F5:** variación % del dashboard pinta rojo cuando es "0%" (solo verde si empieza
  con "+") — caso borde menor.
- **F6:** el gráfico de barras artesanal (divs) funciona; si se piden más gráficos,
  wrappear recharts en vez de crecer el hack.
- **F7:** sidebar muestra TODOS los módulos a todos los roles (salvo Configuración).
  Cuando se implemente S3 (RBAC), filtrar links por permiso — mejora seguridad **y** UX.

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

## 6. ROADMAP PRIORIZADO (para la próxima sesión — IA o humano)

1. **Commitear el trabajo pendiente** (83 archivos + los cambios Docker de hoy).
   Sugerencia: un commit para el estado actual de la app, otro para la mecánica Docker.
2. **Seguridad crítica:** S1 y S2 (endpoints sin auth) — medio día.
3. **RBAC real:** S3 + S4 (`clinica_id` en permisos + enforcement en States y sidebar) — 1 día.
4. **S5** (numeración comprobantes) y **S6** (`asyncio.to_thread` en reportes/PDF) — horas.
5. **Alembic sync** (S7): revisión autogenerada del drift; borrar `_migrate_columns()`.
6. **Probar Docker local** (`docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build`
   → http://localhost:3004, login, cobrar, generar PDF/Excel) y luego **deploy AWS** con
   `scripts/deploy-prod.sh` (crear rama de deploy si se quiere calcar el flujo
   `docker-deploy-prod` de Ventas/Food; el script acepta `BRANCH=`).
7. Fixes menores: F1 (egresos dashboard), F2 (viewport), S9 (purga LoginIntento),
   S11 (truncado bcrypt), borrar `Dockerfile.worker`, `=1.13.0`, `start_redis.bat`.
8. Después: dividir páginas monolíticas (F3), CI con pytest, headers en NPM (S14).

## 7. Notas operativas para quien continúe

- Variables de entorno: ver `.env.example` (completo y comentado). En prod son
  obligatorias `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `SECRET_KEY` (≥32 chars) —
  `rxconfig.py` y `deploy-prod.sh` fallan si faltan.
- El contenedor sirve **todo en el puerto 3000** (`--single-port`); NPM hace TLS y proxy.
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
