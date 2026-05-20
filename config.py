import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ─── Claves de Seguridad ────────────────────────────────────────────────────
    # IMPORTANTE: Genera claves seguras con: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-CHANGE-IN-PRODUCTION")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-CHANGE-IN-PRODUCTION")

    # ─── Base de Datos MySQL ────────────────────────────────────────────────────
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DB = os.getenv("MYSQL_DB", "clinica_estetica")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    DATABASE_URL = os.getenv("DATABASE_URL", SQLALCHEMY_DATABASE_URI)
    SQLMODEL_ECHO = os.getenv("SQLMODEL_ECHO", "false").lower() == "true"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Pool de conexiones para Cloud: reconecta automáticamente si cae la DB
        "pool_pre_ping": True,
        "pool_recycle": 300,      # reciclar conexiones cada 5 min
        "pool_size": 10,
        "max_overflow": 20,
    }

    # ─── General Flask ──────────────────────────────────────────────────────────
    JSON_AS_ASCII = False
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5000").split(",")

    # ─── JWT — Seguridad de Tokens ──────────────────────────────────────────────
    # Access Token: 15 minutos (ventana corta → reduce impacto de robo de token)
    # Refresh Token: 7 días (el usuario permanece logueado si usa el sistema regularmente)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7")))

    # ─── Rate Limiting (Flask-Limiter + Redis) ──────────────────────────────────
    # En producción Cloud: usa Redis para que los límites persistan entre reinicios
    # Formato: "redis://[:password@]host[:port][/db]"
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RQ_DEFAULT_QUEUE = os.getenv("RQ_DEFAULT_QUEUE", "default")
    REPORT_EXPORT_DIR = os.getenv("REPORT_EXPORT_DIR", "exports")
    REPORT_EXPORT_JOB_TIMEOUT = int(os.getenv("REPORT_EXPORT_JOB_TIMEOUT", "600"))
    RATELIMIT_HEADERS_ENABLED = True     # Devuelve X-RateLimit-* headers al cliente
    RATELIMIT_STRATEGY = "fixed-window"  # Alternativa: "moving-window" (más preciso)

    # ─── Multi-tenant ─────────────────────────────────────────────────────────
    # Compatibilidad temporal hasta que los JWT incluyan clinica_id.
    DEFAULT_CLINICA_ID = int(os.getenv("DEFAULT_CLINICA_ID", "0")) or None
    DEFAULT_CLINICA_SLUG = os.getenv("DEFAULT_CLINICA_SLUG", "clinica-default")

    # ─── Fase 2: Cookies HttpOnly (preparado, no activo aún) ────────────────────
    # Descomentar cuando se migre el frontend a cookie-based auth:
    # JWT_TOKEN_LOCATION = ["cookies"]
    # JWT_COOKIE_SECURE = os.getenv("FLASK_ENV", "development") == "production"
    # JWT_COOKIE_HTTPONLY = True
    # JWT_COOKIE_SAMESITE = "Lax"
    # JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    # JWT_REFRESH_COOKIE_NAME = "refresh_token_cookie"
    # JWT_COOKIE_CSRF_PROTECT = True
