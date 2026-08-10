# Plan de actualización de Reflex — Suite TUWAYKI

> Objetivo: actualizar Reflex de la suite (empezando por **LIFE / Clínica**) de forma
> segura, coordinada y verificable, dejando el sistema **completamente andando** en
> local, CI y producción (Docker + Granian), sin romper el paquete compartido
> **tuwayki-core** que usan FOOD y LIFE.
>
> Marcá cada casilla `- [x]` a medida que avances. No pasar de fase sin cerrar la anterior.

---

## ⏳ PENDIENTE — retomar en la próxima sesión

> **LIFE está 100% cerrado del lado técnico** (Reflex 0.9.8 en `main`, CI verde, deploy
> seguro, E2E OK, stack corriendo). Lo que sigue es acción del usuario o de otras
> sesiones. Al retomar, empezar por acá.

### A) LIFE — acción del usuario (no requiere código)
- [ ] **Smoke visual** en Chrome real (`http://localhost:3004`): login, y navegar
      cobro / calendario / dashboard / pacientes. *El pipeline ya está probado en el E2E
      §4.7; esto es confirmación visual.*
- [ ] Probar **exportaciones** (XLSX y PDF de recibo) y **notificaciones**
      (email smtplib / WhatsApp Twilio) en vivo — no se ejercitaron end-to-end.
- [ ] **Deploy a prod** en el servidor: `bash scripts/deploy-prod.sh`
      (ya purga `life_web` solo). Verificar `https://life.tuwayki.app`.
- [ ] Tras el deploy: health externo OK + smoke rápido en producción.

### B) Suite — otras sesiones (FOOD y SHOP a 0.9.8)
> Proceso por sistema: rama → editar pin(es) `reflex*` → regenerar locks en
> `python:3.13-slim` → `pytest`+`ruff` → **PR contra main** → merge → deploy.
- [ ] **FOOD** (`Sistema-para-Food`, hoy 0.9.6.post1) → 0.9.8.
- [ ] **SHOP** (`Sistema-de-Ventas`, hoy 0.9.4) → 0.9.8.
- [ ] **Replicar en los deploy de FOOD y SHOP el fix de purga del volumen `.web`**
      (usan el mismo patrón; sus scripts todavía NO lo hacen).
- [ ] Tras el bump de SHOP: reverificar integración panel Owner ↔ LIFE.

### C) Opcional / housekeeping (no bloquea nada)
- [ ] **Decisión parkeada**: alinear el commit de `tuwayki-core` (LIFE `ef852f2` vs
      FOOD `64850c8`). Independiente del upgrade de reflex.
- [ ] Tag / nota de versión por sistema (0.9.8).
- [ ] Sumar una línea del avance a `PLAN_MEJORAS.md`.
- [ ] (Cosmético, se dejó a propósito) Warning local `volume "…life_mysql_data"
      already exists` — artefacto del renombrado de proyecto Compose; NO tocar el
      compose (rompería el primer deploy en server). Solo se limpia recreando el
      volumen local, con pérdida de datos de test.

---

## 0. Estado actual (línea base — verificado el 2026-08-09)

