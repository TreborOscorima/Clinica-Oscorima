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
      <div class="page-shell animate-in">
        <div class="module-layout">

          <!-- Formulario -->
          <aside class="module-panel">
            <div class="panel-header">
              <h2 class="panel-title" id="pac-form-title">Registrar paciente</h2>
            </div>
            <div class="panel-body">
              <div class="field-group">
                <label class="field-label" for="pac-nombre">Nombre completo</label>
                <input id="pac-nombre" class="input" autocomplete="off" placeholder="Ej: María García">
              </div>
              <div class="field-group">
                <label class="field-label" for="pac-documento">Documento (DNI / CE)</label>
                <input id="pac-documento" class="input" autocomplete="off" placeholder="Ej: 12345678">
              </div>
              <div class="field-group">
                <label class="field-label" for="pac-email">Email</label>
                <input id="pac-email" class="input" type="email" autocomplete="off" placeholder="correo@ejemplo.com">
              </div>
              <div class="field-row">
                <div class="field-group">
                  <label class="field-label" for="pac-telefono">Teléfono</label>
                  <input id="pac-telefono" class="input" autocomplete="off" placeholder="999 000 000">
                </div>
                <div class="field-group">
                  <label class="field-label" for="pac-fnac">F. Nacimiento</label>
                  <input id="pac-fnac" class="input" type="date">
                </div>
              </div>
              <div class="field-group">
                <label class="field-label" for="pac-direccion">Dirección</label>
                <input id="pac-direccion" class="input" autocomplete="off" placeholder="Av. Principal 123">
              </div>
              <div class="field-group">
                <label class="field-label" for="pac-emerg">Contacto de emergencia</label>
                <input id="pac-emerg" class="input" autocomplete="off" placeholder="Nombre y teléfono">
              </div>
              <p id="pac-msg" class="field-feedback--err" style="min-height:18px"></p>
              <div class="field-row" style="margin-top:4px">
                <button id="pac-cancelar" type="button" class="button button--ghost button--full" style="display:none">Cancelar</button>
                <button id="pac-guardar" type="button" class="button button--primary button--full">Guardar</button>
              </div>
            </div>
          </aside>

          <!-- Listado -->
          <section class="module-panel">
            <div class="panel-header">
              <h2 class="panel-title">Pacientes</h2>
              <input id="pac-buscar" class="input input--sm" type="search" placeholder="Buscar por nombre o documento…" autocomplete="off" style="width:220px">
            </div>
            <div class="panel-body panel-body--table">
              <table class="table">
                <thead>
                  <tr><th>Nombre</th><th>Documento</th><th>Email</th><th>Teléfono</th><th>Edad</th><th></th></tr>
                </thead>
                <tbody id="pac-tbody"></tbody>
              </table>
              <div id="pac-pagination" class="pagination-bar" style="display:none"></div>
            </div>
          </section>

        </div>
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
      msg.className = "field-feedback--err";
    };
    const showMessage = (text = "", type = "info") => {
      msg.className = type === "success" ? "field-feedback--ok" : "field-feedback--err";
      msg.textContent = text;
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
      paginationEl.style.display = (state.totalPages > 1) ? "" : "none";
      if (!total || state.totalPages <= 1) return;
      const start = (state.currentPage - 1) * state.perPage + 1;
      const end = Math.min(state.currentPage * state.perPage, total);
      paginationEl.innerHTML = `
        <span class="pagination-info">Mostrando ${start}–${end} de ${total}</span>
        <div class="pagination-btns">
          <button type="button" class="button button--ghost button--sm" data-page="prev" ${state.currentPage === 1 ? "disabled" : ""}>Anterior</button>
          <button type="button" class="button button--ghost button--sm" data-page="next" ${state.currentPage === state.totalPages ? "disabled" : ""}>Siguiente</button>
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
          <td style="white-space:nowrap">
            <button type="button" class="button button--ghost button--sm" data-historial="${r.id}">Historial</button>
            <button type="button" class="button button--ghost button--sm" data-editar="${r.id}">Editar</button>
            <button type="button" class="button button--danger button--sm" data-eliminar="${r.id}">Borrar</button>
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
      if (action === "prev") target = Math.max(1, state.currentPage - 1);
      else if (action === "next") target = Math.min(state.totalPages, state.currentPage + 1);
      else target = Number(action) || 1;
      if (target === state.currentPage) return;
      loadPacientes(target);
    });

    resetForm();
    loadPacientes();
  }

  return { render };
})();
