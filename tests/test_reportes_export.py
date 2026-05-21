import csv
import io
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from flask_jwt_extended import create_access_token
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.pool import StaticPool

from app import create_app
from config import Config
from extensions import db
from models.caja import CajaMovimiento, MetodoPago, TipoMovimiento
from models.clinica import Clinica
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
        clinica = Clinica(id=1, nombre="Clinica Default", slug="clinica-default")
        paciente = Paciente(clinica_id=1, nombre="Paciente Demo")
        profesional = Profesional(nombres="Ana", apellidos="García")
        servicio = Servicio(nombre="Limpieza facial")
        producto = Producto(
            clinica_id=1,
            sku="SKU-1",
            nombre="Gel limpiador",
            stock_actual=1,
            stock_minimo=5,
        )
        producto.categoria = "Faciales"
        producto.unidad = "ml"

        db.session.add_all([clinica, paciente, profesional, servicio, producto])
        db.session.commit()

        turno = Turno(
            clinica_id=1,
            paciente_id=paciente.id,
            profesional_id=profesional.id,
            servicio_id=servicio.id,
            fecha_hora=datetime.now(timezone.utc),
            estado=EstadoTurno.ATENDIDO,
        )

        movimiento = CajaMovimiento(
            clinica_id=1,
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

    def test_exporta_facturacion_en_excel(self):
        response = self.client.get(
            "/api/reportes/facturacion/export/excel",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(response.headers.get("Content-Disposition", "").startswith("attachment;"))

    def test_exporta_facturacion_en_pdf(self):
        response = self.client.get(
            "/api/reportes/facturacion/export/pdf",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertTrue(response.headers.get("Content-Disposition", "").startswith("attachment;"))

    def test_exporta_async_enqueuea_job(self):
        class FakeConnection:
            def ping(self):
                return True

        class FakeJob:
            id = "job-1"

            def get_status(self, refresh=True):
                return "queued"

        class FakeQueue:
            name = "default"
            connection = FakeConnection()

            def enqueue(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs
                return FakeJob()

        fake_queue = FakeQueue()
        with patch("routes.reportes.get_queue", return_value=fake_queue):
            response = self.client.post(
                "/api/reportes/exportar/async",
                json={"tipo": "facturacion", "formato": "excel", "filtros": {"desde": "2026-01-01"}},
                headers=self._auth_headers(),
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json["job_id"], "job-1")
        self.assertEqual(fake_queue.args[0], "tasks.reportes.export_report_job")
        self.assertEqual(fake_queue.args[1], "facturacion")
        self.assertEqual(fake_queue.args[2], "excel")
        self.assertEqual(fake_queue.args[4], 1)

    def test_exporta_async_responde_503_si_redis_no_disponible(self):
        class FakeConnection:
            def ping(self):
                raise RedisConnectionError("down")

        class FakeQueue:
            name = "default"
            connection = FakeConnection()

        with patch("routes.reportes.get_queue", return_value=FakeQueue()):
            response = self.client.post(
                "/api/reportes/exportar/async",
                json={"tipo": "facturacion", "formato": "excel", "filtros": {}},
                headers=self._auth_headers(),
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Redis no está disponible", response.json["message"])


if __name__ == "__main__":
    unittest.main()
