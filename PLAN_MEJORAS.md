# PLAN DE MEJORAS — WaykiSAC Clínica

> Hoja de ruta para llevar el sistema a nivel **profesional y completo**.
> Creado: 2026-08-02 · Última sincronización: 2026-08-07 · Complementa a
> `AUDITORIA_WAYKISAC_CLINICA.md` (estado histórico).
> Convención: marcar `[x]` al completar cada ítem y anotar el commit.

---

## Estado actual (auditoría 2026-08-02)

**Lo que está sano:**
- 16 módulos registrados y navegables; sidebar, rutas y matriz de permisos (`services/permisos.py`) alineados 1:1.
- Los 15 states de página tienen guard `on_mount` (auth + permiso de lectura por módulo).
- 35 tests pasan (`pytest-asyncio` + `aiosqlite`).
- Alembic con un solo head (`a1b2c3d4e5f6`); entrypoint corre `alembic upgrade head`.
- Docker local sano: `tuwayki_life` + `life_mysql` (proyecto `sistema-para-clinicas`) responde `/api/health` OK en `localhost:3004`. Subdominio de prod: `life.tuwayki.app`.
- Multi-tenant consistente: `clinica_id` solo vive en servidor.

**Corregido en esta sesión (2026-08-02):**
- [x] **CI roto en GitHub desde su creación** — todos los commits aparecían con ❌.
      Causa 1: pytest en Actions no encontraba el paquete (`ModuleNotFoundError: clinica_app`) → `pythonpath = .` en `pytest.ini`.
      Causa 2 latente: `aiosqlite` no se instalaba en CI → agregado al workflow.
      Extra: el paso de sintaxis ahora compila todo el paquete (`compileall`), no un solo archivo.
- [x] **44 event handlers que escriben en BD sin validar permiso de escritura** (S3 estaba
      incompleto: solo los handlers "críticos" tenían guard). En Reflex cualquier usuario
      autenticado puede disparar un handler desde el cliente, así que un rol con solo-lectura
      podía eliminar movimientos de caja, cerrar caja, borrar pacientes/notas clínicas,
      cambiar permisos de roles, etc. Ahora **todo** handler mutador valida
      `tiene_permiso(módulo, write=True)`.

---

## P0 — Antes de producción real

- [ ] **Deploy AWS + NPM**: primer deploy en `life.tuwayki.app`. Guía completa lista en
      [DEPLOY_TUWAYKILIFE.md](DEPLOY_TUWAYKILIFE.md) + workflow de CD
      `.github/workflows/deploy-prod.yml` (dispara en push a `docker-deploy-prod`).
      Pendiente: crear DNS `life`, cargar secrets en GitHub, primer deploy manual,
      configurar Proxy Host y aplicar headers de seguridad (S14). *No ejecutar hasta
      terminar de probar todo en local.*
- [ ] **Backups automáticos de MySQL**: `mysqldump` diario (cron en el host o contenedor
      sidecar) + retención 30 días + copia fuera del servidor (S3/Backblaze). *Un sistema
      clínico sin backups no es profesional: es una pérdida de datos esperando fecha.*
- [ ] **Restaurar backup probado**: un backup no probado no existe. Documentar el runbook
      de restauración y ejecutarlo una vez en local.
- [ ] **Sesiones con expiración**: hoy el login vive mientras viva el websocket/estado.
      Agregar TTL de sesión (p. ej. 8-12 h) y re-login forzado.
- [ ] **Auditoría de acciones (audit log)**: tabla `audit_log(user_id, clinica_id, accion,
      entidad, entidad_id, timestamp, detalle)` escrita desde los servicios para operaciones
      sensibles (cobros, anulaciones, cierres de caja, cambios de permisos, borrados).
      En salud esto es requisito, no lujo.

## P1 — Robustez y calidad

