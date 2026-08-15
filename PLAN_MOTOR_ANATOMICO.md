# PLAN — Motor Anatómico 2D/3D (Odontología + Estética)

> Plan de diseño e implementación para incorporar un **Motor Anatómico interactivo
> (2D/3D)** a TUWAYKILIFE, reutilizando la arquitectura existente.
> Creado: 2026-08-14 · Complementa a `PLAN_MEJORAS.md` (bloque P2-ESP, ya cerrado)
> y a `AUDITORIA_WAYKISAC_CLINICA.md`.
>
> **Regla rectora (del pedido):** *extender el sistema existente, no reemplazarlo.*
> Nada de segundo frontend, segundo backend, otra BD, otra auth, ni pacientes
> duplicados. El render 3D es una **vista alterna** sobre los servicios y datos
> que ya existen.

---

## 0. Conclusión de la auditoría (lo que cambia el encuadre)

El pedido original asume que hay que construir odontograma, estética, historia
clínica, productos, fotos, antes/después, planes y permisos. **Todo eso ya está
construido y probado** (bloque **P2-ESP** en `PLAN_MEJORAS.md`, ~263 tests,
verificado E2E contra `life_db`). La **capa de datos clínica ya existe**.

Lo único que el pedido introduce y **hoy no existe** son tres cosas, todas de la
capa espacial/visual:

1. **Render 3D** — odontograma 3D, rostro 3D, cuerpo 3D. Cero código hoy (el
   odontograma 2D son botones HTML coloreados).
2. **Abstracción genérica "Motor Anatómico"** (modelo→región→punto) reutilizable.
3. **Mapa anatómico estético espacial**: zonas faciales/corporales seleccionables
   y **puntos de aplicación** (toxina/relleno con producto+lote+cantidad+coordenada)
   y **evaluación por zona**. Hoy la estética es solo *sesión + fotos + ficha de texto*.

Por lo tanto este plan NO reconstruye nada: **agrega una capa de visualización 3D
sobre datos existentes (odontología)** y **completa el modelo espacial que le falta
a estética**.

---

## 1. Estado real del sistema (qué existe y se reutiliza)

### 1.1 Arquitectura en capas (consistente en los 16 módulos)

```
pages/*.py     UI pura: funciones → rx.Component (rx.el.* + Tailwind). Sin lógica.
state/*.py     rx.State; TODO hereda de BaseState (auth + tenant clinica_id + RBAC).
services/*.py  funciones async puras (reciben `session`): negocio + auditoría atómica.
models/*.py    SQLModel; TODO hereda de TenantSQLModel (clinica_id + soft-delete + ts).
database.py    engine async (aiomysql, expire_on_commit=False) + sync (Alembic/CLI).
alembic/       migraciones aditivas idempotentes, un solo head.
clinica_app.py rx.App + api_transformer: rutas /api/* (Starlette) para PDF/adjuntos/admin.
```

Stack: **Reflex 0.9.8** (Python→React, estado por websocket) · MySQL 8 / SQLModel /
SQLAlchemy 2.0 async · Alembic · JWT+bcrypt · ReportLab/OpenPyXL · Docker.
`clinica_id` **nunca** sale al cliente (vive solo en el servidor).

### 1.2 Módulos ya construidos (no tocar; construir encima)

- **Clínico:** pacientes (con ficha médica: alergias/antecedentes/medicación),
  historia clínica (`NotaClinica` con firma/bloqueo + plantillas por especialidad),
  adjuntos (`Adjunto` + `services/storage` S3-swappable), consentimientos y recetas (PDF).
- **Odontología:** `PiezaDental` (FDI, estado, `caras` JSON, nota), `OdontogramaVersion`
  (snapshots), `services/odontograma` (arcada completa + estados con color + versionado +
  comparación + export PDF). **UI 2D en `/odontograma`.**
