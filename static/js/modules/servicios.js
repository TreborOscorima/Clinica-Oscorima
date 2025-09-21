window.ServiciosModule = (function(){
  async function list(q=""){
    const res = await API.request("/api/servicios"+(q?`?q=${encodeURIComponent(q)}`:""));
    return res.data;
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

  function readForm(){
    return {
      nombre: document.getElementById("srv-nombre").value.trim(),
      precio: parseFloat(document.getElementById("srv-precio").value || "0"),
      duracion_min: parseInt(document.getElementById("srv-duracion").value || "30"),
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
    document.getElementById("srv-guardar").textContent = "Guardar";
    document.getElementById("srv-cancelar").style.display = "none";
  }

  function render(){
    routeTitle.textContent = "Servicios / Tratamientos";
    routeContent.innerHTML = `
      <div class="card">
        <div class="row">
          <div class="col">
            <label>Buscar</label>
            <input id="srv-buscar" placeholder="Nombre de servicio">
          </div>
        </div>
      </div>
      <div class="card">
        <h3>Servicio</h3>
        <div class="row">
          <div class="col"><label>Nombre</label><input id="srv-nombre"></div>
          <div class="col"><label>Precio</label><input id="srv-precio" type="number" step="0.01"></div>
          <div class="col"><label>Duración (min)</label><input id="srv-duracion" type="number" step="5" value="30"></div>
        </div>
        <div class="row">
          <div class="col"><label>Descripción</label><input id="srv-desc"></div>
          <div class="col"><label>Insumos (texto)</label><input id="srv-insumos" placeholder="ej: crema X, aguja 32G"></div>
          <div class="col"><label>Protocolo</label><input id="srv-protocolo" placeholder="pasos..."></div>
        </div>
        <button id="srv-guardar">Guardar</button>
        <button id="srv-cancelar" class="secondary" style="display:none">Cancelar edición</button>
        <div id="srv-msg" class="muted"></div>
      </div>
      <div class="card">
        <table class="table">
          <thead>
            <tr><th>Nombre</th><th>Precio</th><th>Duración</th><th>Descripción</th><th>Insumos</th><th>Protocolo</th><th>Acciones</th></tr>
          </thead>
          <tbody id="srv-tbody"></tbody>
        </table>
      </div>
    `;

    const buscar = document.getElementById("srv-buscar");
    const tbody = document.getElementById("srv-tbody");
    const msg = document.getElementById("srv-msg");
    const btnGuardar = document.getElementById("srv-guardar");
    const btnCancelar = document.getElementById("srv-cancelar");

    async function refresh(){
      const rows = await list(buscar.value);
      tbody.innerHTML = rows.map(r=>`
        <tr>
          <td>${r.nombre||""}</td>
          <td>$${Number(r.precio||0).toFixed(2)}</td>
          <td>${r.duracion_min||""} min</td>
          <td>${r.descripcion||""}</td>
          <td>${r.insumos||""}</td>
          <td>${r.protocolo||""}</td>
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
      if (!data.nombre){ msg.textContent = "El nombre es obligatorio."; return; }
      msg.textContent = ""; btnGuardar.disabled = true;
      try{
        if (editId){
          await update(editId, data);
          msg.textContent = "Servicio actualizado.";
        } else {
          await create(data);
          msg.textContent = "Servicio guardado.";
        }
        resetForm(); refresh();
      }catch(e){ msg.textContent = e.message || "No se pudo guardar"; }
      finally{ btnGuardar.disabled = false; }
    });

    btnCancelar.addEventListener("click", ()=> resetForm());

    tbody.addEventListener("click", async (e)=>{
      const t = e.target;
      if (t.dataset.eliminar){
        if (confirm("¿Eliminar servicio?")){
          try{ await remove(t.dataset.eliminar); refresh(); }catch(e){ alert(e.message); }
        }
      }
      if (t.dataset.editar){
        try{
          const s = await detail(t.dataset.editar);
          editId = s.id; fillForm(s);
          btnGuardar.textContent = "Actualizar";
          btnCancelar.style.display = "";
        }catch(e){ alert(e.message); }
      }
    });

    refresh();
  }

  return { render };
})();
