# Guía de Deploy — TUWAYKILIFE (Sistema para Clínicas)

> Cómo poner TUWAYKILIFE en producción en `life.tuwayki.app` y conectarlo al
> panel Owner del Sistema de Ventas. Mismo patrón que TUWAYKIFOOD.
>
> ⚠️ **Todavía NO ejecutar en producción.** Falta terminar de probar todo en
> local. Esta guía es la referencia para cuando esté listo. Ver puntos
> pendientes en [PLAN_MEJORAS.md](PLAN_MEJORAS.md).

---

## 0. Arquitectura del despliegue

- **TUWAYKILIFE es un stack independiente**: su propio contenedor de app
  (`tuwayki_life`), su propio MySQL (`life_mysql`, schema `life_db`) y su propio
  volumen. No comparte base de datos con Ventas ni con Food.
- **La integración con el Owner es 100% HTTP.** El Sistema de Ventas llama a la
  API `/api/admin/*` y `/api/registro` de la clínica. El único "cable" entre
  ambos es un **secreto compartido** (`LIFE_ADMIN_API_SECRET`) y la **red Docker
  compartida** `nginx-proxy-manager_default`.
- **Un solo puerto**: el contenedor sirve todo en el `3000` interno
  (`--single-port`). NPM hace TLS y proxy.

```
Internet ──HTTPS──> NPM ──http──> tuwayki_life:3000  (life.tuwayki.app)
                              │
Owner/Admin (tuwayki_admin) ──http──> tuwayki_life:3000/api/admin/*  (red interna NPM)
```

---

## 1. Requisitos previos (en el servidor EC2)

- Docker + Docker Compose instalados.
- **nginx-proxy-manager** corriendo (el mismo que usan Ventas y Food).
- La red externa compartida creada una sola vez:
  ```bash
  docker network create nginx-proxy-manager_default
  ```
- Acceso SSH al server (para el deploy manual y para GitHub Actions).

---

## 2. DNS

Crear un registro **A** apuntando el subdominio al EC2:

| Tipo | Nombre | Valor |
|------|--------|-------|
| A | `life` | `<IP pública del EC2>` |

Resultado: `life.tuwayki.app → <IP>`. (Mismo EC2 que `tuwayki.app` y `food.tuwayki.app`.)

---

## 3. Variables de entorno

### 3.1 En el `.env` de TUWAYKILIFE (server, este repo)

Copiar `.env.example` → `.env` y completar. Claves críticas para prod:

```ini
ENV=prod
SECRET_KEY=<32+ chars aleatorios>            # python -c "import secrets; print(secrets.token_hex(32))"
MYSQL_DB=life_db
MYSQL_USER=clinica
MYSQL_PASSWORD=<password>
MYSQL_ROOT_PASSWORD=<password distinto>
PUBLIC_API_URL=https://life.tuwayki.app

# Integración con el panel Owner — el "cable"
LIFE_ADMIN_API_SECRET=<secreto compartido>   # MISMO valor que en el .env de Ventas
LIFE_TRIAL_DAYS=15
```

> `MYSQL_HOST` / `MYSQL_PORT` los inyecta el compose (`life_mysql:3306`) — no setearlos.

### 3.2 En el `.env` del Sistema de Ventas (server del Owner)

```ini
# Cómo el Owner alcanza a la clínica (misma red NPM, por nombre de contenedor)
LIFE_API_URL=http://tuwayki_life:3000
LIFE_ADMIN_API_SECRET=<el MISMO secreto de arriba>
# Para que las tarjetas/landing enlacen al sistema real
PUBLIC_LIFE_URL=https://life.tuwayki.app
```

> **El `LIFE_ADMIN_API_SECRET` debe ser idéntico en los dos `.env`.** Si no
> coinciden, el Owner recibe `401` y no puede gestionar clínicas.
>
> En **local** es distinto: el admin no está en la red NPM, así que usa
> `LIFE_API_URL=http://host.docker.internal:3004` (ya configurado en el
> `docker-compose.local.yml` de Ventas). En **prod** es `http://tuwayki_life:3000`.

---

## 4. Nginx Proxy Manager (Proxy Host)

Crear un Proxy Host nuevo:

- **Domain Names**: `life.tuwayki.app`
- **Scheme**: `http`
- **Forward Hostname**: `tuwayki_life`
- **Forward Port**: `3000`
- **Websockets Support**: **ON** (obligatorio para Reflex)
- **Block Common Exploits**: ON
- **SSL**: solicitar certificado Let's Encrypt + Force SSL + HTTP/2

> El contenedor `tuwayki_life` debe estar en la red `nginx-proxy-manager_default`
> (el compose ya lo conecta vía `life_npm_network`). Verificar con:
> ```bash
> docker inspect tuwayki_life --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
> ```

(Opcional pero recomendado) headers de seguridad en Advanced → Custom Nginx
Configuration, igual que documenta la auditoría (HSTS, X-Frame-Options, etc.).

---

## 5. Deploy automático por GitHub Actions

