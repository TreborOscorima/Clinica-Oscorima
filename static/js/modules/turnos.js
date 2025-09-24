// static/js/modules/turnos.js
/* global API, routeTitle, routeContent */
"use strict";

window.TurnosModule = (function () {
  // =========================
  // API helpers
  // =========================
  async function apiList(estado = "") {
    const q = estado ? `?estado=${encodeURIComponent(estado)}` : "";
    const res = await API.request("/api/turnos" + q);
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
  // UI helpers
  // =========================
  function nowPlus(hours = 1) {
    const d = new Date(Date.now() + hours * 3600 * 1000);
    const pad = (n) => (n < 10 ? `0${n}` : n);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(
      d.getMinutes()
    )}`;
  }
  const money = (n) => (Number(n || 0)).toLocaleString("es-AR", { style: "currency", currency: "ARS" });

  const debounce = (fn, ms = 250) => {
    let t;
    return (...a) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...a), ms);
    };
  };

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
      targetBody.innerHTML = `<tr><td colspan="6" class="muted">Sin servicios</td></tr>`;
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
          <td class="text-right">${money(precio)}</td>
          <td class="text-right">${cant}</td>
          <td class="text-right">${money(desc)}</td>
          <td class="text-right">${money(sub)}</td>
          <td class="table-actions table-actions--compact"><button class="btn btn-danger t-item-del" data-i="${i}">X</button></td>
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
      <section class="card turnos-card">
        <header class="card-header">
          <h3>Filtrar turnos</h3>
          <p class="card-subtitle">Aplicá filtros para priorizar la gestión diaria.</p>
        </header>
        <div class="form-row">
          <label for="t-estado">Estado</label>
          <select id="t-estado">
            <option value="">Todos</option>
            <option value="pendiente">Pendiente</option>
            <option value="confirmado">Confirmado</option>
            <option value="cancelado">Cancelado</option>
            <option value="atendido">Atendido</option>
          </select>
        </div>
      </section>

      <section class="card turnos-card">
        <header class="card-header">
          <h3>Nuevo Turno</h3>
          <p class="card-subtitle">Completá los datos para agendar un nuevo turno.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row">
            <label for="t-pac-buscar">Paciente (DNI o nombre)</label>
            <div class="ac-wrap">
              <input id="t-pac-buscar" placeholder="Ej: 12345678 o Ana Pérez" autocomplete="off">
              <div id="t-pac-sug" class="suggest ac-list" style="display:none"></div>
            </div>
            <input id="t-paciente-id" type="hidden">
            <div id="t-pac-chosen" class="muted"></div>
          </div>
          <div class="form-row">
            <label for="t-fecha">Fecha/Hora</label>
            <input id="t-fecha" type="datetime-local">
          </div>
          <div class="form-row">
            <label for="t-pro-buscar">Profesional (DNI o nombre) — opcional</label>
            <div class="ac-wrap">
              <input id="t-pro-buscar" placeholder="Ej: 56789012 o Dra. López" autocomplete="off">
              <div id="t-pro-sug" class="suggest ac-list" style="display:none"></div>
            </div>
            <input id="t-prof-id" type="hidden">
            <div id="t-pro-chosen" class="muted"></div>
          </div>
        </div>

        <hr class="card-divider">
        <header class="section-header">
          <h4>Servicios del turno</h4>
          <p class="muted">Seleccioná los servicios y ajustá los importes según corresponda.</p>
        </header>
        <div class="form-grid form-grid--compact">
          <div class="form-row">
            <label for="t-srv-buscar">Servicio (nombre)</label>
            <div class="ac-wrap">
              <input id="t-srv-buscar" placeholder="Ej: Botox" autocomplete="off">
              <div id="t-srv-sug" class="suggest ac-list" style="display:none"></div>
            </div>
            <input id="t-servicio-id" type="hidden">
            <div id="t-srv-chosen" class="muted"></div>
          </div>
          <div class="form-row">
            <label for="t-item-precio">Precio</label>
            <input id="t-item-precio" type="number" step="0.01" placeholder="Precio">
          </div>
          <div class="form-row">
            <label for="t-item-cant">Cant.</label>
            <input id="t-item-cant" type="number" step="0.01" value="1" min="1">
          </div>
          <div class="form-row">
            <label for="t-item-desc">Desc.</label>
            <input id="t-item-desc" type="number" step="0.01" value="0" min="0">
          </div>
          <div class="form-row form-row--actions">
            <label class="sr-only" for="t-item-add">Agregar servicio</label>
            <button id="t-item-add" class="btn btn-secondary" type="button">Agregar</button>
          </div>
        </div>

        <div class="table-scroll">
          <table class="table">
            <thead>
              <tr><th>Servicio</th><th>Precio</th><th>Cant.</th><th>Desc.</th><th>Subtotal</th><th></th></tr>
            </thead>
            <tbody id="t-items"></tbody>
            <tfoot>
              <tr>
                <td colspan="4" class="text-right"><b>Total:</b></td>
                <td id="t-total" class="text-right">$0.00</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div class="form-actions">
          <button id="t-crear" class="btn btn-primary" type="button">Guardar</button>
        </div>
        <div id="t-msg" class="form-feedback muted"></div>
      </section>

      <section class="card turnos-card">
        <header class="card-header">
          <h3>Turnos programados</h3>
          <p class="card-subtitle">Revisa los turnos según el filtro seleccionado.</p>
        </header>
        <div class="table-scroll">
          <table class="table">
            <thead>
              <tr><th>ID</th><th>Paciente</th><th>Servicios</th><th>Profesional</th><th>Fecha/Hora</th><th>Estado</th><th>Acciones</th></tr>
            </thead>
            <tbody id="t-tbody"></tbody>
          </table>
        </div>
      </section>

      <!-- Modal detalle turno -->
      <div id="turno-modal-backdrop" class="modal-backdrop"></div>
      <div id="turno-modal" class="modal">
        <div class="modal-card">
          <div class="modal-header"><strong id="turno-modal-title">Detalles del turno</strong></div>
          <div class="modal-body" id="turno-modal-body"></div>
          <div class="modal-footer"><button id="turno-modal-close" type="button" class="btn">Cerrar</button></div>
        </div>
      </div>

      <!-- Modal Cancelar / Reprogramar -->
      <div id="cr-backdrop" class="modal-backdrop"></div>
      <div id="cr-modal" class="modal">
        <div class="modal-card">
          <div class="modal-header"><strong>Cancelar / Reprogramar turno</strong></div>
          <div class="modal-body">
            <div class="tab-switch">
              <button id="cr-tab-cancelar" type="button" class="btn tab-btn tab-btn--active">Cancelar</button>
              <button id="cr-tab-reprogramar" type="button" class="btn tab-btn">Reprogramar</button>
            </div>
            <div id="cr-pane-cancelar" class="tab-pane">
              <p>Para cancelar, escribí <b>CANCELAR</b> y opcionalmente indicá un motivo.</p>
              <input id="cr-cancelar-texto" placeholder="Escribí: CANCELAR" />
              <input id="cr-cancelar-motivo" placeholder="Motivo (opcional)" />
            </div>
            <div id="cr-pane-reprogramar" class="tab-pane hidden">
              <label for="cr-reprog-fecha">Nueva fecha/hora</label>
              <input id="cr-reprog-fecha" type="datetime-local" />
              <div class="muted">Estado post-reprogramación:</div>
              <select id="cr-reprog-estado">
                <option value="pendiente">Pendiente</option>
                <option value="confirmado">Confirmado</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button id="cr-cerrar" type="button" class="btn">Cerrar</button>
            <button id="cr-guardar" type="button" class="btn btn-primary">Aplicar</button>
          </div>
        </div>
      </div>
    `;

    // ====== refs ======
    const tbody = document.getElementById("t-tbody");
    const selEstado = document.getElementById("t-estado");
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

    // =========================
    // Autocompletes
    // =========================
    let pacTimer = null,
      proTimer = null,
      srvTimer = null;
    const openList = (el) => (el.style.display = "block");
    const closeList = (el) => {
      el.style.display = "none";
      el.innerHTML = "";
    };

    // Paciente
    pacBuscar.addEventListener("input", () => {
      clearTimeout(pacTimer);
      const q = pacBuscar.value.trim();
      if (!q) {
        closeList(pacSug);
        return;
      }
      pacTimer = setTimeout(async () => {
        try {
          const r = await buscarPacientes(q);
          pacSug.innerHTML = sugTpl(r, "pac");
          openList(pacSug);
        } catch {
          closeList(pacSug);
        }
      }, 220);
    });
    pacBuscar.addEventListener("focus", () => {
      if (pacSug.innerHTML) openList(pacSug);
    });
    pacBuscar.addEventListener("blur", () => setTimeout(() => closeList(pacSug), 120));
    pacSug.addEventListener("mousedown", (e) => {
      const d = e.target.closest(".sug");
      if (!d) return;
      pacId.value = d.dataset.id;
      pacChosen.textContent = d.dataset.label || "";
      pacBuscar.value = d.dataset.label || "";
    });

    // Profesional
    proBuscar.addEventListener("input", () => {
      clearTimeout(proTimer);
      const q = proBuscar.value.trim();
      if (!q) {
        closeList(proSug);
        return;
      }
      proTimer = setTimeout(async () => {
        try {
          const r = await buscarProfes(q);
          proSug.innerHTML = sugTpl(r, "pro");
          openList(proSug);
        } catch {
          closeList(proSug);
        }
      }, 220);
    });
    proBuscar.addEventListener("focus", () => {
      if (proSug.innerHTML) openList(proSug);
    });
    proBuscar.addEventListener("blur", () => setTimeout(() => closeList(proSug), 120));
    proSug.addEventListener("mousedown", (e) => {
      const d = e.target.closest(".sug");
      if (!d) return;
      proId.value = d.dataset.id;
      proChosen.textContent = d.dataset.label || "";
      proBuscar.value = d.dataset.label || "";
    });

    // Servicios del turno
    srvBuscar.addEventListener("input", () => {
      clearTimeout(srvTimer);
      const q = srvBuscar.value.trim();
      if (!q) {
        closeList(srvSug);
        return;
      }
      srvTimer = setTimeout(async () => {
        try {
          const r = await buscarServicios(q);
          srvSug.innerHTML = sugTpl(r, "srv");
          openList(srvSug);
        } catch {
          closeList(srvSug);
        }
      }, 220);
    });
    srvBuscar.addEventListener("focus", () => {
      if (srvSug.innerHTML) openList(srvSug);
    });
    srvBuscar.addEventListener("blur", () => setTimeout(() => closeList(srvSug), 120));
    srvSug.addEventListener("mousedown", (e) => {
      const d = e.target.closest(".sug");
      if (!d) return;
      srvId.value = d.dataset.id;
      srvChosen.textContent = d.dataset.label || "";
      srvBuscar.value = d.dataset.label || "";
      // Si el servicio trae precio, autocompletar
      const p = Number(d.dataset.precio || 0);
      if (p > 0 && !iPrecio.value) iPrecio.value = p;
    });

    // Agregar servicio al listado del turno (en el formulario de alta)
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
      // limpiar campos
      srvId.value = "";
      srvBuscar.value = "";
      srvChosen.textContent = "";
      iPrecio.value = "";
      iCant.value = "1";
      iDesc.value = "0";

      renderItemsTable(items, itemsBody, totalEl);
      // rebind borrar
      itemsBody.querySelectorAll(".t-item-del").forEach((btn) =>
        btn.addEventListener("click", (e) => {
          const i = Number(e.currentTarget.dataset.i);
          items.splice(i, 1);
          renderItemsTable(items, itemsBody, totalEl);
          bindDelButtons();
        })
      );
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
        pacId.value = "";
        pacBuscar.value = "";
        pacChosen.textContent = "";
        proId.value = "";
        proBuscar.value = "";
        proChosen.textContent = "";
        items = [];
        renderItemsTable(items, itemsBody, totalEl);
        // refrescar listado
        await cargarListado();
        setTimeout(() => (msg.textContent = ""), 2000);
      } catch (e) {
        msg.textContent = `Error: ${e.message || e}`;
        setTimeout(() => (msg.textContent = ""), 2800);
      }
    });

    // Filtro por estado
    selEstado.addEventListener("change", cargarListado);

    // Primera carga
    cargarListado();

    // =========================
    // Modales básicos (detalle y cancelar/reprogramar)
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
        this.box.style.display = "block";
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
      const activeClass = "tab-btn--active";
      if (p === "cancelar") {
        a.classList.add(activeClass);
        b.classList.remove(activeClass);
        pc.classList.remove("hidden");
        pr.classList.add("hidden");
      } else {
        a.classList.remove(activeClass);
        b.classList.add(activeClass);
        pc.classList.add("hidden");
        pr.classList.remove("hidden");
      }
    }

    let crTurnoId = null;
    function openCR(id) {
      crTurnoId = id;
      switchCR("cancelar");
      document.getElementById("cr-backdrop").style.display = "block";
      document.getElementById("cr-modal").style.display = "block";
    }
    function closeCR() {
      crTurnoId = null;
      document.getElementById("cr-backdrop").style.display = "none";
      document.getElementById("cr-modal").style.display = "none";
    }
    function onGuardarCR() {
      return async () => {
        if (!crTurnoId) return;
        // detectar pane activo
        const paneCancelarVisible = !document.getElementById("cr-pane-cancelar").classList.contains("hidden");
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
    // Listado
    // =========================
    async function cargarListado() {
      tbody.innerHTML = `<tr><td colspan="7" class="muted">Cargando…</td></tr>`;
      try {
        const estado = selEstado.value || "";
        const data = await apiList(estado);
        if (!data.length) {
          tbody.innerHTML = `<tr><td colspan="7" class="muted">Sin turnos</td></tr>`;
          return;
        }
        const rows = data
          .map((t) => {
            const serviciosStr =
              (t.items && t.items.length
                ? t.items.map((it) => `${it.servicio_nombre || "-"} x${it.cantidad || 1}`).join(", ")
                : t.servicio_nombre || "-") || "-";
            const proStr = t.profesional_nombre || "-";
            const fechaStr = (t.fecha_hora || "").replace("T", " ").slice(0, 16);
            const estadoStr = (t.estado || "").toUpperCase();

            // Acciones: Detalle, Cancelar/Reprogramar, Atender + Cobrar
            return `<tr>
              <td>${t.id}</td>
              <td>${t.paciente_nombre || "-"}<br><small class="muted">${t.paciente_documento || ""}</small></td>
              <td>${serviciosStr}</td>
              <td>${proStr}</td>
              <td>${fechaStr}</td>
              <td>${estadoStr}</td>
              <td class="table-actions">
                <button class="btn btn-light t-detalle" data-id="${t.id}">Detalle</button>
                <button class="btn t-cr" data-id="${t.id}">Cancelar/Reprogramar</button>
                <button class="btn btn-primary btn-cobrar" data-turno-id="${t.id}">Atender + Cobrar</button>
              </td>
            </tr>`;
          })
          .join("");
        tbody.innerHTML = rows;
      } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7">Error cargando turnos: ${e.message || e}</td></tr>`;
      }
    }

    // =========================
    // Listeners delegados (filas)
    // =========================
    document.body.addEventListener("click", async (e) => {
      // Detalle
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
              : `<div class="muted">Sin items (legacy: servicio_id=${t.servicio_id || "-"})</div>`;
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
          modal.open(`Turno #${t.id}`, html);
        } catch (err) {
          alert(err.message || err);
        }
        return;
      }

      // Cancelar/Reprogramar
      const btnCR = e.target.closest(".t-cr");
      if (btnCR) {
        const id = Number(btnCR.dataset.id);
        openCR(id);
        return;
      }

      // ★ Atender + Cobrar → redirige al POS con turno_id (no cambia estado ni consume insumos aquí)
      const btnCobrar = e.target.closest(".btn-cobrar");
      if (btnCobrar) {
        const tid = btnCobrar.dataset.turnoId || btnCobrar.getAttribute("data-turno-id");
        if (!tid) return;
        location.hash = `#/caja?turno_id=${encodeURIComponent(tid)}&registrar_insumos=1`;
        return;
      }
    });
  }

  // API pública
  return { render };
})();
