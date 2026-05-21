// static/js/modules/compras.js
window.ComprasModule = (function () {

  // ===== API =====
  const _API = window.API || {
    async request(path, opts = {}) {
      const token = localStorage.getItem("token") || sessionStorage.getItem("token") || "";
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

  async function apiBuscarProductos(q) {
    const res = await _API.request(`/api/inventario/productos?q=${encodeURIComponent(q || "")}`);
    return res.data || res || [];
  }
  async function apiListarCompras(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return _API.request(`/api/inventario/compras${qs ? `?${qs}` : ""}`);
  }
  async function apiGetCompra(id) {
    return _API.request(`/api/inventario/compras/${id}`);
  }
  async function apiCrearCompra(data) {
    return _API.request("/api/inventario/compras", { method: "POST", body: JSON.stringify(data) });
  }
  async function apiActualizarCompra(id, data) {
    return _API.request(`/api/inventario/compras/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  // ===== State =====
  let items = [];          // líneas del formulario
  let rows = [];           // lista de compras
  let pg = 1, pages = 1;
  let editingId = null;
  let acTimer = null;

  // ===== Helpers =====
  function money(n) {
    return Number(n || 0).toLocaleString("es-PE", { style: "currency", currency: "PEN" });
  }
  function fmtDate(s) {
    if (!s) return "-";
    return new Date(s).toLocaleDateString("es-PE", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  // ===== Render =====
  function render() {
    const routeTitle = document.getElementById("route-title");
    const routeContent = document.getElementById("route-content");
    if (routeTitle) routeTitle.textContent = "Compras";

    routeContent.innerHTML = `
      <div class="page-shell animate-in">
        <div class="module-layout">

          <!-- PANEL IZQUIERDO: Formulario -->
          <aside class="module-panel">
            <div class="panel-header">
              <h2 class="panel-title" id="cp-form-title">Nueva Compra</h2>
            </div>
            <div class="panel-body">
              <form id="cp-form" autocomplete="off" novalidate>

                <div class="field-group">
                  <label class="field-label" for="cp-proveedor">Proveedor</label>
                  <input id="cp-proveedor" class="input" type="text" placeholder="Nombre del proveedor" />
                </div>

                <div class="field-row">
                  <div class="field-group">
                    <label class="field-label" for="cp-tipo-doc">Tipo de doc.</label>
                    <select id="cp-tipo-doc" class="input">
                      <option value="boleta">Boleta</option>
                      <option value="factura">Factura</option>
                      <option value="ticket">Ticket</option>
                      <option value="otro">Otro</option>
                    </select>
                  </div>
                  <div class="field-group">
                    <label class="field-label" for="cp-numero">N° Documento</label>
                    <input id="cp-numero" class="input" type="text" placeholder="001-0001234" />
                  </div>
                </div>

                <div class="field-group">
                  <label class="field-label" for="cp-nro-registro">N° Registro (opcional)</label>
                  <input id="cp-nro-registro" class="input" type="text" placeholder="REG-0001" />
                </div>

                <div class="field-group">
                  <label class="field-label" for="cp-observacion">Observación</label>
                  <input id="cp-observacion" class="input" type="text" placeholder="Nota opcional" />
                </div>

                <div class="section-divider">
                  <span class="section-divider__label">Productos</span>
                </div>

                <!-- Buscador de producto para agregar -->
                <div class="field-group" style="position:relative">
                  <label class="field-label" for="cp-prod-search">Agregar producto</label>
                  <input id="cp-prod-search" class="input" type="text" placeholder="Buscar por nombre o SKU..." autocomplete="off" />
                  <div id="cp-prod-drop" class="ac-dropdown" hidden></div>
                </div>
                <div class="field-row">
                  <div class="field-group">
                    <label class="field-label" for="cp-prod-qty">Cantidad</label>
                    <input id="cp-prod-qty" class="input" type="number" min="0.001" step="0.001" value="1" />
                  </div>
                  <div class="field-group">
                    <label class="field-label" for="cp-prod-costo">Costo unitario (S/)</label>
                    <input id="cp-prod-costo" class="input" type="number" min="0" step="0.01" value="0" />
                  </div>
                  <div class="field-group" style="align-self:flex-end">
                    <button type="button" id="cp-add-item" class="button button--secondary">+ Agregar</button>
                  </div>
                </div>
                <p id="cp-prod-chosen" class="field-hint" style="margin-bottom:6px"></p>

                <!-- Tabla de ítems -->
                <div class="items-table-wrap" id="cp-items-wrap" style="display:none">
                  <table class="table table--sm">
                    <thead>
                      <tr>
                        <th>Producto</th>
                        <th>Cant.</th>
                        <th>Costo unit.</th>
                        <th>Subtotal</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody id="cp-items-tbody"></tbody>
                  </table>
                  <p class="items-total">Total: <strong id="cp-total">S/ 0.00</strong></p>
                </div>

                <p id="cp-msg" class="field-feedback--err" style="min-height:18px"></p>

                <div class="field-row" style="margin-top:4px">
                  <button type="submit" id="cp-btn-guardar" class="button button--primary button--full">Registrar compra</button>
                  <button type="button" id="cp-btn-cancel-ed" class="button button--ghost" style="display:none">Cancelar edición</button>
                </div>

              </form>
            </div>
          </aside>

          <!-- PANEL DERECHO: Historial -->
          <section class="module-panel">
            <div class="panel-header">
              <h2 class="panel-title">Historial de Compras</h2>
              <div style="display:flex;gap:8px;align-items:center">
                <input id="cp-search" class="input input--sm" type="search" placeholder="Buscar N° doc..." style="width:180px" />
                <button class="button button--ghost button--sm" id="cp-refresh" title="Actualizar" aria-label="Actualizar">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-5.66"/></svg>
                </button>
              </div>
            </div>
            <div class="panel-body panel-body--table">
              <table class="table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>N° Documento</th>
                    <th>Proveedor</th>
                    <th>Ítems</th>
                    <th>Total</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="cp-tbody"></tbody>
              </table>
              <p id="cp-empty" class="muted" style="padding:16px;display:none">Sin compras registradas.</p>
              <div class="pagination-bar" id="cp-pag" style="display:none">
                <span class="pagination-info" id="cp-pag-info"></span>
                <div class="pagination-btns">
                  <button class="button button--ghost button--sm" id="cp-pag-prev">Anterior</button>
                  <button class="button button--ghost button--sm" id="cp-pag-next">Siguiente</button>
                </div>
              </div>
            </div>
          </section>

        </div>

        <!-- Modal detalle -->
        <div class="modal-overlay" id="cp-detail-modal">
          <div class="modal modal--md">
            <div class="modal__header">
              <h3 class="modal__title" id="cp-detail-title">Detalle de compra</h3>
              <button class="modal__close" id="cp-detail-close" aria-label="Cerrar">&times;</button>
            </div>
            <div class="modal__body" id="cp-detail-body"></div>
          </div>
        </div>
      </div>
    `;

    _wireEvents();
    _loadList();
  }

  // ===== Wiring =====
  function _wireEvents() {
    const prodSearch = document.getElementById("cp-prod-search");
    const prodDrop   = document.getElementById("cp-prod-drop");
    const addBtn     = document.getElementById("cp-add-item");
    const form       = document.getElementById("cp-form");
    const searchEl   = document.getElementById("cp-search");
    const refreshBtn = document.getElementById("cp-refresh");
    const prevBtn    = document.getElementById("cp-pag-prev");
    const nextBtn    = document.getElementById("cp-pag-next");
    const cancelEdBtn = document.getElementById("cp-btn-cancel-ed");
    const detailClose = document.getElementById("cp-detail-close");
    const detailOverlay = document.getElementById("cp-detail-modal");

    // --- Autocomplete producto ---
    let chosenProduct = null;
    prodSearch.addEventListener("input", () => {
      chosenProduct = null;
      document.getElementById("cp-prod-chosen").textContent = "";
      clearTimeout(acTimer);
      const q = prodSearch.value.trim();
      if (q.length < 2) { prodDrop.hidden = true; prodDrop.innerHTML = ""; return; }
      acTimer = setTimeout(async () => {
        try {
          const results = await apiBuscarProductos(q);
          if (!results.length) {
            prodDrop.innerHTML = `<div class="ac-empty">Sin resultados</div>`;
            prodDrop.hidden = false;
            return;
          }
          prodDrop.innerHTML = results.map(p =>
            `<div class="ac-item" data-item='${JSON.stringify(p).replace(/'/g, "&#39;")}'>${p.nombre} <span class="muted" style="font-size:.8em">${p.sku || ""}</span></div>`
          ).join("");
          prodDrop.hidden = false;
        } catch { prodDrop.hidden = true; }
      }, 280);
    });

    prodDrop.addEventListener("mousedown", (e) => {
      const item = e.target.closest(".ac-item");
      if (!item) return;
      try { chosenProduct = JSON.parse(item.dataset.item); } catch {}
      prodSearch.value = chosenProduct ? chosenProduct.nombre : "";
      const hint = document.getElementById("cp-prod-chosen");
      if (chosenProduct) {
        hint.textContent = `SKU: ${chosenProduct.sku || "-"}  |  Stock actual: ${chosenProduct.stock_actual ?? "?"}`;
        // prefill last cost if available
        const costoEl = document.getElementById("cp-prod-costo");
        if (costoEl && chosenProduct.precio_costo) costoEl.value = Number(chosenProduct.precio_costo).toFixed(2);
      }
      prodDrop.hidden = true;
      prodDrop.innerHTML = "";
    });

    document.addEventListener("click", (e) => {
      if (!prodDrop.contains(e.target) && e.target !== prodSearch) {
        prodDrop.hidden = true;
      }
    });

    // --- Agregar ítem ---
    addBtn.addEventListener("click", () => {
      if (!chosenProduct) { _flash("cp-msg", "Seleccioná un producto de la lista.", "err"); return; }
      const qty   = parseFloat(document.getElementById("cp-prod-qty").value) || 0;
      const costo = parseFloat(document.getElementById("cp-prod-costo").value) || 0;
      if (qty <= 0) { _flash("cp-msg", "Cantidad debe ser mayor a 0.", "err"); return; }
      if (costo < 0) { _flash("cp-msg", "Costo no puede ser negativo.", "err"); return; }
      items.push({ producto_id: chosenProduct.id, nombre: chosenProduct.nombre, sku: chosenProduct.sku || "", cantidad: qty, costo_unitario: costo });
      chosenProduct = null;
      prodSearch.value = "";
      document.getElementById("cp-prod-chosen").textContent = "";
      document.getElementById("cp-prod-qty").value = "1";
      document.getElementById("cp-prod-costo").value = "0";
      _renderItems();
    });

    // --- Form submit ---
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const proveedor = (document.getElementById("cp-proveedor").value || "").trim();
      const tipo_doc  = document.getElementById("cp-tipo-doc").value;
      const numero    = (document.getElementById("cp-numero").value || "").trim() || undefined;
      const nro_registro = (document.getElementById("cp-nro-registro").value || "").trim() || undefined;
      const observacion  = (document.getElementById("cp-observacion").value || "").trim() || undefined;

      if (!items.length) { _flash("cp-msg", "Agregá al menos un producto.", "err"); return; }

      const payload = {
        proveedor_nombre: proveedor || undefined,
        tipo_doc,
        numero,
        nro_registro,
        observacion,
        items: items.map(it => ({ producto_id: it.producto_id, cantidad: it.cantidad, costo_unitario: it.costo_unitario })),
      };

      const btn = document.getElementById("cp-btn-guardar");
      btn.disabled = true;
      btn.textContent = "Guardando…";
      try {
        if (editingId) {
          await apiActualizarCompra(editingId, payload);
          _flash("cp-msg", "Compra actualizada.", "ok");
        } else {
          await apiCrearCompra(payload);
          _flash("cp-msg", "Compra registrada correctamente.", "ok");
        }
        _resetForm();
        _loadList();
      } catch (err) {
        _flash("cp-msg", err.message || "Error al guardar.", "err");
      } finally {
        btn.disabled = false;
        btn.textContent = editingId ? "Actualizar compra" : "Registrar compra";
      }
    });

    // --- Cancelar edición ---
    cancelEdBtn.addEventListener("click", _resetForm);

    // --- Búsqueda en lista ---
    let searchTimer;
    searchEl.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => { pg = 1; _loadList(); }, 350);
    });
    refreshBtn.addEventListener("click", () => { pg = 1; _loadList(); });
    prevBtn.addEventListener("click", () => { if (pg > 1) { pg--; _loadList(); } });
    nextBtn.addEventListener("click", () => { if (pg < pages) { pg++; _loadList(); } });

    // --- Modal detalle ---
    detailClose.addEventListener("click", () => _closeDetail());
    detailOverlay.addEventListener("click", (e) => { if (e.target === detailOverlay) _closeDetail(); });
  }

  // ===== Render items table =====
  function _renderItems() {
    const tbody  = document.getElementById("cp-items-tbody");
    const wrap   = document.getElementById("cp-items-wrap");
    const totEl  = document.getElementById("cp-total");
    if (!tbody) return;

    if (!items.length) { wrap.style.display = "none"; return; }
    wrap.style.display = "";

    let total = 0;
    tbody.innerHTML = items.map((it, i) => {
      const sub = it.cantidad * it.costo_unitario;
      total += sub;
      return `
        <tr>
          <td>${it.nombre} <span class="muted" style="font-size:.8em">${it.sku}</span></td>
          <td>${it.cantidad}</td>
          <td>${money(it.costo_unitario)}</td>
          <td>${money(sub)}</td>
          <td><button type="button" class="button--icon-sm" data-rm="${i}" title="Quitar">✕</button></td>
        </tr>`;
    }).join("");

    totEl.textContent = money(total);

    tbody.querySelectorAll("[data-rm]").forEach(btn => {
      btn.addEventListener("click", () => {
        items.splice(parseInt(btn.dataset.rm), 1);
        _renderItems();
      });
    });
  }

  // ===== Load list =====
  async function _loadList() {
    const tbody  = document.getElementById("cp-tbody");
    const emptyEl = document.getElementById("cp-empty");
    const pagEl  = document.getElementById("cp-pag");
    if (!tbody) return;

    const q = (document.getElementById("cp-search") || {}).value || "";
    tbody.innerHTML = `<tr><td colspan="6" class="muted" style="padding:14px">Cargando…</td></tr>`;

    try {
      const res = await apiListarCompras({ page: pg, per_page: 10, q });
      rows  = res.data || [];
      pages = res.pages || 1;

      if (!rows.length) {
        tbody.innerHTML = "";
        if (emptyEl) emptyEl.style.display = "";
        if (pagEl) pagEl.style.display = "none";
        return;
      }
      if (emptyEl) emptyEl.style.display = "none";

      tbody.innerHTML = rows.map(c => {
        const prov = (c.proveedor && c.proveedor.nombre) ? c.proveedor.nombre : "-";
        const docLabel = `${c.tipo_doc || ""} ${c.numero || ""}`.trim() || "-";
        return `
          <tr>
            <td>${fmtDate(c.fecha)}</td>
            <td>${docLabel}</td>
            <td>${prov}</td>
            <td>${(c.items || []).length} producto${(c.items || []).length !== 1 ? "s" : ""}</td>
            <td>${money(c.total)}</td>
            <td>
              <button class="button--icon-sm" data-detail="${c.id}" title="Ver detalle">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              </button>
              <button class="button--icon-sm" data-edit="${c.id}" title="Editar">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
            </td>
          </tr>`;
      }).join("");

      // Paginación
      const pagInfo = document.getElementById("cp-pag-info");
      if (pagInfo) pagInfo.textContent = `Página ${pg} de ${pages}  (${res.total} registros)`;
      if (pagEl) pagEl.style.display = pages > 1 ? "" : "none";
      const prevBtn = document.getElementById("cp-pag-prev");
      const nextBtn = document.getElementById("cp-pag-next");
      if (prevBtn) prevBtn.disabled = pg <= 1;
      if (nextBtn) nextBtn.disabled = pg >= pages;

      // Botones de acción en tabla
      tbody.querySelectorAll("[data-detail]").forEach(btn => {
        btn.addEventListener("click", () => _openDetail(parseInt(btn.dataset.detail)));
      });
      tbody.querySelectorAll("[data-edit]").forEach(btn => {
        btn.addEventListener("click", () => _enterEdit(parseInt(btn.dataset.edit)));
      });

    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" class="muted">${err.message || "Error al cargar"}</td></tr>`;
    }
  }

  // ===== Detail modal =====
  async function _openDetail(id) {
    const overlay = document.getElementById("cp-detail-modal");
    const body    = document.getElementById("cp-detail-body");
    const title   = document.getElementById("cp-detail-title");
    if (!overlay) return;
    body.innerHTML = `<p class="muted">Cargando…</p>`;
    overlay.classList.add("is-visible");
    try {
      const c = await apiGetCompra(id);
      const prov = (c.proveedor && c.proveedor.nombre) ? c.proveedor.nombre : "-";
      const docLabel = `${c.tipo_doc || ""} ${c.numero || ""}`.trim() || "-";
      if (title) title.textContent = `Compra #${c.id}`;
      body.innerHTML = `
        <div class="detail-grid">
          <span class="detail-label">Fecha</span><span>${fmtDate(c.fecha)}</span>
          <span class="detail-label">Proveedor</span><span>${prov}</span>
          <span class="detail-label">Documento</span><span>${docLabel}</span>
          <span class="detail-label">N° Registro</span><span>${c.nro_registro || "-"}</span>
          <span class="detail-label">Observación</span><span>${c.observacion || "-"}</span>
          <span class="detail-label">Total</span><span><strong>${money(c.total)}</strong></span>
        </div>
        <div class="section-divider" style="margin:12px 0"><span class="section-divider__label">Productos</span></div>
        <table class="table table--sm">
          <thead><tr><th>Producto</th><th>SKU</th><th>Cant.</th><th>Costo unit.</th><th>Subtotal</th></tr></thead>
          <tbody>
            ${(c.items || []).map(it => {
              const prod = it.producto || {};
              return `<tr>
                <td>${prod.nombre || "-"}</td>
                <td>${prod.sku || "-"}</td>
                <td>${it.cantidad}</td>
                <td>${money(it.costo_unitario)}</td>
                <td>${money(it.subtotal)}</td>
              </tr>`;
            }).join("") || `<tr><td colspan="5" class="muted">Sin ítems</td></tr>`}
          </tbody>
        </table>`;
    } catch (err) {
      body.innerHTML = `<p class="muted">${err.message || "Error al cargar"}</p>`;
    }
  }

  function _closeDetail() {
    const overlay = document.getElementById("cp-detail-modal");
    if (overlay) overlay.classList.remove("is-visible");
  }

  // ===== Edit mode =====
  async function _enterEdit(id) {
    try {
      const c = await apiGetCompra(id);
      editingId = c.id;

      document.getElementById("cp-proveedor").value    = (c.proveedor && c.proveedor.nombre) ? c.proveedor.nombre : "";
      document.getElementById("cp-tipo-doc").value     = c.tipo_doc || "boleta";
      document.getElementById("cp-numero").value       = c.numero || "";
      document.getElementById("cp-nro-registro").value = c.nro_registro || "";
      document.getElementById("cp-observacion").value  = c.observacion || "";

      items = (c.items || []).map(it => ({
        producto_id: it.producto_id,
        nombre: (it.producto && it.producto.nombre) ? it.producto.nombre : `#${it.producto_id}`,
        sku: (it.producto && it.producto.sku) ? it.producto.sku : "",
        cantidad: it.cantidad,
        costo_unitario: it.costo_unitario,
      }));
      _renderItems();

      const title = document.getElementById("cp-form-title");
      if (title) title.textContent = `Editar Compra #${c.id}`;
      const saveBtn = document.getElementById("cp-btn-guardar");
      if (saveBtn) saveBtn.textContent = "Actualizar compra";
      const cancelBtn = document.getElementById("cp-btn-cancel-ed");
      if (cancelBtn) cancelBtn.style.display = "";

      document.getElementById("cp-form").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      alert(err.message || "Error al cargar la compra");
    }
  }

  function _resetForm() {
    editingId = null;
    items = [];
    const form = document.getElementById("cp-form");
    if (form) form.reset();
    _renderItems();
    const title = document.getElementById("cp-form-title");
    if (title) title.textContent = "Nueva Compra";
    const saveBtn = document.getElementById("cp-btn-guardar");
    if (saveBtn) { saveBtn.textContent = "Registrar compra"; saveBtn.disabled = false; }
    const cancelBtn = document.getElementById("cp-btn-cancel-ed");
    if (cancelBtn) cancelBtn.style.display = "none";
    const msg = document.getElementById("cp-msg");
    if (msg) msg.textContent = "";
    const hint = document.getElementById("cp-prod-chosen");
    if (hint) hint.textContent = "";
  }

  // ===== Flash message =====
  function _flash(elId, msg, type = "ok") {
    const el = document.getElementById(elId);
    if (!el) return;
    el.className = type === "ok" ? "field-feedback--ok" : "field-feedback--err";
    el.textContent = msg;
    setTimeout(() => { if (el) el.textContent = ""; }, 3500);
  }

  return { render };

})();
