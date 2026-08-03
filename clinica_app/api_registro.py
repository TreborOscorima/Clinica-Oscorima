"""Autoregistro público de clínicas — habilita el modelo multi-empresa.

POST /api/registro crea una clínica nueva (empresa) con su usuario admin y su
sede principal, en período de prueba. Mismo patrón que TUWAYKIFOOD, reusando
los servicios compartidos de tuwayki-core (validación, sanitización y rate
limiting). La landing de TUWAYKIAPP puede llamar este endpoint servidor-a-
servidor, igual que hace con Food.
"""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from tuwayki_core.utils.logger import get_logger
from tuwayki_core.utils.rate_limit import (
    clear_login_attempts,
    is_rate_limited,
    record_failed_attempt,
    remaining_lockout_time,
)
from tuwayki_core.utils.sanitization import sanitize_name, sanitize_phone
from tuwayki_core.utils.validators import validate_email, validate_password

from clinica_app.database import get_async_session
from clinica_app.models.clinica import Clinica
from clinica_app.models.sede import Sede
from clinica_app.models.user import RoleEnum, User
from clinica_app.services.planes import PLAN_TRIAL

logger = get_logger(__name__)


def _slugify_registro(texto: str) -> str:
    texto = (texto or "").lower().strip()
    texto = re.sub(r"[áàä]", "a", texto)
    texto = re.sub(r"[éèë]", "e", texto)
    texto = re.sub(r"[íìï]", "i", texto)
    texto = re.sub(r"[óòö]", "o", texto)
    texto = re.sub(r"[úùü]", "u", texto)
    texto = re.sub(r"[ñ]", "n", texto)
    texto = re.sub(r"[^a-z0-9\s-]", "", texto)
    texto = re.sub(r"[\s]+", "-", texto)
    texto = re.sub(r"-+", "-", texto)
    return texto[:80].strip("-") or "clinica"


def _trial_days() -> int:
    raw_value = (os.getenv("LIFE_TRIAL_DAYS") or "15").strip()
    try:
        days = int(raw_value)
    except (TypeError, ValueError):
        days = 15
    return max(1, min(days, 365))


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def _registro(request: Request) -> JSONResponse:
    """Crea Clinica + admin + sede principal. La matriz de permisos por rol se
    auto-seedea en el primer login (services/permisos.py)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON inválido."}, status_code=400)

    company_name = sanitize_name(body.get("company_name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    phone = sanitize_phone(body.get("phone") or "").strip()
    password = body.get("password") or ""
    confirm_password = body.get("confirm_password") or ""
    client_ip = _client_ip(request)

    if is_rate_limited(email, ip_address=client_ip):
        remaining = remaining_lockout_time(email, ip_address=client_ip)
        return JSONResponse(
            {"error": f"Demasiados intentos. Espere {remaining} minuto(s) para registrar."},
            status_code=429,
        )

    if not company_name:
        return JSONResponse({"error": "El nombre de la clínica es obligatorio."}, status_code=400)
    if not email or not validate_email(email):
        return JSONResponse({"error": "Ingrese un correo válido."}, status_code=400)
    if not phone:
        return JSONResponse({"error": "El número de contacto es obligatorio."}, status_code=400)
    if password != confirm_password:
        return JSONResponse({"error": "Las contraseñas no coinciden."}, status_code=400)

    is_valid, error = validate_password(password)
    if not is_valid:
        return JSONResponse({"error": error}, status_code=400)

    try:
        async with get_async_session() as session:
            existing = (await session.execute(
                select(User).where(User.email == email)
            )).scalars().first()
            if existing:
                record_failed_attempt(email, ip_address=client_ip)
                return JSONResponse({"error": "El correo ya está registrado."}, status_code=409)

            base_slug = _slugify_registro(company_name)
            slug = base_slug
            suffix = 2
            while (await session.execute(
                select(Clinica).where(Clinica.slug == slug)
            )).scalars().first():
                slug = f"{base_slug}-{suffix}"
                suffix += 1

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            clinica = Clinica(
                nombre=company_name,
                slug=slug,
                email=email,
                telefono=phone,
                plan=PLAN_TRIAL,
                licencia_activa=True,
                trial_ends_at=now + timedelta(days=_trial_days()),
            )
            session.add(clinica)
            await session.flush()

            sede = Sede(
                clinica_id=clinica.id,
                nombre="Sede Principal",
                telefono=phone,
                email=email,
                es_principal=True,
            )
            session.add(sede)

            admin = User(
                clinica_id=clinica.id,
                nombre=company_name,
                email=email,
                rol=RoleEnum.ADMIN,
            )
            # bcrypt es costoso — fuera del event loop, igual que en auth.
            admin.password_hash = await asyncio.to_thread(_hash_password, password)
            session.add(admin)
            await session.commit()

            company_id = clinica.id
    except Exception:
        logger.error("Error inesperado al registrar clínica.", exc_info=True)
        return JSONResponse({"error": "No se pudo completar el registro."}, status_code=500)

    clear_login_attempts(email, ip_address=client_ip)
    return JSONResponse(
        {
            "company_id": company_id,
            "slug": slug,
            "message": "Cuenta creada. Ya puedes iniciar sesión.",
        },
        status_code=201,
    )


def _hash_password(raw: str) -> str:
    import bcrypt
    return bcrypt.hashpw(raw.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


registro_routes = [
    Route("/api/registro", _registro, methods=["POST"]),
]
