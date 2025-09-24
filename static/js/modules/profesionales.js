window.ProfesionalesModule = (function(){
  async function list(q=""){
    const res = await API.request("/api/profesionales"+(q?`?q=${encodeURIComponent(q)}`:""));
    return res.data;
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

  function readForm(){
    return {
      dni: document.getElementById("pro-dni").value.trim(),
      nombres: document.getElementById("pro-nombres").value.trim(),
      apellidos: document.getElementById("pro-apellidos").value.trim(),
      especialidad: document.getElementById("pro-esp").value.trim(),
      matricula: document.getElementById("pro-mat").value.trim() || null,
      // opcional: activo
      activo: document.getElementById("pro-activo") ? document.getElementById("pro-activo").checked : undefined,
    };
  }
  function fillForm(p){
    document.getElementById("pro-dni").value = p.dni || "";
    document.getElementById("pro-nombres").value = p.nombres || "";
    document.getElementById("pro-apellidos").value = p.apellidos || "";
    document.getElementById("pro-esp").value = p.especialidad || "";
    document.getElementById("pro-mat").value = p.matricula || "";
    if (document.getElementById("pro-activo")) {
      document.getElementById("pro-activo").checked = (p.activo !== false);
    }
  }
  function resetForm(){
    fillForm({}); editId = null;
    const btn = document.getElementById("pro-guardar");
    btn.textContent = "Guardar";
    document.getElementById("pro-cancel").classList.add("hidden");
  }

  function render(){
    routeTitle.textContent = "Profesionales";
    routeContent.innerHTML = `
      <section class="card">
        <header class="card-header">
          <h3>Buscar profesionales</h3>
          <p class="card-subtitle">Filtrá la nómina por DNI, nombre o especialidad.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row">
            <label for="pro-buscar">Buscar</label>
            <input id="pro-buscar" placeholder="Nombre, apellido o DNI">
          </div>
        </div>
      </section>
      <section class="card">
        <header class="card-header">
          <h3>Ficha del profesional</h3>
          <p class="card-subtitle">Completá la información principal del profesional.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="pro-dni">DNI</label><input id="pro-dni"></div>
          <div class="form-row"><label for="pro-nombres">Nombres</label><input id="pro-nombres"></div>
          <div class="form-row"><label for="pro-apellidos">Apellidos</label><input id="pro-apellidos"></div>
        </div>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="pro-esp">Especialidad</label><input id="pro-esp"></div>
          <div class="form-row"><label for="pro-mat">Matrícula</label><input id="pro-mat"></div>
          <!-- opcional visibilidad -->
          <!-- <div class="form-row"><label for="pro-activo">Activo</label><input id="pro-activo" type="checkbox" checked></div> -->
        </div>
        <div class="form-actions">
          <button id="pro-guardar" class="btn btn-primary" type="button">Guardar</button>
          <button id="pro-cancel" class="btn btn-secondary hidden" type="button">Cancelar edición</button>
        </div>
        <div id="pro-msg" class="form-feedback muted"></div>
      </section>
      <section class="card">
        <header class="card-header">
          <h3>Profesionales registrados</h3>
          <p class="card-subtitle">Revisá los datos cargados y gestioná acciones rápidas.</p>
        </header>
        <div class="table-scroll">
          <table class="table table--compact">
            <thead><tr><th>DNI</th><th>Nombre</th><th>Especialidad</th><th>Matrícula</th><th>Acciones</th></tr></thead>
            <tbody id="pro-tbody"></tbody>
          </table>
        </div>
      </section>
    `;

    const buscar = document.getElementById("pro-buscar");
    const tbody  = document.getElementById("pro-tbody");
    const msg    = document.getElementById("pro-msg");
    const btnGuardar = document.getElementById("pro-guardar");
    const btnCancel  = document.getElementById("pro-cancel");

    async function refresh(){
      const rows = await list(buscar.value);
      if (!rows.length){
        tbody.innerHTML = `<tr><td colspan="5" class="muted">Sin profesionales registrados.</td></tr>`;
        return;
      }
      tbody.innerHTML = rows.map(r=>`
        <tr>
          <td>${r.dni||""}</td>
          <td>${[r.nombres||"", r.apellidos||""].filter(Boolean).join(" ")}</td>
          <td>${r.especialidad||""}</td>
          <td>${r.matricula||""}</td>
          <td class="table-actions table-actions--compact">
            <button class="btn btn-light" type="button" data-editar="${r.id}">Editar</button>
            <button class="btn btn-danger" type="button" data-eliminar="${r.id}">Eliminar</button>
          </td>
        </tr>
      `).join("");
    }

    buscar.addEventListener("input", refresh);

    btnGuardar.addEventListener("click", async ()=>{
      const data = readForm();
      msg.textContent = ""; btnGuardar.disabled = true;
      try{
        if (!data.dni || !data.nombres || !data.apellidos){
          msg.textContent = "DNI, Nombres y Apellidos son obligatorios.";
          return;
        }
        if (editId){
          await update(editId, data);
          msg.textContent = "Profesional actualizado.";
        } else {
          await create(data);
          msg.textContent = "Profesional guardado.";
        }
        resetForm(); await refresh();
      }catch(e){
        msg.textContent = e.message || "No se pudo guardar";
      }finally{
        btnGuardar.disabled = false;
      }
    });

    btnCancel.addEventListener("click", ()=> resetForm());

    tbody.addEventListener("click", async (e)=>{
      const t = e.target;
      if (t.dataset.eliminar){
        if (confirm("¿Eliminar profesional?")){
          try { await remove(t.dataset.eliminar); await refresh(); }
          catch(e){ alert(e.message); }
        }
      }
      if (t.dataset.editar){
        try{
          const p = await detail(t.dataset.editar);
          editId = p.id; fillForm(p);
          btnGuardar.textContent = "Actualizar";
          btnCancel.classList.remove("hidden");
        }catch(e){ alert(e.message); }
      }
    });

    refresh();
  }

  return { render };
})();
