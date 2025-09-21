# schemas/servicio.py
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow import EXCLUDE
from extensions import db
from models.servicio import Servicio

class ServicioSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Servicio
        load_instance = True
        sqla_session = db.session    # ← clave
        unknown = EXCLUDE
        ordered = True

    id = auto_field(dump_only=True)
    nombre = auto_field(required=True)
    descripcion = auto_field()
    precio = auto_field()
    duracion_min = auto_field()
    protocolo = auto_field()
    # si vas a usar la tabla servicio_insumos, este campo 'insumos' de Servicio
    # puede quedar como texto auxiliar o lo podés remover del schema
