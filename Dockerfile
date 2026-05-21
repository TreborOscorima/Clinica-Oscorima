# ─── Stage 1: dependencias Python ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements_reflex.txt .
RUN pip install --no-cache-dir -r requirements_reflex.txt

# ─── Stage 2: imagen de producción ────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Node.js 20 — necesario para compilar el frontend Next.js de Reflex
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copiar site-packages y binarios instalados en el stage builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código fuente (el .dockerignore excluye Flask era, .env, .git, etc.)
COPY . .

# Inicializar el scaffold de Reflex (crea .web/ con node_modules — sin necesitar DB)
# Se hace en build para evitar demora en el cold start del container
RUN reflex init --loglevel critical

# El frontend de Next.js se compila la primera vez que corre `reflex run --env prod`
# Si quisieras pre-compilarlo aquí (más lento en build, más rápido en start):
# RUN reflex export --frontend-only --no-zip --loglevel critical

EXPOSE 3000 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Producción: compila y sirve frontend + backend WebSocket
CMD ["reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0"]
