# PLAN DE MEJORAS — WaykiSAC Clínica

> Hoja de ruta para llevar el sistema a nivel **profesional y completo**.
> Creado: 2026-08-02 · Última sincronización: 2026-08-13 · Complementa a
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
- [x] **Sesiones con expiración** *(2026-08-08)*: TTL configurable `SESSION_TTL_HOURS`
      (default 12 h, `config.SESSION_TTL_SECONDS`). `BaseState` guarda `login_at` al login
      y `_expirar_si_vencio()` invalida la sesión (reset → `is_authenticated=False`) al
      inicio de cada `on_mount`, así el guard redirige a `/login`. Defensa extra: vencida
      la sesión, `tiene_permiso` niega todo (bloquea handlers disparados sobre un websocket
      que quedó abierto). Lógica pura en `services/sesion.py` con tests (`test_sesion.py`).
- [x] **Auditoría de acciones (audit log)** *(2026-08-08)*: tabla `audit_log` append-only
      (`clinica_id, usuario_id, sede_id, accion, entidad, entidad_id, detalle, creado_en`),
      migración `e5h3i4j5k6l7`. Escrita **dentro de la misma transacción** que la acción
      (atómica) vía `services/auditoria.registrar`. Cubiertas: cobro (crear comprobante),
      cierre de caja, borrado de movimiento de caja, anulación de compra y cambio de
      permisos de rol. Tests en `test_auditoria.py` (incluye que una acción fallida no deja
      rastro). **Visor UI** en `/auditoria` (módulo RBAC `auditoria`, solo-admin; página +
      state + `auditoria.listar` con filtros por acción/entidad y paginación). *Pendiente
      ampliar a borrados de paciente/nota clínica.*

## P1 — Robustez y calidad

- [x] **Cobertura de tests de servicios** *(2026-08-08)*: 83 tests. Cubiertos caja
      (movimientos/resumen/cierre + duplicado), inventario (stock, egreso insuficiente,
      bajo mínimo), compras (recepción→stock, anulación repone stock, validaciones),
      promociones (rango %, vigencia por fechas, toggle), permisos (auto-seed por rol,
      backfill de módulos faltantes, idempotencia, `seedear_todos`) y reportes
      (`kpis_mes`: ingresos/egresos/turnos/pacientes) — además de auth, cobro, cuentas,
      pacientes, turnos.
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
- [x] **Pin de dependencias** *(2026-08-08)*: lockfiles con pines exactos generados con
      `pip-compile` **dentro de `python:3.13-slim`** (misma imagen que prod, para que
      resuelvan igual): `requirements.lock` (prod) y `requirements-dev.lock` (CI, prod+dev).
      El Dockerfile instala `requirements.lock`; el CI instala `requirements-dev.lock`.
      `requirements*.txt` quedan como fuente editable (con el comando de regeneración).
      Verificado: el set pineado instala y corre los 83 tests en la imagen de prod.

## P2 — Funcionalidad para "sistema completo" de clínica

- [ ] **Historia clínica más rica**: adjuntos (estudios, imágenes), plantillas de nota por
      especialidad, firma/bloqueo de nota (una nota firmada no se edita — trazabilidad legal).
      *→ Detallado y priorizado en el bloque **P2-ESP** (Fase A: A2 adjuntos, A3 plantillas +
      firma). Este ítem se cierra al completar esa fase.*
- [ ] **Agenda profesional real**: disponibilidad/horarios por profesional y sede,
      bloqueos (vacaciones), detección de solapamientos al crear turno.
- [ ] **Recordatorios de turnos activos**: `tasks/recordatorios.py` existe — conectarlo a
      un scheduler real (cron/APScheduler) con envío WhatsApp/email y estado de envío.
- [ ] **Facturación electrónica (Perú/SUNAT)**: hoy los comprobantes son internos. Integrar
      facturación electrónica (OSE/PSE) o al menos exportación contable formal.
- [ ] **Portal de resultados / recordatorio al paciente** (opcional, diferenciador).
- [ ] **Reportes ampliados**: producción por profesional, ocupación de agenda, análisis
      de no-shows, margen por servicio (los datos ya existen en los modelos).

## P2-ESP — Multi-especialidad (Estética + Odontología)

