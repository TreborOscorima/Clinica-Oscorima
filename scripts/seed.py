"""
Script de seed para poblar datos de prueba.
Uso: python scripts/seed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Asegura que el paquete principal sea importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine, select

from clinica_app.config import settings
from clinica_app.models import *  # noqa: F401,F403 – registra todos los modelos


def _engine():
    url = (
        f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
        f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"
        "?charset=utf8mb4"
    )
    return create_engine(url, echo=False)


def seed():
    engine = _engine()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        # ── 1. Clínica ─────────────────────────────────────────────────────────
        from clinica_app.models.clinica import Clinica

        clinica = s.exec(select(Clinica).where(Clinica.slug == "oscorima")).first()
        if clinica is None:
            clinica = Clinica(
                nombre="Clínica Oscorima",
                slug="oscorima",
                razon_social="Oscorima S.A.C.",
                documento_fiscal="20123456789",
                email="admin@oscorima.com",
                telefono="+51 999 000 111",
            )
            s.add(clinica)
            s.flush()
            print(f"[+] Clínica creada  id={clinica.id}")
        else:
            print(f"[=] Clínica existente id={clinica.id}")

        cid = clinica.id

        # ── 2. Usuario admin ───────────────────────────────────────────────────
        from clinica_app.models.user import RoleEnum, User

        admin = s.exec(select(User).where(User.email == "admin@wayki.com")).first()
        if admin is None:
            admin = User(
                clinica_id=cid,
                nombre="Administrador",
                email="admin@wayki.com",
                rol=RoleEnum.ADMIN,
            )
            admin.set_password("admin123")
            s.add(admin)
            s.flush()
            print(f"[+] Admin creado  id={admin.id}  pass=admin123")
        else:
            print(f"[=] Admin existente id={admin.id}")

        # ── 3. Profesionales ───────────────────────────────────────────────────
        from clinica_app.models.profesional import Profesional

        profs_data = [
            {"nombres": "María", "apellidos": "González", "especialidad": "Dermatología estética"},
            {"nombres": "Carlos", "apellidos": "Romero",  "especialidad": "Nutrición"},
            {"nombres": "Lucía",  "apellidos": "Vargas",  "especialidad": "Masoterapia"},
        ]
        profs: list[Profesional] = []
        for pd in profs_data:
            p = s.exec(
                select(Profesional).where(
                    Profesional.clinica_id == cid,
                    Profesional.apellidos == pd["apellidos"],
                )
            ).first()
            if p is None:
                p = Profesional(clinica_id=cid, **pd)
                s.add(p)
                s.flush()
                print(f"[+] Prof. {p.nombres} {p.apellidos}  id={p.id}")
            profs.append(p)

        # ── 4. Servicios ───────────────────────────────────────────────────────
        from clinica_app.models.servicio import Servicio

        servs_data = [
            {"nombre": "Limpieza facial profunda",  "precio": "120.00", "categoria": "Facial"},
            {"nombre": "Masaje relajante 60min",    "precio": "90.00",  "categoria": "Masajes"},
            {"nombre": "Depilación láser zona A",   "precio": "150.00", "categoria": "Depilación"},
            {"nombre": "Consulta nutricional",      "precio": "80.00",  "categoria": "Nutrición"},
            {"nombre": "Tratamiento anticelulítico","precio": "110.00", "categoria": "Corporal"},
        ]
        servs: list[Servicio] = []
        for sd in servs_data:
            sv = s.exec(
                select(Servicio).where(
                    Servicio.clinica_id == cid,
                    Servicio.nombre == sd["nombre"],
                )
            ).first()
            if sv is None:
                from decimal import Decimal
                sv = Servicio(clinica_id=cid, nombre=sd["nombre"],
                              precio=Decimal(sd["precio"]), categoria=sd["categoria"])
                s.add(sv)
                s.flush()
                print(f"[+] Servicio: {sv.nombre}  id={sv.id}")
            servs.append(sv)

        # ── 5. Productos (inventario) ──────────────────────────────────────────
        from clinica_app.models.inventario import Producto
        from decimal import Decimal

        prods_data = [
            {"nombre": "Crema hidratante 250ml", "sku": "CRH250", "precio_venta": "45.00",
             "precio_costo": "20.00", "stock_actual": "50", "stock_minimo": "10"},
            {"nombre": "Gel desinfectante 500ml","sku": "GD500",  "precio_venta": "18.00",
             "precio_costo": "8.00",  "stock_actual": "30", "stock_minimo": "5"},
            {"nombre": "Toallas desechables x50","sku": "TD50",   "precio_venta": "12.00",
             "precio_costo": "5.00",  "stock_actual": "100","stock_minimo": "20"},
        ]
        for pd in prods_data:
            pr = s.exec(
                select(Producto).where(
                    Producto.clinica_id == cid,
                    Producto.sku == pd["sku"],
                )
            ).first()
            if pr is None:
                pr = Producto(
                    clinica_id=cid,
                    nombre=pd["nombre"],
                    sku=pd["sku"],
                    precio_venta=Decimal(pd["precio_venta"]),
                    precio_costo=Decimal(pd["precio_costo"]),
                    stock_actual=Decimal(pd["stock_actual"]),
                    stock_minimo=Decimal(pd["stock_minimo"]),
                )
                s.add(pr)
                s.flush()
                print(f"[+] Producto: {pr.nombre}  id={pr.id}")

        # ── 6. Pacientes ───────────────────────────────────────────────────────
        from clinica_app.models.paciente import Paciente

        pacs_data = [
            {"nombre": "Ana Flores",      "documento": "12345678", "email": "ana@ejemplo.com",   "telefono": "987001001"},
            {"nombre": "Roberto Silva",   "documento": "23456789", "email": "rob@ejemplo.com",   "telefono": "987001002"},
            {"nombre": "Carmen Quispe",   "documento": "34567890", "email": "carmen@ejemplo.com","telefono": "987001003"},
            {"nombre": "Jorge Mamani",    "documento": "45678901", "email": "jorge@ejemplo.com", "telefono": "987001004"},
            {"nombre": "Patricia Torres", "documento": "56789012", "email": "pat@ejemplo.com",   "telefono": "987001005"},
        ]
        pacs: list[Paciente] = []
        for pd in pacs_data:
            pa = s.exec(
                select(Paciente).where(
                    Paciente.clinica_id == cid,
                    Paciente.documento == pd["documento"],
                )
            ).first()
            if pa is None:
                pa = Paciente(clinica_id=cid, **pd)
                s.add(pa)
                s.flush()
                print(f"[+] Paciente: {pa.nombre}  id={pa.id}")
            pacs.append(pa)

        # ── 7. Turnos (hoy y mañana) ───────────────────────────────────────────
        from clinica_app.models.turno import EstadoTurno, Turno

        ahora = datetime.now(timezone.utc).replace(tzinfo=None)
        turnos_data = [
            {"paciente": pacs[0], "prof": profs[0], "serv": servs[0],
             "dt": ahora.replace(hour=9,  minute=0, second=0), "estado": EstadoTurno.PENDIENTE},
            {"paciente": pacs[1], "prof": profs[1], "serv": servs[3],
             "dt": ahora.replace(hour=10, minute=30,second=0), "estado": EstadoTurno.CONFIRMADO},
            {"paciente": pacs[2], "prof": profs[2], "serv": servs[1],
             "dt": ahora.replace(hour=11, minute=0, second=0), "estado": EstadoTurno.ATENDIDO},
            {"paciente": pacs[3], "prof": profs[0], "serv": servs[2],
             "dt": (ahora + timedelta(days=1)).replace(hour=9, minute=0, second=0),
             "estado": EstadoTurno.PENDIENTE},
        ]
        for td in turnos_data:
            existing = s.exec(
                select(Turno).where(
                    Turno.clinica_id == cid,
                    Turno.paciente_id == td["paciente"].id,
                    Turno.fecha_hora == td["dt"],
                )
            ).first()
            if existing is None:
                t = Turno(
                    clinica_id=cid,
                    paciente_id=td["paciente"].id,
                    profesional_id=td["prof"].id,
                    servicio_id=td["serv"].id,
                    fecha_hora=td["dt"],
                    estado=td["estado"],
                    created_by_id=admin.id,
                )
                s.add(t)
                s.flush()
                print(f"[+] Turno: {td['paciente'].nombre} @ {td['dt'].strftime('%d/%m %H:%M')}  id={t.id}")

        s.commit()
        print("\n✓ Seed completado")
        print(f"  URL:       http://localhost:3000")
        print(f"  Login:     admin@wayki.com / admin123")
        print(f"  Clinica:   {clinica.nombre} (id={cid})")


if __name__ == "__main__":
    seed()
