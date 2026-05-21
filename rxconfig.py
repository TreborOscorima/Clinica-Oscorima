import reflex as rx
from reflex_base.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="clinica_app",
    plugins=[
        rx.plugins.TailwindV4Plugin(),
    ],
    disable_plugins=[SitemapPlugin],
)
