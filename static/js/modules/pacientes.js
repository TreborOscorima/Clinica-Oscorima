window.PacientesModule = (function(){
  async function list({ q = "", page = 1, perPage = 10 } = {}){
    const params = new URLSearchParams();
    if (q) params.append("q", q);
    if (page) params.append("page", String(page));
    if (perPage) params.append("per_page", String(perPage));
    const res = await API.request("/api/pacientes" + (params.toString() ? `?${params}` : ""));
    return res;
  }
  async function create(data){
    return API.request("/api/pacientes", {method:"POST", body: JSON.stringify(data)});
  }
  async function update(id, data){
    return API.request(`/api/pacientes/${id}`, {method:"PUT", body: JSON.stringify(data)});
  }
  async function remove(id){
    return API.request(`/api/pacientes/${id}`, {method:"DELETE"});
  }
  async function detail(id){
    return API.request(`/api/pacientes/${id}`);
  }

  let editId = null;

  const escHtml = (str) => String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const formatCell = (value) => {
    const str = String(value ?? "").trim();
    return str ? escHtml(str) : '<span class="muted">-</span>';
  };


  let historialModal;

  function ensureHistorialModal(){
    if (historialModal) return historialModal;
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-hidden", "true");

    const modal = document.createElement("div");
    modal.className = "modal";
    modal.innerHTML = `
      <div class="modal__header">
        <h3 class="modal__title">Historial clinico</h3>
      </div>
      <div class="modal__body"></div>
      <div class="modal__footer">
        <button type="button" class="button button--ghost modal-close">Cerrar</button>
      </div>
    `;
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    const titleEl = modal.querySelector(".modal__title");
    const bodyEl = modal.querySelector(".modal__body");

    const close = () => {
      overlay.classList.remove("is-visible");
      overlay.setAttribute("aria-hidden", "true");
    };
    const open = () => {
      overlay.classList.add("is-visible");
      overlay.setAttribute("aria-hidden", "false");
    };
    const setContent = (html) => {
      bodyEl.innerHTML = html;
    };

    modal.querySelectorAll(".modal-close").forEach((btn) => btn.addEventListener("click", close));
    overlay.addEventListener("click", (evt) => {
      if (evt.target === overlay) close();
    });
    document.addEventListener("keydown", (evt) => {
      if (evt.key === "Escape" && overlay.classList.contains("is-visible")) close();
    });

    historialModal = { overlay, modal, titleEl, bodyEl, open, close, setContent };
    return historialModal;
  }

  function formatFechaLabel(fecha){
    if (!fecha) return "--/--/----";
    const str = String(fecha);
    const parts = str.split("-");
    if (parts.length === 3){
      const [y, m, d] = parts;
      if (y.length === 4){
        return `${(d || "").padStart(2, "0")}/${(m || "").padStart(2, "0")}/${y}`;
      }
    }
    return str;
  }

  function formatHoraLabel(hora){
    if (!hora) return "--:--";
    const str = String(hora);
    return str.length > 5 ? str.slice(0, 5) : str;
  }

  function buildTimeline(items){
    if (!Array.isArray(items) || !items.length){
      return '<div class="timeline timeline--empty"><div class="timeline-empty muted">Sin atenciones registradas.</div></div>';
    }
    const blocks = items.map((item) => {
      const fecha = escHtml(formatFechaLabel(item?.fecha));
      const hora = escHtml(formatHoraLabel(item?.hora));
      const servicio = escHtml(item?.servicio || "Servicio sin nombre");
      const profesionalHtml = item?.profesional
        ? `<p class="timeline-content__subtitle">${escHtml(item.profesional)}</p>`
        : '<p class="timeline-content__subtitle muted">Sin profesional asignado</p>';
      let detalleHtml;
      if (item?.detalle){
        const sanitized = escHtml(String(item.detalle)).replace(/\r?\n/g, "<br>");
        detalleHtml = `<p class="timeline-content__detail">${sanitized}</p>`;
      } else {
        detalleHtml = '<p class="timeline-content__detail muted">Sin detalle</p>';
      }
      return `<div class="timeline-item">
        <div class="timeline-date">
          <span class="timeline-date__day">${fecha}</span>
          <span class="timeline-date__time">${hora}</span>
        </div>
        <div class="timeline-content">
          <h4 class="timeline-content__title">${servicio}</h4>
          ${profesionalHtml}
          ${detalleHtml}
        </div>
      </div>`;
    });
    return `<div class="timeline">${blocks.join("")}</div>`;
  }


  function readForm(){
    return {
      nombre: document.getElementById("pac-nombre").value.trim(),
      documento: document.getElementById("pac-documento").value.trim(),
      email: document.getElementById("pac-email").value.trim() || null,
      telefono: document.getElementById("pac-telefono").value.trim() || null,
      direccion: document.getElementById("pac-direccion").value.trim() || null,
      fecha_nacimiento: document.getElementById("pac-fnac").value || null,
      contacto_emergencia: document.getElementById("pac-emerg").value.trim() || null,
    };
  }
  function fillForm(p){
    document.getElementById("pac-nombre").value = p.nombre || "";
    document.getElementById("pac-documento").value = p.documento || "";
    document.getElementById("pac-email").value = p.email || "";
    document.getElementById("pac-telefono").value = p.telefono || "";
    document.getElementById("pac-direccion").value = p.direccion || "";
    document.getElementById("pac-fnac").value = (p.fecha_nacimiento || "").slice(0,10);
    document.getElementById("pac-emerg").value = p.contacto_emergencia || "";
  }
  function resetForm(){
    fillForm({}); editId = null;
    const guardarBtn = document.getElementById("pac-guardar");
    const cancelarBtn = document.getElementById("pac-cancelar");
    const titleEl = document.getElementById("pac-form-title");
    if (guardarBtn) guardarBtn.textContent = "Guardar";
    if (cancelarBtn) cancelarBtn.style.display = "none";
    if (titleEl) titleEl.textContent = "Registrar paciente";
  }

  function render(){
    routeTitle.textContent = "Pacientes";
    routeContent.innerHTML = `
      <div class="page-shell pacientes-page split-layout">
        <aside class="split-layout__sidebar">
          <article class="card form-card pacientes-card">
            <header class="card__header">
              <h2 class="card__title" id="pac-form-title">Registrar paciente</h2>
            </header>

            <div class="card__body">
              <div class="form-grid pacientes-form-grid" style="grid-template-columns: 1fr;">
                <div class="form-field">
                  <label class="form-field__label" for="pac-nombre">Nombre</label>
                  <input id="pac-nombre" class="input" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="pac-documento">Documento</label>
                  <input id="pac-documento" class="input" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="pac-email">Email</label>
                  <input id="pac-email" class="input" type="email" autocomplete="off">
                </div>
                <div class="form-grid form-grid--two">
                    <div class="form-field">
                    <label class="form-field__label" for="pac-telefono">Teléfono</label>
                    <input id="pac-telefono" class="input" autocomplete="off">
                    </div>
                    <div class="form-field">
                    <label class="form-field__label" for="pac-fnac">F. Nacimiento</label>
                    <input id="pac-fnac" class="input" type="date">
                    </div>
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="pac-direccion">Dirección</label>
                  <input id="pac-direccion" class="input" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="pac-emerg">Contacto emergencia</label>
                  <input id="pac-emerg" class="input" autocomplete="off">
                </div>
              </div>
              <div class="pacientes-form-actions" style="margin-top: var(--space-4);">
                <div id="pac-msg" class="form-feedback"></div>
                <div class="pacientes-buttons" style="display: flex; gap: 8px;">
                  <button id="pac-cancelar" type="button" class="button button--ghost" style="width: 100%;">Cancelar</button>
                  <button id="pac-guardar" type="button" class="button button--primary" style="width: 100%;">Guardar</button>
                </div>
              </div>
            </div>
          </article>
        </aside>

        <main class="split-layout__main">
          <article class="card list-card pacientes-list-card" style="height: 100%;">
            <header class="card__header">
              <h2 class="card__title">Listado general</h2>
            </header>
            <div class="card__body" style="flex: 1; display: flex; flex-direction: column;">
              <div class="card-section pacientes-search">
                <div class="card-section__body">
                  <div class="form-field" style="max-width: 320px;">
                    <label class="form-field__label" for="pac-buscar">Buscar</label>
                    <input id="pac-buscar" class="input" placeholder="Nombre o documento" autocomplete="off">
                  </div>
                </div>
              </div>
              
              <div class="table-shell pacientes-table grow">
                <table class="table table--full" id="pac-tabla">
                  <thead>
                    <tr><th>Nombre</th><th>Documento</th><th>Email</th><th>Teléfono</th><th>Edad</th><th>Acciones</th></tr>
                  </thead>
                  <tbody id="pac-tbody"></tbody>
                </table>
              </div>
              <div id="pac-pagination" class="table-pagination"></div>
            </div>
          </article>
        </main>
      </div>
    `;

    const tbody  = document.getElementById("pac-tbody");
    const buscar = document.getElementById("pac-buscar");
    const msg    = document.getElementById("pac-msg");
    const btnGuardar  = document.getElementById("pac-guardar");
    const btnCancelar = document.getElementById("pac-cancelar");
    const paginationEl = document.getElementById("pac-pagination");
    const formTitle = document.getElementById("pac-form-title");

    const state = { currentPage: 1, perPage: 10, totalPages: 1, totalItems: 0, rows: [] };

    const clearMessage = () => {
      msg.textContent = "";
      msg.classList.remove("form-feedback--success", "form-feedback--error");
    };
    const showMessage = (text = "", type = "info") => {
      msg.textContent = text;
      msg.classList.remove("form-feedback--success", "form-feedback--error");
      if (!text) return;
      if (type === "success") msg.classList.add("form-feedback--success");
      if (type === "error") msg.classList.add("form-feedback--error");
    };
    const debounce = (fn, delay = 280) => {
      let timer;
      return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
      };
    };

    function renderPagination(){
      const total = state.totalItems;
      if (!total){
        paginationEl.innerHTML = `<div class="table-pagination__controls"><span class="table-pagination__info">Sin pacientes registrados</span></div>`;
        return;
      }
      const start = (state.currentPage - 1) * state.perPage + 1;
      const end = Math.min(state.currentPage * state.perPage, total);
      const info = `<span class="table-pagination__info">Mostrando ${start}-${end} de ${total}</span>`;
      if (state.totalPages <= 1){
        paginationEl.innerHTML = `<div class="table-pagination__controls">${info}</div>`;
        return;
      }
      const win = 5;
      let first = Math.max(1, state.currentPage - Math.floor(win / 2));
      let last = Math.min(state.totalPages, first + win - 1);
      if (last - first + 1 < win) first = Math.max(1, last - win + 1);
      const numBtns = [];
      for (let p = first; p <= last; p++){
        numBtns.push(`<button type="button" class="button ${p === state.currentPage ? "is-current" : ""}" data-page="${p}">${p}</button>`);
      }
      paginationEl.innerHTML = `
        <div class="table-pagination__controls">
          ${info}
          <div class="table-pagination__buttons">
            <button type="button" class="button" data-page="first" ${state.currentPage === 1 ? "disabled" : ""}>&laquo;</button>
            <button type="button" class="button" data-page="prev" ${state.currentPage === 1 ? "disabled" : ""}>&lsaquo;</button>
            ${numBtns.join("")}
            <button type="button" class="button" data-page="next" ${state.currentPage === state.totalPages ? "disabled" : ""}>&rsaquo;</button>
            <button type="button" class="button" data-page="last" ${state.currentPage === state.totalPages ? "disabled" : ""}>&raquo;</button>
          </div>
        </div>
      `;
    }

    function renderTable(){
      if (!state.rows.length){
        tbody.innerHTML = `<tr><td colspan="6" class="table__empty muted">Sin pacientes</td></tr>`;
        renderPagination();
        return;
      }
      tbody.innerHTML = state.rows.map((r) => `
        <tr>
          <td>${formatCell(r.nombre)}</td>
          <td>${formatCell(r.documento)}</td>
          <td>${formatCell(r.email)}</td>
          <td>${formatCell(r.telefono)}</td>
          <td>${formatCell(r.edad)}</td>
          <td class="table__actions">
            <button type="button" class="button button--ghost" data-historial="${r.id}">Historial</button>
            <button type="button" class="button button--ghost" data-editar="${r.id}">Editar</button>
            <button type="button" class="button button--danger" data-eliminar="${r.id}">Borrar</button>
          </td>
        </tr>
      `).join("");
      renderPagination();
    }

    async function loadPacientes(page = state.currentPage){
      const query = buscar.value.trim();
      tbody.innerHTML = `<tr><td colspan="6" class="table__empty muted">Cargando...</td></tr>`;
      try {
        const resp = await list({ q: query, page, perPage: state.perPage });
        const data = Array.isArray(resp?.data) ? resp.data : Array.isArray(resp) ? resp : [];
        const perPageNumber = Number(resp?.per_page);
        if (Number.isFinite(perPageNumber) && perPageNumber > 0){
          state.perPage = perPageNumber;
        }
        const totalNumber = Number(resp?.total);
        state.totalItems = Number.isFinite(totalNumber) ? totalNumber : data.length;
        const pagesNumber = Number(resp?.pages);
        state.totalPages = Number.isFinite(pagesNumber) && pagesNumber > 0 ? pagesNumber : Math.max(1, Math.ceil((state.totalItems || 0) / state.perPage));
        const respPage = Number(resp?.page);
        state.currentPage = Number.isFinite(respPage) && respPage > 0 ? respPage : page;
        if (state.totalPages && state.currentPage > state.totalPages){
          return loadPacientes(state.totalPages);
        }
        state.rows = data;
        renderTable();
      } catch (error){
        tbody.innerHTML = `<tr><td colspan="6" class="table__empty">Error: ${escHtml(error.message || error)}</td></tr>`;
        paginationEl.innerHTML = "";
      }
    }

    buscar.addEventListener("input", debounce(() => loadPacientes(1)));
    buscar.addEventListener("keydown", (e) => {
      if (e.key === "Enter"){
        e.preventDefault();
        loadPacientes(1);
      }
    });

    btnGuardar.addEventListener("click", async () => {
      const data = readForm();
      clearMessage();
      if (!data.nombre || !data.documento){
        showMessage("Nombre y Documento son obligatorios.", "error");
        return;
      }
      btnGuardar.disabled = true;
      try {
        if (editId){
          await update(editId, data);
          showMessage("Paciente actualizado.", "success");
          resetForm();
          await loadPacientes(state.currentPage);
        } else {
          await create(data);
          resetForm();
          showMessage("Paciente guardado.", "success");
          await loadPacientes(1);
        }
        setTimeout(clearMessage, 2500);
      } catch (e){
        showMessage(e.message || "No se pudo guardar", "error");
      } finally {
        btnGuardar.disabled = false;
      }
    });

    btnCancelar.addEventListener("click", () => {
      resetForm();
      clearMessage();
    });

    tbody.addEventListener("click", async (e) => {
      const historialBtn = e.target.closest("button[data-historial]");
      if (historialBtn){
        const id = historialBtn.dataset.historial;
        if (!id) return;
        const rowData = state.rows.find((row) => String(row.id) === String(id));
        const modal = ensureHistorialModal();
        const nombrePaciente = rowData && rowData.nombre ? String(rowData.nombre).trim() : "";
        const baseTitle = nombrePaciente ? `Historial de ${nombrePaciente}` : "Historial clinico";
        modal.titleEl.textContent = baseTitle;
        modal.setContent('<div class="timeline timeline--loading"><div class="timeline-empty muted">Cargando historial...</div></div>');
        modal.open();
        try {
          const resp = await API.request(`/api/pacientes/${id}/historial`);
          const registros = Array.isArray(resp?.historial) ? resp.historial : [];
          const total = Number(resp?.total);
          const totalValid = Number.isFinite(total) ? total : registros.length;
          modal.titleEl.textContent = totalValid ? `${baseTitle} (${totalValid})` : baseTitle;
          modal.setContent(buildTimeline(registros));
        } catch (error){
          const message = escHtml(error?.message || error || "Error desconocido");
          modal.setContent(`<div class="timeline timeline--empty"><div class="timeline-empty error">Error al cargar historial: ${message}</div></div>`);
        }
        return;
      }

      const btn = e.target.closest("button[data-editar], button[data-eliminar]");
      if (!btn) return;
      const id = btn.dataset.editar || btn.dataset.eliminar;
      if (!id) return;
      if (btn.dataset.eliminar){
        if (!confirm("Borrar paciente?")) return;
        try {
          await remove(id);
          showMessage("Paciente eliminado.", "success");
          const targetPage = state.rows.length > 1 ? state.currentPage : Math.max(1, state.currentPage - 1);
          await loadPacientes(targetPage);
          setTimeout(clearMessage, 2500);
        } catch (error){
          showMessage(error.message || "No se pudo eliminar", "error");
        }
        return;
      }
      try {
        const paciente = await detail(id);
        editId = paciente.id;
        fillForm(paciente);
        btnGuardar.textContent = "Actualizar";
        btnCancelar.style.display = "";
        formTitle.textContent = "Editar paciente";
        clearMessage();
      } catch (error){
        showMessage(error.message || "No se pudo cargar el paciente", "error");
      }
    });
    paginationEl.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-page]");
      if (!btn || btn.disabled) return;
      const action = btn.getAttribute("data-page");
      let target = state.currentPage;
      if (action === "first") target = 1;
      else if (action === "prev") target = Math.max(1, state.currentPage - 1);
      else if (action === "next") target = Math.min(state.totalPages, state.currentPage + 1);
      else if (action === "last") target = state.totalPages;
      else target = Number(action) || 1;
      if (target === state.currentPage) return;
      loadPacientes(target);
    });

    resetForm();
    loadPacientes();
  }

  return { render };
})();
