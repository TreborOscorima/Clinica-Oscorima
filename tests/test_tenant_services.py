import pytest
from sqlalchemy import func, select
from sqlalchemy.pool import StaticPool

from app import create_app
from extensions import db
from models.caja import CajaMovimiento, Comprobante, DeudaPaciente, MetodoPago, TipoMovimiento
from models.clinica import Clinica
from models.inventario import MovimientoStock, Proveedor
from models.paciente import Paciente
from models.servicio import Servicio
from services.caja import CajaService
from services.inventario import InventarioService
from services.exceptions import NotFoundError
from services.pacientes import PacienteService
from services.turnos import TurnoService


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-that-is-long-enough"
    JWT_SECRET_KEY = "test-jwt-secret-key-that-is-long-enough"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    DATABASE_URL = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    SQLMODEL_ECHO = False
    CORS_ORIGINS = []
    RATELIMIT_STORAGE_URI = "memory://"
    REDIS_URL = "redis://localhost:6379/0"
    RQ_DEFAULT_QUEUE = "default"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY = "fixed-window"
    DEFAULT_CLINICA_ID = 1
    DEFAULT_CLINICA_SLUG = "clinica-default"
    JWT_ACCESS_TOKEN_EXPIRES = False
    JWT_REFRESH_TOKEN_EXPIRES = False


@pytest.fixture()
def app_context():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Clinica(id=1, nombre="Clinica A", slug="clinica-default"),
                Clinica(id=2, nombre="Clinica B", slug="clinica-b"),
            ]
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


def test_paciente_service_filters_and_soft_deletes_by_clinica(app_context):
    svc_a = PacienteService(1)
    svc_b = PacienteService(2)

    paciente_a = svc_a.crear({"nombre": "Paciente A", "documento": "A-1"})
    svc_b.crear({"nombre": "Paciente B", "documento": "B-1"})

    assert svc_a.listar()["total"] == 1
    assert svc_b.listar()["total"] == 1

    svc_a.eliminar(paciente_a.id)

    assert svc_a.listar()["total"] == 0
    assert svc_b.listar()["total"] == 1


def test_turno_service_rejects_patient_from_another_clinica(app_context):
    db.session.add_all(
        [
            Paciente(id=10, clinica_id=2, nombre="Paciente externo"),
            Servicio(id=20, nombre="Consulta", precio=100),
        ]
    )
    db.session.commit()

    svc_a = TurnoService(1)

    with pytest.raises(NotFoundError):
        svc_a.crear(
            {
                "paciente_id": 10,
                "servicio_id": 20,
                "fecha_hora": "2026-05-10T10:30:00",
            }
        )


def test_caja_service_filters_summary_and_soft_deletes_by_clinica(app_context):
    svc_a = CajaService(1)
    svc_b = CajaService(2)

    mov_a = svc_a.crear_movimiento(
        {
            "tipo": TipoMovimiento.INGRESO.value,
            "monto": "120.00",
            "metodo_pago": MetodoPago.EFECTIVO.value,
            "observacion": "tenant A",
        }
    )
    svc_b.crear_movimiento(
        {
            "tipo": TipoMovimiento.EGRESO.value,
            "monto": "50.00",
            "metodo_pago": MetodoPago.TARJETA.value,
            "observacion": "tenant B",
        }
    )

    listado_a = svc_a.listar_movimientos({})
    listado_b = svc_b.listar_movimientos({})

    assert len(listado_a["data"]) == 1
    assert listado_a["data"][0]["observacion"] == "tenant A"
    assert len(listado_b["data"]) == 1
    assert listado_b["data"][0]["observacion"] == "tenant B"
    assert svc_a.resumen({})["totales"] == {"ingreso": 120.0}

    svc_a.eliminar_movimiento(mov_a.id)

    assert svc_a.listar_movimientos({})["data"] == []
    assert db.session.execute(select(CajaMovimiento).where(CajaMovimiento.clinica_id == 1, CajaMovimiento.id == mov_a.id)).scalar_one_or_none().is_active is False
    assert len(svc_b.listar_movimientos({})["data"]) == 1


