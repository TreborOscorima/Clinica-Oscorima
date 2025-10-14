# app.py
import sys
from flask import Flask, render_template
from config import Config
from extensions import init_extensions, db

# === Importar TODOS los modelos antes de create_all() ===
from models.user import User, RoleEnum, RolePermission
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

# === Rutas / Blueprints ===
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

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    init_extensions(app)

    @app.get("/")
    def index():
        return render_template("index.html")

    # Registrar blueprints
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

    return app

def db_create():
    app = create_app()
    with app.app_context():
        db.create_all()
        print("✔ Tablas creadas")

def seed_admin():
    app = create_app()
    with app.app_context():
        if not User.query.filter_by(email="admin@clinic.local").first():
            u = User(email="admin@clinic.local", nombre="Admin", rol=RoleEnum.ADMIN)
            u.set_password("Admin123!")
            db.session.add(u)
            db.session.commit()
            print("✔ Admin creado: admin@clinic.local / Admin123!")
        else:
            print("ℹ Admin ya existe")

def run():
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"db_create": db_create, "seed_admin": seed_admin, "run": run}.get(cmd, lambda: print("Comandos: db_create | seed_admin | run"))()
