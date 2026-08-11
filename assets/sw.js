/*
 * TUWAYKILIFE — Service Worker (PWA).
 *
 * Esta app es "siempre online": usa un WebSocket persistente para el estado y
 * bundles JS con hash dinamico de Reflex. Por eso NO cacheamos nada: un cache
 * serviria JS/estado viejo y romperia la app. Este SW existe para habilitar la
 * instalacion ("Instalar app" en Chrome/Edge exige un SW con un fetch handler
 * registrado) y para mostrar una pagina propia cuando el dispositivo se queda
 * sin conexion en una navegacion (en vez del dinosaurio del navegador). Todo lo
 * demas es passthrough puro a la red.
 */

// Pagina offline embebida (no depende de la red ni de ningun asset).
const OFFLINE_HTML = `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Sin conexion — TUWAYKILIFE</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; display: flex; align-items: center;
    justify-content: center; padding: 24px;
    font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: #f9fafb; color: #334155; text-align: center;
  }
  .card { max-width: 360px; }
  .icon {
    width: 64px; height: 64px; margin: 0 auto 20px; border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    background: rgba(2,132,199,0.10); border: 1px solid rgba(2,132,199,0.30);
    font-size: 30px;
  }
  h1 { font-size: 19px; font-weight: 800; margin: 0 0 8px; color: #0f172a; }
  p { font-size: 14px; line-height: 1.5; color: #64748b; margin: 0 0 24px; }
  button {
    background: #0284c7; color: #fff; border: 0; border-radius: 12px;
    font-size: 15px; font-weight: 700; padding: 14px 28px; cursor: pointer;
    width: 100%;
  }
  button:active { transform: scale(0.98); }
</style>
</head>
<body>
  <div class="card">
    <div class="icon">📶</div>
    <h1>Sin conexion</h1>
    <p>Revisa la conexion a internet y reintenta. Los datos de la clinica estan a salvo en el servidor.</p>
    <button onclick="location.reload()">Reintentar</button>
  </div>
</body>
</html>`;

self.addEventListener("install", () => {
  // Tomar control de inmediato al publicar una version nueva del SW.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // Barrido defensivo: si alguna vez existio un cache, lo borramos para
      // no arrastrar assets viejos entre despliegues.
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  // Solo interceptamos navegaciones de pagina (cargar/recargar una URL). Van
  // SIEMPRE a la red primero (nunca servimos version cacheada); solo si la red
  // falla mostramos la pagina offline propia. El resto (JS, WebSocket, API,
  // imagenes) es passthrough puro para no arriesgar contenido desactualizado.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(
        () =>
          new Response(OFFLINE_HTML, {
            headers: { "Content-Type": "text/html; charset=utf-8" },
          })
      )
    );
    return;
  }
  // Passthrough para todo lo demas.
  return;
});
