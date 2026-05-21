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
    routeTitle.textContent = "Servicios";
    routeContent.innerHTML = `
      <div class="page-shell animate-in">
        <div class="module-layout">

          <!-- Formulario -->
          <aside class="module-panel">
            <div class="panel-header">
              <h2 class="panel-title" id="srv-form-title">Registrar servicio</h2>
            </div>
            <div class="panel-body">
              <div class="field-group">
                <label class="field-label" for="srv-nombre">Nombre del servicio</label>
                <input id="srv-nombre" class="input" autocomplete="off" placeholder="Ej: Limpieza facial">
              </div>
              <div class="field-row">
                <div class="field-group">
                  <label class="field-label" for="srv-precio">Precio (S/)</label>
                  <input id="srv-precio" class="input" type="number" step="0.01" min="0" placeholder="0.00">
                </div>
                <div class="field-group">
                  <label class="field-label" for="srv-duracion">Duración (min)</label>
                  <input id="srv-duracion" class="input" type="number" step="5" min="0" value="30">
                </div>
              </div>
              <div class="field-group">
                <label class="field-label" for="srv-desc">Descripción</label>
                <input id="srv-desc" class="input" autocomplete="off" placeholder="Descripción breve">
              </div>
              <div class="field-group">
                <label class="field-label" for="srv-insumos">Insumos</label>
                <input id="srv-insumos" class="input" placeholder="ej: crema X, aguja 32G" autocomplete="off">
              </div>
              <div class="field-group">
                <label class="field-label" for="srv-protocolo">Protocolo</label>
                <input id="srv-protocolo" class="input" placeholder="Pasos del procedimiento…" autocomplete="off">
              </div>
              <p id="srv-msg" class="field-feedback--err" style="min-height:18px"></p>
              <div class="field-row" style="margin-top:4px">
                <button id="srv-cancelar" type="button" class="button button--ghost button--full" style="display:none">Cancelar</button>
                <button id="srv-guardar" type="button" class="button button--primary button--full">Guardar</button>
              </div>
            </div>
          </aside>

          <!-- Listado -->
          <section class="module-panel">
            <div class="panel-header">
              <h2 class="panel-title">Catálogo</h2>
              <input id="srv-buscar" class="input input--sm" type="search" placeholder="Buscar servicio…" autocomplete="off" style="width:200px">
            </div>
            <div class="panel-body panel-body--table">
              <table class="table">
                <thead>
                  <tr><th>Nombre</th><th>Precio</th><th>Duración</th><th>Descripción</th><th></th></tr>
                </thead>
                <tbody id="srv-tbody"></tbody>
              </table>
              <div id="srv-pagination" class="pagination-bar" style="display:none"></div>
            </div>
          </section>

        </div>
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
    const clearMessage = () => { msg.textContent = ""; msg.className = "field-feedback--err"; };
    const showMessage = (text = "", type = "info") => {
      msg.className = type === "success" ? "field-feedback--ok" : "field-feedback--err";
      msg.textContent = text;
    };

    function renderPagination(){
      paginationEl.style.display = (state.totalPages > 1) ? "" : "none";
      if (state.totalPages <= 1) return;
      const start = (state.currentPage - 1) * state.perPage + 1;
      const end = Math.min(state.currentPage * state.perPage, state.totalItems);
      paginationEl.innerHTML = `
        <span class="pagination-info">Mostrando ${start}–${end} de ${state.totalItems}</span>
        <div class="pagination-btns">
          <button type="button" class="button button--ghost button--sm" data-page="prev" ${state.currentPage === 1 ? "disabled" : ""}>Anterior</button>
          <button type="button" class="button button--ghost button--sm" data-page="next" ${state.currentPage === state.totalPages ? "disabled" : ""}>Siguiente</button>
        </div>
      `;
    }

    function renderTable(){
      if (!state.rows.length){
        tbody.innerHTML = `<tr><td colspan="5" class="muted" style="padding:14px">Sin servicios registrados</td></tr>`;
        renderPagination();
        return;
      }
      tbody.innerHTML = state.rows
        .slice((state.currentPage - 1) * state.perPage, state.currentPage * state.perPage)
        .map((r) => `
          <tr>
            <td>${formatCell(r.nombre)}</td>
            <td>S/ ${Number(r.precio || 0).toFixed(2)}</td>
            <td>${formatCell(r.duracion_min ? `${r.duracion_min} min` : "")}</td>
            <td>${formatCell(r.descripcion)}</td>
            <td style="white-space:nowrap">
              <button type="button" class="button button--ghost button--sm" data-editar="${r.id}">Editar</button>
              <button type="button" class="button button--danger button--sm" data-eliminar="${r.id}">Borrar</button>
            </td>
          </tr>
        `).join("");
      renderPagination();
    }

    async function loadServicios(page = state.currentPage){
      const query = buscar.value.trim();
      tbody.innerHTML = `<tr><td colspan="5" class="muted" style="padding:14px">Cargando…</td></tr>`;
      try {
        const rows = await list({ q: query });
        state.rows = Array.isArray(rows) ? rows : [];
        state.totalItems = state.rows.length;
        state.totalPages = Math.max(1, Math.ceil(state.totalItems / state.perPage));
        state.currentPage = Math.min(Math.max(1, page), state.totalPages);
        renderTable();
      } catch (error){
        tbody.innerHTML = `<tr><td colspan="5" class="muted" style="padding:14px">Error: ${escHtml(error.message || error)}</td></tr>`;
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
      if (action === "prev") target = Math.max(1, state.currentPage - 1);
      else if (action === "next") target = Math.min(state.totalPages, state.currentPage + 1);
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
