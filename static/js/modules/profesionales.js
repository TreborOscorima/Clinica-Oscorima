window.ProfesionalesModule = (function(){
  async function list({ q = "", page = 1, perPage = 10 } = {}){
    const params = new URLSearchParams();
    if (q) params.append("q", q);
    if (page) params.append("page", String(page));
    if (perPage) params.append("per_page", String(perPage));
    const res = await API.request("/api/profesionales" + (params.toString() ? `?${params}` : ""));
    return res;
  }
  async function create(data){
    return API.request("/api/profesionales", {method:"POST", body: JSON.stringify(data)});
  }
  async function update(id, data){
    return API.request(`/api/profesionales/${id}`, {method:"PUT", body: JSON.stringify(data)});
  }
  async function remove(id){
    return API.request(`/api/profesionales/${id}`, {method:"DELETE"});
  }
  async function detail(id){
    return API.request(`/api/profesionales/${id}`);
  }

  let editId = null;

  const escHtml = (str) => String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const formatCell = (value) => {
    const str = String(value ?? "").trim();
    return str ? escHtml(str) : '<span class="muted">-</span>';
  };

  function readForm(){
    return {
      dni: document.getElementById("pro-dni").value.trim(),
      nombres: document.getElementById("pro-nombres").value.trim(),
      apellidos: document.getElementById("pro-apellidos").value.trim(),
      especialidad: document.getElementById("pro-esp").value.trim(),
      matricula: document.getElementById("pro-mat").value.trim() || null,
    };
  }
  function fillForm(p){
    document.getElementById("pro-dni").value = p.dni || "";
    document.getElementById("pro-nombres").value = p.nombres || "";
    document.getElementById("pro-apellidos").value = p.apellidos || "";
    document.getElementById("pro-esp").value = p.especialidad || "";
    document.getElementById("pro-mat").value = p.matricula || "";
  }
  function resetForm(){
    fillForm({});
    editId = null;
    const guardarBtn = document.getElementById("pro-guardar");
    const cancelarBtn = document.getElementById("pro-cancel");
    const titleEl = document.getElementById("pro-form-title");
    if (guardarBtn) guardarBtn.textContent = "Guardar";
    if (cancelarBtn) cancelarBtn.style.display = "none";
    if (titleEl) titleEl.textContent = "Registrar profesional";
  }

  function render(){
    routeTitle.textContent = "Profesionales";
    routeContent.innerHTML = `
      <div class="page-shell profesionales-page split-layout">
        <aside class="split-layout__sidebar">
          <article class="card form-card profesionales-card">
            <header class="card__header">
              <h2 class="card__title" id="pro-form-title">Registrar profesional</h2>
            </header>
            <div class="card__body">
              <div class="form-grid profesionales-form-grid" style="grid-template-columns: 1fr;">
                <div class="form-field">
                  <label class="form-field__label" for="pro-dni">DNI</label>
                  <input id="pro-dni" class="input" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="pro-nombres">Nombres</label>
                  <input id="pro-nombres" class="input" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="pro-apellidos">Apellidos</label>
                  <input id="pro-apellidos" class="input" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="pro-esp">Especialidad</label>
                  <input id="pro-esp" class="input" autocomplete="off">
                </div>
                <div class="form-field">
                  <label class="form-field__label" for="pro-mat">Matrícula</label>
                  <input id="pro-mat" class="input" autocomplete="off">
                </div>
              </div>
              <div class="profesionales-form-actions" style="margin-top: var(--space-4);">
                <div id="pro-msg" class="form-feedback"></div>
                <div class="profesionales-buttons" style="display: flex; gap: 8px;">
                  <button id="pro-cancel" type="button" class="button button--ghost" style="width: 100%;">Cancelar</button>
                  <button id="pro-guardar" type="button" class="button button--primary" style="width: 100%;">Guardar</button>
                </div>
              </div>
            </div>
          </article>
        </aside>

        <main class="split-layout__main">
          <article class="card list-card profesionales-list-card" style="height: 100%;">
            <header class="card__header">
              <h2 class="card__title">Catálogo de Profesionales</h2>
            </header>
            <div class="card__body" style="flex: 1; display: flex; flex-direction: column;">
              <div class="card-section profesionales-search">
                <div class="card-section__body">
                  <div class="form-field" style="max-width: 320px;">
                    <label class="form-field__label" for="pro-buscar">Buscar</label>
                    <input id="pro-buscar" class="input" placeholder="Nombre, apellido o DNI" autocomplete="off">
                  </div>
                </div>
              </div>

              <div class="table-shell profesionales-table grow">
                <table class="table table--full" id="pro-tabla">
                  <thead>
                    <tr><th>DNI</th><th>Nombre</th><th>Especialidad</th><th>Matrícula</th><th>Acciones</th></tr>
                  </thead>
                  <tbody id="pro-tbody"></tbody>
                </table>
              </div>
              <div id="pro-pagination" class="table-pagination"></div>
            </div>
          </article>
        </main>
      </div>
    `;

    const buscar = document.getElementById("pro-buscar");
    const tbody  = document.getElementById("pro-tbody");
    const msg    = document.getElementById("pro-msg");
    const btnGuardar = document.getElementById("pro-guardar");
    const btnCancel  = document.getElementById("pro-cancel");
    const paginationEl = document.getElementById("pro-pagination");
    const formTitle = document.getElementById("pro-form-title");

    const state = { currentPage: 1, perPage: 10, totalPages: 1, totalItems: 0, rows: [] };
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
        paginationEl.innerHTML = `<div class="table-pagination__controls"><span class="table-pagination__info">Sin profesionales registrados</span></div>`;
        return;
      }
      const start = (state.currentPage - 1) * state.perPage + 1;
      const end = Math.min(state.currentPage * state.perPage, state.totalItems);
      const info = `<span class="table-pagination__info">Mostrando ${start}-${end} de ${state.totalItems}</span>`;
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
        tbody.innerHTML = `<tr><td colspan="5" class="table__empty muted">Sin profesionales</td></tr>`;
        renderPagination();
        return;
      }
      tbody.innerHTML = state.rows.map((r) => {
        const nombreCompleto = `${r.nombres || ""} ${r.apellidos || ""}`.trim();
        return `
          <tr>
            <td>${formatCell(r.dni)}</td>
            <td>${formatCell(nombreCompleto)}</td>
            <td>${formatCell(r.especialidad)}</td>
            <td>${formatCell(r.matricula)}</td>
            <td class="table__actions">
              <button type="button" class="button button--ghost" data-editar="${r.id}">Editar</button>
              <button type="button" class="button button--danger" data-eliminar="${r.id}">Borrar</button>
            </td>
          </tr>
        `;
      }).join("");
      renderPagination();
    }

    async function loadProfesionales(page = state.currentPage){
      const query = buscar.value.trim();
      tbody.innerHTML = `<tr><td colspan="5" class="table__empty muted">Cargando...</td></tr>`;
      try {
        const resp = await list({ q: query, page, perPage: state.perPage });
        const data = Array.isArray(resp?.data) ? resp.data : Array.isArray(resp) ? resp : [];
        const perPageNumber = Number(resp?.per_page);
        if (Number.isFinite(perPageNumber) && perPageNumber > 0) state.perPage = perPageNumber;
        const totalNumber = Number(resp?.total);
        state.totalItems = Number.isFinite(totalNumber) ? totalNumber : data.length;
        const pagesNumber = Number(resp?.pages);
        state.totalPages = Number.isFinite(pagesNumber) && pagesNumber > 0 ? pagesNumber : Math.max(1, Math.ceil((state.totalItems || 0) / state.perPage));
        const respPage = Number(resp?.page);
        state.currentPage = Number.isFinite(respPage) && respPage > 0 ? respPage : page;
        if (state.totalPages && state.currentPage > state.totalPages){
          return loadProfesionales(state.totalPages);
        }
        state.rows = data;
        renderTable();
      } catch (error){
        tbody.innerHTML = `<tr><td colspan="5" class="table__empty">Error: ${escHtml(error.message || error)}</td></tr>`;
        paginationEl.innerHTML = "";
      }
    }

    buscar.addEventListener("input", debounce(() => loadProfesionales(1)));
    buscar.addEventListener("keydown", (e) => {
      if (e.key === "Enter"){
        e.preventDefault();
        loadProfesionales(1);
      }
    });

    btnGuardar.addEventListener("click", async () => {
      const data = readForm();
      clearMessage();
      if (!data.dni || !data.nombres || !data.apellidos){
        showMessage("DNI, Nombres y Apellidos son obligatorios.", "error");
        return;
      }
      btnGuardar.disabled = true;
      try {
        if (editId){
          await update(editId, data);
          showMessage("Profesional actualizado.", "success");
          resetForm();
          await loadProfesionales(state.currentPage);
        } else {
          await create(data);
          resetForm();
          showMessage("Profesional guardado.", "success");
          await loadProfesionales(1);
        }
        setTimeout(clearMessage, 2500);
      } catch (error){
        showMessage(error.message || "No se pudo guardar", "error");
      } finally {
        btnGuardar.disabled = false;
      }
    });

    btnCancel.addEventListener("click", () => {
      resetForm();
      clearMessage();
    });

    tbody.addEventListener("click", async (e) => {
      const btn = e.target.closest("button[data-editar], button[data-eliminar]");
      if (!btn) return;
      const id = btn.dataset.editar || btn.dataset.eliminar;
      if (!id) return;
      if (btn.dataset.eliminar){
        if (!confirm("¿Eliminar profesional?")) return;
        try {
          await remove(id);
          showMessage("Profesional eliminado.", "success");
          const targetPage = state.rows.length > 1 ? state.currentPage : Math.max(1, state.currentPage - 1);
          await loadProfesionales(targetPage);
          setTimeout(clearMessage, 2500);
        } catch (error){
          showMessage(error.message || "No se pudo eliminar", "error");
        }
        return;
      }
      try {
        const profesional = await detail(id);
        editId = profesional.id;
        fillForm(profesional);
        btnGuardar.textContent = "Actualizar";
        btnCancel.style.display = "";
        formTitle.textContent = "Editar profesional";
        clearMessage();
      } catch (error){
        showMessage(error.message || "No se pudo cargar el profesional", "error");
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
      loadProfesionales(target);
    });

    resetForm();
    loadProfesionales();
  }

  return { render };
})();