- **Estética:** `SesionEstetica` + `SesionInsumo` + galería antes/después (momento),
  ficha del tratamiento, decremento de stock. **UI en `/galeria-estetica`.**
- **Planes:** `PlanTratamiento` + `PlanTratamientoItem` (fases, presupuesto, cobro→Caja).
- **Transversal:** agenda profesional (disponibilidad + bloqueos + solapamientos),
  caja, cobro, cuentas, inventario/lotes, compras, promociones, reportes, auditoría.
- **Plataforma:** multi-tenant + multi-sede, RBAC, perfil de especialidad (D1), Owner Panel.

### 1.3 Design system a heredar (para que el 3D se vea "del producto")

`components/ui.py` + `layout.py`: `shell()` (sidebar + header), `page_header()`,
`primary_btn`/`secondary_btn`, `table_header`, `empty_state`. Lenguaje visual:
primario **sky-600**, bordes **gray-200/300**, `rounded-lg`, sombras sutiles, tipografía
**Inter**, fondo `#f9fafb`, iconos **lucide** (`rx.icon`). El visor 3D debe usar
exactamente estos tokens (barra de herramientas, panel lateral, chips, leyenda).

### 1.4 RBAC y navegación (dónde enchufa)

- El módulo RBAC que cubre lo clínico es **`"historia"`** (odontograma ya usa
  `tiene_permiso("historia", write=True)`). **El 3D reutiliza este permiso** — no se
  crea un módulo RBAC nuevo.
- La **visibilidad por especialidad** ya la resuelve `BaseState.esp_dental` /
  `esp_estetica` (derivadas de `Clinica.rubro` vía `services/especialidad`).
- El **hub** es `/historia-clinica` (`notas_clinicas.py`): ya lanza `/odontograma`,
  `/plan-tratamiento` (si `esp_dental`) y `/galeria-estetica` (si `esp_estetica`) con
  `?paciente_id=`. El mapa estético se sumará ahí con el mismo patrón.

### 1.5 Precedente de integración JavaScript (clave para el 3D)

**Nunca** se envolvió un componente React custom (`grep library=` → 0). La única
integración JS del repo es **JS crudo servido como asset estático**:
`rx.el.script(src="/js/twk-pwa.js")` + `rx.call_script(js)` (atajos de teclado).
`assets/js/` ya existe y se sirve en la raíz del sitio. **Este es el carril de bajo
riesgo para Three.js.**

---

## 2. Decisiones técnicas (tomadas)

### 2.1 Motor de render 3D → **Three.js vanilla, vendorizado**

Elegido: **Three.js como módulo ES vendorizado en `assets/js/anatomy/vendor/`,
sin CDN en runtime y sin npm.** GLTFLoader + Raycaster cubren cargar GLB, rotar,
zoom, pan, hover, highlight, selección y cámaras predefinidas.

| Alternativa | Veredicto para *este* repo |
|---|---|
| **React Three Fiber** | ❌ exige React + dependencias npm en el build de Reflex → choca con "no segundo frontend/mínimas deps" y con la fragilidad ya vista (shims es-toolkit). |
| **`<model-viewer>`** | ❌ trivial para *ver* un GLB pero débil en **picking por mesh** (seleccionar diente/cara/punto), que es el 90% del valor clínico. |
| **Babylon.js** | ➖ potente y con picking, pero más pesado y con menor ecosistema anatómico. Viable, no óptimo. |
| **Three.js vanilla vendorizado** | ✅ cubre todo, **encaja en el patrón `twk-pwa.js` ya usado**, cero deps nuevas, reproducible y offline (Docker/CSP-friendly). |

**Por qué vendorizar y no CDN:** el deploy es Docker cerrado detrás de Nginx; una
dependencia de red en runtime rompería la reproducibilidad y el modo offline. Se
pinea una versión de `three` (p. ej. r160+) copiando `three.module.js` +
`GLTFLoader.js` + `OrbitControls.js` al repo. Actualizar = cambiar el archivo, no un
`package.json`.