> **Contexto (diagnóstico 2026-08-13).** Hoy el sistema es una plataforma de
> gestión **genérica** sólida (agenda, pacientes, cobro, caja, inventario,
> cuentas, compras, reportes, multi-tenant/multi-sede) y en esa capa **ya sirve
> para estética y odontología**. Lo que le falta para posicionarse como software
> *especializado* (no solo administrativo) es la **capa clínica-asistencial**:
> la historia clínica es texto libre (`NotaClinica` con `tipo` + `contenido`),
> `Paciente` no guarda antecedentes/alergias, no hay adjuntos ni consentimientos,
> y no existe odontograma. Este bloque cierra esa brecha, priorizado por
> **valor para ambos rubros primero** y luego los diferenciadores de cada uno.
>
> Regla de oro del orden: **primero lo transversal (Fase A)**, que sube el nivel
> clínico de las dos especialidades a la vez; recién después los módulos propios
> de cada rubro (Fases B y C), que se apoyan en la infraestructura de la A
> (sobre todo en adjuntos y en el motor de PDF).

### Fase A — Base clínica transversal (sirve a estética Y odontología)

- [x] **A1 · Ficha médica del paciente (antecedentes / alergias / medicación).**
      *(2026-08-13)* `Paciente` ampliado con `grupo_sanguineo` (varchar 8),
      `alergias`, `antecedentes`, `medicacion` y `habitos` (Text) — todo nullable.
      Migración aditiva e idempotente `f6a1c2d3e4b5` (aplicada en vivo sobre
      `life_db`). Formulario de paciente con sección "Ficha médica"; **alerta
      roja de alergias** en el panel de detalle del paciente y como banner
      destacado en la Historia Clínica (`NotasClinicasState.paciente_alergias`).
      +3 tests (`test_pacientes.py`, 105 total). Verificado end-to-end en el
      navegador (crear → listar → detalle → historia).
- [x] **A2 · Adjuntos / archivos clínicos** (fotos, radiografías, estudios, PDF).
      *(2026-08-13)* Tabla `adjuntos` (migración `a7b8c9d0e1f2`) con metadatos;
      binario en disco vía `services/storage.py` (abstracción **S3-swappable**,
      aislamiento por clínica `uploads/clinica_<id>/`, guard anti path-traversal).
      Decisión de almacenamiento: **volumen local** `life_uploads:/app/uploads`
      por ahora (S3/Backblaze queda para cuando se lance prod, sin tocar el resto).
      Subida con `rx.upload` + validación de extensión/tamaño (máx 10 MB); sección
      "Archivos del paciente" en Historia Clínica (subir/listar/descargar/borrar).
      Descarga por endpoint `/api/adjunto` protegido con token efímero + chequeo
      de clínica (mismo patrón que el recibo PDF). Borrado = soft-delete + baja
      del archivo físico + **audit log**. +10 tests (115 total). Verificado E2E
      en el navegador (subir PNG → disco+BD → descargar 200 → borrar → auditoría).
      *Habilitador de la galería estética (C1) y el RX odontológico (B1).*
- [x] **A3 · Historia clínica estructurada + firma/bloqueo de nota.**
      *(2026-08-13)* **Firma/bloqueo** (migración `b8c9d0e1f2a3`): `NotaClinica`
      gana `firmada`/`firmada_en`/`firmada_por_id`; una nota firmada queda
      inmutable — `actualizar` y `eliminar` lanzan `ConflictError`, la firma es
      idempotente (no se re-firma) y queda en **audit log**. UI: botón "Firmar"
      + badge/pie con firmante y fecha; editar/borrar se ocultan al firmar.
      **Plantillas por especialidad** (`services/plantillas_nota.py`, sin BD):
      anamnesis, evolución, odontología, estética — selector en el modal que
      inserta el esqueleto (textarea pasa a controlado). +9 tests (124 total).
      Verificado E2E en el navegador. Cierra el ítem "Historia clínica más rica".
- [x] **A4 · Consentimiento informado — HECHO (2026-08-14).** PDF A4 generado con
      ReportLab (`services/pdf_consentimiento.py`, devuelve **bytes** para archivar),
      plantillas por especialidad (`services/plantillas_consentimiento.py`: general,
      estética, odontología, quirúrgico menor — marcador `{procedimiento}`).
      Orquestación en `services/consentimientos.py`: genera → guarda en disco (storage
      A2) → registra como `Adjunto` categoría "consentimiento" → auditoría
      (`accion=generar`). Sin migración (reusa tabla `adjuntos`). Modal en Historia
      Clínica con datos del paciente, procedimiento, profesional y observaciones; el
      PDF queda descargable/imprimible en la lista de adjuntos. +7 tests (131 total).
      Verificado E2E: consentimiento estético para paciente → PDF `%PDF-1.4` en disco,
      fila en `adjuntos` y `audit_log`.
