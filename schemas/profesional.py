from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow import validate
from extensions import db
from models.profesional import Profesional

class ProfesionalSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Profesional
        load_instance = True
        sqla_session = db.session

    id = auto_field(dump_only=True)
    dni = auto_field(required=True, validate=validate.Length(min=4, max=40))
    nombres = auto_field(required=True, validate=validate.Length(min=1, max=120))
    apellidos = auto_field(required=True, validate=validate.Length(min=1, max=120))
    especialidad = auto_field(validate=validate.Length(max=120))
    matricula = auto_field(validate=validate.Length(max=60))
