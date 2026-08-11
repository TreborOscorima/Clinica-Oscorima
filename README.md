# TUWAYKILIFE — Sistema de Gestión para Clínicas y Centros Estéticos

**Tecnología:** Python 3.13 / Reflex 0.9.8 / Tailwind CSS v4 / MySQL 8.0 / Docker
**Núcleo compartido:** `tuwayki-core` (multi-tenant + RBAC + utilidades de plataforma)

**TUWAYKILIFE** es el sistema de gestión integral para **clínicas y centros estéticos** de la marca
**TUWAYKIAPP**: una plataforma **SaaS multi-tenant** que cubre el ciclo completo del negocio — historia
clínica, agenda de turnos, profesionales, servicios/tratamientos, caja, cuentas corrientes, inventario,
compras, promociones y reportes. Construido 100% en Python con **Reflex** (Python → React/Vite).

> **Estado:** en **desarrollo / uso local** (Docker en `http://localhost:3004`). El deploy a producción
> está **preparado** (`life.tuwayki.app`, `scripts/deploy-prod.sh`, GitHub Actions) pero **aún no está
> lanzado** por decisión de producto. Ver [`DEPLOY_TUWAYKILIFE.md`](DEPLOY_TUWAYKILIFE.md).

> **Arquitectura de marca.** **TUWAYKIAPP** es la marca madre. Sus productos comparten `tuwayki-core` y el
> **Owner Panel** de activación de empresas (hospedado en SHOP):
> * **TUWAYKISHOP** — ventas/ERP/POS (retail, PYMES) · repo independiente
> * **TUWAYKIFOOD** — gestión gastronómica (restaurantes) · repo independiente
> * **TUWAYKILIFE** — **este sistema** (clínicas / estética)

---

## Capacidades principales

* **SaaS multi-tenant:** aislamiento por **clínica** (empresa) y **sede** (sucursal), con planes
  comerciales (`trial` / `standard` / `profesional`), período de prueba (`trial_ends_at`), expiración de
  licencia y **gating de módulos por plan** (`ClinicaModulo`).
* **RBAC + multi-sede:** roles por usuario (`RoleEnum`), permisos por rol (`PermisoRol`) y asignación de
  usuarios a sedes (`UsuarioSede`).
* **Pacientes e historia clínica:** ficha de paciente y **notas clínicas** (`NotaClinica`) — evolución,
  antecedentes y registro por atención.
* **Profesionales:** gestión del equipo (médicos/esteticistas) y su vínculo con turnos y servicios.
* **Servicios / tratamientos con insumos:** catálogo de servicios y sus **recetas de insumos**
  (`ServicioInsumo`) — cada tratamiento consume stock de inventario al realizarse. Historial de precios
  (`ServicioPrecioHist`).
* **Agenda de turnos + calendario:** turnos (`Turno`) con múltiples servicios por cita (`TurnoServicio`),
  vista de **calendario** y **recordatorios automáticos** por email (job en background,
  `tasks/recordatorios.py`).
* **Caja y arqueo:** sesiones de caja, movimientos (`CajaMovimiento`), **cierre/arqueo** (`CierreCaja`) y
  comprobantes (`Comprobante` + `ComprobanteItem`).
* **Cobros y comprobantes PDF:** flujo de cobro, emisión de **recibos en PDF** (`services/pdf_recibo.py`)
  con descarga por token seguro (`download_token`).
* **Cuentas corrientes (fiado):** deudas por paciente (`DeudaPaciente`) con seguimiento de cobranza.
* **Inventario:** productos (`Producto`), movimientos de stock (`MovimientoStock`), unidades de medida
  (`UnidadMedida`) e historial de precios (`ProductoPrecioHist`).
* **Compras y proveedores:** proveedores (`Proveedor`), documentos de compra (`Compra` + `CompraItem`),
  con creación, detalle y **anulación**.
* **Promociones:** descuentos y promociones (`Promocion`) aplicables al cobro.
* **Configuración fiscal multi-país:** impuestos configurables (`ImpuestoTasa`, IGV/IVA), **métodos de
  pago** (`MetodoPagoConfig`) y **monedas** (`Moneda`) — presets por país vía `tuwayki-core`.
* **Reportes y exportación:** consolidados por período con descarga, más **reportes programados**
  (`tasks/reportes.py`).
* **Auditoría y seguridad:** log de auditoría (`AuditLog`, IP + usuario + acción) y **protección
  anti-fuerza-bruta** en login (`LoginIntento` con bloqueo por intentos fallidos).

## Módulos (rutas)

| Grupo | Rutas |
|---|---|
| **Acceso** | `/login`, `/` (dashboard) |
| **Clínico** | `/pacientes`, `/historia-clinica`, `/profesionales`, `/servicios` |
| **Agenda** | `/turnos`, `/calendario` |
| **Comercial** | `/caja`, `/cobro`, `/cuentas`, `/compras`, `/inventario`, `/promociones` |
| **Gestión** | `/reportes`, `/configuracion`, `/auditoria` |

**Configuración** (submódulos): datos de empresa, sucursales, usuarios, impuestos, métodos de pago,
monedas y unidades de medida.

## Modelo de datos (entidades clave)

