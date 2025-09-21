window.ReportesModule = (function(){
  async function req(path){
    return API.request(path);
  }

  function render(){
    routeTitle.textContent = "Reportes";
    routeContent.innerHTML = `
      <div class="card">
        <h3>Atenciones</h3>
        <div class="row">
          <div class="col"><label>Desde</label><input id="ra-desde" type="date"></div>
          <div class="col"><label>Hasta</label><input id="ra-hasta" type="date"></div>
          <div class="col"><label>Agrupar por</label>
            <select id="ra-group">
              <option value="dia">Día</option>
              <option value="profesional">Profesional</option>
              <option value="servicio">Servicio</option>
            </select>
          </div>
          <div class="col"><label>&nbsp;</label><button id="ra-run">Calcular</button></div>
          <div class="col"><label>&nbsp;</label><a id="ra-csv" class="button" target="_blank">Exportar CSV</a></div>
        </div>
        <table class="table"><thead><tr><th>Clave</th><th>Cantidad</th></tr></thead><tbody id="ra-tbody"></tbody></table>
      </div>

      <div class="card">
        <h3>Facturación / Caja</h3>
        <div class="row">
          <div class="col"><label>Desde</label><input id="rf-desde" type="datetime-local"></div>
          <div class="col"><label>Hasta</label><input id="rf-hasta" type="datetime-local"></div>
          <div class="col"><label>Agrupar por</label>
            <select id="rf-group">
              <option value="metodo">Método de pago</option>
              <option value="dia">Día</option>
              <option value="servicio">Servicio</option>
              <option value="profesional">Profesional</option>
            </select>
          </div>
          <div class="col"><label>Tipo</label>
            <select id="rf-tipo">
              <option value="">Ambos</option>
              <option value="ingreso">Ingreso</option>
              <option value="egreso">Egreso</option>
            </select>
          </div>
          <div class="col"><label>&nbsp;</label><button id="rf-run">Calcular</button></div>
          <div class="col"><label>&nbsp;</label><a id="rf-csv" class="button" target="_blank">Exportar CSV</a></div>
        </div>
        <div id="rf-total" class="muted"></div>
        <table class="table"><thead><tr><th>Clave</th><th>Monto</th></tr></thead><tbody id="rf-tbody"></tbody></table>
      </div>

      <div class="card">
        <h3>Stock bajo mínimo</h3>
        <div class="row">
          <div class="col"><label>&nbsp;</label><button id="rs-run">Ver</button></div>
          <div class="col"><label>&nbsp;</label><a id="rs-csv" class="button" target="_blank">Exportar CSV</a></div>
        </div>
        <table class="table"><thead><tr><th>SKU</th><th>Nombre</th><th>Categoría</th><th>Stock</th><th>Mín</th><th>Unidad</th></tr></thead><tbody id="rs-tbody"></tbody></table>
      </div>

      <div class="card">
        <h3>Pacientes</h3>
        <div class="row">
          <div class="col"><label>Desde</label><input id="rp-desde" type="date"></div>
          <div class="col"><label>Hasta</label><input id="rp-hasta" type="date"></div>
          <div class="col"><label>Frecuentes (≥ N turnos)</label><input id="rp-n" type="number" value="2"></div>
          <div class="col"><label>Inactivos (días)</label><input id="rp-dias" type="number" value="60"></div>
          <div class="col"><label>&nbsp;</label><button id="rp-run">Calcular</button></div>
        </div>
        <div id="rp-out" class="muted"></div>
      </div>
    `;

    // Atenciones
    const atBody = document.getElementById("ra-tbody");
    document.getElementById("ra-run").addEventListener("click", async ()=>{
      const d = document.getElementById("ra-desde").value;
      const h = document.getElementById("ra-hasta").value;
      const g = document.getElementById("ra-group").value;
      const q = new URLSearchParams({desde:d||"", hasta:h||"", group_by:g});
      const r = await req(`/api/reportes/atenciones?${q}`);
      atBody.innerHTML = r.data.map(x=>`<tr><td>${x.clave}</td><td>${x.cantidad}</td></tr>`).join("");
      document.getElementById("ra-csv").href = `/api/reportes/exportar/csv?tipo=atenciones&${q}`;
    });

    // Facturación
    const facBody = document.getElementById("rf-tbody");
    document.getElementById("rf-run").addEventListener("click", async ()=>{
      const d = document.getElementById("rf-desde").value;
      const h = document.getElementById("rf-hasta").value;
      const g = document.getElementById("rf-group").value;
      const t = document.getElementById("rf-tipo").value;
      const q = new URLSearchParams({desde:d||"", hasta:h||"", group_by:g, tipo:t||""});
      const r = await req(`/api/reportes/facturacion?${q}`);
      facBody.innerHTML = r.data.map(x=>`<tr><td>${x.clave}</td><td>$${Number(x.monto||0).toFixed(2)}</td></tr>`).join("");
      document.getElementById("rf-total").textContent = `TOTAL: $${Number(r.total||0).toFixed(2)}`;
      document.getElementById("rf-csv").href = `/api/reportes/exportar/csv?tipo=facturacion&${q}`;
    });

    // Stock bajo
    const sBody = document.getElementById("rs-tbody");
    document.getElementById("rs-run").addEventListener("click", async ()=>{
      const r = await req("/api/reportes/stock_bajo");
      sBody.innerHTML = r.data.map(x=>`
        <tr><td>${x.sku||""}</td><td>${x.nombre}</td><td>${x.categoria||""}</td>
        <td>${x.stock_actual}</td><td>${x.stock_minimo}</td><td>${x.unidad||""}</td></tr>`).join("");
      document.getElementById("rs-csv").href = `/api/reportes/exportar/csv?tipo=stock_bajo`;
    });

    // Pacientes
    document.getElementById("rp-run").addEventListener("click", async ()=>{
      const d = document.getElementById("rp-desde").value;
      const h = document.getElementById("rp-hasta").value;
      const n = document.getElementById("rp-n").value;
      const dias = document.getElementById("rp-dias").value;
      const q = new URLSearchParams({desde:d||"", hasta:h||"", frecuentes_n:n, inactivos_dias:dias});
      const r = await req(`/api/reportes/pacientes?${q}`);
      document.getElementById("rp-out").textContent = `Nuevos: ${r.nuevos} | Frecuentes (≥${n}): ${r.frecuentes} | Inactivos (≥${dias} días): ${r.inactivos}`;
    });
  }

  return { render };
})();
