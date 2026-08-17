# Runbook de Backups — TUWAYKILIFE (MySQL)

> Un backup no probado no existe. Este runbook está **verificado**: el ciclo
> backup → restore se probó de punta a punta (48 objetos y datos idénticos).

## Qué se respalda y dónde

- `scripts/backup-db.sh` hace un `mysqldump` **consistente** (`--single-transaction`,
  `--routines`, `--triggers`) del contenedor `life_mysql`, lo comprime con gzip,
  **verifica integridad** (no vacío + `gzip -t`) y **rota** los viejos.
- Destino: `./backups/life_db_YYYYmmdd_HHMMSS.sql.gz` (gitignored).
- Retención: `BACKUP_KEEP` backups más nuevos (default **14**).
- El dashboard **`/salud`** muestra la frescura del último backup (la app monta
  `./backups` read-only en `/app/backups`, `BACKUP_DIR=/app/backups`).

## Backup manual

```bash
bash scripts/backup-db.sh
# BACKUP_DIR=/data/backups BACKUP_KEEP=30 bash scripts/backup-db.sh
```

## Backup automático diario

### Linux / EC2 (cron)

```bash
crontab -e
# Todos los días 03:15 (ajustá la ruta del repo):
15 3 * * * cd /home/ubuntu/sist-life-trebor && bash scripts/backup-db.sh >> backups/backup.log 2>&1
```

### Windows (Task Scheduler)

Crear una tarea diaria que ejecute:

```
"C:\Program Files\Git\bin\bash.exe" -lc "cd /d/PROYECTOS/Sistema-Gestion-Clinica && bash scripts/backup-db.sh"
```

> El deploy (`scripts/deploy-prod.sh`) ya hace un backup **pre-deploy** con el
> mismo script; el cron cubre los días sin deploy.

## Restaurar (recuperación ante desastre)

**Probar un backup primero** (restaura en una BD alterna, NO toca prod):

```bash
bash scripts/restore-db.sh backups/life_db_20260817_030000.sql.gz --db life_db_verificacion
# Compará conteos y borrá la BD de prueba cuando termines:
docker exec life_mysql sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE life_db_verificacion;"'
```

**Restaurar sobre producción** (DESTRUCTIVO — reemplaza los datos actuales; pide
confirmación escribiendo `restaurar`):

```bash
bash scripts/restore-db.sh backups/life_db_20260817_030000.sql.gz
```

Después de restaurar sobre prod, reiniciar la app para reconectar limpio:

```bash
docker restart tuwayki_life
```

## Verificación periódica (recomendado)

Una vez al mes, correr una restauración de prueba (`--db life_db_verificacion`)
y confirmar que el conteo de tablas y filas de las tablas clave (`usuarios`,
`pacientes`, `turnos`) coincide con producción. Es la única forma de saber que
los backups sirven.

## Off-site (pendiente, recomendado para prod real)

Los dumps viven en el mismo disco del server. Para resistir la pérdida del
volumen, copiarlos a un almacenamiento externo (S3 `aws s3 sync ./backups
s3://…`, o `rsync` a otro host). Sumar esa línea al cron cuando exista el bucket.

## Notas

- `life_db.productos` es una **VISTA** (no una tabla base); `mysqldump` la
  respalda como `CREATE VIEW`. Es esperable que no aparezca entre los
  `CREATE TABLE` del dump.
- En Docker sobre Windows la **restauración** es lenta (fsync del disco
  virtualizado hace cada `CREATE TABLE` costoso); en Linux/EC2 es casi
  instantánea para dumps chicos. El backup (lectura) es rápido en ambos.
