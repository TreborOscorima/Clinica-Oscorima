import reflex as rx

config = rx.Config(
    app_name="clinica_app",
    # Reflex gestiona su propio servidor; MySQL se conecta vía SQLModel en database.py
    tailwind={
        "theme": {
            "extend": {
                "colors": {
                    "brand": {"50": "#f0f9ff", "500": "#0ea5e9", "600": "#0284c7", "700": "#0369a1"}
                }
            }
        },
        "plugins": [],
    },
)
