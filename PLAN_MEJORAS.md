# PLAN DE MEJORAS — WaykiSAC Clínica

> Hoja de ruta para llevar el sistema a nivel **profesional y completo**.
> Creado: 2026-08-02 · Complementa a `AUDITORIA_WAYKISAC_CLINICA.md` (estado histórico).
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

- [ ] **Deploy AWS + NPM**: primer deploy con `scripts/deploy-prod.sh`; aplicar los headers
      de seguridad documentados en la auditoría (S14) en Nginx Proxy Manager.
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

- [ ] **Cobertura de tests de servicios**: hoy hay 35 tests (auth, cobro, cuentas,
      pacientes, turnos). Faltan: caja (cierres), inventario (stock/movimientos), compras
      (anulación repone stock), promociones (vigencia/descuentos), permisos (seed +
      enforcement), reportes. Meta: cada servicio con tests de su flujo feliz + 2-3 bordes.
- [ ] **Test de RBAC de escritura**: test paramétrico que verifique que cada handler
      mutador de `state/` contiene su guard (el escaneo AST de esta sesión puede convertirse
      en `tests/test_rbac_guards.py` para que el CI lo vigile para siempre).
- [ ] **Linter + formateador en CI**: agregar `ruff check` y `ruff format --check` al
      workflow (rápido, un solo tool). Congelar el estilo del código.
- [ ] **Deps de test declaradas**: crear `requirements-dev.txt` (pytest, pytest-asyncio,
      aiosqlite, ruff) — hoy el venv local y el CI las instalan "a mano".
- [ ] **Warning de teardown en tests**: `RuntimeError: Event loop is closed` de `aiomysql`
      al final de la suite — los tests importan `clinica_app.models` que arrastra la
      creación del engine MySQL. Aislar la creación del engine (lazy) para que los tests
      nunca toquen MySQL.
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