def test_caja_service_abona_deudas_solo_de_su_clinica(app_context):
    paciente_a = Paciente(clinica_id=1, nombre="Paciente deuda A")
    paciente_b = Paciente(clinica_id=2, nombre="Paciente deuda B")
    comp_a = Comprobante(clinica_id=1, paciente_id=1, total=100, total_bruto=100)
    comp_b = Comprobante(clinica_id=2, paciente_id=2, total=80, total_bruto=80)
    db.session.add_all([paciente_a, paciente_b])
    db.session.flush()
    comp_a.paciente_id = paciente_a.id
    comp_b.paciente_id = paciente_b.id
    db.session.add_all([comp_a, comp_b])
    db.session.flush()
    deuda_a = DeudaPaciente(
        clinica_id=1,
        paciente_id=paciente_a.id,
        comprobante_id=comp_a.id,
        total=100,
        pagado=0,
        saldo=100,
        estado="pendiente",
    )
    deuda_b = DeudaPaciente(
        clinica_id=2,
        paciente_id=paciente_b.id,
        comprobante_id=comp_b.id,
        total=80,
        pagado=0,
        saldo=80,
        estado="pendiente",
    )
    db.session.add_all([deuda_a, deuda_b])
    db.session.commit()

    svc_a = CajaService(1)
    result = svc_a.abonar_deudas(
        {
            "paciente_id": paciente_a.id,
            "monto": "30",
            "metodo": MetodoPago.EFECTIVO.value,
            "nota": "primer pago",
        }
    )

    assert result == {"ok": True, "abonado": 30.0, "saldo": 70.0}
    assert svc_a.deudas_por_paciente(paciente_a.id)["saldo_total"] == 70.0
    assert db.session.execute(select(func.count()).select_from(CajaMovimiento).where(CajaMovimiento.clinica_id == 1, CajaMovimiento.paciente_id == paciente_a.id)).scalar() == 1
    assert db.session.execute(select(DeudaPaciente).where(DeudaPaciente.clinica_id == 2, DeudaPaciente.paciente_id == paciente_b.id)).scalar_one_or_none().saldo == 80

    with pytest.raises(NotFoundError):
        svc_a.abonar_deudas({"paciente_id": paciente_b.id, "monto": "10"})


def test_inventario_service_scopes_sku_and_kardex_by_clinica(app_context):
    svc_a = InventarioService(1)
    svc_b = InventarioService(2)

    producto_a = svc_a.crear_producto({"sku": "SKU-1", "nombre": "Producto A"})
    producto_b = svc_b.crear_producto({"sku": "SKU-1", "nombre": "Producto B"})

    assert producto_a.id != producto_b.id
    assert svc_a.obtener_por_sku("SKU-1").id == producto_a.id
    assert svc_b.obtener_por_sku("SKU-1").id == producto_b.id

    svc_a.crear_movimientos_lote(
        [{"producto_id": producto_a.id, "tipo": "INGRESO", "cantidad": "5", "motivo": "seed"}]
    )

    assert svc_a.kardex(producto_a.id)["total"] == 1

    with pytest.raises(NotFoundError):
        svc_b.kardex(producto_a.id)


def test_inventario_service_scopes_price_history_by_clinica(app_context):
    svc_a = InventarioService(1)
    svc_b = InventarioService(2)

    producto_a = svc_a.crear_producto({"sku": "PRICE-1", "nombre": "Producto A", "precio_venta": "25.50"})
    svc_a.actualizar_producto(producto_a.id, {"precio_venta": "30.00", "motivo": "ajuste"})

    historial = svc_a.listar_precios_hist(producto_a.id, tipo="venta")

    assert historial["total"] == 2
    assert historial["data"][0]["valor"] == 30.0

    with pytest.raises(NotFoundError):
        svc_b.listar_precios_hist(producto_a.id, tipo="venta")


def test_inventario_service_creates_purchase_with_tenant_stock_and_provider(app_context):
    svc_a = InventarioService(1)
    svc_b = InventarioService(2)

    producto_a = svc_a.crear_producto({"sku": "MED-1", "nombre": "Medicamento A"})
    producto_b = svc_b.crear_producto({"sku": "MED-2", "nombre": "Medicamento B"})

    result = svc_a.crear_compra(
        {
            "proveedor_nombre": "Proveedor A",
            "tipo_doc": "factura",
            "numero": "F001-1",
            "items": [
                {
                    "producto_id": producto_a.id,
                    "cantidad": "3",
                    "costo_unitario": "12.50",
                }
            ],
        }
    )

    compra = svc_a.fetch_compra(result["id"])
    proveedor = db.session.execute(select(Proveedor).where(Proveedor.clinica_id == 1, Proveedor.nombre == "Proveedor A")).scalar_one_or_none()

    assert result["total"] == 37.5
    assert compra["proveedor"]["nombre"] == "Proveedor A"
    assert proveedor is not None
    assert float(producto_a.stock_actual) == 3
    assert float(producto_a.precio_costo) == 12.5
    assert db.session.execute(select(func.count(MovimientoStock.id)).where(MovimientoStock.clinica_id == 1, MovimientoStock.producto_id == producto_a.id)).scalar() == 1

    movimientos = svc_a.listar_movimientos()
    assert movimientos["total"] == 1
    assert movimientos["data"][0]["producto_label"] == "Proveedor A"
    assert movimientos["data"][0]["monto"] == 37.5

    detalle = svc_a.detalle_movimiento(movimientos["data"][0]["id"])
    assert detalle["compra_id"] == result["id"]
    assert detalle["grupo"]["total"] == 37.5

    with pytest.raises(NotFoundError):
        svc_a.crear_compra(
            {
                "tipo_doc": "boleta",
                "items": [
                    {
                        "producto_id": producto_b.id,
                        "cantidad": "1",
                        "costo_unitario": "9.00",
                    }
                ],
            }
        )
