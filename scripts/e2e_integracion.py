"""E2E de integración del Sistema — corre DENTRO del contenedor tuwayki_life.

Atraviesa los flujos reales (auth → odontograma+caras+PDF → mapa estético
eval/proc/punto/foto+PDF → serving de adjuntos) contra la app viva + BD real +
endpoints HTTP, y limpia todo lo que crea (soft-delete). Objetivo: probar que
las piezas viejas y las nuevas (E8/E9) conviven sin romperse.

Uso:  docker exec tuwayki_life python /tmp/e2e_integracion.py
Salida: líneas "PASS ..." / "FAIL ..." + "RESULT ok=N fail=M".
"""
import asyncio
import urllib.request
import urllib.error

from sqlmodel import select

from clinica_app.clinica_app import _get_async_session
from clinica_app.services import odontograma as odo
from clinica_app.services import estetica_mapa as mapa
from clinica_app.services import auth
from clinica_app.services.download_token import crear_token
from clinica_app.models.paciente import Paciente
from clinica_app.models.inventario import Producto

BASE = "http://localhost:3000"
EMAIL = "admin@demo.com"
PASSWORD = "Demo1234"

_ok = 0
_fail = 0


def check(nombre, cond):
    global _ok, _fail
    if cond:
        _ok += 1
        print(f"PASS {nombre}")
    else:
        _fail += 1
        print(f"FAIL {nombre}")


def http_get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()