- [x] **A5 · Recetas / indicaciones imprimibles — HECHO (2026-08-14).** PDF A5
      (ReportLab, `services/pdf_receta.py`, devuelve **bytes**) en dos modos:
      "receta" (encabezado `Rp/`, cada renglón numerado) e "indicación" (texto
      corrido). Orquestación en `services/recetas.py`: genera → guarda en disco →
      `Adjunto` categoría **"receta"** (agregada a `_CATEGORIAS`) → auditoría
      (`accion=generar`). Sin migración. Modal "Receta / Indicación" en Historia
      Clínica (tipo, diagnóstico, cuerpo, profesional); PDF descargable/imprimible
      en la lista de adjuntos. +7 tests (138 total). Verificado E2E: receta con 3
      renglones para paciente → PDF `%PDF-1.4` en disco, fila `adjuntos` y
      `audit_log`. **Con A5 se cierra toda la Fase A.**

> ✅ **Fase A COMPLETA (2026-08-14):** ficha médica (A1), adjuntos (A2), historia
> estructurada + firma (A3), consentimiento (A4) y recetas/indicaciones (A5). El
> producto pasó de "gestión administrativa" a "gestión clínica" con base común a
> estética y odontología. Siguiente: Fase B (diferenciador odontológico).

### Fase B — Diferenciador ODONTOLÓGICO

- [ ] **B1 · Odontograma.** Modelo de piezas dentales (numeración FDI/universal),
      caras y estados por pieza (sano, caries, obturado, ausente, corona,
      implante, etc.), versionado por fecha para ver evolución. UI de odontograma
      interactivo. *Es EL diferenciador dental: sin esto un odontólogo no lo
      adopta como "su" software.*
- [ ] **B2 · Plan de tratamiento por fases + presupuesto odontológico.**
      Tratamientos propuestos sobre piezas del odontograma, agrupados en fases,
      con presupuesto (aprovecha `Servicio.precio` e historial de precios) y
      seguimiento de avance (propuesto → aprobado → en curso → terminado).
      Enlaza cada fase realizada con su cobro (Caja) y sus insumos
      (`servicio_insumos`, que ya existe).

### Fase C — Diferenciador ESTÉTICO

- [ ] **C1 · Galería antes/después por sesión.** Sobre A2: agrupar fotos por
      sesión/tratamiento y fecha, con vista comparativa antes/después y línea de
      tiempo de evolución del paciente.
- [ ] **C2 · Ficha de tratamiento estético.** Zonas tratadas, productos/insumos
      aplicados por sesión (ya modelable con `servicio_insumos`), parámetros del
      equipo (p. ej. energía/disparos) y plan de sesiones (nº de sesión, próxima
      recomendada) enganchado a la agenda.

### Fase D — Configuración por tipo de clínica

- [ ] **D1 · Perfil de especialidad de la clínica.** Usar `Clinica.rubro` +
      `clinica_modulos` (ambos ya existen) para que al marcar una clínica como
      "odontológica" o "estética" se activen/desactiven módulos y se muestren las
      plantillas de nota (A3), catálogos de servicios y campos propios del rubro.
      Semilla de catálogos precargados por especialidad para acelerar el alta.

> **Recomendación de secuencia:** A1 → A2 → A3 → (A4, A5) → B1 → B2 → C1 → C2 → D1.
> Con la **Fase A** el producto ya da un salto de "gestión administrativa" a
> "historia clínica profesional" para ambos rubros; **B** lo vuelve vendible como
> software odontológico y **C** como software estético; **D** lo empaqueta como
> plataforma multi-especialidad configurable.

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
| 2026-08-08 | P1: +9 tests (permisos + reportes) → 83 total; cobertura de servicios cerrada | `test(services): cobertura de permisos y reportes` |
| 2026-08-08 | P1: lockfiles con pines exactos (`requirements.lock` + `requirements-dev.lock`) generados en `python:3.13-slim`; Dockerfile/CI actualizados | `build(deps): pin exacto de dependencias vía lockfiles` |
| 2026-08-08 | P0: sesiones con TTL (`SESSION_TTL_HOURS`, default 12 h) + enforcement en on_mount y `tiene_permiso` + tests | `feat(security): expiración de sesión (TTL) con re-login forzado` |
| 2026-08-08 | P0: audit log append-only (`audit_log` + migración `e5h3i4j5k6l7`) atómico en cobro/cierre/borrado-caja/anulación/permisos + tests | `feat(security): audit log de acciones sensibles` |
| 2026-08-08 | Visor UI del audit log (`/auditoria`, módulo RBAC solo-admin, filtros + paginación) + tests de `listar` | `feat(auditoria): visor UI de la bitácora` |
