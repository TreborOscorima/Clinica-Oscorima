# app.py
"""
Punto de entrada principal — WaykiSAC Sistema de Gestión para Clínicas

Comandos:
    python app.py run          — Inicia el servidor de desarrollo
    python app.py db_create    — Crea tablas (solo para desarrollo inicial)
    python app.py seed_admin   — Crea/actualiza el usuario admin (admin@clinica.local / admin123)

Para migraciones de producción (Flask-Migrate):
    flask --app app:create_app db init      # Solo la primera vez
    flask --app app:create_app db migrate   # Cada vez que cambies un modelo
    flask --app app:create_app db upgrade   # Aplica la migración a la DB
"""
import sys
from flask import Flask, current_app, render_template
from sqlmodel import select
from config import Config
from extensions import init_extensions, db
from database import create_sqlmodel_tables, get_session

# ─── Importar todos los modelos ANTES de create_all() / Migrate ───────────────
from models.user import User, RoleEnum, PermisoRol
from models.clinica import Clinica
from models.paciente import Paciente
from models.profesional import Profesional
from models.servicio import Servicio
from models.servicio_insumo import ServicioInsumo
from models.inventario import Producto, MovimientoStock, TipoMov
from models.turno_servicio import TurnoServicio
from models.turno import Turno, EstadoTurno
from models.caja import (
    Comprobante,
    CierreCaja,
    CajaMovimiento,
    ComprobanteItem,
    DeudaPaciente,
)

# ─── Blueprints ───────────────────────────────────────────────────────────────
from routes import (
    auth as auth_routes,
    pacientes as pacientes_routes,
    profesionales as profesionales_routes,
    servicios as servicios_routes,
    servicio_insumos as servicio_insumos_routes,
    configuracion as configuracion_routes,
    inventario as inventario_routes,
    turnos as turnos_routes,
    caja as caja_routes,
    reportes as reportes_routes,
)


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(pacientes_routes.bp)
    app.register_blueprint(profesionales_routes.bp)
    app.register_blueprint(servicios_routes.bp)
    app.register_blueprint(caja_routes.bp)
    app.register_blueprint(turnos_routes.bp)
    app.register_blueprint(inventario_routes.bp)
    app.register_blueprint(reportes_routes.bp)
    app.register_blueprint(servicio_insumos_routes.bp)
    app.register_blueprint(configuracion_routes.bp)


def create_app(config_object: type[Config] = Config) -> Flask:
    """
    App factory pattern — compatible con Flask CLI y Flask-Migrate.
    Usar: flask --app app:create_app <comando>
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_object)
    init_extensions(app)  # Registra db, jwt, migrate, limiter, cors

    @app.get("/")
    def index():
        return render_template("index.html")

    register_blueprints(app)

    return app


# ─── Comandos de CLI (solo para desarrollo) ───────────────────────────────────

def db_create() -> None:
    """
    Crea todas las tablas directamente (solo para desarrollo inicial).
    En PRODUCCIÓN usa: flask --app app:create_app db upgrade
    """
    app = create_app()
    with app.app_context():
        db.create_all()
        create_sqlmodel_tables()
        print("✔ Tablas creadas (desarrollo)")
        print("⚠  En producción usa: flask --app app:create_app db upgrade")


def seed_default_clinica() -> Clinica:
    """Crea el tenant inicial para desarrollo y migraciones legacy."""
    session = get_session()
    slug = current_app.config["DEFAULT_CLINICA_SLUG"]
    clinica = session.exec(select(Clinica).where(Clinica.slug == slug)).first()
    if clinica:
        return clinica
    clinica = Clinica(nombre="Clinica Default", slug=slug)
    session.add(clinica)
    session.commit()
    session.refresh(clinica)
    return clinica


def seed_admin() -> None:
    """Crea o actualiza el usuario administrador por defecto."""
    app = create_app()
    with app.app_context():
        NEW_EMAIL = "admin@clinica.local"
        NEW_PASS = "admin123"

        # Buscar por email nuevo o el email legacy
        user: User | None = db.session.execute(
            select(User).where(User.email.in_([NEW_EMAIL, "admin@clinic.local"]))
        ).scalar_one_or_none()

        if not user:
            clinica = seed_default_clinica()
            user = User(
                clinica_id=clinica.id,
                email=NEW_EMAIL,
                nombre="Admin",
                rol=RoleEnum.ADMIN,
            )
            db.session.add(user)

        # Actualizar siempre email, password y activar cuenta
        user.email = NEW_EMAIL
        user.nombre = "Admin"
        user.is_active = True
        user.set_password(NEW_PASS)
        db.session.commit()
        print(f"[OK] Admin listo: {NEW_EMAIL} / {NEW_PASS}")
        print("[!]  Cambia esta contraseña en produccion.")


def run() -> None:
    """Inicia el servidor de desarrollo."""
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    _commands = {
        "db_create": db_create,
        "seed_admin": seed_admin,
        "run": run,
    }
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    _commands.get(cmd, lambda: print("Comandos: db_create | seed_admin | run"))()
