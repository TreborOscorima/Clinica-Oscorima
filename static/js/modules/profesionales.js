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
    document.getElementById("pro-cancel").style.display = "none";
  }

  function render(){
    routeTitle.textContent = "Profesionales";
    routeContent.innerHTML = `
      <div class="card">
        <div class="row">
          <div class="col">
            <label>Buscar</label>
            <input id="pro-buscar" placeholder="Nombre, apellido o DNI">
          </div>
        </div>
      </div>
      <div class="card">
        <h3>Profesional</h3>
        <div class="row">
          <div class="col"><label>DNI</label><input id="pro-dni"></div>
          <div class="col"><label>Nombres</label><input id="pro-nombres"></div>
          <div class="col"><label>Apellidos</label><input id="pro-apellidos"></div>
        </div>
        <div class="row">
          <div class="col"><label>Especialidad</label><input id="pro-esp"></div>
          <div class="col"><label>Matrícula</label><input id="pro-mat"></div>
          <!-- opcional visibilidad -->
          <!-- <div class="col"><label>Activo</label><input id="pro-activo" type="checkbox" checked></div> -->
        </div>
        <button id="pro-guardar">Guardar</button>
        <button id="pro-cancel" class="secondary" style="display:none">Cancelar edición</button>
        <div id="pro-msg" class="muted"></div>
      </div>
      <div class="card">
        <table class="table">
          <thead><tr><th>DNI</th><th>Nombre</th><th>Especialidad</th><th>Matrícula</th><th>Acciones</th></tr></thead>
          <tbody id="pro-tbody"></tbody>
        </table>
      </div>
    `;

    const buscar = document.getElementById("pro-buscar");
    const tbody  = document.getElementById("pro-tbody");
    const msg    = document.getElementById("pro-msg");
    const btnGuardar = document.getElementById("pro-guardar");
    const btnCancel  = document.getElementById("pro-cancel");

    async function refresh(){
      const rows = await list(buscar.value);
      tbody.innerHTML = rows.map(r=>`
        <tr>
          <td>${r.dni||""}</td>
          <td>${r.nombres||""} ${r.apellidos||""}</td>
          <td>${r.especialidad||""}</td>
          <td>${r.matricula||""}</td>
          <td class="actions">
            <button data-editar="${r.id}">Editar</button>
            <button data-eliminar="${r.id}">Borrar</button>
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
          btnCancel.style.display = "";
        }catch(e){ alert(e.message); }
      }
    });

    refresh();
  }

  return { render };
})();