### 2.2 Puente JS ↔ Reflex (el punto técnico delicado) → **elemento-puente oculto**

- **Python → JS** (empujar datos/estado al visor): `rx.call_script(...)` en `on_mount`
  y tras cada cambio de estado. Bien soportado.
- **JS → Python** (devolver la selección de un pick del canvas): se renderiza un
  **input oculto controlado** `rx.el.input(id="anatomy-bridge", on_change=State.on_pick)`;
  el JS del visor, al hacer raycast, escribe
  `bridge.value = JSON.stringify({anatomy_id, cara})` y dispara
  `bridge.dispatchEvent(new Event('input', {bubbles:true}))`. Reflex captura el
  `on_change` y ejecuta el handler con la selección — **sin envolver React**.

Este puente se **prototipa y valida aislado en la Etapa E1 antes de tocar nada
clínico** (es el mayor riesgo técnico).

### 2.3 Catálogos anatómicos → **en código, no en tablas**

Siguiendo la convención del propio repo (FDI y `ESTADOS` son constantes en
`services/odontograma.py`), las **regiones faciales y corporales** se definen como
dicts en `services/anatomia.py` (código), no como filas de BD. Ventaja: versionadas
con el código, sin migraciones para tocar el catálogo, mismo estilo que odontología.

### 2.4 Separación de responsabilidades (exigida por el pedido, §28)

**El renderer nunca toca la BD.** Solo: carga el modelo por rubro, hace raycast,
emite el `anatomy_id` seleccionado y pinta colores/estado que recibe ya calculados.
Toda la persistencia pasa por los `services/*` existentes o nuevos, dentro del tenant
y con auditoría. El 3D es intercambiable y el **2D sigue siendo la fuente de verdad y
el fallback** si el 3D no carga (PC de consultorio vieja).

### 2.5 Identificación por metadatos, no por nombre de mesh (§31)

Cada GLB lleva en cada mesh `userData = {anatomy_type, anatomy_id, region}`. Para
dientes, `anatomy_id` **es el mismo código FDI** que `PiezaDental.numero` → cero
traducción. Para caras dentales, sub-meshes `anatomy_id="16"`, `cara="oclusal"`.

---

## 3. Arquitectura del Motor Anatómico (capa nueva, delgada)

```
                       MOTOR ANATÓMICO
         ┌───────────────────────┬────────────────────────┐
         │  RENDER (nuevo)        │  LÓGICA CLÍNICA         │
         │  assets/js/anatomy/    │  services/ + state/     │
         │  + assets/anatomy/*.glb│  (odonto: YA EXISTE;    │
         │  three vendorizado     │   estética: se agrega)  │
         └──────────┬─────────────┴───────────┬────────────┘
       pick {anatomy_id,cara}         dict {estado,color,...}
                    │                          │
                    ▼                          ▼
        components/anatomy_viewer.py  ⇄  AnatomicalViewerState (mixin)
                                       ⇄  services (odontograma / estetica_mapa)
                                       ⇄  PACIENTE (misma historia clínica, tenant, RBAC)
```

### 3.1 Layout de archivos nuevos

```
assets/
  anatomy/
    dental/            11.glb … 48.glb  (o 1 arcada.glb con sub-meshes por FDI)
    facial/            face.glb
    body/              body.glb
  js/anatomy/
    vendor/            three.module.js, GLTFLoader.js, OrbitControls.js  (pinneados)
    viewer.js          AnatomicalViewer genérico: escena, cámara, luces, raycast, bridge
    regions.js         (opcional) helpers de highlight por anatomy_id

clinica_app/
  components/
    anatomy_viewer.py  # componente Reflex reutilizable: <div canvas> + input-puente
                       # + <script> include + call_script de init/setData
  services/
    anatomia.py        # catálogos de regiones faciales/corporales (código) + helpers
    estetica_mapa.py   # CRUD evaluación / procedimiento / puntos de aplicación (async, auditado)
  state/
    mapa_estetico.py   # estado del mapa facial/corporal
  models/
    evaluacion_estetica.py    # EvaluacionEstetica
    procedimiento_estetico.py # ProcedimientoEstetico + PuntoAplicacion
  pages/
    (odontograma.py: se le agrega toggle [2D]/[3D] — no ruta nueva)
    mapa_estetico.py          # /mapa-estetico?paciente_id=  (rostro/cuerpo 3D)
```

