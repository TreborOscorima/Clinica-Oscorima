window.ServiciosModule = (function(){
  async function list({ q = "" } = {}){
    const params = new URLSearchParams();
    if (q) params.append("q", q);
    const res = await API.request("/api/servicios" + (params.toString() ? `?${params}` : ""));
    return res.data || res || [];
  }
  async function create(data){
    return API.request("/api/servicios", {method:"POST", body: JSON.stringify(data)});
  }
  async function update(id, data){
    return API.request(`/api/servicios/${id}`, {method:"PUT", body: JSON.stringify(data)});
  }
  async function remove(id){
    return API.request(`/api/servicios/${id}`, {method:"DELETE"});
  }
  async function detail(id){
    return API.request(`/api/servicios/${id}`);
  }

  let editId = null;

  const escHtml = (str) => String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const formatCell = (value) => {
    const text = String(value ?? "").trim();
    return text ? escHtml(text) : '<span class="muted">-</span>';
  };

  function readForm(){
    return {
      nombre: document.getElementById("srv-nombre").value.trim(),
      precio: parseFloat(document.getElementById("srv-precio").value || "0"),
      duracion_min: parseInt(document.getElementById("srv-duracion").value || "30", 10),
      descripcion: document.getElementById("srv-desc").value.trim() || null,
      insumos: document.getElementById("srv-insumos").value.trim() || null,
      protocolo: document.getElementById("srv-protocolo").value.trim() || null,
    };
  }
  function fillForm(s){
    document.getElementById("srv-nombre").value = s.nombre || "";
    document.getElementById("srv-precio").value = s.precio ?? "";
    document.getElementById("srv-duracion").value = s.duracion_min ?? 30;
    document.getElementById("srv-desc").value = s.descripcion || "";
    document.getElementById("srv-insumos").value = s.insumos || "";
    document.getElementById("srv-protocolo").value = s.protocolo || "";
  }
  function resetForm(){
    fillForm({}); editId = null;
    const guardarBtn = document.getElementById("srv-guardar");
    const cancelarBtn = document.getElementById("srv-cancelar");
    const titleEl = document.getElementById("srv-form-title");
    if (guardarBtn) guardarBtn.textContent = "Guardar";
    if (cancelarBtn) cancelarBtn.style.display = "none";
    if (titleEl) titleEl.textContent = "Registrar servicio";
  }

  function render(){
    routeTitle.textContent = "Servicios / Tratamientos";
    routeContent.innerHTML = `
      <div class="page-shell servicios-page split-layout">
        <aside class="split-layout__sidebar">
          <article class="card form-card servicios-card">
            <header class="card__header">
              <h2 class="card__title" id="srv-form-title">Registrar servicio</h2>
            </header>
            <div class="card__body">
              <div class="form-grid servicios-form-grid" style="grid-template-columns: 1fr;">
                <div class="form-field">
                  <label class="form-field__label" for="srv-nombre">Nombre</label>
                  <input id="srv-nombre" class="input" autocomplete="off">
                </div>
                <div class="form-grid form-grid--two">
                    <div class="form-field">
                    <label class="form-field__label" for="srv-precio">Precio</label>
                    <input id="srv-precio" class="input" type="number" step="0.01" min="0">
                    </div>
                    <div class="form-field">
                    <label class="form-field__label" for="srv-duracion">Dura. (min)</label>
                    <input id="srv-duracion" class="input" type="number" step="5" min="0" value="30">
                    </div>
                </div>
                <div class="form-field form-field--full">
                  <label class="form-field__label" for="srv-desc">Descripción</label>
                  <input id="srv-desc" class="input" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="srv-insumos">Insumos</label>
                  <input id="srv-insumos" class="input" placeholder="ej: crema X, aguja 32G" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="srv-protocolo">Protocolo</label>
                  <input id="srv-protocolo" class="input" placeholder="pasos..." autocomplete="off">
                </div>
              </div>
              <div class="servicios-form-actions" style="margin-top: var(--space-4);">
                <div id="srv-msg" class="form-feedback"></div>
                <div class="servicios-buttons" style="display: flex; gap: 8px;">
                  <button id="srv-cancelar" type="button" class="button button--ghost" style="width: 100%;">Cancelar</button>
                  <button id="srv-guardar" type="button" class="button button--primary" style="width: 100%;">Guardar</button>
                </div>
              </div>
            </div>
          </article>
        </aside>

        <main class="split-layout__main">
          <article class="card list-card servicios-list-card" style="height: 100%;">
            <header class="card__header">
              <h2 class="card__title">Catálogo de servicios</h2>
            </header>
            <div class="card__body" style="flex: 1; display: flex; flex-direction: column;">
              <div class="card-section servicios-search">
                <div class="card-section__body">
                  <div class="form-field" style="max-width: 320px;">
                    <label class="form-field__label" for="srv-buscar">Buscar</label>
                    <input id="srv-buscar" class="input" placeholder="Nombre de servicio" autocomplete="off">
                  </div>
                </div>
              </div>

              <div class="table-shell servicios-table grow">
                <table class="table table--full">
                  <thead>
                    <tr><th>Nombre</th><th>Precio</th><th>Duración</th><th>Descripción</th><th>Insumos</th><th>Protocolo</th><th>Acciones</th></tr>
                  </thead>
                  <tbody id="srv-tbody"></tbody>
                </table>
              </div>
              <div id="srv-pagination" class="table-pagination"></div>
            </div>
          </article>
        </main>
      </div>
    `;

    const buscar = document.getElementById("srv-buscar");
    const tbody = document.getElementById("srv-tbody");
    const msg = document.getElementById("srv-msg");
    const btnGuardar = document.getElementById("srv-guardar");
    const btnCancelar = document.getElementById("srv-cancelar");
    const paginationEl = document.getElementById("srv-pagination");
    const formTitle = document.getElementById("srv-form-title");

    const state = { currentPage: 1, perPage: 10, rows: [], totalItems: 0, totalPages: 1 };
    const debounce = (fn, delay = 280) => {
      let timer;
      return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
      };
    };
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

    function renderPagination(){
      if (!state.totalItems){
        paginationEl.innerHTML = `<div class="table-pagination__controls"><span class="table-pagination__info">Sin servicios registrados</span></div>`;
        return;
      }
      const start = (state.currentPage - 1) * state.perPage + 1;
      const end = Math.min(state.currentPage * state.perPage, state.totalItems);
      const info = `<span class="table-pagination__info">Mostrando ${start}-${end} de ${state.totalItems}</span>`;
      if (state.totalPages <= 1){
        paginationEl.innerHTML = `<div class="table-pagination__controls">${info}</div>`;
        return;
      }
      const windowSize = 5;
      let first = Math.max(1, state.currentPage - Math.floor(windowSize / 2));
      let last = Math.min(state.totalPages, first + windowSize - 1);
      if (last - first + 1 < windowSize) first = Math.max(1, last - windowSize + 1);
      const buttons = [];
      for (let p = first; p <= last; p++){
        buttons.push(`<button type="button" class="button ${p === state.currentPage ? "is-current" : ""}" data-page="${p}">${p}</button>`);
      }
      paginationEl.innerHTML = `
        <div class="table-pagination__controls">
          ${info}
          <div class="table-pagination__buttons">
            <button type="button" class="button" data-page="first" ${state.currentPage === 1 ? "disabled" : ""}>&laquo;</button>
            <button type="button" class="button" data-page="prev" ${state.currentPage === 1 ? "disabled" : ""}>&lsaquo;</button>
            ${buttons.join("")}
            <button type="button" class="button" data-page="next" ${state.currentPage === state.totalPages ? "disabled" : ""}>&rsaquo;</button>
            <button type="button" class="button" data-page="last" ${state.currentPage === state.totalPages ? "disabled" : ""}>&raquo;</button>
          </div>
        </div>
      `;
    }

    function renderTable(){
      if (!state.rows.length){
        tbody.innerHTML = `<tr><td colspan="7" class="table__empty muted">Sin servicios</td></tr>`;
        renderPagination();
        return;
      }
      tbody.innerHTML = state.rows
        .slice((state.currentPage - 1) * state.perPage, state.currentPage * state.perPage)
        .map((r) => `
          <tr>
            <td>${formatCell(r.nombre)}</td>
            <td>${formatCell(Number(r.precio || 0).toFixed(2))}</td>
            <td>${formatCell(r.duracion_min ? `${r.duracion_min} min` : "")}</td>
            <td>${formatCell(r.descripcion)}</td>
            <td>${formatCell(r.insumos)}</td>
            <td>${formatCell(r.protocolo)}</td>
            <td class="table__actions">
              <button type="button" class="button button--ghost" data-editar="${r.id}">Editar</button>
              <button type="button" class="button button--danger" data-eliminar="${r.id}">Borrar</button>
            </td>
          </tr>
        `).join("");
      renderPagination();
    }

    async function loadServicios(page = state.currentPage){
      const query = buscar.value.trim();
      tbody.innerHTML = `<tr><td colspan="7" class="table__empty muted">Cargando...</td></tr>`;
      try {
        const rows = await list({ q: query });
        state.rows = Array.isArray(rows) ? rows : [];
        state.totalItems = state.rows.length;
        state.totalPages = Math.max(1, Math.ceil(state.totalItems / state.perPage));
        state.currentPage = Math.min(Math.max(1, page), state.totalPages);
        renderTable();
      } catch (error){
        tbody.innerHTML = `<tr><td colspan="7" class="table__empty">Error: ${escHtml(error.message || error)}</td></tr>`;
        paginationEl.innerHTML = "";
      }
    }

    buscar.addEventListener("input", debounce(() => loadServicios(1)));
    buscar.addEventListener("keydown", (e) => {
      if (e.key === "Enter"){
        e.preventDefault();
        loadServicios(1);
      }
    });

    btnGuardar.addEventListener("click", async () => {
      const data = readForm();
      clearMessage();
      if (!data.nombre){
        showMessage("El nombre es obligatorio.", "error");
        return;
      }
      btnGuardar.disabled = true;
      try {
        if (editId){
          await update(editId, data);
          showMessage("Servicio actualizado.", "success");
        } else {
          await create(data);
          showMessage("Servicio guardado.", "success");
        }
        resetForm();
        await loadServicios(editId ? state.currentPage : 1);
        setTimeout(clearMessage, 2500);
      } catch (error){
        showMessage(error.message || "No se pudo guardar", "error");
      } finally {
        btnGuardar.disabled = false;
      }
    });

    btnCancelar.addEventListener("click", () => {
      resetForm();
      clearMessage();
    });

    tbody.addEventListener("click", async (e) => {
      const btn = e.target.closest("button[data-editar], button[data-eliminar]");
      if (!btn) return;
      const id = btn.dataset.editar || btn.dataset.eliminar;
      if (!id) return;
      if (btn.dataset.eliminar){
        if (!confirm("¿Eliminar servicio?")) return;
        try {
          await remove(id);
          showMessage("Servicio eliminado.", "success");
          const targetPage = state.rows.length > 1 ? state.currentPage : Math.max(1, state.currentPage - 1);
          await loadServicios(targetPage);
          setTimeout(clearMessage, 2500);
        } catch (error){
          showMessage(error.message || "No se pudo eliminar", "error");
        }
        return;
      }
      try {
        const servicio = await detail(id);
        editId = servicio.id;
        fillForm(servicio);
        btnGuardar.textContent = "Actualizar";
        btnCancelar.style.display = "";
        formTitle.textContent = "Editar servicio";
        clearMessage();
      } catch (error){
        showMessage(error.message || "No se pudo cargar el servicio", "error");
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
      state.currentPage = target;
      renderTable();
    });

    resetForm();
    loadServicios();
  }

  return { render };
})();
