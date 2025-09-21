window.PacientesModule = (function(){
  async function list(q=""){
    const res = await API.request("/api/pacientes"+(q?`?q=${encodeURIComponent(q)}`:""));
    return res.data;
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
    document.getElementById("pac-fnac").value = (p.fecha_nacimiento||"").slice(0,10);
    document.getElementById("pac-emerg").value = p.contacto_emergencia || "";
  }
  function resetForm(){
    fillForm({}); editId = null;
    document.getElementById("pac-guardar").textContent = "Guardar";
    document.getElementById("pac-cancelar").style.display = "none";
  }

  function render(){
    routeTitle.textContent = "Pacientes";
    routeContent.innerHTML = `
      <div class="card">
        <div class="row">
          <div class="col">
            <label>Buscar</label>
            <input id="pac-buscar" placeholder="Nombre o documento">
          </div>
          <div class="col"></div>
        </div>
      </div>
      <div class="card" style="margin-top:10px">
        <h3 id="pac-form-title">Paciente</h3>
        <div class="row">
          <div class="col"><label>Nombre</label><input id="pac-nombre"></div>
          <div class="col"><label>Documento</label><input id="pac-documento"></div>
          <div class="col"><label>Email</label><input id="pac-email" type="email"></div>
          <div class="col"><label>Teléfono</label><input id="pac-telefono"></div>
        </div>
        <div class="row">
          <div class="col"><label>Dirección</label><input id="pac-direccion"></div>
          <div class="col"><label>Fecha nacimiento</label><input id="pac-fnac" type="date"></div>
          <div class="col"><label>Contacto emergencia</label><input id="pac-emerg"></div>
        </div>
        <button id="pac-guardar">Guardar</button>
        <button id="pac-cancelar" class="secondary" style="display:none">Cancelar edición</button>
        <div id="pac-msg" class="muted"></div>
      </div>
      <div class="card" style="margin-top:10px">
        <table class="table">
          <thead><tr><th>Nombre</th><th>Doc</th><th>Email</th><th>Tel</th><th>Edad</th><th>Acciones</th></tr></thead>
          <tbody id="pac-tbody"></tbody>
        </table>
      </div>
    `;

    const tbody  = document.getElementById("pac-tbody");
    const buscar = document.getElementById("pac-buscar");
    const msg    = document.getElementById("pac-msg");
    const btnGuardar  = document.getElementById("pac-guardar");
    const btnCancelar = document.getElementById("pac-cancelar");

    async function refresh(){
      const rows = await list(buscar.value);
      tbody.innerHTML = rows.map(r=>`
        <tr>
          <td>${r.nombre||""}</td>
          <td>${r.documento||""}</td>
          <td>${r.email||""}</td>
          <td>${r.telefono||""}</td>
          <td>${r.edad??""}</td>
          <td class="actions">
            <button data-editar="${r.id}">Editar</button>
            <button data-eliminar="${r.id}">Borrar</button>
          </td>
        </tr>
      `).join("");
    }

    buscar.addEventListener("input", ()=> refresh());

    btnGuardar.addEventListener("click", async ()=>{
      const data = readForm();
      msg.textContent = ""; btnGuardar.disabled = true;
      try{
        if (!data.nombre || !data.documento){
          msg.textContent = "Nombre y Documento son obligatorios.";
          return;
        }
        if (editId){
          await update(editId, data);
          msg.textContent = "Paciente actualizado.";
        } else {
          await create(data);
          msg.textContent = "Paciente guardado.";
        }
        resetForm(); await refresh();
      }catch(e){
        msg.textContent = e.message || "No se pudo guardar";
      }finally{
        btnGuardar.disabled = false;
      }
    });

    btnCancelar.addEventListener("click", ()=> resetForm());

    tbody.addEventListener("click", async (e)=>{
      const t = e.target;
      if (t.dataset.eliminar){
        if (confirm("¿Borrar paciente?")){
          try { await remove(t.dataset.eliminar); await refresh(); }
          catch(e){ alert(e.message); }
        }
      }
      if (t.dataset.editar){
        try{
          const p = await detail(t.dataset.editar);
          editId = p.id; fillForm(p);
          document.getElementById("pac-guardar").textContent = "Actualizar";
          btnCancelar.style.display = "";
        }catch(e){ alert(e.message); }
      }
    });

    refresh();
  }

  return { render };
})();
