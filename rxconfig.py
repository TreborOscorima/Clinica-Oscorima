import reflex as rx
from reflex_base.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="clinica_app",
    plugins=[
        rx.plugins.TailwindV4Plugin(),
    ],
    disable_plugins=[SitemapPlugin],
    # Meta tags para PWA y mobile
    head_components=[
        rx.el.meta(name="viewport",         content="width=device-width, initial-scale=1, maximum-scale=1"),
        rx.el.meta(name="theme-color",      content="#0284c7"),
        rx.el.meta(name="mobile-web-app-capable", content="yes"),
        rx.el.meta(name="apple-mobile-web-app-capable", content="yes"),
        rx.el.meta(name="apple-mobile-web-app-status-bar-style", content="default"),
        rx.el.meta(name="apple-mobile-web-app-title", content="WaykiSAC"),
        rx.el.link(rel="manifest", href="/manifest.json"),
    ],
)
