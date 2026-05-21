/* global API, routeTitle, routeContent */
"use strict";

window.TurnosModule = (function () {
  // ── API ──────────────────────────────────────────────────────────────
  const req = (path, opts) => API.request(path, opts);
  const apiList = ({ estado = "", page = 1, perPage = 10 } = {}) => {
    const p = new URLSearchParams({ page, per_page: perPage });
    if (estado) p.set("estado", estado);
    return req(`/api/turnos?${p}`);
  };
  const apiCreate    = (d)    => req("/api/turnos", { method: "POST", body: JSON.stringify(d) });
  const apiGetTurno  = (id)   => req(`/api/turnos/${id}`);
  const apiSetEstado = (id,d) => req(`/api/turnos/${id}/estado`, { method: "PUT", body: JSON.stringify(d) });
  const apiReprog    = (id,d) => req(`/api/turnos/${id}/reprogramar`, { method: "PUT", body: JSON.stringify(d) });
  const apiBuscarPac = (q)    => req(`/api/pacientes?q=${encodeURIComponent(q)}`).then(r => r.data || []);
  const apiBuscarPro = (q)    => req(`/api/profesionales?q=${encodeURIComponent(q)}`).then(r => r.data || []);
  const apiBuscarSrv = (q)    => req(`/api/servicios?q=${encodeURIComponent(q)}`).then(r => r.data || []);

  // ── Utils ─────────────────────────────────────────────────────────────
  const esc  = (s) => String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const money = (n) => Number(n || 0).toLocaleString("es-PE", { style:"currency", currency:"PEN" });
  const pad   = (n) => (n < 10 ? `0${n}` : n);
  function nowPlus(h) {
    const d = new Date(Date.now() + h * 3600000);
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  const ESTADOS = {
    pendiente:  { label:"Pendiente",   cls:"badge--warning" },
    confirmado: { label:"Confirmado",  cls:"badge--info"    },
    cancelado:  { label:"Cancelado",   cls:"badge--danger"  },
    atendido:   { label:"Atendido",    cls:"badge--success" },
  };
  const badge = (e) => {
    const s = ESTADOS[e] || { label: e, cls: "badge--neutral" };
    return `<span class="badge ${s.cls}">${s.label}</span>`;
  };

  // ── Autocomplete helper ───────────────────────────────────────────────
  function autocomplete({ input, dropdown, fetcher, onSelect, onClear }) {
    let timer;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      if (onClear) onClear();
      const q = input.value.trim();
      if (q.length < 2) { dropdown.innerHTML = ""; dropdown.hidden = true; return; }
      timer = setTimeout(async () => {
        try {
          const items = await fetcher(q);
          if (!items.length) { dropdown.innerHTML = `<div class="ac-empty">Sin resultados</div>`; dropdown.hidden = false; return; }
          dropdown.innerHTML = items.slice(0, 8).map(it => {
            const d = JSON.stringify(it).replace(/"/g, "&quot;");
            return `<div class="ac-item" data-item="${d}">${esc(it._label || it.nombre || `${it.nombres||""} ${it.apellidos||""}`.trim())}</div>`;
          }).join("");
          dropdown.hidden = false;
        } catch { dropdown.hidden = true; }
      }, 220);
    });
    dropdown.addEventListener("mousedown", (e) => {
      const el = e.target.closest(".ac-item");
      if (!el) return;
      e.preventDefault();
      const item = JSON.parse(el.dataset.item.replace(/&quot;/g, '"'));
      onSelect(item);
      dropdown.hidden = true;
      dropdown.innerHTML = "";
    });
    input.addEventListener("blur", () => setTimeout(() => { dropdown.hidden = true; }, 150));
    input.addEventListener("focus", () => { if (dropdown.innerHTML) dropdown.hidden = false; });
  }

  // ── State ─────────────────────────────────────────────────────────────
  let items = [];
  let rows  = [], currentPage = 1, pageSize = 10, totalPages = 1, totalItems = 0;
  let crTurnoId = null;

  // ── Render ─────────────────────────────────────────────────────────────
  function render() {
    routeTitle.textContent = "Turnos";
    routeContent.innerHTML = `
      <div class="module-layout">

        <!-- PANEL IZQUIERDO: formulario -->
        <aside class="module-panel module-panel--form">
          <div class="panel-header">
            <h2 class="panel-title">Nuevo turno</h2>
          </div>
          <div class="panel-body">

            <div class="field-group">
              <label class="field-label">Paciente</label>
              <div class="ac-wrap">
                <input id="t-pac" class="input" placeholder="Buscar por nombre o DNI" autocomplete="off"/>
                <div id="t-pac-dd" class="ac-dropdown" hidden></div>
                <input id="t-pac-id" type="hidden"/>
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">Fecha y hora</label>
              <input id="t-fecha" class="input" type="datetime-local"/>
            </div>

            <div class="field-group">
              <label class="field-label">Profesional</label>
              <div class="ac-wrap">
                <input id="t-pro" class="input" placeholder="Buscar profesional" autocomplete="off"/>
                <div id="t-pro-dd" class="ac-dropdown" hidden></div>
                <input id="t-pro-id" type="hidden"/>
              </div>
            </div>

            <div class="section-divider">
              <span class="section-divider__label">Servicios</span>
            </div>

            <div class="field-row">
              <div class="field-group field-group--grow">
                <div class="ac-wrap">
                  <input id="t-srv" class="input" placeholder="Buscar servicio..." autocomplete="off"/>
                  <div id="t-srv-dd" class="ac-dropdown" hidden></div>
                  <input id="t-srv-id"     type="hidden"/>
                  <input id="t-srv-precio" type="hidden"/>
                </div>
              </div>
              <div class="field-group" style="width:72px">
                <label class="field-label">Cant.</label>
                <input id="t-cant" class="input" type="number" value="1" min="1" step="1"/>
              </div>
              <div class="field-group" style="width:72px">
                <label class="field-label">Desc.</label>
                <input id="t-desc" class="input" type="number" value="0" min="0" step="0.01"/>
              </div>
            </div>
            <button id="t-add" type="button" class="button button--secondary button--sm">+ Agregar servicio</button>

            <div class="items-table-wrap" style="margin-top:12px">
              <table class="table table--compact">
                <thead><tr><th>Servicio</th><th>P.Unit</th><th>Cant</th><th>Sub</th><th></th></tr></thead>
                <tbody id="t-items-body"></tbody>
              </table>
              <div class="items-total" id="t-total">Total: S/ 0.00</div>
            </div>

            <p id="t-msg" class="field-feedback"></p>
            <button id="t-guardar" class="button button--primary button--full" style="margin-top:12px">Guardar turno</button>
          </div>
        </aside>

        <!-- PANEL DERECHO: listado -->
        <main class="module-panel module-panel--list">
          <div class="panel-header">
            <h2 class="panel-title">Listado de turnos</h2>
            <div class="panel-header__actions">
              <select id="t-filtro-estado" class="input input--sm" style="width:160px">
                <option value="">Todos los estados</option>
                <option value="pendiente">Pendiente</option>
                <option value="confirmado">Confirmado</option>
                <option value="atendido">Atendido</option>
                <option value="cancelado">Cancelado</option>
              </select>
            </div>
          </div>
          <div class="panel-body panel-body--table">
            <div class="table-wrap">
              <table class="table table--full">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Paciente</th>
                    <th>Servicios</th>
                    <th>Profesional</th>
                    <th>Fecha/Hora</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody id="t-tbody"></tbody>
              </table>
            </div>
            <div id="t-pagination" class="pagination-bar"></div>
          </div>
        </main>
      </div>

      <!-- Modal detalle -->
      <div id="t-modal-overlay" class="modal-overlay" aria-hidden="true">
        <div class="modal" role="dialog">
          <div class="modal__header">
            <h3 class="modal__title" id="t-modal-title">Detalle del turno</h3>
            <button class="modal__close" id="t-modal-close" aria-label="Cerrar">&times;</button>
          </div>
          <div class="modal__body" id="t-modal-body"></div>
          <div class="modal__footer">
            <button class="button button--ghost" id="t-modal-close2">Cerrar</button>
          </div>
        </div>
      </div>

      <!-- Modal cancelar/reprogramar -->
      <div id="t-cr-overlay" class="modal-overlay" aria-hidden="true">
        <div class="modal" role="dialog">
          <div class="modal__header">
            <h3 class="modal__title">Cancelar / Reprogramar</h3>
            <button class="modal__close" id="t-cr-close" aria-label="Cerrar">&times;</button>
          </div>
          <div class="modal__body">
            <div class="tab-group" style="margin-bottom:16px">
              <button class="button button--tab is-active" id="t-tab-can">Cancelar</button>
              <button class="button button--tab"           id="t-tab-rep">Reprogramar</button>
            </div>
            <div id="t-pane-can">
              <p class="field-hint">Escribí <strong>CANCELAR</strong> para confirmar.</p>
              <input id="t-can-texto"  class="input" placeholder="CANCELAR" style="margin-bottom:8px"/>
              <input id="t-can-motivo" class="input" placeholder="Motivo (opcional)"/>
            </div>
            <div id="t-pane-rep" style="display:none">
              <label class="field-label">Nueva fecha/hora</label>
              <input id="t-rep-fecha"  class="input" type="datetime-local" style="margin-bottom:8px"/>
              <label class="field-label">Estado post-reprogramación</label>
              <select id="t-rep-estado" class="input">
                <option value="pendiente">Pendiente</option>
                <option value="confirmado">Confirmado</option>
              </select>
            </div>
          </div>
          <div class="modal__footer">
            <button class="button button--ghost" id="t-cr-cancel">Cerrar</button>
            <button class="button button--primary" id="t-cr-apply">Aplicar</button>
          </div>
        </div>
      </div>
    `;

    // ── Refs ────────────────────────────────────────────────────────────
    const pacInput  = document.getElementById("t-pac");
    const pacDd     = document.getElementById("t-pac-dd");
    const pacId     = document.getElementById("t-pac-id");
    const proInput  = document.getElementById("t-pro");
    const proDd     = document.getElementById("t-pro-dd");
    const proId     = document.getElementById("t-pro-id");
    const srvInput  = document.getElementById("t-srv");
    const srvDd     = document.getElementById("t-srv-dd");
    const srvId     = document.getElementById("t-srv-id");
    const srvPrecio = document.getElementById("t-srv-precio");
    const cantEl    = document.getElementById("t-cant");
    const descEl    = document.getElementById("t-desc");
    const fechaEl   = document.getElementById("t-fecha");
    const addBtn    = document.getElementById("t-add");
    const itemsBody = document.getElementById("t-items-body");
    const totalEl   = document.getElementById("t-total");
    const msgEl     = document.getElementById("t-msg");
    const tbody     = document.getElementById("t-tbody");
    const filtroEst = document.getElementById("t-filtro-estado");
    const paginEl   = document.getElementById("t-pagination");

    fechaEl.value = nowPlus(1);
    items = [];

    // ── Autocompletes ───────────────────────────────────────────────────
    autocomplete({
      input: pacInput, dropdown: pacDd,
      fetcher: (q) => apiBuscarPac(q).then(list => list.map(p => ({
        ...p,
        _label: `${p.nombre || [p.nombres, p.apellidos].filter(Boolean).join(" ")} (${p.documento || p.dni || "s/doc"})`,
      }))),
      onClear: () => pacId.value = "",
      onSelect: (p) => {
        pacId.value = p.id;
        pacInput.value = p.nombre || `${p.nombres||""} ${p.apellidos||""}`.trim();
      },
    });

    autocomplete({
      input: proInput, dropdown: proDd,
      fetcher: (q) => apiBuscarPro(q).then(list => list.map(p => ({
        ...p,
        _label: `${p.nombres||""} ${p.apellidos||""}`.trim() || p.nombre,
      }))),
      onClear: () => proId.value = "",
      onSelect: (p) => {
        proId.value = p.id;
        proInput.value = `${p.nombres||""} ${p.apellidos||""}`.trim() || p.nombre;
      },
    });

    autocomplete({
      input: srvInput, dropdown: srvDd,
      fetcher: (q) => apiBuscarSrv(q).then(list => list.map(s => ({
        ...s,
        _label: `${s.nombre} — ${money(s.precio)}`,
      }))),
      onClear: () => { srvId.value = ""; srvPrecio.value = ""; },
      onSelect: (s) => {
        srvId.value = s.id;
        srvPrecio.value = s.precio || 0;
        srvInput.value = s.nombre;
        cantEl.focus();
      },
    });

    // ── Items list ──────────────────────────────────────────────────────
    function renderItems() {
      if (!items.length) {
        itemsBody.innerHTML = `<tr><td colspan="5" class="table__empty">Sin servicios</td></tr>`;
        totalEl.textContent = "Total: S/ 0.00";
        return;
      }
      let total = 0;
      itemsBody.innerHTML = items.map((it, i) => {
        const sub = Math.max(it.precio * it.cantidad - it.descuento, 0);
        total += sub;
        return `<tr>
          <td>${esc(it.nombre)}</td>
          <td>${money(it.precio)}</td>
          <td>${it.cantidad}</td>
          <td>${money(sub)}</td>
          <td><button class="button button--icon-sm" data-del="${i}" title="Quitar">&times;</button></td>
        </tr>`;
      }).join("");
      totalEl.textContent = `Total: ${money(total)}`;
    }
    renderItems();

    itemsBody.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-del]");
      if (!btn) return;
      items.splice(Number(btn.dataset.del), 1);
      renderItems();
    });

    addBtn.addEventListener("click", () => {
      if (!srvId.value) { flash(msgEl, "Seleccioná un servicio del listado."); return; }
      const cant = Number(cantEl.value || 1);
      const desc = Number(descEl.value || 0);
      if (cant <= 0) { flash(msgEl, "Cantidad inválida."); return; }
      items.push({ servicio_id: Number(srvId.value), nombre: srvInput.value, precio: Number(srvPrecio.value || 0), cantidad: cant, descuento: desc });
      srvId.value = ""; srvPrecio.value = ""; srvInput.value = "";
      cantEl.value = "1"; descEl.value = "0";
      renderItems();
    });

    // ── Guardar ──────────────────────────────────────────────────────────
    document.getElementById("t-guardar").addEventListener("click", async () => {
      if (!pacId.value)  { flash(msgEl, "Seleccioná un paciente."); return; }
      if (!fechaEl.value) { flash(msgEl, "Indicá fecha y hora."); return; }
      if (!items.length) { flash(msgEl, "Agregá al menos un servicio."); return; }
      try {
        const r = await apiCreate({
          paciente_id:   Number(pacId.value),
          profesional_id: proId.value ? Number(proId.value) : undefined,
          fecha_hora:    fechaEl.value,
          items: items.map(it => ({ servicio_id: it.servicio_id, precio: it.precio, cantidad: it.cantidad, descuento: it.descuento })),
        });
        flash(msgEl, `Turno #${r.id} creado.`, "ok");
        pacInput.value = ""; pacId.value = "";
        proInput.value = ""; proId.value = "";
        items = []; renderItems();
        cargar(1);
      } catch (e) {
        flash(msgEl, e.message || "Error al crear turno.");
      }
    });

    // ── Listado ──────────────────────────────────────────────────────────
    filtroEst.addEventListener("change", () => cargar(1));

    function rowHtml(t) {
      const srvStr = t.items && t.items.length
        ? t.items.map(it => `${esc(it.servicio_nombre || "-")} x${it.cantidad || 1}`).join(", ")
        : esc(t.servicio_nombre || "-");
      const proStr  = esc(t.profesional_nombre || "-");
      const fecha   = (t.fecha_hora || "").replace("T"," ").slice(0,16);
      return `<tr>
        <td>${t.id}</td>
        <td><strong>${esc(t.paciente_nombre || "-")}</strong><br><small class="muted">${esc(t.paciente_documento || "")}</small></td>
        <td>${srvStr}</td>
        <td>${proStr}</td>
        <td>${fecha}</td>
        <td>${badge(t.estado)}</td>
        <td class="table-actions">
          <button class="button button--ghost button--sm t-ver"  data-id="${t.id}">Ver</button>
          <button class="button button--ghost button--sm t-cr"   data-id="${t.id}">C/R</button>
          <button class="button button--primary button--sm t-cob" data-id="${t.id}">Cobrar</button>
        </td>
      </tr>`;
    }

    function renderTabla() {
      tbody.innerHTML = rows.length
        ? rows.map(rowHtml).join("")
        : `<tr><td colspan="7" class="table__empty">Sin turnos</td></tr>`;
      renderPaginacion();
    }

    function renderPaginacion() {
      if (!totalItems) { paginEl.innerHTML = `<span class="pagination-info">0 registros</span>`; return; }
      const s = (currentPage-1)*pageSize+1, e2 = Math.min(currentPage*pageSize, totalItems);
      let btns = "";
      const win = 5, f = Math.max(1, currentPage-2), l = Math.min(totalPages, f+win-1);
      for (let p=f; p<=l; p++) btns += `<button class="button button--sm ${p===currentPage?"is-current":""}" data-page="${p}">${p}</button>`;
      paginEl.innerHTML = `
        <span class="pagination-info">Mostrando ${s}-${e2} de ${totalItems}</span>
        <div class="pagination-btns">
          <button class="button button--sm" data-page="prev" ${currentPage===1?"disabled":""}>&#8249;</button>
          ${btns}
          <button class="button button--sm" data-page="next" ${currentPage===totalPages?"disabled":""}>&#8250;</button>
        </div>`;
    }

    paginEl.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-page]");
      if (!btn || btn.disabled) return;
      const a = btn.dataset.page;
      let p = currentPage;
      if (a === "prev") p = Math.max(1, p-1);
      else if (a === "next") p = Math.min(totalPages, p+1);
      else p = Number(a);
      if (p !== currentPage) cargar(p);
    });

    async function cargar(page = 1) {
      tbody.innerHTML = `<tr><td colspan="7" class="table__empty">Cargando...</td></tr>`;
      try {
        const r = await apiList({ estado: filtroEst.value, page, perPage: pageSize });
        rows = r.data || [];
        totalItems = r.total || rows.length;
        pageSize   = r.per_page || 10;
        totalPages = r.pages || 1;
        currentPage = r.page || page;
        renderTabla();
      } catch(e) {
        tbody.innerHTML = `<tr><td colspan="7" class="table__empty">Error: ${esc(e.message)}</td></tr>`;
      }
    }
    cargar();

    // ── Delegados tabla ──────────────────────────────────────────────────
    tbody.addEventListener("click", async (e) => {
      // Ver detalle
      const btnVer = e.target.closest(".t-ver");
      if (btnVer) {
        const id = Number(btnVer.dataset.id);
        try {
          const t = await apiGetTurno(id);
          const srvHtml = t.items && t.items.length
            ? `<ul class="detail-list">${t.items.map(it => {
                const sub = Math.max(Number(it.precio||0)*Number(it.cantidad||1)-Number(it.descuento||0),0);
                return `<li>${esc(it.servicio_nombre||"-")} — ${money(it.precio)} x${it.cantidad} = <strong>${money(sub)}</strong></li>`;
              }).join("")}</ul>`
            : `<p class="muted">Sin servicios</p>`;
          document.getElementById("t-modal-title").textContent = `Turno #${t.id}`;
          document.getElementById("t-modal-body").innerHTML = `
            <div class="detail-grid">
              <div><span class="detail-label">Paciente</span><span>${esc(t.paciente_nombre||t.paciente_id)}</span></div>
              <div><span class="detail-label">Profesional</span><span>${esc(t.profesional_nombre||"-")}</span></div>
              <div><span class="detail-label">Fecha/Hora</span><span>${(t.fecha_hora||"").replace("T"," ").slice(0,16)}</span></div>
              <div><span class="detail-label">Estado</span>${badge(t.estado)}</div>
            </div>
            <div style="margin-top:16px"><strong>Servicios</strong>${srvHtml}</div>`;
          openModal("t-modal-overlay");
        } catch(err) { alert(err.message); }
        return;
      }

      // Cancelar/Reprogramar
      const btnCR = e.target.closest(".t-cr");
      if (btnCR) {
        crTurnoId = Number(btnCR.dataset.id);
        document.getElementById("t-can-texto").value = "";
        document.getElementById("t-can-motivo").value = "";
        document.getElementById("t-rep-fecha").value = "";
        switchTab("can");
        openModal("t-cr-overlay");
        return;
      }

      // Cobrar → ir a caja
      const btnCob = e.target.closest(".t-cob");
      if (btnCob) {
        location.hash = `#/caja?turno_id=${btnCob.dataset.id}`;
        return;
      }
    });

    // ── Modal detalle ────────────────────────────────────────────────────
    ["t-modal-close","t-modal-close2"].forEach(id => {
      document.getElementById(id).addEventListener("click", () => closeModal("t-modal-overlay"));
    });
    document.getElementById("t-modal-overlay").addEventListener("click", (e) => {
      if (e.target.id === "t-modal-overlay") closeModal("t-modal-overlay");
    });

    // ── Modal CR ─────────────────────────────────────────────────────────
    document.getElementById("t-tab-can").addEventListener("click", () => switchTab("can"));
    document.getElementById("t-tab-rep").addEventListener("click", () => switchTab("rep"));
    ["t-cr-close","t-cr-cancel"].forEach(id => {
      document.getElementById(id).addEventListener("click", () => closeModal("t-cr-overlay"));
    });
    document.getElementById("t-cr-overlay").addEventListener("click", (e) => {
      if (e.target.id === "t-cr-overlay") closeModal("t-cr-overlay");
    });
    document.getElementById("t-cr-apply").addEventListener("click", async () => {
      if (!crTurnoId) return;
      const isCancelar = document.getElementById("t-pane-can").style.display !== "none";
      try {
        if (isCancelar) {
          if (document.getElementById("t-can-texto").value.trim() !== "CANCELAR")
            throw new Error('Escribí exactamente "CANCELAR"');
          await apiSetEstado(crTurnoId, {
            estado: "cancelado",
            motivo_cancelacion: document.getElementById("t-can-motivo").value.trim() || undefined,
          });
        } else {
          const fecha = document.getElementById("t-rep-fecha").value;
          if (!fecha) throw new Error("Indicá la nueva fecha/hora.");
          await apiReprog(crTurnoId, { fecha_hora: fecha, estado: document.getElementById("t-rep-estado").value });
        }
        closeModal("t-cr-overlay");
        cargar(currentPage);
      } catch(e) { alert(e.message); }
    });
  }

  // ── Helpers UI ────────────────────────────────────────────────────────
  function flash(el, msg, type = "err") {
    el.textContent = msg;
    el.className = `field-feedback ${type === "ok" ? "field-feedback--ok" : "field-feedback--err"}`;
    setTimeout(() => { el.textContent = ""; el.className = "field-feedback"; }, 3000);
  }
  function openModal(id) {
    const el = document.getElementById(id);
    if (el) { el.removeAttribute("aria-hidden"); el.classList.add("is-visible"); }
  }
  function closeModal(id) {
    const el = document.getElementById(id);
    if (el) { el.setAttribute("aria-hidden","true"); el.classList.remove("is-visible"); }
  }
  function switchTab(tab) {
    const isCan = tab === "can";
    document.getElementById("t-tab-can").classList.toggle("is-active", isCan);
    document.getElementById("t-tab-rep").classList.toggle("is-active", !isCan);
    document.getElementById("t-pane-can").style.display = isCan ? "" : "none";
    document.getElementById("t-pane-rep").style.display = isCan ? "none" : "";
  }

  return { render };
})();
