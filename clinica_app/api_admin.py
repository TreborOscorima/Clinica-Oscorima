"""API admin para el panel Owner de TUWAYKI (integración HTTP).

Espejo del contrato de TUWAYKIFOOD (`/api/admin/*`). El Sistema de Ventas
gestiona las clínicas por HTTP — sin base de datos compartida. Todas las rutas
exigen el header `X-Admin-Secret` == LIFE_ADMIN_API_SECRET.

Cada clínica (fila de `clinicas`) es una "company" para el panel Owner.
"""
from __future__ import annotations

import hmac
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from clinica_app.config import LIFE_ADMIN_API_SECRET
from clinica_app.database import get_async_session
from clinica_app.models.clinica import Clinica
from clinica_app.models.user import RoleEnum, User
from clinica_app.services.planes import PLANES_VALIDOS, plan_label

logger = logging.getLogger(__name__)


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _require_admin_secret(request: Request) -> JSONResponse | None:
    expected = (LIFE_ADMIN_API_SECRET or "").strip()
    provided = request.headers.get("X-Admin-Secret", "")
    if not expected or not hmac.compare_digest(provided, expected):
        return JSONResponse({"error": "No autorizado."}, status_code=401)
    return None


def _clinica_admin_dict(c: Clinica, admin_email: str = "") -> dict:
    return {
        "id": c.id,
        "name": c.nombre,
        "slug": c.slug,
        "admin_email": admin_email or (c.email or ""),
        "is_active": bool(c.licencia_activa),
        "plan": c.plan or "trial",
        "trial_ends_at": c.trial_ends_at.strftime("%Y-%m-%d") if c.trial_ends_at else None,
        "plan_expires_at": c.plan_expires_at.strftime("%Y-%m-%d") if c.plan_expires_at else None,
        "created_at": c.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if c.created_at else None,
    }


async def _admin_emails_por_clinica(session, clinica_ids: list[int]) -> dict[int, str]:
    """Email del primer usuario ADMIN de cada clínica (para la columna del panel)."""
    if not clinica_ids:
        return {}
    rows = (await session.execute(
        select(User.clinica_id, User.email)
        .where(User.clinica_id.in_(clinica_ids), User.rol == RoleEnum.ADMIN)
        .order_by(User.id.asc())
    )).all()
    out: dict[int, str] = {}
    for clinica_id, email in rows:
        out.setdefault(clinica_id, email)
    return out


async def _admin_list_companies(request: Request) -> JSONResponse:
    err = _require_admin_secret(request)
    if err is not None:
        return err
    search = (request.query_params.get("search") or "").strip()
    try:
        page = max(1, int(request.query_params.get("page", "1")))
        per_page = max(1, min(100, int(request.query_params.get("per_page", "15"))))
    except ValueError:
        page, per_page = 1, 15

    async with get_async_session() as session:
        stmt = select(Clinica).where(Clinica.is_active.is_(True))
        if search:
            stmt = stmt.where(Clinica.nombre.ilike(f"%{search}%"))
        total = (await session.execute(
            select(func.count()).select_from(stmt.subquery())
        )).scalar_one()
        page_items = (await session.execute(
            stmt.order_by(Clinica.id.desc()).offset((page - 1) * per_page).limit(per_page)
        )).scalars().all()
        emails = await _admin_emails_por_clinica(session, [c.id for c in page_items])
        items = [_clinica_admin_dict(c, emails.get(c.id, "")) for c in page_items]

    return JSONResponse({"items": items, "total": total}, status_code=200)


async def _admin_company_detail(request: Request) -> JSONResponse:
    err = _require_admin_secret(request)
    if err is not None:
        return err
    try:
        company_id = int(request.path_params["id"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "id inválido."}, status_code=400)

    async with get_async_session() as session:
        clinica = await session.get(Clinica, company_id)
        if clinica is None:
            return JSONResponse({"error": "No encontrado."}, status_code=404)
        emails = await _admin_emails_por_clinica(session, [company_id])

    return JSONResponse(_clinica_admin_dict(clinica, emails.get(company_id, "")), status_code=200)