### 3.2 Flujo de datos (ejemplo odontograma 3D)

1. `/odontograma?paciente_id=X` con toggle `[2D] [3D]`. En 3D, `OdontogramaState`
   ya tiene `superior`/`inferior` (mismos datos que el 2D).
2. `on_mount`/cambio → `rx.call_script("AnatomyViewer.setData(<json arcada>)")` pinta
   cada diente con su color de estado.
3. Usuario hace click en el diente 16 → `viewer.js` raycast → escribe en el input-puente
   `{anatomy_id:"16"}` → `OdontogramaState.on_pick` (equivale a `abrir_pieza`) → abre el
   modal existente.
4. Guardar → `services/odontograma.guardar_pieza(...)` (ya existe, auditado) → refresca
   estado → `setData` repinta. **Persistencia real, sin lógica nueva de datos.**

---

## 4. Modelo de datos: reutilizar vs. agregar

### 4.1 Odontología → **ninguna tabla nueva**

`PiezaDental` ya guarda `caras` (JSON por superficie). El 3D solo **expone
visualmente** la selección de cara que el modelo ya soporta. `OdontogramaVersion`,
export PDF y comparación se reutilizan tal cual.

### 4.2 Estética → **2 migraciones aditivas** (lo que falta de verdad)

Reutiliza `Paciente`, `SesionEstetica`, `Producto`/inventario (trazabilidad + lote),
`Adjunto` (fotos/antes-después). Agrega solo el modelo espacial:

```
EvaluacionEstetica (tabla evaluaciones_esteticas)     # §24 evaluación por zona
  clinica_id, sede_id, paciente_id, sesion_id?(FK sesión),
  zona_codigo (str, del catálogo de services/anatomia),
  categoria (simetria|volumen|arrugas|flacidez|pigmentacion|textura|hidratacion|...),
  severidad (int 0–4 | null), observacion (text), + TenantSQLModel

ProcedimientoEstetico (tabla procedimientos_esteticos) # §19 procedimiento en zona
  clinica_id, sede_id, paciente_id, sesion_id?(FK),
  zona_codigo (str), tipo (botulinum_toxin|hyaluronic_acid|biostimulator|…, catálogo código),
  observacion (text), + TenantSQLModel

PuntoAplicacion (tabla puntos_aplicacion)              # §20 CORAZÓN del pedido estético
  clinica_id, sede_id, procedimiento_id (FK),
  zona_codigo (str),
  coord_x, coord_y (float 0..1 normalizadas sobre el modelo/vista),
  producto_id?(FK inv_productos), lote (str), cantidad (Numeric), unidad (str),
  observacion (str), + TenantSQLModel
```

- Catálogos de **zonas** y **tipos de procedimiento** = constantes en
  `services/anatomia.py` (código), como FDI/ESTADOS. No son tablas.
- Migraciones **aditivas e idempotentes**, encadenadas al head actual (patrón de todo
  el repo). Sin tocar tablas existentes.

### 4.3 Lo que NO se crea (ya existe con otro nombre)

`patients`, `professionals`, `clinical_photos`, `product_batches`, `treatment_plans`,
`clinical_records`, `appointments` → todo ya existe. **No duplicar.**

---

## 5. Plan de implementación por etapas (incremental y validado)

