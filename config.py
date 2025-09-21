import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev")

    # Base de datos MySQL
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DB = os.getenv("MYSQL_DB", "clinica_estetica")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    CORS_ORIGINS = ["http://localhost:5000"]

    # 🔑 Token JWT prolongado: 7 días
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