| Sistema | Ruta | Repo (`D:\PROYECTOS\`) | Reflex | tuwayki-core | Usa core |
|---|---|---|---|---|---|
| **LIFE** (Clínica) | `/life` | `Sistema-Gestion-Clinica` | `0.9.4` | `@ef852f2` | ✅ |
| **FOOD** | `/food` | `Sistema-para-Food` | `0.9.6.post1` | `@64850c8` | ✅ |
| **SHOP** (Ventas / Owner) | `/shop` | `Sistema-de-Ventas` | `0.9.4` | — | ❌ |
| **tuwayki-core** | — | `tuwayki-core` | v1.0.0 (agnóstico a reflex) | — | — |

**Última estable de Reflex:** `0.9.8`.

### Hechos que condicionan el plan
- **tuwayki-core NO depende de reflex** (su `pyproject.toml` solo pinea sqlmodel,
  sqlalchemy, aiomysql, pymysql, cryptography, PyJWT, dotenv, openpyxl, reportlab,
  redis). ⇒ Bumpear reflex **no puede romper core**, y core ya convive con el
  0.9.6.post1 de FOOD. Riesgo de core respecto a reflex = **cero**.
- **FOOD ya está por delante** (0.9.6.post1): ya tiene los parches de seguridad de
  0.9.6 (#6665: starlette / python-multipart / granian / vite). LIFE y SHOP siguen
  expuestos en 0.9.4.
- **Drift de core**: FOOD (`64850c8`) y LIFE (`ef852f2`) apuntan a commits distintos
  del paquete compartido. Decisión aparte (ver Fase 1).
- 0.9.4 → 0.9.8 es salto **de parches dentro de la misma minor (0.9.x)**. El salto
  peligroso (0.8.0, Next.js→Remix) ya está pasado. **Sin breaking changes declarados**
  en 0.9.5–0.9.8; única deprecación: `ArrayVar.foreach` (método) → NO afecta a
  `rx.foreach` (función), que es lo que usamos.

---

## 1. Decisiones a tomar ANTES de tocar nada

- [x] **Versión objetivo de la suite.** **`0.9.8` para las tres apps** (Opción A).
  - ➡️ **Decisión tomada:** `0.9.8 para LIFE, FOOD y SHOP`  (fecha: `2026-08-09`)

- [x] **Alcance de esta ronda.** **Solo LIFE ahora.** FOOD y SHOP subirán a 0.9.8
      cada una en su propia sesión de trabajo.
  - ➡️ **Decisión:** `Solo LIFE en esta tanda; FOOD y SHOP por separado`

- [ ] **Drift de tuwayki-core.** ¿Alineamos LIFE al mismo commit que FOOD (`64850c8`),
      dejamos cada uno en el suyo, o re-pineamos ambos a un commit común nuevo?
  - Nota: como core es agnóstico a reflex, esto es **independiente** del bump de
    reflex. Para esta ronda LIFE **mantiene `ef852f2`** (no se toca core aquí).
  - ➡️ **Decisión:** `LIFE mantiene ef852f2 en esta ronda; alineación de commit se evalúa aparte`

---

## 2. Fase 0 — Preparación

- [x] Crear rama de trabajo en LIFE: `chore/upgrade-reflex-0.9.8` ✅
- [x] Árbol limpio (solo untracked: plan + assets `TUWAYKILIFE*.png`). ✅
- [x] Changelogs 0.9.5 → 0.9.8 revisados. ✅
- [x] Toolchain de locks verificado: Docker 29.6.2 + `python:3.13-slim` + `pip-tools`. ✅
- [ ] Anotar versión de `bun` / node que usa Reflex hoy (por si 0.9.7 `frozen_lockfile`
      cambia algo en el `.web`) — se verá al correr `reflex init`.

---

## 3. Fase 1 — tuwayki-core (paquete compartido)

> core no cambia por reflex, pero es la pieza que tocan FOOD y LIFE: hay que dejarlo
> **verificado y con un commit claro** antes de mover las apps.

- [x] core **no tiene suite propia** (sin carpeta `tests`) → nada que correr. ✅
- [x] `pyproject.toml` **no declara reflex** (agnóstico confirmado). ✅
- [ ] **Si se decide alinear el commit** (ver Fase 1 de decisiones):
  - [ ] Elegir/crear el commit objetivo de core (ej. `64850c8` o uno nuevo).
  - [ ] Actualizar el pin `tuwayki-core @ git+...@<commit>` en **LIFE** y **FOOD**.
  - [ ] Verificar que la API que consumen ambos (formateo de números/moneda,
        auth JWT, exportación, etc.) no cambió de firma.
- [ ] Registrar el commit de core que queda como referencia de la suite: `__________`

---

## 4. Fase 2 — LIFE (Clínica) — actualización principal

### 4.1 Editar pines
- [x] `requirements.txt` línea 9: `reflex==0.9.4` → `reflex==0.9.8`. ✅
- [x] Componentes `reflex-components-*` los resolvió `pip-compile`. ✅

### 4.2 Regenerar los lock files (DENTRO de `python:3.13-slim`)
```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W):/app" -w /app python:3.13-slim bash -c "
  apt-get update -qq && apt-get install -y -qq git &&
  pip install -q pip-tools &&
  pip-compile --strip-extras --output-file=requirements.lock requirements.txt &&
  pip-compile --strip-extras --output-file=requirements-dev.lock requirements.txt requirements-dev.txt"
