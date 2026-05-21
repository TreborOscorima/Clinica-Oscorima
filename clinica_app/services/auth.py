from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlmodel import Session

from clinica_app.models.user import User
from clinica_app.services.exceptions import ServiceError


def autenticar(session: Session, email: str, password: str) -> User:
    """
    Valida credenciales y devuelve el User.
    Siempre lanza ServiceError con mensaje genérico para prevenir user-enumeration.
    """
    user: User | None = session.exec(
        select(User).where(User.email == email.strip().lower())
    ).first()

    if not user or not user.check_password(password) or not user.is_active:
        raise ServiceError("Credenciales inválidas", 401)

    return user


def datos_usuario(user: User) -> dict[str, Any]:
    return {
        "id":         user.id,
        "nombre":     user.nombre,
        "email":      user.email,
        "rol":        user.rol.value,
        "clinica_id": user.clinica_id,
    }
