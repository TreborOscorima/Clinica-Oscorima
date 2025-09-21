# models/servicio_insumo.py
from sqlalchemy import UniqueConstraint, ForeignKey
from extensions import db

class ServicioInsumo(db.Model):
    __tablename__ = "servicio_insumos"
    id = db.Column(db.Integer, primary_key=True)
    servicio_id = db.Column(db.Integer, ForeignKey("servicios.id"), nullable=False, index=True)
    producto_id = db.Column(db.Integer, ForeignKey("inv_productos.id"), nullable=False, index=True)
    cantidad_por_sesion = db.Column(db.Numeric(12,3), nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("servicio_id", "producto_id", name="uq_servicio_producto"),
    )
