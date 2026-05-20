from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field

from models.caja import (
    CajaMovimiento,
    Comprobante,
    CierreCaja,
    ComprobanteItem,
    DeudaPaciente,
)


class CajaMovimientoSchema(SQLAlchemySchema):
    class Meta:
        model = CajaMovimiento
        load_instance = True

    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    fecha = auto_field()
    tipo = auto_field()
    monto = auto_field()
    metodo_pago = auto_field()
    paciente_id = auto_field()
    profesional_id = auto_field()
    servicio_id = auto_field()
    comprobante_id = auto_field()
    observacion = auto_field()
    turno_id = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)


class ComprobanteSchema(SQLAlchemySchema):
    class Meta:
        model = Comprobante
        load_instance = True

    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    tipo = auto_field()
    numero = auto_field()
    fecha = auto_field()
    paciente_id = auto_field()
    # Totales
    total = auto_field()              # neto
    total_bruto = auto_field()
    descuento_global = auto_field()
    # Otros
    forma_pago = auto_field()
    observacion = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)


class CierreCajaSchema(SQLAlchemySchema):
    class Meta:
        model = CierreCaja
        load_instance = True

    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    fecha = auto_field()
    total_ingresos = auto_field()
    total_egresos = auto_field()
    saldo = auto_field()
    usuario_id = auto_field()
    creado_en = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)


class ComprobanteItemSchema(SQLAlchemySchema):
    class Meta:
        model = ComprobanteItem
        load_instance = True

    id = auto_field(dump_only=True)
    comprobante_id = auto_field()
    tipo = auto_field()
    ref_id = auto_field()
    nombre = auto_field()
    cantidad = auto_field()
    precio_unit = auto_field()
    subtotal = auto_field()


class DeudaPacienteSchema(SQLAlchemySchema):
    class Meta:
        model = DeudaPaciente
        load_instance = True

    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    paciente_id = auto_field()
    comprobante_id = auto_field()
    total = auto_field()
    pagado = auto_field()
    saldo = auto_field()
    estado = auto_field()
    is_active = auto_field(dump_only=True)
    deleted_at = auto_field(dump_only=True)
    creado_en = auto_field()
    actualizado_en = auto_field()