- [~] **Cobertura de tests de servicios** *(en progreso, 2026-08-07)*: 74 tests. Cubiertos
      caja (movimientos/resumen/cierre + duplicado), inventario (stock, egreso insuficiente,
      bajo mínimo), compras (recepción→stock, anulación repone stock, validaciones) y
      promociones (rango %, vigencia por fechas, toggle) — además de auth, cobro, cuentas,
      pacientes, turnos. **Faltan:** permisos (seed + enforcement) y reportes.
- [x] **Test de RBAC de escritura**: `tests/test_rbac_guards.py` existe — escaneo AST que
      verifica que cada handler mutador de `state/` contiene su guard; el CI lo vigila.
- [x] **Linter en CI (modo suave)**: `ruff check .` en el workflow con `ruff.toml` que
      selecciona solo `F` + `E9` (errores reales, no estilo). `ruff format` queda pendiente
      para una pasada futura de endurecimiento. *(2026-08-07)*
- [x] **Deps de test declaradas**: `requirements-dev.txt` (pytest, pytest-asyncio,
      aiosqlite, ruff); el CI instala `requirements.txt -r requirements-dev.txt`. *(2026-08-07)*
- [x] **Warning de teardown en tests** *(2026-08-07)*: el `RuntimeError: Event loop is
      closed` de `aiomysql` ya no se reproduce — el engine async se crea al importar pero
      nunca conecta (la suite corre sobre aiosqlite), así que aiomysql no deja tareas
      colgadas. Se limpiaron además los 4 `DeprecationWarning: datetime.utcnow()` de
      `test_auth.py` (→ `datetime.now(timezone.utc).replace(tzinfo=None)`, espejo de
      `planes._now_naive`). Suite: **41 passed, 0 warnings**.
- [ ] **Pin de dependencias**: `requirements.txt` usa `>=` en casi todo — un `pip install`
      futuro puede romper prod. Generar lockfile (`pip-compile` o pins exactos).

## P2 — Funcionalidad para "sistema completo" de clínica

- [ ] **Historia clínica más rica**: adjuntos (estudios, imágenes), plantillas de nota por
      especialidad, firma/bloqueo de nota (una nota firmada no se edita — trazabilidad legal).
- [ ] **Agenda profesional real**: disponibilidad/horarios por profesional y sede,
      bloqueos (vacaciones), detección de solapamientos al crear turno.
- [ ] **Recordatorios de turnos activos**: `tasks/recordatorios.py` existe — conectarlo a
      un scheduler real (cron/APScheduler) con envío WhatsApp/email y estado de envío.
- [ ] **Facturación electrónica (Perú/SUNAT)**: hoy los comprobantes son internos. Integrar
      facturación electrónica (OSE/PSE) o al menos exportación contable formal.
- [ ] **Portal de resultados / recordatorio al paciente** (opcional, diferenciador).
- [ ] **Reportes ampliados**: producción por profesional, ocupación de agenda, análisis
      de no-shows, margen por servicio (los datos ya existen en los modelos).

## P3 — Experiencia y operación

- [ ] **Paginación/virtualización en listados grandes** (pacientes, movimientos de caja)
      — verificar que todos los listados paginan en servidor, no en memoria.
- [ ] **Estados vacíos y mensajes de error consistentes** en los 16 módulos (revisar que
      los `except ServiceError: pass` silenciosos muestren feedback al usuario — hoy varios
      tragan el error sin avisar).
- [ ] **Modo oscuro** (Reflex + Tailwind lo hacen barato).
- [ ] **Observabilidad**: logging estructurado en servicios (hoy casi no hay logs),
      Sentry o similar para errores en prod, y un dashboard de salud (uptime + espacio
      en disco + backups OK).
- [ ] **Staging**: la rama `docker-deploy-prod` ya corre CI — darle un entorno propio
      de staging antes de tocar prod.

## Deuda técnica conocida (no urgente)

- `SQLModel.metadata.create_all` en el arranque convive con Alembic — aceptado como
  fallback dev, pero en prod debería estar detrás de `if ENV != "prod"`.
