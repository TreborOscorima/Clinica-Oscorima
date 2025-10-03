from marshmallow import Schema, fields, EXCLUDE

class HistorialItemSchema(Schema):
    class Meta:
        ordered = True
        unknown = EXCLUDE

    turno_id = fields.Int(required=True)
    fecha = fields.String(required=True)
    hora = fields.String(required=True)
    servicio = fields.String(required=True)
    profesional = fields.String(allow_none=True)
    detalle = fields.String(allow_none=True)

class HistorialResponseSchema(Schema):
    class Meta:
        ordered = True
        unknown = EXCLUDE

    paciente_id = fields.Int(required=True)
    paciente_nombre = fields.String()
    total = fields.Int()
    historial = fields.List(fields.Nested(HistorialItemSchema))