`Clinica` (tenant) · `Sede` · `User` / `UsuarioSede` / `PermisoRol` · `Profesional` · `Paciente` ·
`NotaClinica` · `Servicio` / `ServicioInsumo` / `ServicioPrecioHist` · `Turno` / `TurnoServicio` ·
`Comprobante` / `ComprobanteItem` / `CajaMovimiento` / `CierreCaja` / `DeudaPaciente` · `Producto` /
`MovimientoStock` / `UnidadMedida` / `ProductoPrecioHist` · `Proveedor` / `Compra` / `CompraItem` ·
`Promocion` · `ImpuestoTasa` / `MetodoPagoConfig` / `Moneda` · `ClinicaModulo` · `AuditLog` /
`LoginIntento`.

Todas las tablas de negocio heredan de `TenantMixin` (filtrado automático por `clinica_id` / `sede_id`) más
`TimestampMixin` y `SoftDeleteMixin`.

---

## Núcleo compartido (`tuwayki-core`)

El aislamiento multi-tenant, el RBAC base y utilidades comunes (auth, criptografía, cálculos fiscales,
formateo de moneda, exportaciones, timezone) viven en **`tuwayki-core`**, un paquete **público** en GitHub
reutilizado por los 3 productos de la marca. Es **agnóstico de Reflex** (no lo importa), por lo que un
upgrade de Reflex en LIFE no obliga a tocarlo.

Se instala **pinneado por SHA vía `requirements.txt`** (fuente de verdad única, sin `_vendor`):

```
tuwayki-core @ git+https://github.com/TreborOscorima/tuwayki-core.git@<SHA>
```

Para **bumpear el core**: editar el SHA en `requirements.txt`, correr los tests y redeployar.

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| **Frontend** | React (compilado por Reflex desde Python), Tailwind CSS v4 (`TailwindV4Plugin`) + Radix Theme |
| **Backend** | Python 3.13 + **Reflex 0.9.8** (estado por websockets) |
| **Núcleo multi-tenant** | `tuwayki-core` (público, pinneado por SHA vía `requirements.txt`) |
| **Base de datos** | MySQL 8.0 (`life_db`) + SQLModel / SQLAlchemy 2.0 + PyMySQL |
| **Migraciones** | Alembic |
| **Autenticación** | JWT (PyJWT) + bcrypt, con rate-limit / lockout de login |
| **Reportes** | ReportLab (PDF) + OpenPyXL (Excel) |
| **Testing** | pytest + pytest-asyncio |
| **Despliegue** | Docker Compose + Nginx Proxy Manager |

---

## Desarrollo local

Requisitos: Python 3.13, un MySQL accesible y acceso a GitHub para instalar `tuwayki-core`.
La preparación del entorno sigue el skill `setup-python-env`; para correr/recargar, `reflex-process-management`.

```bash
# 1. Entorno virtual + dependencias
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows (Git Bash)

# 2. Variables de entorno (copiar y completar)
cp .env.example .env

# 3. Migraciones
alembic upgrade head

# 4. (Opcional) Datos de ejemplo
python scripts/seed.py

# 5. Correr
reflex run
```

## Docker (local, réplica de producción)

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```

Levanta MySQL (`life_mysql`, puerto host `33308`) + la app (`tuwayki_life`) en `http://localhost:3004`.
El frontend se compila dentro del contenedor en el primer arranque (healthcheck en `/api/ping`).

Health checks:
`GET /api/ping` → `{"status":"ok"}` · `GET /api/health` → `{"status":"ok","app":"tuwaykilife-clinica",...}`.

> ⚠️ Tras un **cambio de versión de Reflex**, recrear el volumen `life_web` para forzar un build fresco del
> frontend (evita servir un bundle cacheado).

## Despliegue a producción (preparado, no lanzado)

El deploy está listo pero **el servicio no está en producción todavía**. Cuando producto decida lanzarlo:
push a la rama de deploy → GitHub Actions → SSH a EC2 → `scripts/deploy-prod.sh` (build + health check),
sirviendo `life.tuwayki.app` vía Nginx Proxy Manager. Detalle en
[`DEPLOY_TUWAYKILIFE.md`](DEPLOY_TUWAYKILIFE.md).

---

## Tests

```bash
pytest tests/
```

Suite de integración de la lógica de negocio: autenticación (incl. lockout), pacientes, caja, cobros,
cuentas, compras, inventario, auditoría y aislamiento multi-tenant.

## Documentación

| Documento | Contenido |
|---|---|
| [`DEPLOY_TUWAYKILIFE.md`](DEPLOY_TUWAYKILIFE.md) | Guía de despliegue (EC2 / Docker / dominio) |
| [`PLAN_ACTUALIZACION_REFLEX.md`](PLAN_ACTUALIZACION_REFLEX.md) | Plan y verificación del upgrade de Reflex (flota) |
| [`PLAN_MEJORAS.md`](PLAN_MEJORAS.md) | Roadmap de mejoras |
| [`AUDITORIA_WAYKISAC_CLINICA.md`](AUDITORIA_WAYKISAC_CLINICA.md) | Auditoría del sistema |

---

**Sistemas hermanos:** **SHOP** (Sistema-de-Ventas, retail/POS) y **FOOD** (Sistema-para-Food,
gastronomía). Los tres comparten `tuwayki-core` y el Owner Panel de activación de empresas. Los repos son
100% independientes (venvs y despliegues separados).
