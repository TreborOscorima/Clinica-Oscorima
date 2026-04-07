from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from marshmallow import ValidationError

# ─── Instancias globales de extensiones ───────────────────────────────────────
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

# Limiter: usa get_remote_address como clave por defecto.
# El storage_uri se configura desde Config.RATELIMIT_STORAGE_URI (Redis en producción).
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],          # Sin límite global por defecto; se aplica por ruta
    storage_uri=None,           # Se inyecta desde app.config en init_extensions
)


def init_extensions(app: Flask) -> None:
    """Inicializa todas las extensiones de Flask con la app factory."""

    CORS(app, supports_credentials=True, origins=app.config.get("CORS_ORIGINS", []))

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Flask-Limiter: toma RATELIMIT_STORAGE_URI desde config (Redis en cloud)
    limiter.init_app(app)

    # ─── Manejadores de error globales ────────────────────────────────────────

    @app.errorhandler(ValidationError)
    def handle_marshmallow_error(err: ValidationError):
        return {"message": "Datos inválidos", "errors": err.messages}, 400

    @app.errorhandler(429)
    def handle_rate_limit_exceeded(e):
        """Respuesta clara cuando se supera el límite de intentos."""
        return {
            "message": "Demasiados intentos. Por favor, espera un momento antes de reintentar.",
            "retry_after": getattr(e, "retry_after", None),
        }, 429
