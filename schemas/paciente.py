# schemas/paciente.py
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow import EXCLUDE, fields, pre_load, validate
from extensions import db
from models.paciente import Paciente  # ← import correcto del modelo

class PacienteSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Paciente
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
        ordered = True

    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    nombre = auto_field(required=True)
    documento = auto_field()
    direccion = auto_field()
    email = fields.Email(allow_none=True) 
    telefono = auto_field()
    fecha_nacimiento = fields.Date(allow_none=True)  # si querés forzar formato: fields.Date(format="%Y-%m-%d")
    contacto_emergencia = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    edad = fields.Integer(dump_only=True)

    @pre_load
    def compat_fields(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        # dni -> documento
        if "dni" in data and "documento" not in data:
            data["documento"] = data.get("dni")
        # nombres + apellidos -> nombre (si no viene 'nombre' directo)
        if "nombre" not in data:
            n = (data.get("nombres") or "").strip()
            a = (data.get("apellidos") or "").strip()
            if n or a:
                data["nombre"] = (n + " " + a).strip()
        return data
