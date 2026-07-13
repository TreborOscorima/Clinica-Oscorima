"""Token efímero firmado para proteger endpoints de descarga."""
from __future__ import annotations

import hashlib
import hmac
import time

from clinica_app.config import SECRET_KEY

_TTL = 120  # segundos


def crear_token(user_id: int, clinica_id: int) -> str:
    ts = str(int(time.time()))
    payload = f"{user_id}:{clinica_id}:{ts}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}:{sig}"


def validar_token(token: str) -> tuple[int, int] | None:
    """Retorna (user_id, clinica_id) si el token es válido, None si no."""
    if not token:
        return None
    parts = token.split(":")
    if len(parts) != 4:
        return None
    try:
        user_id, clinica_id, ts_str, sig = parts
        user_id = int(user_id)
        clinica_id = int(clinica_id)
        ts = int(ts_str)
    except (ValueError, TypeError):
        return None

    if time.time() - ts > _TTL:
        return None

    payload = f"{user_id}:{clinica_id}:{ts_str}"
    expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        return None

    return user_id, clinica_id
