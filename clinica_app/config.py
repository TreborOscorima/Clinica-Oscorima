from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_USER     = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST     = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT     = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB       = os.getenv("MYSQL_DB", "clinica_estetica")

# Driver síncrono — solo para Alembic / CLI scripts
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4",
)

# Driver asíncrono — usado por todos los event handlers de Reflex
# Requiere: pip install aiomysql
ASYNC_DATABASE_URL: str = os.getenv(
    "ASYNC_DATABASE_URL",
    f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4",
)

REDIS_URL: str      = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SECRET_KEY: str     = os.getenv("SECRET_KEY", "dev-key-CHANGE-IN-PRODUCTION")
SQLMODEL_ECHO: bool = os.getenv("SQLMODEL_ECHO", "false").lower() == "true"

REPORT_EXPORT_DIR: str = os.getenv("REPORT_EXPORT_DIR", "exports")

# Rate limiting de login
LOGIN_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECS:  int = int(os.getenv("LOGIN_WINDOW_SECS", "60"))

# ── Notificaciones Email (SMTP) ────────────────────────────────────────────────
SMTP_HOST:    str  = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT:    int  = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER:    str  = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM:    str  = os.getenv("SMTP_FROM", "")
SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "WaykiSAC Clínica")
NOTIF_EMAIL_ENABLED: bool = os.getenv("NOTIF_EMAIL_ENABLED", "false").lower() == "true"

# ── Notificaciones WhatsApp (Twilio) ───────────────────────────────────────────
TWILIO_ACCOUNT_SID:  str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN:   str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WA_FROM:      str = os.getenv("TWILIO_WA_FROM", "whatsapp:+14155238886")
NOTIF_WA_ENABLED:    bool = os.getenv("NOTIF_WA_ENABLED", "false").lower() == "true"

# ── Nombre de la clínica para mensajes ────────────────────────────────────────
CLINICA_NOMBRE: str = os.getenv("CLINICA_NOMBRE", "la clínica")