async def _admin_set_active(request: Request, active: bool) -> JSONResponse:
    err = _require_admin_secret(request)
    if err is not None:
        return err
    try:
        company_id = int(request.path_params["id"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "id inválido."}, status_code=400)

    async with get_async_session() as session:
        clinica = await session.get(Clinica, company_id)
        if clinica is None:
            return JSONResponse({"error": "No encontrado."}, status_code=404)
        clinica.licencia_activa = active
        session.add(clinica)
        await session.commit()
        result = {"id": clinica.id, "is_active": clinica.licencia_activa}

    return JSONResponse(result, status_code=200)


async def _admin_activate(request: Request) -> JSONResponse:
    return await _admin_set_active(request, True)


async def _admin_suspend(request: Request) -> JSONResponse:
    return await _admin_set_active(request, False)


async def _admin_extend_trial(request: Request) -> JSONResponse:
    err = _require_admin_secret(request)
    if err is not None:
        return err
    try:
        company_id = int(request.path_params["id"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "id inválido."}, status_code=400)
    try:
        body = await request.json()
        extra_days = int(body.get("extra_days"))
    except Exception:
        return JSONResponse({"error": "extra_days inválido."}, status_code=400)
    if extra_days < 1 or extra_days > 365:
        return JSONResponse({"error": "extra_days debe estar entre 1 y 365."}, status_code=400)

    async with get_async_session() as session:
        clinica = await session.get(Clinica, company_id)
        if clinica is None:
            return JSONResponse({"error": "No encontrado."}, status_code=404)
        now = _now_naive()
        base = clinica.trial_ends_at if clinica.trial_ends_at and clinica.trial_ends_at > now else now
        clinica.trial_ends_at = base + timedelta(days=extra_days)
        clinica.licencia_activa = True
        session.add(clinica)
        await session.commit()
        result = {"id": clinica.id, "trial_ends_at": clinica.trial_ends_at.strftime("%Y-%m-%d")}

    return JSONResponse(result, status_code=200)


async def _admin_set_plan(request: Request) -> JSONResponse:
    err = _require_admin_secret(request)
    if err is not None:
        return err
    try:
        company_id = int(request.path_params["id"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "id inválido."}, status_code=400)
    try:
        body = await request.json()
        plan = (body.get("plan") or "").strip().lower()
        expires_days = body.get("expires_days")
    except Exception:
        return JSONResponse({"error": "JSON inválido."}, status_code=400)

    if plan not in PLANES_VALIDOS:
        return JSONResponse(
            {"error": f"Plan inválido. Opciones: {', '.join(sorted(PLANES_VALIDOS))}"},
            status_code=400,
        )

    async with get_async_session() as session:
        clinica = await session.get(Clinica, company_id)
        if clinica is None:
            return JSONResponse({"error": "No encontrado."}, status_code=404)
        now = _now_naive()
        clinica.plan = plan
        if expires_days is not None:
            try:
                days = int(expires_days)
                if days < 1 or days > 3650:
                    return JSONResponse({"error": "expires_days debe estar entre 1 y 3650."}, status_code=400)
                clinica.plan_expires_at = now + timedelta(days=days)
            except (TypeError, ValueError):
                return JSONResponse({"error": "expires_days debe ser un entero."}, status_code=400)
        else:
            clinica.plan_expires_at = None
        clinica.licencia_activa = True
        session.add(clinica)
        await session.commit()
        result = {
            "id": clinica.id,
            "plan": clinica.plan,
            "plan_label": plan_label(clinica.plan),
            "plan_expires_at": clinica.plan_expires_at.strftime("%Y-%m-%d") if clinica.plan_expires_at else None,
        }

    return JSONResponse(result, status_code=200)


_ROLE_LABELS = {
    RoleEnum.ADMIN: "Administración",
    RoleEnum.RECEP: "Recepción",
    RoleEnum.PROF: "Profesional",
    RoleEnum.CONT: "Contador",
}


def _role_label(rol) -> str:
    return _ROLE_LABELS.get(rol, "Usuario")


