import csv
import io
import unittest
from datetime import datetime

from flask_jwt_extended import create_access_token
from sqlalchemy.pool import StaticPool

from app import create_app
from config import Config
from extensions import db
from models.caja import CajaMovimiento, MetodoPago, TipoMovimiento
from models.inventario import Producto
from models.paciente import Paciente
from models.profesional import Profesional
from models.servicio import Servicio
from models.turno import EstadoTurno, Turno


class ReportesExportCSVTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_db_uri = Config.SQLALCHEMY_DATABASE_URI
        cls._engine_opts_existed = hasattr(Config, "SQLALCHEMY_ENGINE_OPTIONS")
        cls._orig_engine_opts = getattr(Config, "SQLALCHEMY_ENGINE_OPTIONS", None)
        Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
        Config.SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }

    @classmethod
    def tearDownClass(cls):
        Config.SQLALCHEMY_DATABASE_URI = cls._orig_db_uri
        if cls._engine_opts_existed:
            Config.SQLALCHEMY_ENGINE_OPTIONS = cls._orig_engine_opts
        elif hasattr(Config, "SQLALCHEMY_ENGINE_OPTIONS"):
            delattr(Config, "SQLALCHEMY_ENGINE_OPTIONS")

    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self._seed_data()
            self.token = create_access_token(identity="tester")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def _seed_data(self):
        paciente = Paciente(nombre="Paciente Demo")
        profesional = Profesional(nombres="Ana", apellidos="García")
        servicio = Servicio(nombre="Limpieza facial")
        producto = Producto(
            sku="SKU-1",
            nombre="Gel limpiador",
            stock_actual=1,
            stock_minimo=5,
        )
        producto.categoria = "Faciales"
        producto.unidad = "ml"

        db.session.add_all([paciente, profesional, servicio, producto])
        db.session.commit()

        turno = Turno(
            paciente_id=paciente.id,
            profesional_id=profesional.id,
            servicio_id=servicio.id,
            fecha_hora=datetime.utcnow(),
            estado=EstadoTurno.ATENDIDO,
        )

        movimiento = CajaMovimiento(
            tipo=TipoMovimiento.INGRESO,
            monto=120,
            metodo_pago=MetodoPago.EFECTIVO,
            paciente_id=paciente.id,
            profesional_id=profesional.id,
            servicio_id=servicio.id,
        )

        db.session.add_all([turno, movimiento])
        db.session.commit()

    def _csv_rows(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        decoded = response.data.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(decoded)))

    def test_exporta_stock_bajo_en_csv(self):
        response = self.client.get(
            "/api/reportes/exportar/csv?tipo=stock_bajo",
            headers=self._auth_headers(),
        )
        rows = self._csv_rows(response)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sku"], "SKU-1")
        self.assertEqual(rows[0]["stock_actual"], "1.0")
        self.assertEqual(rows[0]["stock_minimo"], "5.0")

    def test_exporta_atenciones_en_csv(self):
        response = self.client.get(
            "/api/reportes/exportar/csv?tipo=atenciones",
            headers=self._auth_headers(),
        )
        rows = self._csv_rows(response)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cantidad"], "1")
        self.assertTrue(rows[0]["clave"])  # fecha agrupada o etiqueta

    def test_exporta_facturacion_en_csv(self):
        response = self.client.get(
            "/api/reportes/exportar/csv?tipo=facturacion",
            headers=self._auth_headers(),
        )
        rows = self._csv_rows(response)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["clave"], MetodoPago.EFECTIVO.value)
        self.assertEqual(rows[0]["monto"], "120.0")
        self.assertEqual(rows[0]["total_global"], "120.0")


if __name__ == "__main__":
    unittest.main()
