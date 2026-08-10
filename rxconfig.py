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
        # Reflex 0.9.x compila los componentes/páginas compartidas a
        # `.web/app_components/**`, dir que NO entra en el content-glob por
        # defecto (`./app/**`, `./utils/**`). Con `@config`, Tailwind v4 usa
        # ese content explícito y NO auto-detecta, así que las clases usadas
        # solo en app_components (p. ej. `lg:hidden`) no se generan en el CSS.
        # Se pasa `content` explícito incluyendo app_components (y components).
        rx.plugins.TailwindV4Plugin(
            config={
                "plugins": ["@tailwindcss/typography@0.5.20"],
                "content": [
                    "./app/**/*.{js,ts,jsx,tsx}",
                    "./app_components/**/*.{js,ts,jsx,tsx}",
                    "./components/**/*.{js,ts,jsx,tsx}",
                    "./utils/**/*.{js,ts,jsx,tsx}",
                ],
            }
        ),
    ],
    disable_plugins=[SitemapPlugin],
    telemetry_enabled=not IS_PROD,
    show_built_with_reflex=False,
    # Nota: los meta/links de branding y PWA se inyectan vía
    # rx.App(head_components=[...]) en clinica_app.py (rx.Config no los honra).
)
