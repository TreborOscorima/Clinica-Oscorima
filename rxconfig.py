from __future__ import annotations

import os

from dotenv import load_dotenv
import reflex as rx
from reflex_base.plugins.sitemap import SitemapPlugin

load_dotenv()

ENV = (os.getenv("ENV") or "dev").strip().lower()
IS_PROD = ENV in {"prod", "production"}

FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3003"))
API_URL = os.getenv("PUBLIC_API_URL")

if IS_PROD:
    for _var in ("MYSQL_PASSWORD", "AUTH_SECRET_KEY"):
        if not os.getenv(_var):
            raise RuntimeError(f"[rxconfig] Variable obligatoria en producción: {_var}")

config = rx.Config(
    app_name="clinica_app",
    frontend_port=FRONTEND_PORT,
    **({"api_url": API_URL} if API_URL else {}),
    plugins=[
        rx.plugins.TailwindV4Plugin(),
    ],
    disable_plugins=[SitemapPlugin],
    telemetry_enabled=not IS_PROD,
    show_built_with_reflex=False,
    # Nota: los meta/links de branding y PWA se inyectan vía
    # rx.App(head_components=[...]) en clinica_app.py (rx.Config no los honra).
)
