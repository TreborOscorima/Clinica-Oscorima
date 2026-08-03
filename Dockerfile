# WaykiSAC Clínica (Reflex + MySQL) - Imagen para producción
# Build multi-stage: builder compila wheels; runtime recibe solo site-packages.
# Misma mecánica que Sistema-de-Ventas y TUWAYKIFOOD.

# =============================================================================
# Stage 1: builder — instala deps Python (compila wheels si es necesario)
# =============================================================================
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# =============================================================================
# Stage 2: runtime — imagen final liviana
# =============================================================================
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --no-create-home --shell /sbin/nologin app \
    && mkdir -p /app/.web /app/exports \
    && chown -R app:app /app

COPY --chown=app:app . .

COPY --chown=app:app scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=5 \
    CMD curl -fsS http://localhost:3000/api/ping || exit 1

USER app

ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]
CMD ["reflex", "run", "--env", "prod", "--loglevel", "warning", "--backend-host", "0.0.0.0", "--single-port"]