> Cada etapa: entra por rama, se prueba (pytest + E2E en navegador), se registra en
> `PLAN_MEJORAS.md` con commit, y **recién ahí** empieza la siguiente. Sin demos aisladas.

| # | Etapa | Entregable | Toca | Riesgo |
|---|---|---|---|---|
| **E0** | Cimientos de assets | Vendorizar `three` + GLTFLoader/OrbitControls en `assets/js/anatomy/vendor/`; carpeta `assets/anatomy/`. | assets | Bajo |
| **E1** | **Puente JS↔Reflex (prototipo aislado)** | `components/anatomy_viewer.py` + `viewer.js`: un cubo/diente **procedural** que al click devuelve `anatomy_id` a un handler de Reflex y repinta color desde Python. **Valida el riesgo central.** | components, 1 page de prueba | **Alto → se ataca primero** |
| **E2** | Motor genérico | `AnatomicalViewer` con escena/cámara/luces/OrbitControls, cámaras predefinidas (frontal/oclusal/lateral), hover+highlight, carga GLB por metadatos, API `setData/reset/setCamera`. | viewer.js, componente | Medio |
| **E3** | **Odontograma 3D** | Toggle `[2D][3D]` en `/odontograma` sobre `OdontogramaState` (datos existentes). Dientes **procedurales** primero; arquitectura lista para sustituir por GLB. Selección → modal existente → `guardar_pieza`. | odontograma page/state | Medio |
| **E4** | Superficies en 3D | Selección de **cara** (oclusal/vestibular/…) en el diente 3D → escribe en `caras` JSON (ya soportado). Leyenda y colores por cara. | viewer.js, odontograma | Medio |
| **E5** | Estética — backend | Modelos `EvaluacionEstetica`, `ProcedimientoEstetico`, `PuntoAplicacion` + 2 migraciones + `services/anatomia.py` (catálogos zonas/procedimientos) + `services/estetica_mapa.py` (CRUD auditado) + **tests**. | models, services, alembic, tests | Medio |
| **E6** | **Mapa facial 3D** | `/mapa-estetico?paciente_id=` (rostro): seleccionar zona (§17), registrar evaluación (§24), **puntos de aplicación** (§20) con producto+lote+cantidad (reusa inventario). Botón desde Historia Clínica (si `esp_estetica`). | page/state, viewer | **Alto** (núcleo estético) |
| **E7** | Mapa corporal 3D | Mismo motor, `body.glb` + catálogo corporal (§18), vistas frontal/posterior/lateral. | page/state, assets | Medio |
| **E8** | Fotos + antes/después ligados a zona | Asociar `Adjunto`/`SesionEstetica` a `zona_codigo`; comparativa antes/después por zona (reusa galería C1). | estetica_mapa, page | Bajo |
| **E9** | Reportes | Odonto: piezas tratadas/evolución (ya hay export PDF; ampliar). Estética: procedimientos/productos/lotes/zonas/puntos (PDF con ReportLab, patrón existente). | services/reportes, pdf_* | Medio |
| **E10** | GLB anatómicos realistas | Sustituir geometría procedural por GLB con `userData` (arte externo). **Sin tocar lógica clínica** (la abstracción lo permite). | assets | Bajo (arte aparte) |
| **E11** | Optimización + responsive | Lazy-load de GLB, instancing de dientes, LOD, reutilizar materiales, `dispose()`; adaptación laptop/tablet/pantalla grande. | viewer.js | Medio |

**Ítems ya HECHOS que el pedido listaba como etapas** (no se repiten): auditoría,
informe de arquitectura, modelo de datos base, odontograma 2D, diagnósticos/
tratamientos (vía estado de pieza + planes), historial odontológico, productos y
trazabilidad, fotografías, antes/después (galería), planes de tratamiento, permisos,
suite de pruebas base.

---

## 6. Rendimiento (PC de consultorio)

