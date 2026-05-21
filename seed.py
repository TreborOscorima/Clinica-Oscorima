"""
seed.py — Setup inicial de la base de datos.

Crea todas las tablas y siembra la primera clínica + usuario admin.

Uso:
    python seed.py
    python seed.py --clinica "Mi Clínica" --email admin@miclinica.com --password mi_clave
"""
from __future__ import annotations

import argparse
import sys

from sqlmodel import SQLModel, select

# Importar todos los modelos para que SQLModel registre sus metadatos
import clinica_app.models  # noqa: F401 — side-effect: registra tablas
from clinica_app.database import _engine, get_session
from clinica_app.models.clinica import Clinica
from clinica_app.models.user import RoleEnum, User


def _crear_tablas() -> None:
    print("Creando tablas...", end=" ", flush=True)
    SQLModel.metadata.create_all(_engine)
    print("OK")


def _seed(clinica_nombre: str, slug: str, email: str, password: str, nombre_admin: str) -> None:
    with get_session() as session:
        # ── Clínica ───────────────────────────────────────────────────────────
        clinica = session.exec(select(Clinica).where(Clinica.slug == slug)).first()
        if clinica:
            print(f"Clínica '{slug}' ya existe — omitiendo.")
        else:
            clinica = Clinica(nombre=clinica_nombre, slug=slug)
            session.add(clinica)
            session.flush()
            print(f"Clínica creada: '{clinica_nombre}' (id={clinica.id})")

        # ── Usuario admin ─────────────────────────────────────────────────────
        usuario = session.exec(select(User).where(User.email == email)).first()
        if usuario:
            print(f"Usuario '{email}' ya existe — omitiendo.")
        else:
            usuario = User(
                clinica_id=clinica.id,
                nombre=nombre_admin,
                email=email,
                rol=RoleEnum.ADMIN,
            )
            usuario.set_password(password)
            session.add(usuario)
            session.flush()
            print(f"Usuario admin creado: '{email}' (id={usuario.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicializar DB y seed inicial")
    parser.add_argument("--clinica",  default="WaykiSAC Demo",  help="Nombre de la clínica")
    parser.add_argument("--slug",     default="waykisac",        help="Slug único de la clínica")
    parser.add_argument("--email",    default="admin@wayki.com", help="Email del administrador")
    parser.add_argument("--password", default="admin123",        help="Contraseña del administrador")
    parser.add_argument("--nombre",   default="Administrador",   help="Nombre del administrador")
    args = parser.parse_args()

    _crear_tablas()
    _seed(args.clinica, args.slug, args.email, args.password, args.nombre)

    print()
    print("=" * 50)
    print("Setup completo. Podés iniciar la app con:")
    print("  reflex run")
    print()
    print(f"  URL:      http://localhost:3000")
    print(f"  Email:    {args.email}")
    print(f"  Password: {args.password}")
    print("=" * 50)


if __name__ == "__main__":
    main()