async def main():
    # ── 0. Salud + auth ───────────────────────────────────────────────────────
    st, _, _ = http_get(f"{BASE}/api/ping")
    check("health /api/ping 200", st == 200)

    async with _get_async_session() as s:
        user = await auth.autenticar(s, EMAIL, PASSWORD)
        check("auth autenticar admin@demo.com", user is not None and user.id > 0)
        cid = user.clinica_id
        uid = user.id

        # paciente real de la clínica
        pac = (await s.execute(
            select(Paciente).where(Paciente.clinica_id == cid, Paciente.is_active.is_(True))
        )).scalars().first()
        check("existe paciente en la clínica", pac is not None)
        pid = pac.id

    token = crear_token(uid, cid)

    # ── 1. Odontograma con CARAS (integración pieza + caras JSON) ─────────────
    async with _get_async_session() as s:
        d = await odo.guardar_pieza(
            s, cid, pid, "16",
            estado="caries",
            caras={"oclusal": "caries", "mesial": "obturado"},
            nota="E2E integracion", usuario_id=uid,
        )
        await s.commit()
        check("odontograma guardar_pieza con caras", d["estado"] == "caries")
        check("caras persistidas (oclusal+mesial)",
              d["caras"].get("oclusal") == "caries" and d["caras"].get("mesial") == "obturado")

    async with _get_async_session() as s:
        arc = await odo.listar(s, cid, pid)
        pieza16 = next((p for p in (arc["superior"] + arc["inferior"]) if p["numero"] == "16"), None)
        check("listar refleja la pieza 16 con caras",
              pieza16 is not None and pieza16["caras"].get("oclusal") == "caries")

    # PDF odontograma por HTTP (integración endpoint + token)
    st, ct, body = http_get(
        f"{BASE}/api/odontograma/pdf?paciente_id={pid}&clinica_id={cid}&token={token}")
    check("PDF odontograma HTTP 200 + pdf", st == 200 and "application/pdf" in ct and body[:5] == b"%PDF-")

    # ── 2. Mapa estético: eval + proc + punto + foto (E5/E6/E8) ────────────────
    creado = {}
    async with _get_async_session() as s:
        prod = (await s.execute(
            select(Producto).where(Producto.clinica_id == cid, Producto.is_active.is_(True))
        )).scalars().first()
        ev = await mapa.registrar_evaluacion(
            s, cid, pid, zona_codigo="frente", categoria="arrugas", severidad=2, usuario_id=uid)
        pr = await mapa.crear_procedimiento(
            s, cid, pid, zona_codigo="entrecejo", tipo="toxina_botulinica", usuario_id=uid)
        pt = await mapa.agregar_punto(
            s, cid, pr["id"], coord_x="0.5", coord_y="0.3",
            producto_id=(prod.id if prod else None), lote="LOT-E2E", cantidad="4", unidad="UI", usuario_id=uid)
        foto = await mapa.registrar_foto_zona(
            s, cid, pid, zona_codigo="frente", momento="antes",
            nombre="e2e.png", stored_name="e2e_no_file.png", usuario_id=uid)
        await s.commit()
        creado = {"eval": ev["id"], "proc": pr["id"], "foto": foto["id"]}
        check("estetica evaluacion creada", ev["id"] > 0)
        check("estetica procedimiento creado", pr["id"] > 0)
        check("estetica punto con producto", pt["id"] > 0 and pt["lote"] == "LOT-E2E")
        check("estetica foto por zona creada", foto["id"] > 0)

    # resumen_mapa integra las 3 cosas + fotos (E8)
    async with _get_async_session() as s:
        res = await mapa.resumen_mapa(s, cid, pid)
        check("resumen_mapa cuenta evaluación en frente",
              res["zonas"].get("frente", {}).get("evaluaciones", 0) >= 1)
        check("resumen_mapa cuenta procedimiento en entrecejo",
              res["zonas"].get("entrecejo", {}).get("procedimientos", 0) >= 1)
        check("resumen_mapa cuenta foto en frente (E8)",
              res["zonas"].get("frente", {}).get("fotos", 0) >= 1)

    # datos_export integra todo (E9) + PDF estético por HTTP
    async with _get_async_session() as s:
        datos = await mapa.datos_export(s, cid, pid)
        check("datos_export n_procedimientos>=1", datos["n_procedimientos"] >= 1)
        punto0 = datos["procedimientos"][0]["puntos"][0] if datos["procedimientos"] and datos["procedimientos"][0]["puntos"] else {}
        check("datos_export resuelve producto_nombre",
              (not prod) or punto0.get("producto_nombre", "") != "")

    st, ct, body = http_get(
        f"{BASE}/api/estetica/pdf?paciente_id={pid}&clinica_id={cid}&token={token}")
    check("PDF estetica HTTP 200 + pdf (E9)", st == 200 and "application/pdf" in ct and body[:5] == b"%PDF-")

    # ── 3. Seguridad de endpoints (token inválido / clínica ajena) ─────────────
    st, _, _ = http_get(f"{BASE}/api/estetica/pdf?paciente_id={pid}&clinica_id={cid}&token=basura")
    check("PDF estetica rechaza token inválido (401)", st == 401)
    st, _, _ = http_get(f"{BASE}/api/estetica/pdf?paciente_id={pid}&clinica_id=999999&token={token}")
    check("PDF estetica rechaza clínica ajena (403)", st == 403)

    # ── 4. Aislamiento multi-tenant (clínica inexistente no ve nada) ──────────
    async with _get_async_session() as s:
        vacio = await mapa.listar_procedimientos(s, 999999, pid)
        check("multi-tenant: clínica ajena no ve procedimientos", vacio == [])

    # ── 5. Limpieza (soft-delete de todo lo creado) ───────────────────────────
    async with _get_async_session() as s:
        await mapa.eliminar_procedimiento(s, cid, creado["proc"], usuario_id=uid)
        await mapa.eliminar_evaluacion(s, cid, creado["eval"], usuario_id=uid)
        await mapa.eliminar_foto_zona(s, cid, creado["foto"], usuario_id=uid)
        # pieza: volver a sano sin caras
        await odo.guardar_pieza(s, cid, pid, "16", estado="sano", caras=None, nota=None, usuario_id=uid)
        await s.commit()
    async with _get_async_session() as s:
        res2 = await mapa.resumen_mapa(s, cid, pid)
        arc2 = await odo.listar(s, cid, pid)
        p16 = next((p for p in (arc2["superior"] + arc2["inferior"]) if p["numero"] == "16"), None)
        check("cleanup: sin fotos residuales en frente",
              res2["zonas"].get("frente", {}).get("fotos", 0) == 0)
        check("cleanup: pieza 16 vuelta a sano sin caras",
              p16 is not None and p16["estado"] == "sano" and not p16["caras"])

    print(f"RESULT ok={_ok} fail={_fail}")


asyncio.run(main())
