from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field

from models.user import User, PermisoRol


class UserSchema(SQLAlchemySchema):
    class Meta:
        model = User
        load_instance = True

    id = auto_field(dump_only=True)
    clinica_id = auto_field(load_only=True)
    email = auto_field()
    nombre = auto_field()
    rol = auto_field()
    is_active = auto_field()
    deleted_at = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)


class PermisoRolSchema(SQLAlchemySchema):
    class Meta:
        model = PermisoRol
        load_instance = True

    id = auto_field(dump_only=True)
    role = auto_field()
    module = auto_field()
    can_read = auto_field()
    can_write = auto_field()
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