```
- [x] `requirements.lock` regenerado. ✅
- [x] `requirements-dev.lock` regenerado. ✅
- [x] `git diff` revisado. Cambios: reflex/reflex-base/reflex-components-core
      `0.9.4→0.9.8`; **`wrapt 2.3.0→2.1.2`** (downgrade forzado por reflex 0.9.8, riesgo
      bajo). `tuwayki-core` intacto en `ef852f2`. Seguridad: starlette 1.5.0 /
      granian 2.8.1 / python-multipart 0.0.32 **ya estaban sobre los umbrales seguros**
      (el bump las fija como piso, no era un parche urgente). ✅

### 4.3 Instalar y recompilar
- [x] Instalado en `.venv` desde los locks → reflex **0.9.8** confirmado. ✅
- [x] Import de la app completo bajo 0.9.8 (todo el árbol `rx.*`/páginas/states
      construye; solo corta al conectar a MySQL `life_mysql`, que es de la red Docker). ✅
- [x] ✅ **Stack Docker local verificado end-to-end** (2026-08-09):
  - Imagen reconstruida con reflex 0.9.8; migraciones Alembic OK; frontend
    **recompilado limpio** (Compiling 100% / Production Build 100%).
  - Endpoints: `/api/ping` 200, `/_health` 200, frontend `/` 200, contenedor `healthy`.
  - **WebSocket `/_event`: `101 Switching Protocols`** + handshake socket.io válido.
  - UI renderiza (login, branding, título `TUWAYKILIFE | ...`), ruteo/auth-redirect OK.
  - ⚠️ **Aprendizaje**: el volumen `life_web` persiste el `.web` compilado entre
    rebuilds → tras subir de versión hay que **eliminar `sistema-para-clinicas_life_web`**
    o el backend rechaza el frontend viejo (`Frontend version 0.9.4 does not match`).
    Añadir este paso al deploy de prod (ver §6).

### 4.4 Tests automatizados
- [x] Suite completa: **100 passed** en 0.9.8. ✅
- [x] Test AST de RBAC incluido en la suite → verde. ✅
- [x] `ruff check .` → All checks passed. ✅
- [x] CI en verde tras el push (PR #4, `lint-and-test` success). ✅

### 4.5 Smoke test manual (priorizar páginas con estado pesado / `rx.foreach`)
> Estas concentran el riesgo real de un bump (render de listas, hidratación):
- [ ] **Login / auth** (incluye enforcement del Owner panel).
- [ ] **Cobro** (`pages/cobro.py`) — búsqueda de pacientes, carrito, recibo.
- [ ] **Calendario** (`pages/calendario.py`) — grillas de turnos por hora/día.
- [ ] **Dashboard** (`pages/dashboard.py`) — tarjetas + tabla de turnos recientes.
- [ ] **Pacientes** — alta/edición (validación de documento numérico, `is_saving`).
- [ ] **Caja / Cuentas / Compras / Inventario** — tablas con `foreach`.
- [ ] **Configuración** (usuarios, sedes, monedas, impuestos, métodos de pago).
- [ ] **Auditoría** — visor de bitácora.
- [ ] Exportaciones (openpyxl / reportlab) generan XLSX y PDF correctos.
- [ ] Notificaciones (email smtplib / WhatsApp Twilio) siguen operativas.

### 4.6 Integración cruzada LIFE ↔ SHOP (Owner panel)
> Es HTTP, independiente de la versión de reflex, pero hay que confirmarlo.
- [x] API `/api/admin/companies` con `X-Admin-Secret` → **200 con datos reales de MySQL**
      (`Clinica Default`, plan profesional, 4 usuarios). HTTP→auth→DB→JSON OK bajo 0.9.8. ✅
- [x] Sin secreto → **401** (enforcement correcto). ✅

### 4.7 E2E completo (2026-08-09) — sistema al 100%
| Capa | Qué se probó | Resultado |
|---|---|---|
| Lógica de negocio | `pytest` (auth, pacientes, cobro, caja, compras, cuentas, inventario, auditoría) contra DB real | **100 passed** ✅ |
| Rutas/SSR | 17 páginas (`/`, `/pacientes`, `/cobro`, `/calendario`, …) siguiendo redirects | **17/17 → 200** con títulos correctos ✅ |
| API pública | `/api/ping`, `/api/health`, `/health` | 200 ✅ |
| API protegida | `/api/reportes/descargar`, `/api/recibo/pdf`, `/api/admin/*`, `/api/registro` sin credenciales | rechaza 401/400 ✅ |
| Realtime | socket.io client → `/_event` | conecta + `sid` válido ✅ |
| WebSocket crudo | upgrade `/_event` | `101 Switching Protocols` ✅ |
| DB vía HTTP | Owner panel autenticado | 200 con datos MySQL ✅ |
| Contenedor | healthcheck | `healthy`, reflex 0.9.8 ✅ |

> Único punto no cubierto programáticamente: clicks/typing en la UI (el navegador
> embebido no tunela `ws://` a localhost). El pipeline subyacente quedó probado en
> todas las capas; el smoke visual con clicks lo hace el usuario en su Chrome real.

---

## 5. Fase 3 — FOOD y SHOP (alineación de la suite)

> Solo si en la Fase 1 se decidió alinear toda la suite a la misma versión.

### FOOD (`Sistema-para-Food`) — de 0.9.6.post1 → objetivo
- [ ] Rama propia + editar `requirements.txt` (reflex + reflex-components-*).
- [ ] Regenerar locks en `python:3.13-slim` (mismo procedimiento que LIFE).
- [ ] `reflex init` + arranque + suite de tests verde.
- [ ] Smoke test de sus flujos principales.

### SHOP (`Sistema-de-Ventas`) — de 0.9.4 → objetivo
- [ ] Rama propia + editar `requirements.txt` (línea 42).
- [ ] Regenerar locks / instalar / recompilar.
- [ ] Tests + smoke test.
- [ ] Verificar que el **panel Owner** sigue hablando con LIFE tras su propio bump.

---

## 6. Fase 4 — Docker y despliegue a producción

- [ ] Build de imagen de LIFE con los nuevos locks: `docker build ...` sin errores.
- [ ] **⚠️ Al subir de versión, purgar el volumen del frontend compilado** para que
      Reflex recompile con la nueva versión (si no, sirve el `.web` viejo y da
      `Frontend version X does not match`):
      `docker volume rm sistema-para-clinicas_life_web` (el de datos MySQL se conserva).
- [ ] Levantar stack (`docker compose`) y verificar que Granian sirve el frontend
      compilado (recordar: el puerto de la app **no** se publica en prod).
- [ ] Comprobar arranque sin el bug de sockets huérfanos (ver memoria Docker).
- [ ] Variables obligatorias en prod presentes (`MYSQL_PASSWORD`, `AUTH_SECRET_KEY`).
- [ ] Health check / smoke en el entorno desplegado.
- [ ] Repetir build/deploy para FOOD y SHOP si entraron en esta tanda.

---

## 7. Cierre

- [x] Merge de LIFE a `main` con CI verde (PR #4, squash, 2026-08-09). ✅
- [ ] Tag / nota de versión por sistema.
- [x] Memoria actualizada (`suite-reflex-0.9.8-upgrade`, `docker-life-web-volume-stale`). ✅
- [ ] Actualizar `PLAN_MEJORAS.md` si corresponde.

---

## 8. Plan de rollback

- Cada bump vive en su **rama**; `main` queda intacto hasta el merge.
- Los `requirements.lock` viejos están en git ⇒ revertir = `git checkout main -- requirements.lock requirements-dev.lock requirements.txt` + rebuild.
- Imagen Docker anterior conservada/etiquetada antes de redeploy para volver atrás rápido.
- Como core es agnóstico a reflex, un rollback de reflex **no** obliga a tocar core.

---

## 9. Registro de resultados (bitácora)

| Fecha | Sistema | Acción | Resultado | Notas |
|---|---|---|---|---|
| 2026-08-09 | LIFE | Rama `chore/upgrade-reflex-0.9.8` + pin `reflex==0.9.8` | OK | — |
| 2026-08-09 | LIFE | Regenerar locks en `python:3.13-slim` | OK | wrapt 2.3.0→2.1.2; core intacto |
| 2026-08-09 | LIFE | `pip install` locks en `.venv` | OK | reflex 0.9.8 |
| 2026-08-09 | LIFE | `pytest` (100) + `ruff` | 100 passed / clean | — |
| 2026-08-09 | LIFE | Smoke import app bajo 0.9.8 | OK | corta solo en MySQL (env Docker) |
| 2026-08-09 | LIFE | CI (PR #4) lint-and-test | ✅ pass (46s) | entorno limpio |
| 2026-08-09 | LIFE | Stack Docker local + rebuild frontend limpio | ✅ healthy | `/api/ping`,`/_health` 200; WS `/_event` 101; UI OK |
| 2026-08-09 | LIFE | Purga volumen `life_web` (frontend stale) | OK | necesario tras bump; datos MySQL intactos |
| 2026-08-09 | LIFE | **E2E completo** (7 capas: pytest+rutas+API+WS+socket.io+DB) | ✅ 100% verde | ver §4.7 |
| | LIFE | Docker build + deploy prod (servidor) | ⏳ pendiente | recordar purgar `life_web` |
