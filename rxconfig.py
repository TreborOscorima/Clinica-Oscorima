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
    # Meta tags para PWA y mobile
    head_components=[
        rx.el.meta(name="viewport",         content="width=device-width, initial-scale=1"),
        rx.el.meta(name="theme-color",      content="#0284c7"),
        rx.el.meta(name="mobile-web-app-capable", content="yes"),
        rx.el.meta(name="apple-mobile-web-app-capable", content="yes"),
        rx.el.meta(name="apple-mobile-web-app-status-bar-style", content="default"),
        rx.el.meta(name="apple-mobile-web-app-title", content="WaykiSAC"),
        rx.el.link(rel="manifest", href="/manifest.json"),
    ],
)