- GLB por-diente cargados **bajo demanda**; o una sola arcada con sub-meshes.
- **Instancing** para geometría repetida; **reutilizar materiales** por estado.
- **LOD** y límite de polígonos; `renderer` pausado cuando la pestaña no está visible.
- `dispose()` de geometrías/materiales al desmontar (evitar fugas de memoria WebGL).
- **Fallback:** si no hay WebGL o el GLB no carga, el 2D (que sigue vivo) toma el relevo.

## 7. Seguridad y privacidad

- Todo pasa por `BaseState` (auth + TTL + tenant `clinica_id` server-only + RBAC `historia`).
- Los GLB anatómicos son **genéricos** (no PII); las fotos siguen sirviéndose por el
  endpoint `/api/adjunto` con token efímero + chequeo de clínica (patrón existente).
- Handlers mutadores nuevos llevan su guard `tiene_permiso("historia", write=True)`
  (lo verifica el test AST `test_rbac_guards.py`).

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Puente JS→Reflex frágil | Se prototipa y valida **aislado en E1** con input-puente (patrón conocido, sin React). |
| Deps npm rompen el build de Reflex | **No se agregan**: Three vendorizado como ES module estático. |
| Deploy de frontend (rebuild imagen + purgar `life_web`) | Documentar; los GLB/JS son estáticos versionados, no `docker cp`. |
| Peso 3D en consultorio | Lazy-load, instancing, LOD, procedural fallback, 2D siempre disponible. |
| Calidad de modelos GLB | Arte externo desacoplado (E10); arquitectura lista para sustituir sin tocar clínica. |
| "Diagnóstico vs tratamiento" formal (§14) | Hoy cubierto por estado-de-pieza + planes; separación formal queda como refinamiento opcional, no bloquea. |

## 9. Criterios de aceptación (del pedido §48)

**Odontología:** abrir paciente → Odontología → odontograma → `[3D]` → rotar →
seleccionar diente 16 → cara oclusal → registrar caries + tratamiento → guardar →
recargar → dato persiste → historial muestra el cambio. *(Datos y persistencia YA
existen; E3/E4 agregan el 3D y la cara.)*

**Estética:** abrir paciente → Estética → mapa facial 3D → rotar → seleccionar frente
→ registrar evaluación → puntos de aplicación → toxina + producto + lote + cantidad →
guardar → asociar fotografía → consultar evolución → comparar antes/después. *(E5–E8.)*

## 10. No-goals (lo que este plan explícitamente NO hace)

Reescribir el proyecto · cambiar de framework · segundo frontend/backend/BD · otra
auth · duplicar pacientes/profesionales/productos · romper páginas actuales · botones
sin función · persistencia simulada · agregar dependencias innecesarias.

---

## Registro de avances (se completa al implementar)

| Fecha | Etapa | Commit |
|-------|-------|--------|
| 2026-08-14 | Plan escrito (este documento) | `docs(anatomia): plan del motor anatómico 2D/3D` |
| 2026-08-14 | **E0 + E1 HECHO** — Three.js r160 vendorizado en `assets/js/anatomy/vendor/` (three.module + OrbitControls + GLTFLoader + BufferGeometryUtils, imports reescritos a rutas relativas, self-contained sin CDN runtime). `viewer.js` (motor genérico: escena, OrbitControls, raycast, `setData`/`getColors`/`dispose`, fallback WebGL). Componente `anatomy_viewer.py` + puente input oculto; el módulo se inyecta con `document.createElement` (React no ejecuta `<script>` de JSX). Página lab `/anatomy-lab` (permiso `historia`) + `AnatomyLabState`. **Verificado E2E:** click 3D → `anatomy_id` correcto llega a Python → estado por pieza → `setData` repinta (pieza seleccionada sky-600; estado caries #dc2626 al deseleccionar). 272 tests verdes. **Riesgo central del plan (puente JS↔Reflex) validado.** | `feat(anatomia): E0+E1 motor 3D — three vendorizado + puente JS↔Reflex` |
