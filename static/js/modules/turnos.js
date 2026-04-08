/* global API, routeTitle, routeContent */
"use strict";

window.TurnosModule = (function () {
  // =========================
  // API helpers
  // =========================
  async function apiList({ estado = "", page = 1, perPage = 10 } = {}) {
    const params = new URLSearchParams();
    if (estado) params.append("estado", estado);
    params.append("page", String(page));
    params.append("per_page", String(perPage));
    return API.request("/api/turnos" + (params.toString() ? `?${params}` : ""));
  }
  async function apiCreate(data) {
    return API.request("/api/turnos", { method: "POST", body: JSON.stringify(data) });
  }
  async function apiSetEstado(id, body) {
    return API.request(`/api/turnos/${id}/estado`, { method: "PUT", body: JSON.stringify(body) });
  }
  async function apiGetTurno(id) {
    return API.request(`/api/turnos/${id}`);
  }
  async function apiReprogramar(id, body) {
    return API.request(`/api/turnos/${id}/reprogramar`, { method: "PUT", body: JSON.stringify(body) });
  }
  async function buscarPacientes(q) {
    const res = await API.request("/api/pacientes" + (q ? `?q=${encodeURIComponent(q)}` : ""));
    return res.data || [];
  }
  async function buscarProfes(q) {
    const res = await API.request("/api/profesionales" + (q ? `?q=${encodeURIComponent(q)}` : ""));
    return res.data || [];
  }
  async function buscarServicios(q) {
    const res = await API.request("/api/servicios" + (q ? `?q=${encodeURIComponent(q)}` : ""));
    return res.data || [];
  }

  // =========================
  // Utils
  // =========================
  function nowPlus(hours = 1) {
    const d = new Date(Date.now() + hours * 3600 * 1000);
    const pad = (n) => (n < 10 ? `0${n}` : n);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(
      d.getMinutes()
    )}`;
  }
  const money = (n) => Number(n || 0).toLocaleString("es-PE", { style: "currency", currency: "PEN" });

  const escHtml = (str) =>
    String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const escAttr = (str) => escHtml(str).replace(/"/g, "&quot;");

  function sugTpl(list, tipo) {
    if (!list || !list.length) return `<div class="ac-list-empty">Sin resultados</div>`;
    return list
      .slice(0, 8)
      .map((item) => {
        if (tipo === "pac") {
          const nombreRaw =
            (item.nombre && String(item.nombre).trim()) ||
            [item.nombres, item.apellidos].filter(Boolean).join(" ").trim();
          const nombre = nombreRaw || "Sin nombre";
          const documento = String(item.documento ?? item.dni ?? "").trim() || "s/DNI";
          const label = `${nombre} (${documento})`;
          return `<div class="sug" data-id="${escAttr(item.id ?? "")}" data-label="${escAttr(label)}" data-nombre="${escAttr(nombre)}" data-dni="${escAttr(documento)}">${escHtml(label)}</div>`;
        } else if (tipo === "pro") {
          const nombreRaw =
            `${item.nombres || ""} ${item.apellidos || ""}`.trim() ||
            (item.nombre ? String(item.nombre).trim() : "");
          const nombre = nombreRaw || "Sin nombre";
          const documento = String(item.dni ?? item.documento ?? "").trim() || "s/DNI";
          const label = `${nombre} (${documento})`;
          return `<div class="sug" data-id="${escAttr(item.id ?? "")}" data-label="${escAttr(label)}" data-nombre="${escAttr(nombre)}" data-dni="${escAttr(documento)}">${escHtml(label)}</div>`;
        } else {
          const nombre = String(item.nombre || "").trim();
          const precio = Number(item.precio || 0);
          const duracion = item.duracion_min ? ` (${item.duracion_min} min)` : ``;
          const label = `${nombre} - ${money(precio)}${duracion}`;
          return `<div class="sug" data-id="${escAttr(item.id ?? "")}" data-nombre="${escAttr(nombre)}" data-precio="${escAttr(item.precio ?? 0)}" data-duracion="${escAttr(item.duracion_min ?? "")}" data-label="${escAttr(label)}">${escHtml(label)}</div>`;
        }
      })
      .join("");
  }


  function renderItemsTable(items, targetBody, totalEl) {
    if (!items.length) {
      targetBody.innerHTML = `<tr><td colspan="6" class="table__empty muted">Sin servicios</td></tr>`;
      totalEl.textContent = money(0);
      return;
    }
    const rows = items
      .map((it, i) => {
        const precio = Number(it.precio || 0);
        const cant = Number(it.cantidad || 1);
        const desc = Number(it.descuento || 0);
        const sub = Math.max(precio * cant - desc, 0);
        return `<tr>
          <td>${it.nombre || it.servicio_nombre || "-"}</td>
          <td>${money(precio)}</td>
          <td>${cant}</td>
          <td>${money(desc)}</td>
          <td>${money(sub)}</td>
          <td class="table__actions"><button class="button button--danger t-item-del" data-i="${i}">Quitar</button></td>
        </tr>`;
      })
      .join("");
    targetBody.innerHTML = rows;
    const total = items.reduce((a, it) => {
      const precio = Number(it.precio || 0);
      const cant = Number(it.cantidad || 1);
      const desc = Number(it.descuento || 0);
      return a + Math.max(precio * cant - desc, 0);
    }, 0);
    totalEl.textContent = money(total);
  }

  // =========================
  // Main render
  // =========================
  function render() {
    routeTitle.textContent = "Turnos";
    routeContent.innerHTML = `
      <div class="page-shell turnos-page split-layout">
        <aside class="split-layout__sidebar">
          <article class="card form-card">
            <header class="card__header">
              <h2 class="card__title">Registrar turno</h2>
            </header>

            <div class="card__body">
              <div class="form-grid">
                <div class="form-field">
                  <label class="form-field__label" for="t-pac-buscar">Paciente</label>
                  <div class="auto-complete">
                    <input id="t-pac-buscar" class="input" placeholder="Ej: Ana Perez" autocomplete="off" />
                    <div id="t-pac-sug" class="ac-list" style="display:none"></div>
                  </div>
                  <input id="t-paciente-id" type="hidden" />
                </div>

                <div class="form-field">
                  <label class="form-field__label" for="t-pac-dni">DNI</label>
                  <input id="t-pac-dni" class="input" placeholder="DNI" autocomplete="off" inputmode="numeric" />
                </div>

                <div class="form-field">
                  <label class="form-field__label" for="t-fecha">Fecha y hora</label>
                  <input id="t-fecha" class="input" type="datetime-local" />
                </div>

                <div class="form-field">
                  <label class="form-field__label" for="t-pro-buscar">Profesional</label>
                  <div class="auto-complete">
                    <input id="t-pro-buscar" class="input" placeholder="Ej: Dra. Lopez" autocomplete="off" />
                    <div id="t-pro-sug" class="ac-list" style="display:none"></div>
                  </div>
                  <input id="t-prof-id" type="hidden" />
                </div>
              </div>

              <hr class="section-divider" style="margin: var(--space-3) 0" />

              <div class="card-section">
                <h3 class="card-section__title" style="font-size: .95rem;">Servicio</h3>
                <div class="card-section__body">
                  <div class="form-grid form-grid--two">
                    <div class="form-field form-field--full">
                      <div class="auto-complete">
                        <input id="t-srv-buscar" class="input" placeholder="Buscar servicio..." autocomplete="off" />
                        <div id="t-srv-sug" class="ac-list" style="display:none"></div>
                      </div>
                      <input id="t-servicio-id" type="hidden" />
                    </div>
                    
                    <div class="form-field" style="display:none">
                      <input id="t-item-precio" class="input" type="number" step="0.01" />
                    </div>

                    <div class="form-field">
                      <label class="form-field__label" for="t-item-cant">Cant.</label>
                      <input id="t-item-cant" class="input" type="number" step="0.01" value="1" min="1" />
                    </div>

                    <div class="form-field">
                      <label class="form-field__label" for="t-item-desc">Desc.</label>
                      <input id="t-item-desc" class="input" type="number" step="0.01" value="0" />
                    </div>

                    <div class="form-field form-field--cta form-field--full">
                      <button id="t-item-add" type="button" class="button button--secondary" style="width: 100%;">Agregar</button>
                    </div>
                  </div>

                  <div class="table-shell" style="max-height: 180px; margin-top: var(--space-2);">
                    <table class="table" style="font-size: 0.8rem;">
                      <thead><tr><th>Servicio</th><th>$$</th><th></th></tr></thead>
                      <tbody id="t-items"></tbody>
                    </table>
                  </div>
                  <div style="text-align: right; font-weight: bold; font-size: 0.95rem;" id="t-total">S/ 0.00</div>

                  <div class="form-actions turnos-actions" style="margin-top: var(--space-3);">
                    <p id="t-msg" class="form-actions__feedback"></p>
                    <button id="t-crear" class="button button--primary" style="width: 100%;">Guardar turno</button>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </aside>

        <main class="split-layout__main">
          <article class="card list-card" style="height: 100%;">
            <header class="card__header">
              <h2 class="card__title">Listado de turnos</h2>
            </header>
            <div class="card__body" style="flex: 1; display: flex; flex-direction: column;">
              <div class="card-section card-section--filters">
                <div class="form-field" style="max-width: 220px;">
                  <select id="t-estado" class="input input--select">
                    <option value="">Estado: Todos</option>
                    <option value="pendiente">Pendiente</option>
                    <option value="confirmado">Confirmado</option>
                    <option value="cancelado">Cancelado</option>
                    <option value="atendido">Atendido</option>
                  </select>
                </div>
              </div>

              <div class="table-shell grow">
                <table class="table table--full">
                  <thead>
                    <tr><th>ID</th><th>Paciente</th><th>Servicios</th><th>Profesional</th><th>Fecha/Hora</th><th>Estado</th><th>Acciones</th></tr>
                  </thead>
                  <tbody id="t-tbody"></tbody>
                </table>
              </div>

              <div id="t-pagination" class="table-pagination"></div>
            </div>
          </article>
        </main>

        <!-- Modales -->
        <div id="turno-modal-backdrop" class="dialog-backdrop"></div>
        <div id="turno-modal" class="dialog">
          <div class="dialog__panel">
            <div class="dialog__header"><strong id="turno-modal-title">Detalles del turno</strong></div>
            <div class="dialog__body" id="turno-modal-body"></div>
            <div class="dialog__footer">
              <button id="turno-modal-close" type="button" class="button button--ghost">Cerrar</button>
            </div>
          </div>
        </div>

        <div id="cr-backdrop" class="dialog-backdrop"></div>
        <div id="cr-modal" class="dialog">
          <div class="dialog__panel">
            <div class="dialog__header"><strong>Cancelar / Reprogramar turno</strong></div>
            <div class="dialog__body">
              <div class="tab-group">
                <button id="cr-tab-cancelar" class="button button--ghost">Cancelar</button>
                <button id="cr-tab-reprogramar" class="button button--ghost" style="opacity:.7">Reprogramar</button>
              </div>
              <div id="cr-pane-cancelar">
                <p>Para cancelar, escriba <b>CANCELAR</b> y opcionalmente indica un motivo.</p>
                <input id="cr-cancelar-texto" class="input" placeholder="Escriba: CANCELAR" />
                <input id="cr-cancelar-motivo" class="input" placeholder="Motivo (opcional)" />
              </div>
              <div id="cr-pane-reprogramar" style="display:none">
                <label class="form-field__label" for="cr-reprog-fecha">Nueva fecha/hora</label>
                <input id="cr-reprog-fecha" class="input" type="datetime-local" />
                <div class="muted">Estado post-reprogramación:</div>
                <select id="cr-reprog-estado" class="input input--select">
                  <option value="pendiente">Pendiente</option>
                  <option value="confirmado">Confirmado</option>
                </select>
              </div>
            </div>
            <div class="dialog__footer">
              <button id="cr-cerrar" type="button" class="button button--ghost">Cerrar</button>
              <button id="cr-guardar" type="button" class="button button--primary">Aplicar</button>
            </div>
          </div>
        </div>
      </div>
    `;

    // ====== refs ======
    const tbody = document.getElementById("t-tbody");
    const selEstado = document.getElementById("t-estado");
    const paginationEl = document.getElementById("t-pagination");
    const msg = document.getElementById("t-msg");

    const pacBuscar = document.getElementById("t-pac-buscar");
    const pacSug = document.getElementById("t-pac-sug");
    const pacDni = document.getElementById("t-pac-dni");
    const pacDniSug = document.getElementById("t-pac-dni-sug");
    const pacId = document.getElementById("t-paciente-id");
    const pacChosen = document.getElementById("t-pac-chosen");

    const proBuscar = document.getElementById("t-pro-buscar");
    const proSug = document.getElementById("t-pro-sug");
    const proDni = document.getElementById("t-pro-dni");
    const proDniSug = document.getElementById("t-pro-dni-sug");
    const proId = document.getElementById("t-prof-id");
    const proChosen = document.getElementById("t-pro-chosen");

    const fechaEl = document.getElementById("t-fecha");
    fechaEl.value = nowPlus(1);

    // Servicios
    const srvBuscar = document.getElementById("t-srv-buscar");
    const srvSug = document.getElementById("t-srv-sug");
    const srvId = document.getElementById("t-servicio-id");
    const srvChosen = document.getElementById("t-srv-chosen");
    const iPrecio = document.getElementById("t-item-precio");
    const iCant = document.getElementById("t-item-cant");
    const iDesc = document.getElementById("t-item-desc");
    const itemsBody = document.getElementById("t-items");
    const totalEl = document.getElementById("t-total");

    let items = [];

    // ===== Listado + paginación (servidor) =====
    let rows = [];
    let currentPage = 1;
    let pageSize = 10;
    let totalPages = 1;
    let totalItems = 0;

    function rowTpl(t) {
      const serviciosStr =
        (t.items && t.items.length
          ? t.items.map((it) => `${it.servicio_nombre || "-"} x${it.cantidad || 1}`).join(", ")
          : t.servicio_nombre || "-") || "-";
      const proStr = t.profesional_nombre || "-";
      const fechaStr = (t.fecha_hora || "").replace("T", " ").slice(0, 16);
      const estadoStr = (t.estado || "").toUpperCase();
      return `<tr>
        <td>${t.id}</td>
        <td>${t.paciente_nombre || "-"}<br><small class="muted">${t.paciente_documento || ""}</small></td>
        <td>${serviciosStr}</td>
        <td>${proStr}</td>
        <td>${fechaStr}</td>
        <td>${estadoStr}</td>
        <td class="table__actions">
          <button class="button button--ghost t-detalle" data-id="${t.id}">Detalle</button>
          <button class="button button--ghost t-cr" data-id="${t.id}">Cancelar/Reprogramar</button>
          <button class="button button--primary btn-cobrar" data-turno-id="${t.id}">Atender + Cobrar</button>
        </td>
      </tr>`;
    }

    function renderTable() {
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="table__empty muted">Sin turnos</td></tr>`;
        renderPagination();
        return;
      }
      tbody.innerHTML = rows.map(rowTpl).join("");
      renderPagination();
    }

    function renderPagination() {
      if (!totalItems) {
        paginationEl.innerHTML = `<div class="table-pagination__controls"><span class="table-pagination__info">Mostrando 0-0 de 0</span></div>`;
        return;
      }
      const start = (currentPage - 1) * pageSize + 1;
      const end = Math.min(currentPage * pageSize, totalItems);

      const win = 5;
      let first = Math.max(1, currentPage - Math.floor(win / 2));
      let last = Math.min(totalPages, first + win - 1);
      if (last - first + 1 < win) first = Math.max(1, last - win + 1);

      const numBtns = [];
      for (let p = first; p <= last; p++) {
        numBtns.push(
          `<button type="button" class="button ${p === currentPage ? "is-current" : ""}" data-page="${p}" aria-label="Página ${p}">${p}</button>`
        );
      }

      paginationEl.innerHTML = `
        <div class="table-pagination__controls">
          <span class="table-pagination__info">Mostrando ${start}-${end} de ${totalItems}</span>
          <div class="table-pagination__buttons">
            <button type="button" class="button" data-page="first" ${currentPage === 1 ? "disabled" : ""}>&laquo;</button>
            <button type="button" class="button" data-page="prev" ${currentPage === 1 ? "disabled" : ""}>&lsaquo;</button>
            ${numBtns.join("")}
            <button type="button" class="button" data-page="next" ${currentPage === totalPages ? "disabled" : ""}>&rsaquo;</button>
            <button type="button" class="button" data-page="last" ${currentPage === totalPages ? "disabled" : ""}>&raquo;</button>
          </div>
        </div>
      `;
    }

    paginationEl.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-page]");
      if (!btn || btn.disabled) return;
      const action = btn.getAttribute("data-page");
      let target = currentPage;
      if (action === "first") target = 1;
      else if (action === "prev") target = Math.max(1, currentPage - 1);
      else if (action === "next") target = Math.min(totalPages, currentPage + 1);
      else if (action === "last") target = totalPages;
      else target = Number(action) || 1;
      if (target === currentPage) return;
      cargarListado(target);
    });

    // =========================
    // Autocompletes
    // =========================
    const openList = (el) => { if (!el) return; el.style.display = "block"; };
    const closeList = (el) => { if (!el) return; el.style.display = "none"; el.innerHTML = ""; };
    function setupAutocomplete({ input, list, fetcher, type, minChars = 1, onSelect, onInput }) {
      if (!input || !list || typeof onSelect !== "function") return;
      let timer = null;
      input.addEventListener("input", () => {
        if (onInput) onInput();
        const q = input.value.trim();
        clearTimeout(timer);
        if (q.length < minChars) {
          closeList(list);
          return;
        }
        timer = setTimeout(async () => {
          try {
            const html = sugTpl(await fetcher(q), type);
            list.innerHTML = html;
            openList(list);
          } catch (err) {
            closeList(list);
          }
        }, 220);
      });
      input.addEventListener("focus", () => {
        if (list.innerHTML) openList(list);
      });
      input.addEventListener("blur", () => setTimeout(() => closeList(list), 120));
      list.addEventListener("mousedown", (e) => {
        const option = e.target.closest(".sug");
        if (!option) return;
        onSelect(option.dataset);
        closeList(list);
      });
    }

    const stripParenthesis = (val) => String(val || "").replace(/\s+\([^)]*\)\s*$/, "").trim();
    const toTrim = (val) => String(val || "").trim();

    const resetPacienteSelection = () => {
      pacId.value = "";
      pacChosen.textContent = "";
    };
    const applyPacienteSelection = (data) => {
      pacId.value = data.id || "";
      const nombre = stripParenthesis(data.nombre || data.label);
      pacBuscar.value = nombre;
      if (pacDni) pacDni.value = toTrim(data.dni);
      pacChosen.textContent = data.label || nombre;
    };
    setupAutocomplete({
      input: pacBuscar,
      list: pacSug,
      fetcher: buscarPacientes,
      type: "pac",
      onInput: () => {
        resetPacienteSelection();
        if (pacDni && document.activeElement === pacBuscar) pacDni.value = "";
      },
      onSelect: applyPacienteSelection,
    });
    setupAutocomplete({
      input: pacDni,
      list: pacDniSug,
      fetcher: buscarPacientes,
      type: "pac",
      onInput: () => {
        resetPacienteSelection();
        if (pacBuscar && document.activeElement === pacDni) pacBuscar.value = "";
      },
      onSelect: applyPacienteSelection,
    });

    const resetProfesionalSelection = () => {
      proId.value = "";
      proChosen.textContent = "";
    };
    const applyProfesionalSelection = (data) => {
      proId.value = data.id || "";
      const nombre = stripParenthesis(data.nombre || data.label);
      proBuscar.value = nombre;
      if (proDni) proDni.value = toTrim(data.dni);
      proChosen.textContent = data.label || nombre;
    };
    setupAutocomplete({
      input: proBuscar,
      list: proSug,
      fetcher: buscarProfes,
      type: "pro",
      onInput: () => {
        resetProfesionalSelection();
        if (proDni && document.activeElement === proBuscar) proDni.value = "";
      },
      onSelect: applyProfesionalSelection,
    });
    setupAutocomplete({
      input: proDni,
      list: proDniSug,
      fetcher: buscarProfes,
      type: "pro",
      onInput: () => {
        resetProfesionalSelection();
        if (proBuscar && document.activeElement === proDni) proBuscar.value = "";
      },
      onSelect: applyProfesionalSelection,
    });

    const resetServicioSelection = () => {
      srvId.value = "";
      srvChosen.textContent = "";
      iPrecio.value = "";
    };
    setupAutocomplete({
      input: srvBuscar,
      list: srvSug,
      fetcher: buscarServicios,
      type: "srv",
      onInput: resetServicioSelection,
      onSelect: (data) => {
        srvId.value = data.id || "";
        const nombre = toTrim(data.nombre || data.label);
        srvBuscar.value = nombre;
        srvChosen.textContent = data.label || nombre;
        if (Object.prototype.hasOwnProperty.call(data, "precio")) {
          const precioNum = Number(data.precio);
          if (!Number.isNaN(precioNum)) {
            let formatted = precioNum.toFixed(2);
            formatted = formatted.replace(/\.00$/, "").replace(/(\.\d)0$/, "$1");
            iPrecio.value = formatted;
          } else if (data.precio) {
            iPrecio.value = data.precio;
          }
        }
        if (!iCant.value || Number(iCant.value) <= 0) iCant.value = "1";
        iCant.focus();
      },
    });

    // Agregar item
    document.getElementById("t-item-add").addEventListener("click", () => {
      const sid = Number(srvId.value || 0);
      const nombre = srvBuscar.value.trim() || srvChosen.textContent.trim();
      const precio = Number(iPrecio.value || 0);
      const cantidad = Number(iCant.value || 1);
      const descuento = Number(iDesc.value || 0);
      if (!sid) {
        msg.textContent = "Elegí un servicio del listado";
        setTimeout(() => (msg.textContent = ""), 1800);
        return;
      }
      if (cantidad <= 0) {
        msg.textContent = "Cantidad inválida";
        setTimeout(() => (msg.textContent = ""), 1800);
        return;
      }
      items.push({ servicio_id: sid, nombre, precio, cantidad, descuento });
      srvId.value = "";
      srvBuscar.value = "";
      srvChosen.textContent = "";
      iPrecio.value = "";
      iCant.value = "1";
      iDesc.value = "0";
      renderItemsTable(items, itemsBody, totalEl);
      bindDelButtons();
    });

    function bindDelButtons() {
      itemsBody.querySelectorAll(".t-item-del").forEach((btn) =>
        btn.addEventListener("click", (e) => {
          const i = Number(e.currentTarget.dataset.i);
          items.splice(i, 1);
          renderItemsTable(items, itemsBody, totalEl);
          bindDelButtons();
        })
      );
    }

    // Guardar turno
    document.getElementById("t-crear").addEventListener("click", async () => {
      try {
        const payload = {
          paciente_id: Number(pacId.value || 0),
          profesional_id: proId.value ? Number(proId.value) : undefined,
          fecha_hora: document.getElementById("t-fecha").value,
          items: items.map((it) => ({
            servicio_id: it.servicio_id,
            precio: it.precio,
            cantidad: it.cantidad,
            descuento: it.descuento,
          })),
        };
        if (!payload.paciente_id) throw new Error("Seleccioná un paciente.");
        if (!payload.fecha_hora) throw new Error("Indicá fecha y hora.");
        if (!payload.items.length) throw new Error("Agregá al menos un servicio.");
        const r = await apiCreate(payload);
        msg.textContent = `Turno #${r.id} creado.`;
        // limpiar formulario
        pacId.value = ""; pacBuscar.value = ""; pacChosen.textContent = ""; if (pacDni) pacDni.value = "";
        proId.value = ""; proBuscar.value = ""; proChosen.textContent = ""; if (proDni) proDni.value = "";
        items = []; renderItemsTable(items, itemsBody, totalEl);
        // refrescar listado
        await cargarListado(1);
        setTimeout(() => (msg.textContent = ""), 2000);
      } catch (e) {
        msg.textContent = `Error: ${e.message || e}`;
        setTimeout(() => (msg.textContent = ""), 2800);
      }
    });

    // Filtro por estado
    selEstado.addEventListener("change", () => cargarListado(1));

    // Primera carga
    cargarListado();

    // =========================
    // Modales (detalle / cancelar-reprogramar)
    // =========================
    const modal = {
      back: document.getElementById("turno-modal-backdrop"),
      box: document.getElementById("turno-modal"),
      title: document.getElementById("turno-modal-title"),
      body: document.getElementById("turno-modal-body"),
      closeBtn: document.getElementById("turno-modal-close"),
      open(h, html) {
        this.title.textContent = h || "Detalle";
        this.body.innerHTML = html || "";
        this.back.style.display = "block";
        this.box.style.display = "flex";
      },
      close() {
        this.back.style.display = "none";
        this.box.style.display = "none";
      },
    };
    modal.closeBtn.addEventListener("click", () => modal.close());

    document.getElementById("cr-cerrar").addEventListener("click", () => closeCR());
    document.getElementById("cr-guardar").addEventListener("click", onGuardarCR());
    document.getElementById("cr-tab-cancelar").addEventListener("click", () => switchCR("cancelar"));
    document.getElementById("cr-tab-reprogramar").addEventListener("click", () => switchCR("reprogramar"));

    function switchCR(p) {
      const a = document.getElementById("cr-tab-cancelar");
      const b = document.getElementById("cr-tab-reprogramar");
      const pc = document.getElementById("cr-pane-cancelar");
      const pr = document.getElementById("cr-pane-reprogramar");
      if (p === "cancelar") {
        a.style.opacity = "1"; b.style.opacity = ".7"; pc.style.display = "block"; pr.style.display = "none";
      } else {
        a.style.opacity = ".7"; b.style.opacity = "1"; pc.style.display = "none"; pr.style.display = "block";
      }
    }

    let crTurnoId = null;
    function openCR(id) {
      crTurnoId = id;
      document.getElementById("cr-backdrop").style.display = "block";
      document.getElementById("cr-modal").style.display = "flex";
    }
    function closeCR() {
      crTurnoId = null;
      document.getElementById("cr-backdrop").style.display = "none";
      document.getElementById("cr-modal").style.display = "none";
    }
    function onGuardarCR() {
      return async () => {
        if (!crTurnoId) return;
        const paneCancelarVisible = document.getElementById("cr-pane-cancelar").style.display !== "none";
        try {
          if (paneCancelarVisible) {
            const texto = document.getElementById("cr-cancelar-texto").value.trim();
            const motivo = document.getElementById("cr-cancelar-motivo").value.trim();
            if (texto !== "CANCELAR") throw new Error('Escribí exactamente "CANCELAR"');
            await apiSetEstado(crTurnoId, { estado: "cancelado", motivo_cancelacion: motivo || undefined });
          } else {
            const nueva = document.getElementById("cr-reprog-fecha").value;
            const estado = document.getElementById("cr-reprog-estado").value || "pendiente";
            if (!nueva) throw new Error("Indicá la nueva fecha/hora.");
            await apiReprogramar(crTurnoId, { fecha_hora: nueva, estado });
          }
          closeCR();
          await cargarListado();
        } catch (e) {
          alert(e.message || e);
        }
      };
    }

    // =========================
    // Listado + fetch
    // =========================
    async function cargarListado(page = currentPage) {
      tbody.innerHTML = `<tr><td colspan="7" class="table__empty muted">Cargando...</td></tr>`;
      try {
        const estado = selEstado.value || "";
        const resp = await apiList({ estado, page, perPage: pageSize });
        const {
          data = [],
          page: respPage,
          per_page: respPerPage,
          pages: respPages,
          total: respTotal,
        } = resp || {};
        const rawRows = Array.isArray(data) ? data : Array.isArray(resp) ? resp : [];
        rows = Array.isArray(rawRows) ? rawRows : [];

        const perPageNumber = Number(respPerPage);
        if (Number.isFinite(perPageNumber) && perPageNumber > 0) {
          pageSize = perPageNumber;
        } else if (!pageSize || pageSize <= 0) {
          pageSize = 10;
        }

        const totalNumber = Number(respTotal);
        if (Number.isFinite(totalNumber) && totalNumber >= 0) {
          totalItems = totalNumber;
        } else {
          totalItems = rows.length;
        }

        const pagesNumber = Number(respPages);
        if (Number.isFinite(pagesNumber) && pagesNumber > 0) {
          totalPages = pagesNumber;
        } else {
          totalPages = Math.max(1, Math.ceil((totalItems || 0) / pageSize));
        }

        const pageNumber = Number(respPage);
        if (Number.isFinite(pageNumber) && pageNumber > 0) {
          currentPage = pageNumber;
        } else {
          currentPage = page;
        }
        currentPage = Math.min(Math.max(1, currentPage), totalPages || 1);

        renderTable();
      } catch (e) {
        rows = [];
        totalItems = 0;
        totalPages = 1;
        tbody.innerHTML = `<tr><td colspan="7" class="table__empty">Error cargando turnos: ${e.message || e}</td></tr>`;
        renderPagination();
      }
    }

    // Delegados tabla
    document.body.addEventListener("click", async (e) => {
      const btnDet = e.target.closest(".t-detalle");
      if (btnDet) {
        const id = Number(btnDet.dataset.id);
        try {
          const t = await apiGetTurno(id);
          const serviciosHtml =
            t.items && t.items.length
              ? `<ul>${t.items
                  .map((it) => {
                    const precio = Number(it.precio ?? it.servicio_precio_lista ?? 0);
                    const cant = Number(it.cantidad || 1);
                    const desc = Number(it.descuento || 0);
                    const sub = Math.max(precio * cant - desc, 0);
                    return `<li>${it.servicio_nombre || "-"} — ${money(precio)} x${cant} (desc ${money(
                      desc
                    )}) = <b>${money(sub)}</b></li>`;
                  })
                  .join("")}</ul>`
              : `<div class="muted">Sin items</div>`;
          const html = `
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
              <div><b>Paciente:</b> ${t.paciente_nombre || t.paciente_id}</div>
              <div><b>Profesional:</b> ${t.profesional_nombre || "-"}</div>
              <div><b>Fecha/Hora:</b> ${(t.fecha_hora || "").replace("T", " ").slice(0,16)}</div>
              <div><b>Estado:</b> ${(t.estado || "").toUpperCase()}</div>
            </div>
            <hr>
            <b>Servicios</b>
            ${serviciosHtml}
          `;
          const modal = {
            back: document.getElementById("turno-modal-backdrop"),
            box: document.getElementById("turno-modal"),
            title: document.getElementById("turno-modal-title"),
            body: document.getElementById("turno-modal-body"),
          };
          modal.title.textContent = `Turno #${t.id}`;
          modal.body.innerHTML = html;
          modal.back.style.display = "block";
          modal.box.style.display = "flex";
        } catch (err) {
          alert(err.message || err);
        }
        return;
      }

      const btnCR = e.target.closest(".t-cr");
      if (btnCR) { 
        const id = Number(btnCR.dataset.id);
        document.getElementById("cr-backdrop").style.display = "block";
        document.getElementById("cr-modal").style.display = "flex";
        // guardar id actual
        const ev = new CustomEvent("set-cr-id", { detail: { id } });
        document.dispatchEvent(ev);
        return;
      }

      const btnCobrar = e.target.closest(".btn-cobrar");
      if (btnCobrar) {
        const tid = btnCobrar.dataset.turnoId || btnCobrar.getAttribute("data-turno-id");
        if (!tid) return;
        location.hash = `#/caja?turno_id=${encodeURIComponent(tid)}&registrar_insumos=1`;
        return;
      }
    });

    // guardado simple de id para CR
    let crId = null;
    document.addEventListener("set-cr-id", (e) => { crId = e.detail.id; });
    document.getElementById("cr-cerrar").addEventListener("click", () => {
      document.getElementById("cr-backdrop").style.display = "none";
      document.getElementById("cr-modal").style.display = "none";
      crId = null;
    });
    document.getElementById("cr-guardar").addEventListener("click", async () => {
      try {
        const cancelarVisible = document.getElementById("cr-pane-cancelar").style.display !== "none";
        if (cancelarVisible) {
          const texto = document.getElementById("cr-cancelar-texto").value.trim();
          const motivo = document.getElementById("cr-cancelar-motivo").value.trim();
          if (texto !== "CANCELAR") throw new Error('Escribí exactamente "CANCELAR"');
          await apiSetEstado(crId, { estado: "cancelado", motivo_cancelacion: motivo || undefined });
        } else {
          const nueva = document.getElementById("cr-reprog-fecha").value;
          const estado = document.getElementById("cr-reprog-estado").value || "pendiente";
          if (!nueva) throw new Error("Indicá la nueva fecha/hora.");
          await apiReprogramar(crId, { fecha_hora: nueva, estado });
        }
        document.getElementById("cr-backdrop").style.display = "none";
        document.getElementById("cr-modal").style.display = "none";
        crId = null;
        await cargarListado();
      } catch (e) {
        alert(e.message || e);
      }
    });
  }

  // API pública
  return { render };
})();
