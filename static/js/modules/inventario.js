// static/js/modules/inventario.js
window.InventarioModule = (function(){

  // =======================
  // API (fallback) + helpers
  // =======================
  const API = window.API || {
    async request(path, opts = {}) {
      const token =
        localStorage.getItem("token") ||
        sessionStorage.getItem("token") ||
        "";
      const headers = Object.assign(
        {},
        opts.raw ? {} : { "Content-Type": "application/json" },
        token ? { Authorization: `Bearer ${token}` } : {}
      );
      const res = await fetch(path, { ...opts, headers });
      let data = null;
      try { data = await res.json(); } catch {}
      if (!res.ok) throw new Error((data && data.message) || "Error de servidor");
      return data;
    }
  };

  // =======================
  // API helpers
  // =======================
  async function buscarProductos(q){
    const res = await API.request(`/api/inventario/productos?q=${encodeURIComponent(q||"")}`);
    return res.data || res || [];
  }
  async function listarProductos(params={}){
    const qs = new URLSearchParams(params).toString();
    return API.request(`/api/inventario/productos${qs?`?${qs}`:""}`);
  }
  async function getProducto(id){
    return API.request(`/api/inventario/productos/${id}`);
  }
  async function getProductoBySku(sku){
    return API.request(`/api/inventario/productos/by-sku?sku=${encodeURIComponent(sku||"")}`);
  }
  async function crearProducto(data){
    return API.request("/api/inventario/productos", { method:"POST", body: JSON.stringify(data) });
  }
  async function actualizarProducto(id, data){
    return API.request(`/api/inventario/productos/${id}`, { method:"PUT", body: JSON.stringify(data) });
  }
  async function setProductoActivo(id, activo){
    return API.request(`/api/inventario/productos/${id}/activo`, { method:"PATCH", body: JSON.stringify({activo}) });
  }

  async function listarMov(params={}){
    const qs = new URLSearchParams(params).toString();
    return API.request(`/api/inventario/movimientos${qs?`?${qs}`:""}`);
  }
  async function getMov(id){
    return API.request(`/api/inventario/movimientos/${id}`);
  }
  async function crearMovLote(items){
    return API.request("/api/inventario/movimientos/lote", { method:"POST", body: JSON.stringify({items}) });
  }
  async function kardex(producto_id, params={}){
    const qs = new URLSearchParams(params).toString();
    return API.request(`/api/inventario/kardex?producto_id=${producto_id}${qs?`&${qs}`:""}`);
  }
  // compras
  async function crearCompra(data){
    return API.request("/api/inventario/compras", { method:"POST", body: JSON.stringify(data) });
  }
  async function getCompra(id){
    return API.request(`/api/inventario/compras/${id}`);
  }
  async function findCompraByNumero(numero){
    return API.request(`/api/inventario/compras/buscar?numero=${encodeURIComponent(numero)}`);
  }
  async function updateCompra(id, data){
    return API.request(`/api/inventario/compras/${id}`, { method:"PUT", body: JSON.stringify(data) });
  }

  // ===== Historial de precios/costos =====
  async function listarHistorialPrecios(pid, tipo = "", limit = 100){
    const qs = new URLSearchParams({});
    if (tipo) qs.set("tipo", tipo);
    if (limit) qs.set("limit", String(limit));
    return API.request(`/api/inventario/productos/${pid}/precios${qs.toString() ? `?${qs}` : ""}`);
  }
  function showHistModal(pid, resp){
    const rows = (resp && resp.data) || [];
    openModal(`
      <div>
        <h4>Historial de precios — Producto #${pid}</h4>
        ${rows.length ? `
          <table class="table">
            <thead><tr><th>Tipo</th><th>Valor</th><th>Vigente desde</th><th>Motivo</th></tr></thead>
            <tbody>
              ${rows.map(r => `
                <tr>
                  <td>${r.tipo}</td>
                  <td>${Number(r.valor||0).toFixed(2)}</td>
                  <td>${r.vigente_desde ? new Date(r.vigente_desde).toLocaleString() : "-"}</td>
                  <td>${r.motivo || ""}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        ` : `<p class="muted">Sin registros.</p>`}
      </div>
    `);
  }

  // =======================
  // UI helpers
  // =======================
  const routeTitle = document.getElementById("route-title") || { textContent:"" };
  const routeContent = document.getElementById("route-content") || document.body;

  function money(n){ return (Number(n||0)).toLocaleString('es-PE',{style:'currency',currency:'PEN'}) }
  function fmtDateIso(s){ return (s||"").replace("T"," ").slice(0,16); }

  // Devuelve un texto legible para un proveedor (acepta string u objeto)
  function proveedorToText(prov){
    if (!prov) return "";
    if (typeof prov === "string") return prov;
    if (prov && typeof prov === "object" && prov.data) prov = prov.data;
    const cand =
      prov.nombre ||
      prov.razon_social ||
      prov.nombre_comercial ||
      prov.display_name ||
      prov.alias ||
      prov.denominacion;
    if (cand) return String(cand);
    if (prov.ruc) return String(prov.ruc);
    if (prov.id != null) return `ID ${prov.id}`;
    try { return JSON.stringify(prov); } catch { return ""; }
  }

  // --- Shim modal (si no existe globalmente) ---
  if (typeof window.openModal !== "function") {
    window.openModal = function (html) {
      const overlay = document.createElement("div");
      Object.assign(overlay.style, {
        position: "fixed", inset: 0, background: "rgba(0,0,0,.45)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 9999
      });
      overlay.innerHTML = `
        <div class="__modal-card">
          ${html}
          <div style="text-align:right;margin-top:12px">
            <button id="__modal_close__" class="btn">Cerrar</button>
          </div>
        </div>`;
      const card = overlay.querySelector(".__modal-card");
      Object.assign(card.style, {
        background: "#fff", padding: "14px", borderRadius: "12px",
        width: "min(92vw, 560px)", maxHeight: "80vh", overflow: "auto",
        boxShadow: "0 10px 30px rgba(0,0,0,.2)"
      });
      overlay.addEventListener("click", (e)=> { if (e.target === overlay) overlay.remove(); });
      overlay.querySelector("#__modal_close__").addEventListener("click", ()=> overlay.remove());
      document.body.appendChild(overlay);
    };
  }

  // estilos mínimos (switch + celdas editables + sugerencias)
  (function injectStyles(){
    if(document.getElementById("inv-switch-style")) return;
    const st=document.createElement("style");
    st.id="inv-switch-style";
    st.textContent=`
      .switch{position:relative;display:inline-block;width:42px;height:22px}
      .switch input{opacity:0;width:0;height:0}
      .slider{position:absolute;cursor:pointer;inset:0;background:#d1d5db;border-radius:999px;transition:.2s}
      .slider:before{position:absolute;content:"";height:18px;width:18px;left:2px;top:2px;background:white;border-radius:50%;transition:.2s;box-shadow:0 1px 2px rgba(0,0,0,.25)}
      input:checked + .slider{background:var(--color-success,#22c55e)}
      input:checked + .slider:before{transform:translateX(20px)}
      .sug{padding:0.6rem 0.85rem;cursor:pointer}
      .sug.active,.sug:hover{background:var(--hover-bg,#f3f4f6)}
      .pl-row .ed{display:none;width:100%;padding:8px 12px;border:1px solid #d7dce3;border-radius:var(--border-radius-sm,8px);font:inherit}
      .pl-row.editing .ro{display:none}
      .pl-row.editing .ed{display:inline-block}
    `;
    document.head.appendChild(st);
  })();

  function makeSuggestionNavigator({inputEl, listEl, fetcher, tpl, onChoose}){
    if (!inputEl || !listEl) return;
    let items = [], sel = -1, t = null;
    function render(){ listEl.innerHTML = tpl(items); listEl.style.display = items.length ? "block":"none"; }
    async function search(q){ try{ items = await fetcher(q); sel=-1; render(); } catch{ items=[]; render(); } }
    inputEl.addEventListener("input", ()=>{ clearTimeout(t); t = setTimeout(()=> search(inputEl.value.trim()), 180); });
    inputEl.addEventListener("keydown",(e)=>{
      if(!items.length) return;
      const els=[...listEl.querySelectorAll(".sug")];
      if(e.key==="ArrowDown"){ sel=Math.min(sel+1, items.length-1); e.preventDefault(); }
      if(e.key==="ArrowUp"){ sel=Math.max(sel-1, 0); e.preventDefault(); }
      if(e.key==="Enter" && sel>=0){ onChoose(items[sel]); listEl.style.display="none"; e.preventDefault(); }
      els.forEach((el,i)=> el.classList.toggle("active", i===sel));
    });
    listEl.addEventListener("click",(e)=>{
      const el=e.target.closest(".sug"); if(!el) return;
      const idx=Number(el.dataset.idx||"-1"); if(idx<0) return;
      onChoose(items[idx]); listEl.style.display="none";
    });
    document.addEventListener("click",(e)=>{ if(!listEl.contains(e.target) && e.target!==inputEl) listEl.style.display="none"; });
  }

  // =======================
  // Filas / templates
  // =======================
  function filaCompraTpl(idx){
    return `
      <tr data-row="${idx}">
        <td>
          <div class="ac-wrap">
            <input class="cp-prod-buscar" placeholder="SKU o nombre" autocomplete="off">
            <div class="suggest ac-list cp-sug" style="display:none"></div>
          </div>
          <input type="hidden" class="cp-prod-id">
          <div class="muted cp-prod-chosen"></div>
        </td>
        <td><input class="cp-cant" type="number" step="0.001"></td>
        <td><input class="cp-costo" type="number" step="0.01"></td>
        <td class="cp-subtotal">${money(0)}</td>
        <td class="table-actions table-actions--compact"><button class="btn btn-danger cp-eliminar" type="button">Quitar</button></td>
      </tr>
    `;
  }
  function filaLoteTpl(idx){
    return `
      <tr data-row="${idx}">
        <td>
          <div class="ac-wrap">
            <input class="lt-prod-buscar" placeholder="Buscar producto" autocomplete="off">
            <div class="suggest ac-list lt-sug" style="display:none"></div>
          </div>
          <input type="hidden" class="lt-prod-id">
          <div class="muted lt-prod-chosen"></div>
        </td>
        <td>
          <select class="lt-tipo">
            <option value="ingreso">Ingreso</option>
            <option value="egreso">Egreso</option>
            <option value="ajuste">Ajuste</option>
          </select>
        </td>
        <td><input class="lt-cant" type="number" step="0.001"></td>
        <td><input class="lt-motivo" placeholder="Motivo"></td>
        <td><input class="lt-ref" placeholder="Referencia"></td>
        <td class="table-actions table-actions--compact"><button class="btn btn-danger lt-eliminar" type="button">Quitar</button></td>
      </tr>
    `;
  }

  // =======================
  // Render principal
  // =======================
  function render(){
    routeTitle.textContent = "Inventario";

    routeContent.innerHTML = `
      <section class="card inventory-card">
        <header class="card-header">
          <h3>Alta rápida de producto</h3>
          <p class="card-subtitle">Registrá un nuevo producto con los datos esenciales para operar.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="pr-sku">SKU</label><input id="pr-sku" placeholder="Código interno"></div>
          <div class="form-row"><label for="pr-nombre">Nombre</label><input id="pr-nombre" required placeholder="Nombre del producto"></div>
          <div class="form-row"><label for="pr-min">Stock mínimo</label><input id="pr-min" type="number" step="0.001" placeholder="0"></div>
          <div class="form-row"><label for="pr-pv">Precio de venta</label><input id="pr-pv" type="number" step="0.01" placeholder="0.00"></div>
        </div>
        <div class="form-actions">
          <button id="pr-guardar" class="btn btn-primary" type="button">Guardar producto</button>
        </div>
        <div id="pr-msg" class="form-feedback muted"></div>
      </section>

      <section class="card inventory-card">
        <header class="card-header">
          <h3>Listado de productos</h3>
          <p class="card-subtitle">Gestioná stock, precios y estado desde un único panel.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="pl-q">Buscar</label><input id="pl-q" placeholder="SKU o nombre"></div>
          <div class="form-row">
            <label for="pl-estado">Estado</label>
            <select id="pl-estado">
              <option value="">Todos</option>
              <option value="true">Activos</option>
              <option value="false">Inactivos</option>
            </select>
          </div>
          <div class="form-row">
            <label for="pl-per">Por página</label>
            <select id="pl-per"><option>10</option><option>25</option><option>50</option></select>
          </div>
          <div class="form-row form-row--actions">
            <label class="sr-only" for="pl-filtrar">Aplicar filtros</label>
            <button id="pl-filtrar" class="btn btn-secondary" type="button">Aplicar filtros</button>
          </div>
        </div>
        <div class="table-scroll">
          <table class="table table--compact">
            <thead><tr>
              <th>SKU</th><th>Nombre</th><th>Stock</th><th>Mínimo</th><th>Precio venta</th><th>Últ. costo</th><th>Activo</th><th>Acciones</th>
            </tr></thead>
            <tbody id="pl-tbody"></tbody>
          </table>
        </div>
        <div class="pager">
          <button id="pl-prev" class="btn btn-secondary" type="button">Anterior</button>
          <span id="pl-info" class="muted"></span>
          <button id="pl-next" class="btn btn-secondary" type="button">Siguiente</button>
        </div>
        <div id="pl-msg" class="form-feedback muted"></div>
      </section>

      <section class="card inventory-card" id="card-compra">
        <header class="card-header">
          <h3>Registrar compra</h3>
          <p class="card-subtitle">Ingresá comprobantes para actualizar el inventario automáticamente.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="cp-prov-nombre">Proveedor</label><input id="cp-prov-nombre" placeholder="Nombre del proveedor"></div>
          <div class="form-row"><label for="cp-tipo">Tipo de comprobante</label>
            <select id="cp-tipo"><option value="boleta">Boleta</option><option value="factura">Factura</option><option value="otro">Otro</option></select>
          </div>
          <div class="form-row"><label for="cp-numero">Número</label><input id="cp-numero" placeholder="Serie-00000000"></div>
          <div class="form-row"><label for="cp-registro">Nro. registro</label><input id="cp-registro" placeholder="(si aplica)"></div>
        </div>
        <hr class="card-divider">
        <header class="section-header">
          <h4>Detalle de productos</h4>
          <p class="muted">Buscá el producto, definí cantidades y costos para cada ítem.</p>
        </header>
        <div class="table-scroll">
          <table class="table table--compact" id="cp-tabla">
            <thead><tr><th>Producto</th><th>Cantidad</th><th>Costo unit.</th><th>Subtotal</th><th></th></tr></thead>
            <tbody id="cp-tbody"></tbody>
          </table>
        </div>
        <div class="form-actions form-actions--right">
          <button id="cp-add-row" class="btn btn-secondary" type="button">Agregar producto</button>
        </div>
        <div class="inventory-total">
          <span>Total compra</span>
          <strong id="cp-total">${money(0)}</strong>
        </div>
        <div class="form-actions">
          <button id="cp-guardar" class="btn btn-primary" type="button">Guardar compra</button>
          <div id="cp-cancelar-wrap" style="display:none"><button id="cp-cancelar-ed" class="btn btn-secondary" type="button">Cancelar edición</button></div>
        </div>
        <div id="cp-compra-msg" class="form-feedback muted"></div>
      </section>

      <section class="card inventory-card">
        <header class="card-header">
          <h3>Movimientos recientes</h3>
          <p class="card-subtitle">Consultá ingresos, egresos y ajustes registrados.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="fl-desde">Desde</label><input id="fl-desde" type="date"></div>
          <div class="form-row"><label for="fl-hasta">Hasta</label><input id="fl-hasta" type="date"></div>
          <div class="form-row"><label for="fl-tipo">Tipo</label>
            <select id="fl-tipo">
              <option value="">Todos</option>
              <option value="ingreso">Ingresos</option>
              <option value="egreso">Egresos</option>
              <option value="ajuste">Ajustes</option>
            </select>
          </div>
          <div class="form-row form-row--actions">
            <label class="sr-only" for="fl-filtrar">Filtrar movimientos</label>
            <button id="fl-filtrar" class="btn btn-secondary" type="button">Filtrar</button>
          </div>
        </div>
        <div class="table-scroll">
          <table class="table table--compact">
            <thead><tr><th>Fecha</th><th>Producto</th><th>Tipo</th><th>Monto</th><th>Motivo</th><th>Referencia</th><th>Acciones</th></tr></thead>
            <tbody id="mv-tbody"></tbody>
          </table>
        </div>
        <div class="pager">
          <button id="mv-prev" class="btn btn-secondary" type="button">Anterior</button>
          <span id="mv-info" class="muted"></span>
          <button id="mv-next" class="btn btn-secondary" type="button">Siguiente</button>
        </div>
      </section>

      <section class="card inventory-card">
        <header class="card-header">
          <h3>Movimientos por lotes</h3>
          <p class="card-subtitle">Cargá múltiples movimientos manuales en una sola acción.</p>
        </header>
        <div class="table-scroll">
          <table class="table table--compact">
            <thead><tr><th>Producto</th><th>Tipo</th><th>Cantidad</th><th>Motivo</th><th>Referencia</th><th></th></tr></thead>
            <tbody id="lt-tbody"></tbody>
          </table>
        </div>
        <div class="form-actions">
          <button id="lt-add-row" class="btn btn-secondary" type="button">Agregar fila</button>
          <button id="lt-guardar" class="btn btn-primary" type="button">Registrar movimientos</button>
        </div>
        <div id="lt-msg" class="form-feedback muted"></div>
      </section>

      <section class="card inventory-card">
        <header class="card-header">
          <h3>Kardex por producto</h3>
          <p class="card-subtitle">Seguimiento detallado de las entradas y salidas por producto.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row">
            <label for="kx-prod">Producto</label>
            <div class="ac-wrap">
              <input id="kx-prod" placeholder="Buscar producto" autocomplete="off">
              <div id="kx-sug" class="suggest ac-list" style="display:none"></div>
            </div>
            <input type="hidden" id="kx-prod-id">
          </div>
          <div class="form-row">
            <label for="kx-perpage">Registros por página</label>
            <select id="kx-perpage"><option value="10">10</option><option value="20">20</option><option value="50">50</option></select>
          </div>
          <div class="form-row form-row--actions">
            <label class="sr-only" for="kx-ver">Ver kardex</label>
            <button id="kx-ver" class="btn btn-secondary" type="button">Ver kardex</button>
          </div>
        </div>
        <div class="table-scroll">
          <table class="table table--compact">
            <thead><tr><th>Fecha</th><th>Tipo</th><th>Cantidad</th><th>Saldo</th><th>Motivo</th><th>Referencia</th></tr></thead>
            <tbody id="kx-tbody"></tbody>
          </table>
        </div>
        <div class="pager">
          <button id="kx-prev" class="btn btn-secondary" type="button">Anterior</button>
          <span id="kx-info" class="muted"></span>
          <button id="kx-next" class="btn btn-secondary" type="button">Siguiente</button>
        </div>
      </section>
    `;

    // ===== Crear producto rápido =====
    document.getElementById("pr-guardar").addEventListener("click", async ()=>{
      const sku = document.getElementById("pr-sku").value;
      const nombre = document.getElementById("pr-nombre").value;
      const stock_minimo = Number(document.getElementById("pr-min").value || "0");
      const precio_venta = Number(document.getElementById("pr-pv").value || "0");
      const msg = document.getElementById("pr-msg");
      msg.textContent = "";
      if (!nombre){ msg.textContent = "Nombre requerido"; return; }
      try{
        // si el SKU ya existe, forzamos edición (precargamos)
        if ((sku||"").trim()){
          const ex = await getProductoBySku(sku.trim());
          if (ex && ex.id){
            await actualizarProducto(ex.id, { sku, nombre, stock_minimo, precio_venta }); // actualizo rápido
            msg.textContent = `Producto #${ex.id} actualizado.`;
            plLoad();
            document.getElementById("pr-sku").value="";
            document.getElementById("pr-nombre").value="";
            document.getElementById("pr-min").value="";
            document.getElementById("pr-pv").value="";
            return;
          }
        }
        await crearProducto({ sku, nombre, stock_minimo, precio_venta });
        msg.textContent = "Producto creado.";
        document.getElementById("pr-sku").value="";
        document.getElementById("pr-nombre").value="";
        document.getElementById("pr-min").value="";
        document.getElementById("pr-pv").value="";
        plLoad();
      }catch(e){ msg.textContent = e.message || "No se pudo crear/actualizar el producto."; }
    });

    // ===== Listado de productos (paginado + switch activo + edición inline) =====
    const plQ = document.getElementById("pl-q");
    const plEstado = document.getElementById("pl-estado");
    const plPer = document.getElementById("pl-per");
    const plTbody = document.getElementById("pl-tbody");
    const plInfo = document.getElementById("pl-info");
    const plMsg = document.getElementById("pl-msg");
    let plPage = 1, plPerPage = Number(plPer.value||10), plTotal=0;

    function rowTpl(p){
      return `
        <tr class="pl-row" data-id="${p.id}" data-orig-sku="${p.sku||""}" data-orig-nombre="${(p.nombre||"").replace(/"/g,"&quot;")}" data-orig-min="${Number(p.stock_minimo||0).toFixed(3)}" data-orig-pv="${Number(p.precio_venta||0).toFixed(2)}">
          <td>
            <span class="ro sku">${p.sku||""}</span>
            <input class="ed sku" value="${p.sku||""}" maxlength="60">
          </td>
          <td>
            <span class="ro nombre">${p.nombre||""}</span>
            <input class="ed nombre" value="${(p.nombre||"").replace(/"/g,"&quot;")}" maxlength="180">
          </td>
          <td>${Number(p.stock_actual||0).toFixed(3)}</td>
          <td>
            <span class="ro min">${Number(p.stock_minimo||0).toFixed(3)}</span>
            <input class="ed min" type="number" step="0.001" value="${Number(p.stock_minimo||0).toFixed(3)}">
          </td>
          <td>
            <span class="ro pv">${Number(p.precio_venta||0).toFixed(2)}</span>
            <input class="ed pv" type="number" step="0.01" value="${Number(p.precio_venta||0).toFixed(2)}">
          </td>
          <td>${Number(p.ultimo_costo||0).toFixed(2)}</td>
          <td>
            <label class="switch">
              <input type="checkbox" class="pl-activo" data-id="${p.id}" ${p.activo ? "checked":""}>
              <span class="slider"></span>
            </label>
          </td>
          <td class="table-actions table-actions--compact">
            <button class="btn btn-secondary pl-edit" type="button">Editar</button>
            <button class="btn btn-primary pl-save" type="button" style="display:none">Guardar</button>
            <button class="btn btn-secondary pl-cancel" type="button" style="display:none">Cancelar</button>
            <button class="btn btn-light pl-hist" type="button">Historial</button>
          </td>
        </tr>
      `;
    }

    async function plLoad(){
      plMsg.textContent = "";
      try{
        const params = { q: (plQ.value||"").trim(), page: plPage, per_page: plPerPage };
        const est = plEstado.value;
        if(est !== "") params.activo = est;

        const r = await listarProductos(params);
        const rows = r.data || [];
        plTotal = r.total || rows.length;

        plTbody.innerHTML = rows.map(rowTpl).join("");

        const maxPage = Math.max(1, Math.ceil(plTotal/plPerPage));
        plInfo.textContent = `Página ${plPage} de ${maxPage} — ${plTotal} productos`
        document.getElementById("pl-prev").disabled = (plPage<=1);
        document.getElementById("pl-next").disabled = (plPage>=maxPage);
      }catch(e){
        plMsg.textContent = e.message || "No se pudo cargar el listado.";
      }
    }
    window.plLoad = plLoad;

    document.getElementById("pl-filtrar").addEventListener("click", ()=>{ plPage=1; plPerPage=Number(plPer.value||10); plLoad(); });
    document.getElementById("pl-prev").addEventListener("click", ()=>{ if(plPage>1){ plPage--; plLoad(); }});
    document.getElementById("pl-next").addEventListener("click", ()=>{ plPage++; plLoad(); });
    plQ.addEventListener("keydown",(e)=>{ if(e.key==="Enter"){ plPage=1; plLoad(); }});
    plLoad();

    // Switch activo/inactivo
    plTbody.addEventListener("change", async (e)=>{
      const sw = e.target.closest(".pl-activo");
      if(!sw) return;
      const id = Number(sw.dataset.id);
      const nuevo = !!sw.checked;
      try{
        await setProductoActivo(id, nuevo);
      }catch(err){
        sw.checked = !nuevo;
        plMsg.textContent = err.message || "No se pudo actualizar el estado.";
      }
    });

    // Edición inline
    function setRowMode(tr, editing){
      tr.classList.toggle("editing", !!editing);
      tr.querySelector(".pl-edit").style.display   = editing ? "none":"inline-block";
      tr.querySelector(".pl-save").style.display   = editing ? "inline-block":"none";
      tr.querySelector(".pl-cancel").style.display = editing ? "inline-block":"none";
      const skuIn  = tr.querySelector("input.ed.sku");
      if(editing && skuIn) skuIn.focus();
    }
    function resetRowValues(tr){
      tr.querySelector("input.ed.sku").value    = tr.dataset.origSku || "";
      tr.querySelector("input.ed.nombre").value = tr.dataset.origNombre || "";
      tr.querySelector("input.ed.min").value    = tr.dataset.origMin || "0.000";
      const pvIn = tr.querySelector("input.ed.pv");
      if (pvIn) pvIn.value = tr.dataset.origPv || "0.00";
    }
    function updateRowRO(tr, data){
      tr.dataset.origSku    = data.sku || "";
      tr.dataset.origNombre = data.nombre || "";
      tr.dataset.origMin    = Number(data.stock_minimo||0).toFixed(3);
      tr.dataset.origPv     = Number(data.precio_venta||0).toFixed(2);
      tr.querySelector(".ro.sku").textContent    = tr.dataset.origSku;
      tr.querySelector(".ro.nombre").textContent = tr.dataset.origNombre;
      tr.querySelector(".ro.min").textContent    = tr.dataset.origMin;
      const pvRo = tr.querySelector(".ro.pv");
      if (pvRo) pvRo.textContent = tr.dataset.origPv;
    }

    plTbody.addEventListener("click", async (e)=>{
      const tr = e.target.closest(".pl-row"); if(!tr) return;
      const id = Number(tr.dataset.id);

      // Historial
      if (e.target.closest(".pl-hist")){
        try{
          const hist = await listarHistorialPrecios(id, "", 100);
          showHistModal(id, hist);
        }catch(err){
          openModal(`<div style="padding:8px"><p>No se pudo cargar el historial.</p><p class="muted">${err?.message||""}</p></div>`);
        }
        return;
      }

      // Editar
      if(e.target.closest(".pl-edit")){
        setRowMode(tr, true);
        return;
      }

      // Cancelar
      if(e.target.closest(".pl-cancel")){
        resetRowValues(tr);
        setRowMode(tr, false);
        return;
      }

      // Guardar
      if(e.target.closest(".pl-save")){
        const sku    = tr.querySelector("input.ed.sku").value.trim();
        const nombre = tr.querySelector("input.ed.nombre").value.trim();
        const minStr = tr.querySelector("input.ed.min").value;
        const pvStr  = (tr.querySelector("input.ed.pv") || { value:"" }).value;
        const stock_minimo = Number(minStr || "0");
        const precio_venta = Number(pvStr || "0");
        if(!nombre){ plMsg.textContent="Nombre requerido"; return; }
        try{
          const payload = { sku, nombre, stock_minimo, precio_venta };
          // Si cambió PV, pedimos motivo
          const origPv = Number(tr.dataset.origPv || "0");
          if (Number(precio_venta.toFixed ? precio_venta.toFixed(2) : precio_venta) !== Number(origPv.toFixed ? origPv.toFixed(2) : origPv)) {
            payload.motivo = prompt("Motivo del cambio de precio de venta:", "actualización manual") || "actualización manual";
          }
          const r = await actualizarProducto(id, payload);
          updateRowRO(tr, r);
          setRowMode(tr, false);
          plMsg.textContent = `Producto #${id} actualizado.`;
        }catch(err){
          plMsg.textContent = err.message || "No se pudo actualizar el producto.";
        }
      }
    });

    // Enter = Guardar, Esc = Cancelar
    plTbody.addEventListener("keydown",(e)=>{
      const tr = e.target.closest(".pl-row.editing");
      if(!tr) return;
      if(e.key === "Escape"){
        e.preventDefault();
        resetRowValues(tr);
        setRowMode(tr, false);
      }
      if(e.key === "Enter"){
        e.preventDefault();
        tr.querySelector(".pl-save").click();
      }
    });

    // ===== Registrar compra (CREAR/EDITAR) =====
    const cpCard      = document.getElementById("card-compra");
    const cpTbody     = document.getElementById("cp-tbody");
    const cpTotalEl   = document.getElementById("cp-total");
    const cpMsg       = document.getElementById("cp-compra-msg");
    const btnGuardar  = document.getElementById("cp-guardar");
    const btnCancelEdWrap = document.getElementById("cp-cancelar-wrap");
    const btnCancelEd = document.getElementById("cp-cancelar-ed");
    let cpEditingId = null;

    function recalcCompra(){
      let total=0;
      cpTbody.querySelectorAll("tr").forEach(tr=>{
        const cant=Number(tr.querySelector(".cp-cant").value||"0");
        const costo=Number(tr.querySelector(".cp-costo").value||"0");
        const sub=cant*costo;
        tr.querySelector(".cp-subtotal").textContent=money(sub);
        total+=sub;
      });
      cpTotalEl.textContent = money(total);
    }
    function makeSuggestionNavigatorRow(inputEl, listEl, onChoose){
      makeSuggestionNavigator({
        inputEl, listEl,
        fetcher: buscarProductos,
        tpl: items=>items.slice(0,8).map((p,i)=>`<div class="sug" data-idx="${i}">${(p.sku||"")} — ${p.nombre||""}</div>`).join(""),
        onChoose
      });
    }

    // makeCompraRow (async para prefill)
    async function makeCompraRow(prefill){
      const idx=Date.now()+Math.floor(Math.random()*1000);
      cpTbody.insertAdjacentHTML("beforeend", filaCompraTpl(idx));
      const tr = cpTbody.querySelector(`tr[data-row="${idx}"]`);
      const inp=tr.querySelector(".cp-prod-buscar"), sug=tr.querySelector(".cp-sug");
      const hid=tr.querySelector(".cp-prod-id"), chosen=tr.querySelector(".cp-prod-chosen");
      makeSuggestionNavigatorRow(inp, sug, p=>{ hid.value=p.id; chosen.textContent=`${p.sku||""} — ${p.nombre||""}`; inp.value=""; });
      tr.querySelector(".cp-cant").addEventListener("input", recalcCompra);
      tr.querySelector(".cp-costo").addEventListener("input", recalcCompra);

      if(prefill){
        hid.value = prefill.producto_id;
        tr.querySelector(".cp-cant").value = prefill.cantidad;
        tr.querySelector(".cp-costo").value = prefill.costo_unitario;

        try {
          const p = prefill.producto ? prefill.producto : await getProducto(prefill.producto_id);
          chosen.textContent = `${p.sku||""} — ${p.nombre||""}`;
        } catch {
          chosen.textContent = `ID ${prefill.producto_id}`;
        }
        recalcCompra();
      }
    }

    function clearCompraForm(){
      document.getElementById("cp-prov-nombre").value="";
      document.getElementById("cp-tipo").value="boleta";
      document.getElementById("cp-numero").value="";
      document.getElementById("cp-registro").value="";
      cpTbody.innerHTML="";
      cpTotalEl.textContent=money(0);
      makeCompraRow();
    }
    function enterCompraEditMode(compra){
      cpEditingId = compra.id;
      document.getElementById("cp-prov-nombre").value = compra.proveedor?.nombre || "";
      document.getElementById("cp-tipo").value      = compra.tipo_doc || "boleta";
      document.getElementById("cp-numero").value    = compra.numero || "";
      document.getElementById("cp-registro").value  = compra.nro_registro || "";

      cpTbody.innerHTML="";
      (compra.items||[]).forEach(it=> makeCompraRow(it));
      recalcCompra();

      btnGuardar.textContent = "Actualizar compra";
      btnCancelEdWrap.style.display = "block";
      cpMsg.textContent = `Editando compra #${compra.id}`;
      cpCard.scrollIntoView({ behavior:"smooth", block:"start" });
    }
    function exitCompraEditMode(){
      cpEditingId = null;
      btnGuardar.textContent = "Guardar compra";
      btnCancelEdWrap.style.display = "none";
      cpMsg.textContent = "";
      clearCompraForm();
    }

    document.getElementById("cp-add-row").addEventListener("click", ()=> makeCompraRow());
    cpTbody.addEventListener("click",(e)=>{ const b=e.target.closest(".cp-eliminar"); if(b){ b.closest("tr").remove(); recalcCompra(); }});
    if(btnCancelEd) btnCancelEd.addEventListener("click", ()=> exitCompraEditMode());
    makeCompraRow();

    btnGuardar.addEventListener("click", async ()=>{
      cpMsg.textContent="";
      const proveedor_nombre=(document.getElementById("cp-prov-nombre").value||"").trim();
      const tipo_doc=document.getElementById("cp-tipo").value;
      const numero=(document.getElementById("cp-numero").value||"").trim();
      const nro_registro=(document.getElementById("cp-registro").value||"").trim();
      const items=[];
      cpTbody.querySelectorAll("tr").forEach(tr=>{
        const pid=Number(tr.querySelector(".cp-prod-id").value||"0");
        const cant=Number(tr.querySelector(".cp-cant").value||"0");
        const costo=Number(tr.querySelector(".cp-costo").value||"0");
        if(pid && cant>0 && costo>0) items.push({ producto_id: pid, cantidad: cant, costo_unitario: costo });
      });
      if(!items.length){ cpMsg.textContent="Agregá al menos un ítem válido."; return; }

      try{
        let r;
        if(cpEditingId){
          r = await updateCompra(cpEditingId, { proveedor_nombre, tipo_doc, numero, nro_registro, items });
          cpMsg.innerHTML=`Compra <b>#${r.id}</b> actualizada. Total ${money(r.total)}`;
        }else{
          r = await crearCompra({ proveedor_nombre, tipo_doc, numero, nro_registro, items });
          cpMsg.innerHTML=`Compra <b>#${r.id}</b> guardada. Total ${money(r.total)}`;
        }
        exitCompraEditMode();
        mvLoad();
        plLoad();
      }catch(e){ cpMsg.textContent=e.message||"No se pudo guardar la compra."; }
    });

    // ===== Movimientos (listado) =====
    const mvTbody = document.getElementById("mv-tbody");
    const mvInfo  = document.getElementById("mv-info");
    let mvPage=1, mvPerPage=10, mvTotal=0;

    async function mvLoad(){
      const params = {
        desde: document.getElementById("fl-desde").value || "",
        hasta: document.getElementById("fl-hasta").value || "",
        tipo: document.getElementById("fl-tipo").value || "",
        page: mvPage, per_page: mvPerPage
      };
      Object.keys(params).forEach(k=>{ if(!params[k]) delete params[k]; });
      const r = await listarMov(params);
      const rows = r.data || [];
      mvTotal = r.total || rows.length;

      function fallbackProductoLabel(row){
        const t = String(row.tipo||"").toUpperCase();
        if(t.includes("INGRESO")) return row.producto_label || "INGRESO";
        if(t.includes("EGRESO"))  return row.producto_label || "SALIDA";
        return row.producto_label || "AJUSTE";
      }
      function fallbackMonto(row){
        if (row.monto != null) return row.monto;
        if (row.total != null) return row.total;
        return 0;
      }

      mvTbody.innerHTML = rows.map(r=>`
        <tr>
          <td>${fmtDateIso(r.fecha)}</td>
          <td>${fallbackProductoLabel(r)}</td>
          <td>${(r.tipo||"").toUpperCase()}</td>
          <td>${money(fallbackMonto(r))}</td>
          <td>${r.motivo||""}</td>
          <td>${r.referencia||""}</td>
          <td class="table-actions table-actions--compact">
            <button class="btn btn-secondary mv-revisar" type="button" data-id="${r.id}">Revisar</button>
            ${(String(r.tipo||'').toLowerCase()==='ingreso') ? `<button class="btn btn-secondary mv-editar" type="button" data-id="${r.id}">Editar</button>` : ``}
          </td>
        </tr>
      `).join("");

      const maxPage = Math.max(1, Math.ceil(mvTotal/mvPerPage));
      mvInfo.textContent = `Página ${mvPage} de ${maxPage} — ${mvTotal} movimientos`;
      document.getElementById("mv-prev").disabled = (mvPage<=1);
      document.getElementById("mv-next").disabled = (mvPage>=maxPage);
    }
    document.getElementById("fl-filtrar").addEventListener("click", ()=>{ mvPage=1; mvLoad(); });
    document.getElementById("mv-prev").addEventListener("click", ()=>{ if(mvPage>1){ mvPage--; mvLoad(); }});
    document.getElementById("mv-next").addEventListener("click", ()=>{ mvPage++; mvLoad(); });

    mvTbody.addEventListener("click", async (e)=>{
      const btnEd = e.target.closest(".mv-editar");
      const btnRv = e.target.closest(".mv-revisar");

      if (btnRv) {
        try {
          const m = await getMov(Number(btnRv.dataset.id));

          // Normalizar y completar productos del detalle
          let items = (m.grupo && Array.isArray(m.grupo.items)) ? m.grupo.items : [];
          const toFetch = [];
          items.forEach(it => {
            const pid = (it.producto && it.producto.id) ? it.producto.id : (it.producto_id || null);
            const hasName = !!(it.producto && (it.producto.nombre || it.producto.sku));
            if (!hasName && pid) toFetch.push({ it, pid });
          });
          if (toFetch.length) {
            const fetched = await Promise.all(toFetch.map(({pid}) => getProducto(pid).catch(()=>null)));
            fetched.forEach((p, i) => { if (p) toFetch[i].it.producto = p; });
          }

          const proveedorTxt =
            (m.compra ? proveedorToText(m.compra.proveedor) : "") ||
            (m.producto_label || "");

          const nroReg = (m.compra && (m.compra.nro_registro || m.compra.nroRegistro || m.compra.registro)) || "—";

          const itemsHtml = items.length ? `
            <hr>
            <h4 style="margin:6px 0">Detalle</h4>
            <table class="table">
              <thead><tr><th>Producto</th><th>Cantidad</th><th>Subtotal</th></tr></thead>
              <tbody>
                ${items.map(it=>{
                  const pr = it.producto || {};
                  const nombre = pr.nombre || "";
                  const sku = pr.sku || "";
                  return `
                    <tr>
                      <td>${sku ? sku+" — " : ""}${nombre}</td>
                      <td>${Number(it.cantidad||0).toFixed(3)}</td>
                      <td>${money(it.costo_unitario||0)}</td>
                      <td>${money(it.subtotal||0)}</td>
                    </tr>
                  `;
                }).join("")}
              </tbody>
              <tfoot>
                <tr><td colspan="3" style="text-align:right"><b>Total</b></td><td><b>${money((m.grupo && m.grupo.total)||0)}</b></td></tr>
              </tfoot>
            </table>
          ` : "";

          openModal(`
            <div style="padding:6px 8px;">
              <h4>Movimiento #${m.id}</h4>
              <p><b>Fecha:</b> ${fmtDateIso(m.fecha)}</p>
              <p><b>Tipo:</b> ${(m.tipo||"").toUpperCase()}</p>
              <p><b>Cantidad:</b> ${money(m.monto ?? 0)}</p>
              <p><b>Motivo:</b> ${m.motivo||""}</p>
              <p><b>Nro. Registro:</b> ${nroReg}</p>
              ${m.compra ? `<p><b>Comprobante:</b> ${(m.compra.tipo_doc||"").toUpperCase()} ${m.compra.numero||""}</p>` : ""}
              ${m.compra ? `<p><b>Proveedor:</b> ${proveedorTxt}</p>` : ""}
              ${itemsHtml}
            </div>
          `);
        } catch (err) {
          openModal(`<div style="padding:6px 8px;">
            <p>No se pudo cargar el detalle del movimiento.</p>
            <p class="muted">${err?.message||""}</p>
          </div>`);
        }
        return;
      }

      if (btnEd) {
        const id = btnEd.dataset.id;
        const m = await getMov(id);
        let compra = null;

        if (m.compra && m.compra.id) {
          compra = m.compra;
        } else if (m.compra_id) {
          compra = await getCompra(m.compra_id);
        } else if ((m.referencia||"").trim()) {
          const byRef = await findCompraByNumero(m.referencia.trim());
          if (byRef && byRef.id) compra = byRef;
        }

        if (!compra) {
          openModal(`<div class="inv-modal-body"><p>No pude ubicar la compra de este movimiento.</p><p>Motivo: ${m.motivo||"-"} — Ref: ${m.referencia||"-"}</p></div>`);
          return;
        }
        enterCompraEditMode(compra);
      }
    });

    mvLoad();

    // ===== Movimientos por lotes =====
    const ltTbody = document.getElementById("lt-tbody");
    const ltMsg = document.getElementById("lt-msg");
    function makeLoteRow(){
      const idx=Date.now()+Math.floor(Math.random()*1000);
      ltTbody.insertAdjacentHTML("beforeend", filaLoteTpl(idx));
      const tr=ltTbody.querySelector(`tr[data-row="${idx}"]`);
      const inp=tr.querySelector(".lt-prod-buscar"), sug=tr.querySelector(".lt-sug");
      const hid=tr.querySelector(".lt-prod-id"), chosen=tr.querySelector(".lt-prod-chosen");
      makeSuggestionNavigator({
        inputEl: inp, listEl: sug, fetcher: buscarProductos,
        tpl: items=>items.slice(0,8).map((p,i)=>`<div class="sug" data-idx="${i}">${(p.sku||"")} — ${p.nombre||""}</div>`).join(""),
        onChoose: p=>{ hid.value=p.id; chosen.textContent=`${p.sku||""} — ${p.nombre||""}`; }
      });
    }
    document.getElementById("lt-add-row").addEventListener("click", ()=> makeLoteRow());
    ltTbody.addEventListener("click",(e)=>{ const b=e.target.closest(".lt-eliminar"); if(b){ b.closest("tr").remove(); }});
    makeLoteRow();
    document.getElementById("lt-guardar").addEventListener("click", async ()=>{
      ltMsg.textContent="";
      const items=[];
      ltTbody.querySelectorAll("tr").forEach(tr=>{
        const pid=Number(tr.querySelector(".lt-prod-id").value||"0");
        const tipo=tr.querySelector(".lt-tipo").value;
        const cant=Number(tr.querySelector(".lt-cant").value||"0");
        const mot=tr.querySelector(".lt-motivo").value||"";
        const ref=tr.querySelector(".lt-ref").value||"";
        if(pid && cant>0) items.push({ producto_id: pid, tipo, cantidad: cant, motivo: mot, referencia: ref });
      });
      if(!items.length){ ltMsg.textContent="Agregá al menos un ítem válido."; return; }
      try{
        await crearMovLote(items);
        ltMsg.textContent="Movimientos registrados.";
        ltTbody.innerHTML=""; makeLoteRow(); mvLoad();
      }catch(e){ ltMsg.textContent=e.message||"No se pudieron registrar los movimientos."; }
    });

    // ===== Kardex =====
    const kxInp = document.getElementById("kx-prod");
    const kxSug = document.getElementById("kx-sug");
    const kxPid = document.getElementById("kx-prod-id");
    const kxTbody = document.getElementById("kx-tbody");
    const kxInfo = document.getElementById("kx-info");
    let kxPage=1;

    makeSuggestionNavigator({
      inputEl: kxInp, listEl: kxSug, fetcher: buscarProductos,
      tpl: items=>items.slice(0,8).map((p,i)=>`<div class="sug" data-idx="${i}">${(p.sku||"")} — ${p.nombre||""}</div>`).join(""),
      onChoose: p=>{ kxPid.value=p.id; kxInp.value=`${p.sku||""} — ${p.nombre||""}`; }
    });

    async function kxLoad(){
      const pid = Number(kxPid.value||"0"); if(!pid) return;
      const per_page = Number(document.getElementById("kx-perpage").value||"10");
      const r = await kardex(pid, { page: kxPage, per_page, order: "desc" });
      const rows = r.data || [];
      const total = r.total || rows.length;
      kxTbody.innerHTML = rows.map(r=>`
        <tr>
          <td>${fmtDateIso(r.fecha)}</td>
          <td>${r.tipo}</td>
          <td>${Number(r.cantidad).toFixed(3)}</td>
          <td>${Number(r.saldo).toFixed(3)}</td>
          <td>${r.motivo||""}</td>
          <td>${r.referencia||""}</td>
        </tr>
      `).join("");
      const maxPage = Math.max(1, Math.ceil(total/per_page));
      kxInfo.textContent = `Página ${kxPage} de ${maxPage} — ${total} movs`;
      document.getElementById("kx-prev").disabled = (kxPage<=1);
      document.getElementById("kx-next").disabled = (kxPage>=maxPage);
    }
    document.getElementById("kx-ver").addEventListener("click", ()=>{ kxPage=1; kxLoad(); });
    document.getElementById("kx-prev").addEventListener("click", ()=>{ if(kxPage>1){ kxPage--; kxLoad(); }});
    document.getElementById("kx-next").addEventListener("click", ()=>{ kxPage++; kxLoad(); });
  }

  return { render };
})();
