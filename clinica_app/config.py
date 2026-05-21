from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_USER     = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST     = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT     = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB       = os.getenv("MYSQL_DB", "clinica_estetica")

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4",
)

REDIS_URL: str      = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SECRET_KEY: str     = os.getenv("SECRET_KEY", "dev-key-CHANGE-IN-PRODUCTION")
SQLMODEL_ECHO: bool = os.getenv("SQLMODEL_ECHO", "false").lower() == "true"

REPORT_EXPORT_DIR: str = os.getenv("REPORT_EXPORT_DIR", "exports")

# Rate limiting de login
LOGIN_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECS:  int = int(os.getenv("LOGIN_WINDOW_SECS", "60"))