El workflow [`.github/workflows/deploy-prod.yml`](.github/workflows/deploy-prod.yml)
replica el de TUWAYKIFOOD.

**Cómo dispara:**
- Push a la rama **`docker-deploy-prod`** → deploy automático.
- Manualmente desde Actions → *deploy-prod* → *Run workflow* (`workflow_dispatch`).
- Un push a `main` **NO** despliega (solo corre `ci.yml`: lint + tests).

**Secrets requeridos** (Settings → Secrets and variables → Actions):

| Secret | Valor |
|--------|-------|
| `DEPLOY_SSH_HOST` | IP/hostname del EC2 |
| `DEPLOY_SSH_USER` | usuario SSH (ej. `ubuntu`) |
| `DEPLOY_SSH_PRIVATE_KEY` | contenido completo del `.pem` |
| `DEPLOY_APP_DIR` | ruta del repo en el server (ej. `/home/ubuntu/sist-life-trebor`) |
| `DEPLOY_SSH_PORT` | (opcional) puerto SSH, default 22 |

**Qué hace:** SSH al server → `scripts/deploy-prod.sh` (git reset a
`docker-deploy-prod`, backup MySQL, build, `alembic upgrade head` en el
entrypoint, espera healthy) → verifica `https://life.tuwayki.app/api/health`
(espera `{"status":"ok","app":"waykisac-clinica"}`).

**Flujo de release habitual:** trabajar y mergear en `main` (corre CI). Cuando
una versión está lista para prod, mergear/pushear `main → docker-deploy-prod`.

---

## 6. Primer deploy (manual, una sola vez)

En el EC2, antes de que el DNS/NPM estén listos:

```bash
git clone https://github.com/TreborOscorima/Gestion-de-Clinica.git sist-life-trebor
cd sist-life-trebor
git checkout docker-deploy-prod
cp .env.example .env && nano .env          # completar (sección 3.1)
docker network create nginx-proxy-manager_default   # si no existe

# Primer arranque sin verificar la URL pública (NPM aún no configurado)
bash scripts/deploy-prod.sh --skip-public-check
```

Luego configurar el Proxy Host en NPM (sección 4) y verificar:

```bash
curl -s https://life.tuwayki.app/api/health
# → {"status":"ok","app":"waykisac-clinica"}
```

A partir de acá, los deploys siguientes salen solos por GitHub Actions
(push a `docker-deploy-prod`).

---

## 7. Conectar el Owner (Sistema de Ventas)

Una vez que la clínica responde en `life.tuwayki.app`:

1. Setear en el `.env` de Ventas las 3 variables `LIFE_*` (sección 3.2) con el
   **mismo secreto** que la clínica.
2. Redeployar el Sistema de Ventas (su propio `deploy-prod.yml`) para que
   `tuwayki_admin` tome las variables y el código.
3. Verificar que ambos contenedores comparten `nginx-proxy-manager_default`
   (para que `tuwayki_life` resuelva por nombre desde `tuwayki_admin`).

---

## 8. Checklist de verificación post-deploy

- [ ] `curl https://life.tuwayki.app/api/health` → `app=waykisac-clinica`, `status=ok`.
- [ ] `https://life.tuwayki.app/login` carga.
- [ ] Registro público: alta desde `tuwayki.app/life` → `/registro?producto=life`
      crea la clínica (con sede principal + admin + trial).
- [ ] En el panel Owner, pestaña **TUWAYKILIFE** lista esa clínica nueva.
- [ ] Desde el Owner: cambiar plan / suspender funciona (200, no 401).
- [ ] **Enforcement**: al suspender una clínica, su login queda bloqueado
      ("cuenta suspendida"); al reactivar, vuelve a entrar.

---

## 9. Rollback y troubleshooting

- **Rollback**: en el server, `git checkout <commit-anterior>` en la rama de
  deploy y `bash scripts/deploy-prod.sh`, o revertir el commit y re-pushear a
  `docker-deploy-prod`. El backup de MySQL queda en `./backups/life_db_*.sql.gz`.
- **Owner recibe 401**: el `LIFE_ADMIN_API_SECRET` no coincide entre los dos
  `.env`, o está vacío en la clínica.
- **Owner recibe "No se pudo conectar"**: `LIFE_API_URL` mal seteado, o los
  contenedores no comparten `nginx-proxy-manager_default`.
- **La app no arranca**: revisar `docker logs tuwayki_life`; en el primer
  arranque corre `alembic upgrade head`.
- **Health 502 en NPM**: el Proxy Host apunta a `tuwayki_life:3000` y el
  contenedor debe estar en la red NPM.

---

## 10. Orden de rollout (resumen)

1. DNS `life` → EC2.
2. `.env` de la clínica (con `LIFE_ADMIN_API_SECRET`).
3. Primer deploy manual de la clínica (`--skip-public-check`).
4. Proxy Host en NPM + verificar health público.
5. `.env` de Ventas (mismo secreto) + redeploy del Owner.
6. Checklist de verificación (sección 8).
7. En adelante: releases por push a `docker-deploy-prod`.
