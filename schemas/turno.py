# schemas/turno.py
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow import EXCLUDE, fields, validates_schema, ValidationError
from extensions import db
from models.turno import Turno, EstadoTurno
from models.turno_servicio import TurnoServicio
from models.servicio import Servicio

class TurnoServicioSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TurnoServicio
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
        ordered = True

    id = auto_field(dump_only=True)
    servicio_id = auto_field(required=True)
    precio = auto_field()            # puede venir null -> se usa precio del Servicio al atender
    cantidad = auto_field()
    descuento = auto_field()
    nota = auto_field()

    # legibles
    servicio_nombre = fields.Function(lambda o: getattr(o.servicio, "nombre", None))
    servicio_precio_lista = fields.Function(lambda o: getattr(o.servicio, "precio", None))

class TurnoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Turno
        load_instance = True
        sqla_session = db.session
        unknown = EXCLUDE
        ordered = True

    id = auto_field(dump_only=True)
    paciente_id = auto_field(required=True)
    profesional_id = auto_field()
    # legacy: permitir todavía servicio_id, pero no es requerido si vienen items
    servicio_id = auto_field()
    fecha_hora = auto_field(required=True)
    created_by_id = auto_field(dump_only=True)

    # Enum como string
    estado = fields.Function(
        serialize=lambda obj: obj.estado.value if obj.estado else None,
        deserialize=lambda v: EstadoTurno(v) if v else None
    )
    motivo_cancelacion = auto_field()

    # NUEVO: items múltiples del turno
    items = fields.List(fields.Nested(TurnoServicioSchema), required=False)

    # legibles para las grillas
    paciente_nombre = fields.Function(lambda o: getattr(o.paciente, "nombre", None))
    paciente_documento = fields.Function(lambda o: getattr(o.paciente, "documento", None))
    profesional_nombre = fields.Function(
        lambda o: f"{getattr(o.profesional,'nombres','') or ''} {getattr(o.profesional,'apellidos','') or ''}".strip()
        if getattr(o, 'profesional', None) else None
    )
    profesional_documento = fields.Function(lambda o: getattr(o.profesional, "dni", None))
    servicio_nombre = fields.Function(lambda o: getattr(o.servicio, "nombre", None))
    servicio_precio = fields.Function(lambda o: getattr(o.servicio, "precio", None))
    servicio_duracion = fields.Function(lambda o: getattr(o.servicio, "duracion_min", None))
    usuario_registro = fields.Function(lambda o: getattr(o.created_by, "nombre", None))

    @validates_schema
    def _validar_items_o_servicio(self, data, **kwargs):
        """
        Compat: aceptamos o bien items (múltiples servicios), o bien servicio_id legacy.
        Al menos uno debe venir.
        """
        items = data.get("items") or []
        servicio_id = data.get("servicio_id")
        if not items and not servicio_id:
            raise ValidationError("Debe indicar al menos un servicio (items) o servicio_id legacy.", field_name="items")
        # validaciones mínimas de items
        for it in items:
            if it.cantidad is not None:
                try:
                    # asegurar positivo
                    if float(it.cantidad) <= 0:
                        raise ValidationError("La cantidad debe ser > 0", field_name="items")
                except Exception:
                    raise ValidationError("Cantidad inválida", field_name="items")
            if it.descuento is not None:
                try:
                    float(it.descuento)
                except Exception:
                    raise ValidationError("Descuento inválido", field_name="items")