- es-toolkit shims en el entrypoint Docker: workaround de Reflex 0.9.x — revisar al
  actualizar Reflex.
- El repo remoto se renombró a `TreborOscorima/Gestion-de-Clinica`; actualizar `origin`
  local cuando se pueda (la URL vieja redirige por ahora).

---

## Registro de avances

| Fecha | Ítem | Commit |
|-------|------|--------|
| 2026-08-02 | Fix CI (pythonpath + aiosqlite + compileall) | `fix(ci): pytest no encontraba el paquete clinica_app` |
| 2026-08-02 | 44 write-guards RBAC + test permanente `test_rbac_guards.py` | `fix(security): write-guards RBAC en todos los handlers mutadores` |
| 2026-08-02 | Rename Docker → `tuwayki_life` / proyecto `sistema-para-clinicas` (TUWAYKILIFE), volumen MySQL migrado sin pérdida | `chore(docker): rename a tuwayki_life (TUWAYKILIFE)` |
| 2026-08-02 | Simetría total prefijo `life_` (`life_mysql`, `life_*` volúmenes/red) + subdominio `life.tuwayki.app` | `chore(docker): life_mysql + subdominio life.tuwayki.app` |
| 2026-08-02 | Schema `clinica_estetica` → `life_db` (multi-especialidad) | `chore(db): renombrar schema a life_db` |
| 2026-08-02 | Integración panel Owner: campos de licencia en Clinica, API `/api/admin/*` (secreto compartido), bloqueo de login por suspensión/vencimiento, planes trial/standard/profesional | `feat(owner): integración con el panel Owner (TUWAYKILIFE)` |
| 2026-08-02 | Multi-empresa: `/api/registro` público (clinica + admin + sede principal + trial) reusando `tuwayki-core` (validators, sanitization, rate-limit); tarjeta TUWAYKILIFE activa en la landing | `feat(registro): alta pública multi-empresa con tuwayki-core` |
| 2026-08-02 | Página `/life` en la landing + formulario de registro (pestaña TUWAYKILIFE en `/registro`, `life_api_client`) | `feat(landing): página /life con registro` |
| 2026-08-02 | Guía de deploy + workflow CD `deploy-prod.yml` (dormido hasta push a `docker-deploy-prod`) | `docs(deploy): guía TUWAYKILIFE + workflow CD` |
| 2026-08-03 | Simetría de nombres con SHOP/FOOD: `SECRET_KEY` → `AUTH_SECRET_KEY` | `refactor: renombrar SECRET_KEY a AUTH_SECRET_KEY` |
| 2026-08-05 | Owner API: listar usuarios de una clínica y resetear su contraseña desde el panel | `feat(owner-api): endpoints listar usuarios y resetear contraseña` |
| 2026-08-05 | Owner API (Fase 2): endpoint de renovación de suscripción | `feat(owner-api): endpoint de renovación de suscripción` |
| 2026-08-05 | Owner (Fase 3): módulos y límites por clínica (enforcement desde el panel) | `feat(owner): módulos y límites por clínica` |
| 2026-08-05 | Owner API (Fase 5): reportar conteos reales de usuarios/sedes al panel | `feat(owner-api): reportar conteos reales de usuarios/sedes` |
| 2026-08-07 | Limpieza de código muerto detectado por ruff (imports/variables sin usar) | `chore(cleanup): eliminar código muerto detectado por ruff` |
| 2026-08-07 | P1: `ruff.toml` suave + `ruff check` en CI + `requirements-dev.txt` | `ci(quality): ruff suave + requirements-dev` |
| 2026-08-07 | P1: limpiar `DeprecationWarning` de `datetime.utcnow()` en la suite | `test(auth): eliminar DeprecationWarning de datetime.utcnow()` |
| 2026-08-07 | P1: +33 tests de servicios (caja, inventario, compras, promociones) → 74 total | `test(services): cobertura de caja, inventario, compras y promociones` |
