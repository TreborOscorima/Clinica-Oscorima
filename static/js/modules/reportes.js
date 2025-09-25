window.ReportesModule = (function(){
  async function req(path){
    return API.request(path);
  }

  function render(){
    routeTitle.textContent = "Reportes";
    routeContent.innerHTML = `
      <section class="card">
        <header class="card-header">
          <h3>Atenciones</h3>
          <p class="card-subtitle">Analizá la cantidad de consultas según rango y agrupación.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="ra-desde">Desde</label><input id="ra-desde" type="date"></div>
          <div class="form-row"><label for="ra-hasta">Hasta</label><input id="ra-hasta" type="date"></div>
          <div class="form-row"><label for="ra-group">Agrupar por</label>
            <select id="ra-group">
              <option value="dia">Día</option>
              <option value="profesional">Profesional</option>
              <option value="servicio">Servicio</option>
            </select>
          </div>
        </div>
        <div class="form-actions">
          <button id="ra-run" class="btn btn-primary" type="button">Calcular</button>
          <a id="ra-csv" class="btn btn-secondary" target="_blank" rel="noopener">Exportar CSV</a>
        </div>
        <div class="table-scroll">
          <table class="table table--compact"><thead><tr><th>Clave</th><th>Cantidad</th></tr></thead><tbody id="ra-tbody"></tbody></table>
        </div>
      </section>

      <section class="card">
        <header class="card-header">
          <h3>Facturación / Caja</h3>
          <p class="card-subtitle">Consultá montos cobrados y egresos agrupados por método, fecha o responsable.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="rf-desde">Desde</label><input id="rf-desde" type="datetime-local"></div>
          <div class="form-row"><label for="rf-hasta">Hasta</label><input id="rf-hasta" type="datetime-local"></div>
          <div class="form-row"><label for="rf-group">Agrupar por</label>
            <select id="rf-group">
              <option value="metodo">Método de pago</option>
              <option value="dia">Día</option>
              <option value="servicio">Servicio</option>
              <option value="profesional">Profesional</option>
            </select>
          </div>
          <div class="form-row"><label for="rf-tipo">Tipo</label>
            <select id="rf-tipo">
              <option value="">Ambos</option>
              <option value="ingreso">Ingreso</option>
              <option value="egreso">Egreso</option>
            </select>
          </div>
        </div>
        <div class="form-actions">
          <button id="rf-run" class="btn btn-primary" type="button">Calcular</button>
          <a id="rf-csv" class="btn btn-secondary" target="_blank" rel="noopener">Exportar CSV</a>
        </div>
        <div id="rf-total" class="muted"></div>
        <div class="table-scroll">
          <table class="table table--compact"><thead><tr><th>Clave</th><th>Monto</th></tr></thead><tbody id="rf-tbody"></tbody></table>
        </div>
      </section>

      <section class="card">
        <header class="card-header">
          <h3>Stock bajo mínimo</h3>
          <p class="card-subtitle">Detectá productos críticos y exportá el listado para seguimiento.</p>
        </header>
        <div class="form-actions">
          <button id="rs-run" class="btn btn-primary" type="button">Ver</button>
          <a id="rs-csv" class="btn btn-secondary" target="_blank" rel="noopener">Exportar CSV</a>
        </div>
        <div class="table-scroll">
          <table class="table table--compact"><thead><tr><th>SKU</th><th>Nombre</th><th>Categoría</th><th>Stock</th><th>Mín</th><th>Unidad</th></tr></thead><tbody id="rs-tbody"></tbody></table>
        </div>
      </section>

      <section class="card">
        <header class="card-header">
          <h3>Pacientes</h3>
          <p class="card-subtitle">Identificá nuevos ingresos, pacientes frecuentes e inactivos.</p>
        </header>
        <div class="form-grid form-grid--split">
          <div class="form-row"><label for="rp-desde">Desde</label><input id="rp-desde" type="date"></div>
          <div class="form-row"><label for="rp-hasta">Hasta</label><input id="rp-hasta" type="date"></div>
          <div class="form-row"><label for="rp-n">Frecuentes (≥ N turnos)</label><input id="rp-n" type="number" value="2"></div>
          <div class="form-row"><label for="rp-dias">Inactivos (días)</label><input id="rp-dias" type="number" value="60"></div>
        </div>
        <div class="form-actions">
          <button id="rp-run" class="btn btn-primary" type="button">Calcular</button>
        </div>
        <div id="rp-out" class="muted"></div>
      </section>
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
