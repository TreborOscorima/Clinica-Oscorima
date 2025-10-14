// static/js/modules/caja.js
"use strict";

window.CajaModule = (function () {
  // =======================
  // Config endpoints bAosqueda
  // =======================
  const SEARCH_ENDPOINTS = {
    producto: (q) => `/api/inventario/productos?q=${encodeURIComponent(q)}`,
    servicio: (q) => `/api/servicios?q=${encodeURIComponent(q)}`,
    paciente: (q) => `/api/pacientes?q=${encodeURIComponent(q)}`,
  };

  // =======================
  // API helper con token + headers extra
  // =======================
  const API = {
    async request(path, opts = {}) {
      const token =
        localStorage.getItem("token") ||
        sessionStorage.getItem("token") ||
        "";
      const base = opts.raw ? {} : { "Content-Type": "application/json" };
      const auth = token ? { Authorization: `Bearer ${token}` } : {};
      const headers = Object.assign({}, base, auth, opts.headers || {});
      const res = await fetch(path, { ...opts, headers });
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try { const j = await res.json(); msg = j.message || j.error || msg; } catch (_){}
        throw new Error(msg);
      }
      if (opts.raw) return res;
      const ct = res.headers.get("content-type") || "";
      return ct.includes("application/json") ? res.json() : res.text();
    },
    get(path) { return this.request(path); },
    post(path, body, extra = {}) {
      return this.request(path, { method: "POST", body: JSON.stringify(body), ...(extra || {}) });
    },
  };

  // =======================
  // Utils
  // =======================
  const money = (n) => `S/ ${Number(n || 0).toFixed(2)}`;
  const debounce = (fn, ms = 250) => { let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; };
  const makeIdem = () => (crypto.randomUUID ? crypto.randomUUID() : (Date.now()+"-"+Math.random().toString(16).slice(2)));

  // =======================
  // Estado / refs
  // =======================
  let items = [];
  let pagos = [];
  let pacienteSel = null;
  let descuento = { tipo: "none", valor: 0 };
  let currentTurnoId = null;
  let refs = {};

  // =======================
  // Helpers
  // =======================
  function getQueryParams(){
    const h = location.hash || "";
    const q = h.includes("?") ? h.split("?")[1] : "";
    const p = new URLSearchParams(q);
    const obj = {}; for (const [k,v] of p.entries()) obj[k]=v; return obj;
  }

  // =======================
  // Render principal
  // =======================
  function render() {
    const routeTitle = document.getElementById("route-title") || { textContent: "" };
    const routeContent = document.getElementById("route-content") || document.body;
    routeTitle.textContent = "Caja & Facturacion";

    routeContent.innerHTML = `

      <div class="page-shell caja-page">
        <section class="section-block">
          <article class="card form-card pos-card">
            <header class="card__header">
              <p class="card__eyebrow">Caja & Facturacion</p>
              <h2 class="card__title">Punto de venta</h2>
              <p class="card__subtitle">Registra consumos, aplica descuentos y cobra al instante.</p>
            </header>

            <div class="card__body">
              <div class="card-section">
                <h3 class="card-section__title">Datos del paciente</h3>
                <div class="card-section__body">
                  <div class="form-grid form-grid--four pos-grid pos-grid--patient">
                    <div class="form-field">
                      <label class="form-field__label">Paciente</label>
                      <div class="auto-complete">
                        <input id="pos-pac-q" class="input" placeholder="Buscar por nombre/DNI" autocomplete="off">
                        <div id="pos-pac-suggest" class="ac-list" style="display:none"></div>
                      </div>
                      <input type="hidden" id="pos-paciente-id">
                    </div>
                    <div class="form-field">
                      <label class="form-field__label">Documento</label>
                      <input id="pos-pac-doc" class="input" placeholder="DNI" autocomplete="off">
                    </div>
                    <div class="form-field">
                      <label class="form-field__label">Tipo comprobante</label>
                      <select id="pos-tipo" class="input input--select">
                        <option value="boleta">Boleta</option>
                        <option value="factura">Factura</option>
                        <option value="recibo">Recibo</option>
                      </select>
                    </div>
                    <div class="form-field form-field--cta">
                      <button id="pos-check-deuda" type="button" class="button button--ghost">Ver deuda</button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="card-section">
                <h3 class="card-section__title">Agregar item</h3>
                <div class="card-section__body">
                  <div class="form-grid form-grid--pos-items pos-grid">
                    <div class="form-field">
                      <label class="form-field__label">Tipo</label>
                      <select id="pos-item-tipo" class="input input--select">
                        <option value="producto">Producto</option>
                        <option value="servicio">Servicio</option>
                      </select>
                    </div>
                    <div class="form-field">
                      <label class="form-field__label">Buscar</label>
                      <div class="auto-complete">
                        <input id="pos-item-q" class="input" autocomplete="off" placeholder="Nombre o SKU">
                        <div id="pos-suggest" class="ac-list" style="display:none"></div>
                      </div>
                    </div>
                    <div class="form-field">
                      <label class="form-field__label">Cantidad</label>
                      <input id="pos-item-cant" class="input" type="number" step="0.01" min="0.01" value="1">
                    </div>
                    <div class="form-field">
                      <label class="form-field__label">Precio unitario</label>
                      <input id="pos-item-precio" class="input" type="number" step="0.01" min="0" placeholder="auto">
                    </div>
                    <div class="form-field form-field--cta">
                      <button id="pos-item-add" type="button" class="button button--primary">Agregar</button>
                    </div>
                  </div>

                  <div class="table-shell pos-items-table">
                    <table class="table" id="pos-tabla">
                      <thead>
                        <tr><th>Tipo</th><th>Descripción</th><th>Cantidad</th><th>Precio unitario</th><th class="right">Subtotal</th><th></th></tr>
                      </thead>
                      <tbody></tbody>
                      <tfoot>
                        <tr><td colspan="4" class="right"><b>Total</b></td><td id="pos-total" class="right">S/ 0.00</td><td></td></tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              </div>

              <div class="card-section">
                <h3 class="card-section__title">Descuento global</h3>
                <div class="card-section__body">
                  <div class="form-grid form-grid--three pos-grid pos-grid--discount">
                    <div class="form-field">
                      <label class="form-field__label">Tipo de descuento</label>
                      <select id="pos-dsc-tipo" class="input input--select">
                        <option value="none">Sin descuento</option>
                        <option value="porcentaje">% Porcentaje</option>
                        <option value="monto">Monto</option>
                      </select>
                    </div>
                    <div class="form-field">
                      <label class="form-field__label">Valor</label>
                      <input id="pos-dsc-valor" class="input" type="number" step="0.01" min="0" value="0">
                    </div>
                    <div class="form-field">
                      <label class="form-field__label">Resumen</label>
                      <div id="pos-dsc-res" class="pos-discount-summary">Subtotal: S/ 0.00 - Desc: S/ 0.00 - Total: S/ 0.00</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="card-section">
                <h3 class="card-section__title">Pagos</h3>
                <div class="card-section__body pos-payments">
                  <div id="pos-pagos" class="pos-payments__list"></div>
                  <div class="pos-payments__footer">
                    <button id="pos-add-pago" type="button" class="button button--ghost">Agregar pago</button>
                    <div class="pos-payments__totals"><b>Total pagado:</b> <span id="pos-pagado">S/ 0.00</span> &mdash; <b>Saldo:</b> <span id="pos-saldo">S/ 0.00</span></div>
                  </div>
                </div>
              </div>

              <div class="card-section">
                <h3 class="card-section__title">Observaciones</h3>
                <div class="card-section__body pos-observaciones">
                  <input id="pos-obs" class="input" placeholder="Opcional">
                  <div id="pos-res" class="form-feedback"></div>
                  <div class="pos-actions">
                    <button id="pos-emitir" type="button" class="button button--primary button--lg">Pagar y emitir comprobante</button>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </section>
      </div>
    `;
    refs = {
      pacQ: document.getElementById("pos-pac-q"),
      pacSug: document.getElementById("pos-pac-suggest"),
      pacId: document.getElementById("pos-paciente-id"),
      pacDoc: document.getElementById("pos-pac-doc"),
      tipoComp: document.getElementById("pos-tipo"),

      itemTipo: document.getElementById("pos-item-tipo"),
      itemQ: document.getElementById("pos-item-q"),
      itemCant: document.getElementById("pos-item-cant"),
      itemPrecio: document.getElementById("pos-item-precio"),
      itemAdd: document.getElementById("pos-item-add"),
      suggest: document.getElementById("pos-suggest"),

      tbody: document.querySelector("#pos-tabla tbody"),
      totalEl: document.getElementById("pos-total"),
      pagosBox: document.getElementById("pos-pagos"),
      addPagoBtn: document.getElementById("pos-add-pago"),
      pagadoEl: document.getElementById("pos-pagado"),
      saldoEl: document.getElementById("pos-saldo"),

      dscTipo: document.getElementById("pos-dsc-tipo"),
      dscValor: document.getElementById("pos-dsc-valor"),
      dscRes: document.getElementById("pos-dsc-res"),

      obs: document.getElementById("pos-obs"),
      res: document.getElementById("pos-res"),
      emitir: document.getElementById("pos-emitir"),
      checkDeuda: document.getElementById("pos-check-deuda"),
    };

    // Estado inicial
    items = [];
    pagos = [{ metodo: "efectivo", monto: 0 }];
    pacienteSel = null;
    if (refs.pacDoc) refs.pacDoc.value = "";
    descuento = { tipo: "none", valor: 0 };
    currentTurnoId = null;

    // wireup
    bindPaciente();
    bindItemSearch();
    bindPagos();
    bindDescuento();
    bindEmitir();
    bindAtajos();

    drawItems();
    drawPagos();
    recalc();

    prefillFromTurnoIfNeeded();
  }

  // =======================
  // Paciente
  // =======================
  function bindPaciente() {
    const { pacQ, pacSug, pacId, pacDoc } = refs;
    const show = (arr) => {
      if (!arr || !arr.length) { pacSug.style.display="none"; pacSug.innerHTML=""; return; }
      pacSug.style.display="block";
      pacSug.innerHTML = arr.map((p)=>{
        const id = p.id ?? p.paciente_id ?? "";
        const nombre = (p.nombre || ([p.nombres, p.apellidos].filter(Boolean).join(" ")) || p.label || "").trim();
        const doc = String(p.documento || p.dni || p.doc || "");
        const safeDocAttr = doc.replace(/"/g, "&quot;");
        const safeNameAttr = nombre.replace(/"/g, "&quot;");
        const docHtml = doc ? ` <span class="muted">${doc}</span>` : "";
        return `<div class="sug" data-id="${id}" data-name="${safeNameAttr}" data-doc="${safeDocAttr}">${nombre}${docHtml}</div>`;
      }).join("");
    };
    const runSearch = async (querySource) => {
      const raw = querySource !== undefined ? String(querySource || "") : (pacQ.value || "");
      const q = raw.trim();
      if (q.length < 2) { show([]); return; }
      try {
        const r = await API.get(SEARCH_ENDPOINTS.paciente(q));
        const arr = Array.isArray(r) ? r : (r.data || []);
        show(arr);
      } catch (_) {
        show([]);
      }
    };
    const debouncedSearch = debounce(runSearch, 250);
    const clearPacienteSel = () => {
      pacienteSel = null;
      pacId.value = "";
    };
    const onPacInput = () => {
      clearPacienteSel();
      if (pacDoc) pacDoc.value = "";
      debouncedSearch(pacQ.value);
    };
    pacQ.addEventListener("input", onPacInput);
    pacQ.addEventListener("focus", () => debouncedSearch(pacQ.value));
    pacQ.addEventListener("blur", () => setTimeout(() => pacSug.style.display = "none", 150));
    if (pacDoc) {
      const onDocInput = () => {
        clearPacienteSel();
        if (pacQ.value) pacQ.value = "";
        debouncedSearch(pacDoc.value);
      };
      pacDoc.addEventListener("input", onDocInput);
      pacDoc.addEventListener("focus", () => debouncedSearch(pacDoc.value));
      pacDoc.addEventListener("blur", () => setTimeout(() => pacSug.style.display = "none", 150));
    }
    pacSug.addEventListener("click",(e)=>{
      const el = e.target.closest(".sug"); if(!el) return;
      const documento = el.dataset.doc || "";
      const id = Number(el.dataset.id || "0");
      pacienteSel = { id: id, nombre: el.dataset.name || "", documento };
      pacId.value = pacienteSel.id || "";
      pacQ.value = pacienteSel.nombre || "";
      if (pacDoc) pacDoc.value = pacienteSel.documento || "";
      pacSug.style.display="none";
    });

    refs.checkDeuda.addEventListener("click", async ()=>{
      try{
        if (!pacienteSel || !pacienteSel.id) throw new Error("Seleccione un paciente");
        const r = await API.get(`/api/caja/deudas/paciente/${pacienteSel.id}`);
        const items = (r.items||[]).map(d=>`<tr><td>${d.comprobante_id}</td><td>${d.estado}</td><td class="right">${money(d.total)}</td><td class="right">${money(d.pagado)}</td><td class="right"><b>${money(d.saldo)}</b></td></tr>`);
        const html = `
          <h3>Deuda del paciente</h3>
          <div class="stat">Total pendiente: <b>${money(r.total_saldo || 0)}</b></div>
          <table class="table" style="margin-top:10px">
            <thead><tr><th>Comp.</th><th>Estado</th><th class="right">Total</th><th class="right">Pagado</th><th class="right">Saldo</th></tr></thead>
            <tbody>${items.join("") || `<tr><td colspan="5">Sin deudas</td></tr>`}</tbody>
          </table>`;
        const el = document.createElement("div"); el.innerHTML = html; const modalEl = document.createElement("div"); modalEl.className="cj-modal"; modalEl.innerHTML=`<div class="cj-modal__box"><div class="cj-modal__body">${html}</div><div class="cj-modal__footer"><button id="__modal_close__" type="button" class="button button--ghost">Cerrar</button></div></div>`; document.body.appendChild(modalEl); modalEl.addEventListener("click",(e)=>{ if(e.target.id==="__modal_close__"||e.target===modalEl) modalEl.remove(); });
      }catch(e){
        const m = document.createElement("div"); m.className="stat"; m.textContent = `No se pudo obtener la deuda: ${e.message}`; document.body.appendChild(m); setTimeout(()=>m.remove(),2500);
      }
    });
  }

  // =======================
  // BAosqueda de Atems
  // =======================
  function bindItemSearch() {
    const { itemTipo, itemQ, suggest, itemCant, itemPrecio, itemAdd } = refs;
    let selected = null;

    const show = (arr) => {
      if (!arr || !arr.length) { suggest.style.display="none"; suggest.innerHTML=""; return; }
      suggest.style.display="block";
      suggest.innerHTML = arr.map((x)=>{
        const id = x.id ?? x.servicio_id ?? x.producto_id;
        const nombre = x.nombre ?? x.descripcion ?? x.label ?? "";
        const safeNombre = nombre.replace(/"/g, '&quot;');
        const precio = Number(x.precio_venta ?? x.precio ?? x.costo ?? 0);
        return `<div class="sug" data-id="${id}" data-nombre="${safeNombre}" data-precio="${precio}">
            <span class="grow">${nombre}</span>
            <span class="muted">${money(precio)}</span>
        </div>`;
      }).join("");
    };

    const search = debounce(async ()=>{
      const q = itemQ.value.trim(); selected = null; if (q.length<2) return show([]);
      try{
        const ep = SEARCH_ENDPOINTS[itemTipo.value]; if (!ep) return show([]);
        const r = await API.get(ep(q)); const arr = Array.isArray(r)?r:(r.data||[]); show(arr);
      }catch(_){ show([]); }
    }, 250);

    itemQ.addEventListener("input", search);
    itemQ.addEventListener("focus", search);
    itemQ.addEventListener("blur", ()=>setTimeout(()=>suggest.style.display="none",150));
    suggest.addEventListener("click",(e)=>{
      const el = e.target.closest(".sug"); if(!el) return;
      selected = {
        id: Number(el.dataset.id),
        nombre: el.dataset.nombre,
        precio: Number(el.dataset.precio || 0),
      };
      itemQ.value = selected.nombre || "";
      if (!itemPrecio.value) itemPrecio.value = selected.precio || "";
      suggest.style.display="none";
    });

    itemAdd.addEventListener("click", ()=>{
      try{
        if (!selected || !selected.id) throw new Error("DebAs seleccionar un Atem del listado (con ID).");
        const cantidad = Number(itemCant.value || 0); if (cantidad <= 0) throw new Error("Cantidad invAlida");
        const precio = Number(itemPrecio.value || selected.precio || 0); if (precio < 0) throw new Error("Precio invAlido");
        items.push({ tipo: itemTipo.value, id: selected.id, nombre: selected.nombre, cantidad, precio });
        itemQ.value = ""; itemCant.value = "1"; itemPrecio.value = ""; selected = null;
        drawItems(); recalc();
      }catch(e){
        refs.res.textContent = e.message; setTimeout(()=>refs.res.textContent="", 2500);
      }
    });

    [itemQ, itemCant, itemPrecio].forEach(inp => inp.addEventListener("keydown",(e)=>{ if(e.key==="Enter"){ e.preventDefault(); itemAdd.click(); } }));
  }

  function drawItems(){
    const { tbody } = refs;
    if (!items.length){ tbody.innerHTML = `<tr><td colspan="6" class="muted">Sin items</td></tr>`; return recalc(); }
    tbody.innerHTML = items.map((it,i)=>`
      <tr>
        <td class="muted">${it.tipo}</td>
        <td>${it.nombre}</td>
        <td><input class="input input--sm it-cant" data-i="${i}" type="number" step="0.01" min="0.01" value="${it.cantidad}"></td>
        <td><input class="input input--sm it-precio" data-i="${i}" type="number" step="0.01" min="0" value="${it.precio}"></td>
        <td class="right">${money(it.cantidad * it.precio)}</td>
        <td class="right"><button type="button" class="button button--danger it-del" data-i="${i}">Quitar</button></td>
      </tr>`).join("");

    tbody.querySelectorAll(".it-cant").forEach(inp=> inp.addEventListener("input",(e)=>{ const i=Number(e.target.dataset.i); items[i].cantidad = Number(e.target.value||0); recalcRow(i); }));
    tbody.querySelectorAll(".it-precio").forEach(inp=> inp.addEventListener("input",(e)=>{ const i=Number(e.target.dataset.i); items[i].precio = Number(e.target.value||0); recalcRow(i); }));
    tbody.querySelectorAll(".it-del").forEach(btn=> btn.addEventListener("click",(e)=>{ const i=Number(e.target.dataset.i); items.splice(i,1); drawItems(); recalc(); }));
  }

  function recalcRow(i){
    const row = refs.tbody.querySelectorAll("tr")[i];
    if (row){ const it=items[i]; row.children[4].textContent = money(it.cantidad * it.precio); }
    recalc();
  }

  // =======================
  // Pagos
  // =======================
  function bindPagos(){
    const { addPagoBtn, pagosBox } = refs;

    addPagoBtn.addEventListener("click", ()=>{ pagos.push({ metodo:"efectivo", monto:0 }); drawPagos(); });

    pagosBox.addEventListener("input",(e)=>{
      const i = Number(e.target.dataset.i);
      if (e.target.classList.contains("pos-metodo")) pagos[i].metodo = e.target.value;
      else if (e.target.classList.contains("pos-monto")) pagos[i].monto = Number(e.target.value || 0);
      recalc();
    });

    pagosBox.addEventListener("click",(e)=>{
      if (e.target.classList.contains("pos-del")){
        const i = Number(e.target.dataset.i);
        pagos.splice(i,1); if (!pagos.length) pagos.push({ metodo:"efectivo", monto:0 });
        drawPagos(); recalc();
      }
    });
  }

  function drawPagos(){
    const { pagosBox } = refs;
    pagosBox.innerHTML = pagos.map((p,i)=>`
      <div class="pos-payments__item" data-i="${i}">
        <div class="form-field">
          <label class="form-field__label">Metodo</label>
          <select class="input input--select pos-metodo" data-i="${i}">
            <option value="efectivo"${p.metodo==="efectivo"?" selected":""}>Efectivo</option>
            <option value="tarjeta"${p.metodo==="tarjeta"?" selected":""}>Tarjeta</option>
            <option value="transferencia"${p.metodo==="transferencia"?" selected":""}>Transferencia</option>
            <option value="otro"${p.metodo==="otro"?" selected":""}>Otro</option>
          </select>
        </div>
        <div class="form-field">
          <label class="form-field__label">Monto</label>
          <input class="input pos-monto" data-i="${i}" type="number" step="0.01" min="0" value="${p.monto}">
        </div>
        <button type="button" class="button button--danger pos-del" data-i="${i}">Quitar</button>
      </div>`).join("");
  }

  // =======================
  // Descuento
  // =======================
  function bindDescuento(){
    const { dscTipo, dscValor } = refs;
    const onChange = ()=>{ descuento.tipo = dscTipo.value; descuento.valor = Number(dscValor.value||0); recalc(); };
    dscTipo.addEventListener("input", onChange);
    dscValor.addEventListener("input", onChange);
  }

  function recalc(){
    const subtotal = items.reduce((a,it)=> a + Number(it.cantidad||0)*Number(it.precio||0), 0);
    let desc = 0;
    if (descuento.tipo === "porcentaje"){
      const pct = Math.min(Math.max(Number(descuento.valor||0),0),100);
      desc = subtotal * (pct/100);
    } else if (descuento.tipo === "monto"){
      const m = Math.max(Number(descuento.valor||0),0);
      desc = Math.min(m, subtotal);
    }
    const total = subtotal - desc;
    const pagado = pagos.reduce((a,p)=> a + Number(p.monto||0), 0);
    const saldo = total - pagado;

    refs.totalEl.textContent = money(total);
    refs.pagadoEl.textContent = money(pagado);
    refs.saldoEl.textContent = money(saldo);
    refs.dscRes.textContent = `Subtotal: ${money(subtotal)} a Desc: ${money(desc)} a Total: ${money(total)}`;
  }

  // =======================
  // Prefill Turno
  // =======================
  async function prefillFromTurnoIfNeeded(){
    const params = getQueryParams();
    const tid = params.turno_id ? Number(params.turno_id) : null;
    if (!tid) return;

    try{
      const t = await API.get(`/api/turnos/${tid}`);
      if (t.paciente_id){
        const pacienteDocumento = (t.paciente_documento || t.paciente_doc || t.paciente_dni || "");
        pacienteSel = { id:Number(t.paciente_id), nombre: t.paciente_nombre || "", documento: pacienteDocumento };
        refs.pacId.value = pacienteSel.id;
        refs.pacQ.value = pacienteSel.nombre || (`Paciente #${pacienteSel.id}`);
        if (refs.pacDoc) refs.pacDoc.value = pacienteDocumento || "";
      }
      const turnItems = Array.isArray(t.items)&&t.items.length ? t.items : (
        t.servicio_id ? [{ servicio_id:t.servicio_id, precio:t.servicio_precio, cantidad:1, descuento:0, servicio_nombre:t.servicio_nombre }] : []
      );
      items = turnItems.map(it=>{
        const precioLista = Number(it.precio ?? it.servicio_precio ?? 0);
        const cant = Number(it.cantidad || 1);
        const desc = Number(it.descuento || 0);
        const precioUnit = Math.max(precioLista - (desc/cant || 0), 0);
        return { tipo:"servicio", id:Number(it.servicio_id), nombre: it.servicio_nombre || "Servicio", cantidad:cant, precio:precioUnit };
      });
      currentTurnoId = tid;
      pagos = [{ metodo:"efectivo", monto:0 }];
      drawItems(); drawPagos(); recalc();
    }catch(e){
      refs.res.textContent = `No se pudo prefillear desde el turno ${tid}: ${e.message||e}`;
      setTimeout(()=>refs.res.textContent="", 3000);
    }
  }

  // =======================
  // Emitir
  // =======================
  function bindEmitir(){
    refs.emitir.addEventListener("click", async ()=>{
      try{
        if (!items.length) throw new Error("AgregA al menos un Atem vAlido.");

        const payload = {
          tipo: refs.tipoComp.value,
          paciente_id: pacienteSel ? pacienteSel.id : null,
          observacion: (refs.obs.value || "").trim(),
          items: items.map(it=>({ tipo: it.tipo, id: it.id, nombre: it.nombre, cantidad: it.cantidad, precio: it.precio })),
          pagos: pagos.map(p=>({ metodo: p.metodo, monto: Number(p.monto || 0) })),
          descuento_tipo: descuento.tipo !== "none" ? descuento.tipo : null,
          descuento_valor: Number(descuento.valor || 0),
          turno_id: currentTurnoId || null,
        };

        refs.emitir.disabled = true;
        refs.res.textContent = "Emitiendo...";

        // NUEVO: Idempotency-Key para evitar duplicados por doble click/reintentos
        const idem = makeIdem();
        const r = await API.post("/api/caja/pos", payload, { headers: { "Idempotency-Key": idem } });

        refs.res.innerHTML = `a... Comprobante <b>${r?.comprobante?.numero || r?.comprobante?.id}</b> emitido. Total: <b>${money(r?.comprobante?.total || 0)}</b>. ${r?.pdf_url ? `<button id="pos-dlpdf" type="button" class="button button--ghost" style="margin-left:8px">Descargar PDF</button>` : ""}`;

        if (r?.pdf_url){
          const btn = document.getElementById("pos-dlpdf");
          btn.addEventListener("click", async ()=>{
            try{
              const res = await API.request(r.pdf_url, { raw:true });
              const blob = await res.blob(); const url = URL.createObjectURL(blob);
              const a = document.createElement("a"); a.href = url;
              const nombre = `${(r.comprobante?.tipo || "comp").toUpperCase()}_${r.comprobante?.numero || r.comprobante?.id}.pdf`;
              a.download = nombre; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
            }catch(e){ refs.res.textContent = `No se pudo descargar el PDF: ${e.message || e}`; }
          });
        }

        // limpiar
        items = []; pagos = [{ metodo:"efectivo", monto:0 }]; drawItems(); drawPagos(); refs.obs.value=""; descuento = { tipo:"none", valor:0 }; if (refs.dscTipo) refs.dscTipo.value="none"; if (refs.dscValor) refs.dscValor.value="0"; currentTurnoId = null; recalc();

      }catch(e){
        refs.res.textContent = `Error: ${e.message || e}`;
      }finally{
        refs.emitir.disabled = false;
      }
    });
  }

  // =======================
  // Atajos
  // =======================
  function bindAtajos(){
    const { itemQ, itemCant, itemPrecio, itemAdd } = refs;
    [itemQ, itemCant, itemPrecio].forEach(inp=> inp.addEventListener("keydown",(e)=>{ if(e.key==="Enter"){ e.preventDefault(); itemAdd.click(); } }));
    document.addEventListener("keydown",(e)=>{
      const el = document.activeElement;
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter"){
        if (el && el.id === "pos-obs") return;
        e.preventDefault(); refs.emitir.click();
      }
    });
  }

  return { render };
})();



