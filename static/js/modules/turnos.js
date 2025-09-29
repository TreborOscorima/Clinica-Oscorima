/* global API, routeTitle, routeContent */
"use strict";

window.TurnosModule = (function () {
  // =========================
  // API helpers
  // =========================
  async function apiList(estado = "") {
    // Pedimos más registros para que la paginación client-side tenga varias páginas
    const params = new URLSearchParams();
    if (estado) params.append("estado", estado);
    params.append("limit", "500"); // si el backend lo soporta, nos da hasta 500
    const res = await API.request("/api/turnos" + (params.toString() ? `?${params}` : ""));
    // En nuestro wrapper res.data suele ser array
    return res.data || [];
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

  function sugTpl(list, tipo) {
    if (!list || !list.length) return `<div class="ac-list-empty">Sin resultados</div>`;
    return list
      .slice(0, 8)
      .map((item) => {
        if (tipo === "pac") {
          const label = `${item.nombre || (item.nombres ? item.nombres + " " + (item.apellidos || "") : "")} (${
            item.documento || "s/DNI"
          })`;
          return `<div class="sug" data-id="${item.id}" data-label="${label}">${label}</div>`;
        } else if (tipo === "pro") {
          const label = `${(item.nombres || "") + " " + (item.apellidos || "")} (${item.dni || "s/DNI"})`;
          return `<div class="sug" data-id="${item.id}" data-label="${label}">${label}</div>`;
        } else {
          // servicio
          const label = `${item.nombre} - ${money(item.precio || 0)}${
            item.duracion_min ? ` (${item.duracion_min} min)` : ``
          }`;
          return `<div class="sug" data-id="${item.id}" data-nombre="${item.nombre}" data-precio="${
            item.precio || 0
          }" data-duracion="${item.duracion_min || ""}" data-label="${label}">${label}</div>`;
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
      <div class="page-shell turnos-page">
        <section class="section-block">
          <article class="card form-card">
            <header class="card__header">
              <p class="card__eyebrow">Gestion de turnos</p>
              <h2 class="card__title">Registrar turno</h2>
              <p class="card__subtitle">Completa los datos del paciente, asigna los servicios y guarda el turno.</p>
            </header>

            <div class="card__body">
              <div class="form-grid form-grid--three turnos-form-head">
                <div class="form-field">
                  <label class="form-field__label">Paciente</label>
                  <div class="input-group">
                    <div class="input-group__column">
                      <span class="input-group__label">Nombre y apellido</span>
                      <div class="auto-complete">
                        <input id="t-pac-buscar" placeholder="Ej: Ana Perez" autocomplete="off" />
                        <div id="t-pac-sug" class="ac-list" style="display:none"></div>
                      </div>
                    </div>
                    <div class="input-group__column input-group__column--compact">
                      <span class="input-group__label">DNI</span>
                      <div class="auto-complete auto-complete--mini">
                        <input id="t-pac-dni" placeholder="DNI" autocomplete="off" inputmode="numeric" />
                        <div id="t-pac-dni-sug" class="ac-list" style="display:none"></div>
                      </div>
                    </div>
                  </div>
                  <input id="t-paciente-id" type="hidden" />
                  <p id="t-pac-chosen" class="form-field__note"></p>
                </div>

                <!-- 1) FECHA centrada (clase form-field--center) -->
                <div class="form-field form-field--center">
                  <label class="form-field__label" for="t-fecha">Fecha y hora</label>
                  <input id="t-fecha" class="input" type="datetime-local" />
                </div>

                <div class="form-field">
                  <label class="form-field__label">Profesional (opcional)</label>
                  <div class="input-group">
                    <div class="input-group__column">
                      <span class="input-group__label">Nombre y apellido</span>
                      <div class="auto-complete">
                        <input id="t-pro-buscar" placeholder="Ej: Dra. Lopez" autocomplete="off" />
                        <div id="t-pro-sug" class="ac-list" style="display:none"></div>
                      </div>
                    </div>
                    <div class="input-group__column input-group__column--compact">
                      <span class="input-group__label">DNI</span>
                      <div class="auto-complete auto-complete--mini">
                        <input id="t-pro-dni" placeholder="DNI" autocomplete="off" inputmode="numeric" />
                        <div id="t-pro-dni-sug" class="ac-list" style="display:none"></div>
                      </div>
                    </div>
                  </div>
                  <input id="t-prof-id" type="hidden" />
                  <p id="t-pro-chosen" class="form-field__note"></p>
                </div>
              </div>

              <hr class="section-divider" />

              <div class="card-section">
                <h3 class="card-section__title">Servicios del turno</h3>
                <div class="card-section__body">
                  <!-- 2) GRID ordenado y responsive -->
                  <div class="form-grid form-grid--services">
                    <div class="form-field">
                      <label class="form-field__label">Servicio</label>
                      <div class="auto-complete">
                        <input id="t-srv-buscar" placeholder="Ej: Botox" autocomplete="off" />
                        <div id="t-srv-sug" class="ac-list" style="display:none"></div>
                      </div>
                      <input id="t-servicio-id" type="hidden" />
                      <p id="t-srv-chosen" class="form-field__note"></p>
                    </div>
                    <div class="form-field">
                      <label class="form-field__label" for="t-item-precio">Precio</label>
                      <input id="t-item-precio" class="input" type="number" step="0.01" placeholder="Precio" />
                    </div>
                    <div class="form-field">
                      <label class="form-field__label" for="t-item-cant">Cantidad</label>
                      <input id="t-item-cant" class="input" type="number" step="0.01" value="1" min="1" />
                    </div>
                    <div class="form-field">
                      <label class="form-field__label" for="t-item-desc">Descuento</label>
                      <input id="t-item-desc" class="input" type="number" step="0.01" value="0" min="0" />
                    </div>
                    <div class="form-field form-field--cta">
                      <button id="t-item-add" type="button" class="button button--primary">Agregar servicio</button>
                    </div>
                  </div>

                  <div class="table-shell">
                    <table class="table table--compact">
                      <thead>
                        <tr><th>Servicio</th><th>Precio</th><th>Cant.</th><th>Desc.</th><th>Subtotal</th><th></th></tr>
                      </thead>
                      <tbody id="t-items"></tbody>
                      <tfoot>
                        <tr class="table__summary">
                          <td colspan="4" class="table__summary-label">Total</td>
                          <td id="t-total" class="table__summary-value">S/ 0.00</td>
                          <td></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  <div class="form-actions turnos-actions">
                    <p id="t-msg" class="form-actions__feedback"></p>
                    <button id="t-crear" class="button button--primary">Guardar turno</button>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </section>

        <section class="section-block">
          <article class="card list-card">
            <header class="card__header">
              <p class="card__eyebrow">Gestion de turnos</p>
              <h2 class="card__title">Listado de turnos</h2>
              <p class="card__subtitle">Consulta los turnos mas recientes cargados en el sistema.</p>
            </header>
            <div class="card__body">
              <div class="card-section card-section--filters">
                <div class="form-field">
                  <label class="form-field__label" for="t-estado">Estado</label>
                  <select id="t-estado" class="input input--select">
                    <option value="">Todos</option>
                    <option value="pendiente">Pendiente</option>
                    <option value="confirmado">Confirmado</option>
                    <option value="cancelado">Cancelado</option>
                    <option value="atendido">Atendido</option>
                  </select>
                </div>
              </div>

              <div class="table-shell">
                <table class="table table--full">
                  <thead>
                    <tr><th>ID</th><th>Paciente</th><th>Servicios</th><th>Profesional</th><th>Fecha/Hora</th><th>Estado</th><th>Acciones</th></tr>
                  </thead>
                  <tbody id="t-tbody"></tbody>
                </table>
              </div>

              <!-- 3) Paginación UI -->
              <div id="t-pagination" class="table-pagination"></div>
            </div>
          </article>
        </section>

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
    const pacId = document.getElementById("t-paciente-id");
    const pacChosen = document.getElementById("t-pac-chosen");

    const proBuscar = document.getElementById("t-pro-buscar");
    const proSug = document.getElementById("t-pro-sug");
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

    let items = []; // {servicio_id, nombre, precio, cantidad, descuento}

    // ===== Listado + paginación (en memoria) =====
    let allRows = [];
    let currentPage = 1;
    let pageSize = 10;

    function paginate(data, page, size) {
      const total = data.length;
      const totalPages = Math.max(1, Math.ceil(total / size));
      const p = Math.min(Math.max(1, page), totalPages);
      const start = (p - 1) * size;
      const end = Math.min(start + size, total);
      return { slice: data.slice(start, end), page: p, total, totalPages, start: start + 1, end };
    }

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

    function renderTablePage() {
      const { slice, page, total, totalPages, start, end } = paginate(allRows, currentPage, pageSize);
      if (!total) {
        tbody.innerHTML = `<tr><td colspan="7" class="table__empty muted">Sin turnos</td></tr>`;
        paginationEl.innerHTML = "";
        return;
      }
      tbody.innerHTML = slice.map(rowTpl).join("");

      // ventana de 5 páginas
      const win = 5;
      let first = Math.max(1, page - Math.floor(win / 2));
      let last = Math.min(totalPages, first + win - 1);
      if (last - first + 1 < win) first = Math.max(1, last - win + 1);

      const numBtns = [];
      for (let p = first; p <= last; p++) {
        numBtns.push(
          `<button class="button ${p === page ? "is-current" : ""}" data-page="${p}" aria-label="Página ${p}">${p}</button>`
        );
      }

      paginationEl.innerHTML = `
        <div class="table-pagination__controls">
          <span class="table-pagination__info">Mostrando ${start}-${end} de ${total}</span>
          <div class="table-pagination__buttons">
            <button class="button" data-page="first" ${page === 1 ? "disabled" : ""}>«</button>
            <button class="button" data-page="prev" ${page === 1 ? "disabled" : ""}>‹</button>
            ${numBtns.join("")}
            <button class="button" data-page="next" ${page === totalPages ? "disabled" : ""}>›</button>
            <button class="button" data-page="last" ${page === totalPages ? "disabled" : ""}>»</button>
          </div>
        </div>
      `;
    }

    // Clicks de paginación (delegado)
    paginationEl.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-page]");
      if (!btn) return;
      const action = btn.getAttribute("data-page");
      const totalPages = Math.max(1, Math.ceil(allRows.length / pageSize));
      if (action === "first") currentPage = 1;
      else if (action === "prev") currentPage = Math.max(1, currentPage - 1);
      else if (action === "next") currentPage = Math.min(totalPages, currentPage + 1);
      else if (action === "last") currentPage = totalPages;
      else currentPage = Number(action) || 1;
      renderTablePage();
    });

    // =========================
    // Autocompletes
    // =========================
    let pacTimer = null, proTimer = null, srvTimer = null;
    const openList = (el) => (el.style.display = "block");
    const closeList = (el) => { el.style.display = "none"; el.innerHTML = ""; };

    // Paciente
    pacBuscar.addEventListener("input", () => {
      clearTimeout(pacTimer);
      const q = pacBuscar.value.trim();
      if (!q) { closeList(pacSug); return; }
      pacTimer = setTimeout(async () => {
        try { pacSug.innerHTML = sugTpl(await buscarPacientes(q), "pac"); openList(pacSug); }
        catch { closeList(pacSug); }
      }, 220);
    });
    pacBuscar.addEventListener("focus", () => { if (pacSug.innerHTML) openList(pacSug); });
    pacBuscar.addEventListener("blur", () => setTimeout(() => closeList(pacSug), 120));
    pacSug.addEventListener("mousedown", (e) => {
      const d = e.target.closest(".sug"); if (!d) return;
      pacId.value = d.dataset.id; pacChosen.textContent = d.dataset.label || ""; pacBuscar.value = d.dataset.label || "";
    });

    // Profesional
    proBuscar.addEventListener("input", () => {
      clearTimeout(proTimer);
      const q = proBuscar.value.trim();
      if (!q) { closeList(proSug); return; }
      proTimer = setTimeout(async () => {
        try { proSug.innerHTML = sugTpl(await buscarProfes(q), "pro"); openList(proSug); }
        catch { closeList(proSug); }
      }, 220);
    });
    proBuscar.addEventListener("focus", () => { if (proSug.innerHTML) openList(proSug); });
    proBuscar.addEventListener("blur", () => setTimeout(() => closeList(proSug), 120));
    proSug.addEventListener("mousedown", (e) => {
      const d = e.target.closest(".sug"); if (!d) return;
      proId.value = d.dataset.id; proChosen.textContent = d.dataset.label || ""; proBuscar.value = d.dataset.label || "";
    });

    // Servicios
    srvBuscar.addEventListener("input", () => {
      clearTimeout(srvTimer);
      const q = srvBuscar.value.trim();
      if (!q) { closeList(srvSug); return; }
      srvTimer = setTimeout(async () => {
        try { srvSug.innerHTML = sugTpl(await buscarServicios(q), "srv"); openList(srvSug); }
        catch { closeList(srvSug); }
      }, 220);
    });
    srvBuscar.addEventListener("focus", () => { if (srvSug.innerHTML) openList(srvSug); });
    srvBuscar.addEventListener("blur", () => setTimeout(() => closeList(srvSug), 120));
    srvSug.addEventListener("mousedown", (e) => {
      const d = e.target.closest(".sug"); if (!d) return;
      srvId.value = d.dataset.id; srvChosen.textContent = d.dataset.label || ""; srvBuscar.value = d.dataset.label || "";
      const p = Number(d.dataset.precio || 0);
      if (p > 0 && !iPrecio.value) iPrecio.value = p;
    });

    // Agregar item
    document.getElementById("t-item-add").addEventListener("click", () => {
      const sid = Number(srvId.value || 0);
      const nombre = srvBuscar.value.trim() || srvChosen.textContent.trim();
      const precio = Number(iPrecio.value || 0);
      const cantidad = Number(iCant.value || 1);
      const descuento = Number(iDesc.value || 0);
      if (!sid) { msg.textContent = "Elegí un servicio del listado"; setTimeout(() => (msg.textContent = ""), 1800); return; }
      if (cantidad <= 0) { msg.textContent = "Cantidad inválida"; setTimeout(() => (msg.textContent = ""), 1800); return; }
      items.push({ servicio_id: sid, nombre, precio, cantidad, descuento });
      // limpiar
      srvId.value = ""; srvBuscar.value = ""; srvChosen.textContent = "";
      iPrecio.value = ""; iCant.value = "1"; iDesc.value = "0";
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
        pacId.value = ""; pacBuscar.value = ""; pacChosen.textContent = "";
        proId.value = ""; proBuscar.value = ""; proChosen.textContent = "";
        items = []; renderItemsTable(items, itemsBody, totalEl);
        // refrescar listado
        await cargarListado(true);
        setTimeout(() => (msg.textContent = ""), 2000);
      } catch (e) {
        msg.textContent = `Error: ${e.message || e}`;
        setTimeout(() => (msg.textContent = ""), 2800);
      }
    });

    // Filtro por estado
    selEstado.addEventListener("change", () => cargarListado(true));

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
    async function cargarListado(resetPage = false) {
      tbody.innerHTML = `<tr><td colspan="7" class="table__empty muted">Cargando...</td></tr>`;
      try {
        const estado = selEstado.value || "";
        const data = await apiList(estado);
        // Orden descendente por id si viene mezclado
        allRows = Array.isArray(data) ? [...data].sort((a,b) => (b.id||0) - (a.id||0)) : [];
        if (resetPage) currentPage = 1;
        renderTablePage();
      } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="table__empty">Error cargando turnos: ${e.message || e}</td></tr>`;
        paginationEl.innerHTML = "";
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