async def _admin_list_users(request: Request) -> JSONResponse:
    """Usuarios de la clínica cuya contraseña puede resetear el Owner Admin.

    A diferencia de Food (una sola cuenta de dueño), Life es multi-usuario: se
    devuelven todas las cuentas de la clínica (admin primero) para poder elegir
    cuál resetear desde el panel.
    """
    err = _require_admin_secret(request)
    if err is not None:
        return err
    try:
        company_id = int(request.path_params["id"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "id inválido."}, status_code=400)

    async with get_async_session() as session:
        clinica = await session.get(Clinica, company_id)
        if clinica is None:
            return JSONResponse({"error": "No encontrado."}, status_code=404)
        rows = (await session.execute(
            select(User)
            .where(User.clinica_id == company_id)
            .order_by(User.id.asc())
        )).scalars().all()
        # Admin primero, después por id.
        rows.sort(key=lambda u: (u.rol != RoleEnum.ADMIN, u.id or 0))
        items = [
            {
                "id": u.id,
                "username": u.email,
                "full_name": u.nombre,
                "role": _role_label(u.rol),
            }
            for u in rows
        ]

    return JSONResponse({"items": items}, status_code=200)


def _generar_password_temporal() -> str:
    """Contraseña temporal legible para entregar al usuario una sola vez."""
    import secrets
    return "Life-" + secrets.token_urlsafe(6)


async def _admin_reset_password(request: Request) -> JSONResponse:
    """Resetea la contraseña de un usuario de la clínica.

    Genera una temporal, la guarda hasheada (bcrypt vía User.set_password) y la
    devuelve UNA vez. El body puede traer `user_id` para elegir la cuenta; si no,
    se resetea el primer ADMIN de la clínica. Queda registrado en el log (sin el
    valor). El panel Owner guarda su propia auditoría de la acción.
    """
    err = _require_admin_secret(request)
    if err is not None:
        return err
    try:
        company_id = int(request.path_params["id"])
    except (KeyError, ValueError):
        return JSONResponse({"error": "id inválido."}, status_code=400)
    try:
        body = await request.json()
    except Exception:
        body = {}
    actor = (body.get("actor") or body.get("actor_email") or "owner-admin").strip() or "owner-admin"
    raw_user_id = body.get("user_id")

    temp_password = _generar_password_temporal()
    async with get_async_session() as session:
        clinica = await session.get(Clinica, company_id)
        if clinica is None:
            return JSONResponse({"error": "No encontrado."}, status_code=404)

        user = None
        if raw_user_id not in (None, "", 0, "0"):
            try:
                user = await session.get(User, int(raw_user_id))
            except (TypeError, ValueError):
                user = None
            # No permitir resetear un usuario de otra clínica.
            if user is not None and user.clinica_id != company_id:
                user = None
        if user is None:
            user = (await session.execute(
                select(User)
                .where(User.clinica_id == company_id, User.rol == RoleEnum.ADMIN)
                .order_by(User.id.asc())
            )).scalars().first()
        if user is None:
            return JSONResponse(
                {"error": "La clínica no tiene una cuenta administrable."},
                status_code=409,
            )

        user.set_password(temp_password)
        session.add(user)
        await session.commit()
        username = user.email
        logger.warning(
            "Reset de contraseña Owner Admin: clinica=%s user_id=%s email=%s actor=%s",
            company_id, user.id, username, actor,
        )

    return JSONResponse(
        {"temp_password": temp_password, "username": username}, status_code=200
    )


admin_routes = [
    Route("/api/admin/companies", _admin_list_companies, methods=["GET"]),
    Route("/api/admin/companies/{id}", _admin_company_detail, methods=["GET"]),
    Route("/api/admin/companies/{id}/activate", _admin_activate, methods=["POST"]),
    Route("/api/admin/companies/{id}/suspend", _admin_suspend, methods=["POST"]),
    Route("/api/admin/companies/{id}/extend-trial", _admin_extend_trial, methods=["POST"]),
    Route("/api/admin/companies/{id}/set-plan", _admin_set_plan, methods=["POST"]),
    Route("/api/admin/companies/{id}/users", _admin_list_users, methods=["GET"]),
    Route("/api/admin/companies/{id}/reset-password", _admin_reset_password, methods=["POST"]),
]
